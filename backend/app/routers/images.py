from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db, SessionLocal
from app.models.scrape_task import ScrapeTask
from app.models.image_asset import ImageAsset
import os
import asyncio

router = APIRouter(prefix="/images", tags=["Images"])

@router.get("/queue", summary="Get all jobs currently in image generation or review")
def get_image_queue(db: Session = Depends(get_db)):
    jobs = db.query(ScrapeTask).filter(ScrapeTask.status.in_([
        "image_generation", 
        "image_generation_stopped",
        "image_generation_complete"
    ])).all()
    
    queue = []
    for job in jobs:
        assets = db.query(ImageAsset).filter(ImageAsset.scrape_task_id == job.id).all()
        # Group by variation group
        groups = {}
        for a in assets:
            if a.variation_group not in groups:
                groups[a.variation_group] = []
            groups[a.variation_group].append(a)

        queue.append({
            "job_id": job.id,
            "task_name": job.task_name,
            "product_name": job.product_data.get("product_identity", {}).get("product_name", job.task_name) if job.product_data else job.task_name,
            "status": job.status,
            "assets": [
                {
                    "variation_group": name,
                    "prompt": items[0].prompt_text if items else "",
                    "variations": [
                        {
                            "id": i.id,
                            "url": i.storage_path,
                            "status": i.status,
                            "asset_name": i.asset_name,
                                "metadata": {
                                    "size_kb": round(os.path.getsize(i.storage_path) / 1024, 1) if os.path.exists(i.storage_path) else 0,
                                    "type": "Lifestyle" if "lifestyle" in name.lower() else "Feature" if "feature" in name.lower() else "Banner (A+)",
                                    "ratio": "1:1",
                                    "created_on": i.created_at.strftime("%b %d, %Y %H:%M") if i.created_at else "Unknown"
                                }
                        } for i in items
                    ]
                } for name, items in groups.items()
            ]
        })
    return queue

@router.post("/{asset_id}/regenerate", summary="Regenerate an image variation")
def regenerate_asset(asset_id: str, prompt_text: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    local_asset = db.query(ImageAsset).filter(ImageAsset.id == asset_id).first()
    if not local_asset:
        raise HTTPException(status_code=404, detail="Asset not found")
        
    job = db.query(ScrapeTask).filter(ScrapeTask.id == local_asset.scrape_task_id).first()
    sku = "unknown"
    product = {}
    if job and job.product_data:
        product = job.product_data
        sku = product.get("product_identity", {}).get("sku", "unknown")
        
    from app.tasks.tools.image_generator import _safe_folder_name
    safe_sku = _safe_folder_name(sku)
    IMAGE_OUTPUT_DIR = os.getenv("IMAGE_OUTPUT_DIR", "output/images")
    folder = os.path.join(IMAGE_OUTPUT_DIR, safe_sku)
    os.makedirs(folder, exist_ok=True)
    
    # Count existing regenerated items for this group to append number
    regen_count = db.query(ImageAsset).filter(
        ImageAsset.scrape_task_id == local_asset.scrape_task_id,
        ImageAsset.variation_group == local_asset.variation_group,
        ImageAsset.asset_name.like("%-regenerated%")
    ).count()
    
    prod_name = product.get("product_identity", {}).get("product_name", sku)
    safe_prod_name = _safe_folder_name(prod_name)[:30] # Limit length
    new_asset_name = f"{safe_prod_name}-regenerated{regen_count + 1}.png"
    
    save_path = os.path.join(folder, new_asset_name)
    
    # Insert the new asset immediately with status="generating"
    new_asset = ImageAsset(
        scrape_task_id=local_asset.scrape_task_id,
        asset_name=new_asset_name,
        storage_path=save_path,
        prompt_text=prompt_text,
        variation_group=local_asset.variation_group,
        status="generating"
    )
    db.add(new_asset)
    db.commit()
    db.refresh(new_asset)
    
    new_asset_id = new_asset.id

    def run_regenerate(target_asset_id: str):
        from app.tasks.tools.image_generator import _generate_single_image
        import uuid
        
        db_local = SessionLocal()
        try:
            target_asset = db_local.query(ImageAsset).filter(ImageAsset.id == target_asset_id).first()
            if not target_asset: return
            
            job_local = db_local.query(ScrapeTask).filter(ScrapeTask.id == target_asset.scrape_task_id).first()
            prod_local = job_local.product_data if job_local else {}
            
            from app.tasks.gen_images import download_reference_images
            async def _do_gen():
                ref_image_paths = await download_reference_images(prod_local)
                return await _generate_single_image(target_asset.prompt_text, ref_image_paths, target_asset.storage_path)
            
            result = asyncio.run(_do_gen())
            if result:
                target_asset.status = "pending" # pending approval
                db_local.commit()
            else:
                db_local.delete(target_asset)
                db_local.commit()
                
        except Exception as e:
            print(f"Regenerate failed: {e}")
            if 'target_asset' in locals() and target_asset:
                target_asset.status = "failed"
                db_local.commit()
        finally:
            db_local.close()

    background_tasks.add_task(run_regenerate, new_asset_id)
    return {"status": "success", "message": "Regenerating variation..."}

@router.post("/{asset_id}/approve", summary="Approve an image variation")
def approve_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(ImageAsset).filter(ImageAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    asset.status = "approved"
    
    # Reject others in the same group
    db.query(ImageAsset).filter(
        ImageAsset.scrape_task_id == asset.scrape_task_id,
        ImageAsset.variation_group == asset.variation_group,
        ImageAsset.id != asset_id
    ).update({"status": "rejected"})
    
    db.commit()
    return {"status": "success", "message": "Asset approved"}

@router.post("/job/{job_id}/stop", summary="Stop image generation for a job")
def stop_generation(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScrapeTask).filter(ScrapeTask.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "image_generation_stopped"
    db.commit()
    return {"status": "success", "message": "Stopping..."}

@router.post("/job/{job_id}/abort", summary="Abort image generation entirely")
def abort_generation(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScrapeTask).filter(ScrapeTask.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete all generated image assets for this job
    db.query(ImageAsset).filter(ImageAsset.scrape_task_id == job_id).delete()
    
    job.status = "aborted"
    db.commit()
    return {"status": "success", "message": "Job aborted"}

@router.post("/job/{job_id}/revert", summary="Revert job to JSON Review")
def revert_to_json(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScrapeTask).filter(ScrapeTask.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Delete all generated image assets for this job
    db.query(ImageAsset).filter(ImageAsset.scrape_task_id == job_id).delete()
    
    job.status = "waiting_for_approval"
    db.commit()
    return {"status": "success", "message": "Job reverted to JSON review"}

@router.post("/job/{job_id}/resume", summary="Resume image generation for a job")
def resume_generation(job_id: str, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(ScrapeTask).filter(ScrapeTask.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = "image_generation"
    db.commit()
    
    # Capture job_id as a plain string BEFORE the session closes
    job_id_str = str(job.id)
    
    from app.tasks.gen_images import _run_image_pipeline
    import asyncio
    
    def run_async_pipeline():
        asyncio.run(_run_image_pipeline(job_id_str))
        
    background_tasks.add_task(run_async_pipeline)
    return {"status": "success", "message": "Resuming..."}

@router.post("/job/{job_id}/finish", summary="Finish image review and move to bundle/success phase")
def finish_review(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScrapeTask).filter(ScrapeTask.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    # Check if all image groups have an approved asset? (Optional, skipping strict check to allow manual override)
    
    job.status = "success"  # Ready for bundles
    job.progress = 100
    db.commit()
    return {"status": "success", "message": "Image review finished"}

@router.delete("/{asset_id}", summary="Delete an image variation")
def delete_asset(asset_id: str, db: Session = Depends(get_db)):
    asset = db.query(ImageAsset).filter(ImageAsset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")
    
    # Optionally remove file from disk
    if os.path.exists(asset.storage_path):
        try:
            os.remove(asset.storage_path)
        except Exception:
            pass

    db.delete(asset)
    db.commit()
    return {"status": "success", "message": "Asset deleted"}
