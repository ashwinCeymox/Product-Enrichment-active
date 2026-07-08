import asyncio
import os
import uuid
import httpx
from app.celery_app import celery_app
from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask
from app.models.image_asset import ImageAsset
from app.tasks.tools.img_prompt import generate_all_prompts
from app.tasks.tools.image_generator import generate_product_images

REFERENCE_IMAGE_CACHE = "output/reference_cache"

async def download_reference_images(product: dict, max_images: int = 4) -> list[str]:
    paths = []
    try:
        scraped = product.get("images", {}).get("scraped_images", [])
        if not scraped: return paths
        
        os.makedirs(REFERENCE_IMAGE_CACHE, exist_ok=True)
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            for i, img in enumerate(scraped[:max_images]):
                url = img.get("url", "")
                if not url: continue
                
                ext = os.path.splitext(url.split("?")[0])[1] or ".jpg"
                save_path = os.path.join(REFERENCE_IMAGE_CACHE, f"ref_{uuid.uuid4().hex}{ext}")
                
                try:
                    response = await client.get(url)
                    response.raise_for_status()
                    with open(save_path, "wb") as f:
                        f.write(response.content)
                    paths.append(save_path)
                except Exception as e:
                    print(f"Failed to download ref image {url}: {e}")
                    
        return paths
    except Exception as e:
        print(f"Ref images download failed: {e}")
        return paths

async def _run_image_pipeline(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(ScrapeTask).filter(ScrapeTask.id == job_id).first()
        if not job or not job.product_data:
            return
            
        if job.status in ["success", "aborted", "waiting_for_approval", "completed"]:
            return
            
        product = job.product_data
        base_sku = product.get("product_identity", {}).get("sku", job.task_name)
        # Ensure 100% filesystem isolation for this specific task
        sku = f"{base_sku}_{job.id}"
        
        # 1. Download Reference Images
        ref_image_paths = await download_reference_images(product)
        
        # 2. Generate Prompts (DeepSeek)
        prompt_results = await generate_all_prompts(product)
        
        def check_cancel():
            db.refresh(job)
            return job.status in ["image_generation_stopped", "success", "aborted"]
        
        def on_image_generated(group_type: str, index: int, prompt: str, img_data: dict, title: str = None):
            var_group = f"lifestyle_{index+1}" if group_type == "lifestyle" else f"feature_{index+1}"
            asset_name = f"Lifestyle-{index+1}.png" if group_type == "lifestyle" else f"Feature-{title.replace(' ', '')}.png"
            
            # Check if an asset for this variation_group already exists (e.g. from a resumed or retried job)
            existing = db.query(ImageAsset).filter(
                ImageAsset.scrape_task_id == job.id,
                ImageAsset.variation_group == var_group,
                ~ImageAsset.asset_name.like("%-regenerated%") # Only overwrite base images, not regenerated ones
            ).first()
            
            if existing:
                existing.asset_name = asset_name
                existing.storage_path = img_data["path"]
                existing.prompt_text = prompt
                existing.status = "pending"
            else:
                asset = ImageAsset(
                    scrape_task_id=job.id,
                    asset_name=asset_name,
                    storage_path=img_data["path"],
                    prompt_text=prompt,
                    variation_group=var_group,
                    status="pending"
                )
                db.add(asset)
            db.commit()
            
        # 3. Generate Images (OpenRouter Gemini Nano Banana)
        image_results = await generate_product_images(
            lifestyle_prompts=prompt_results["lifestyle"],
            feature_prompts=prompt_results["features"],
            product_sku=sku,
            reference_image_paths=ref_image_paths,
            check_cancel_cb=check_cancel,
            on_image_generated_cb=on_image_generated
        )
        
        db.refresh(job)
        if job.status != "image_generation_stopped":
            job.status = "image_generation_complete"
        db.commit()
        
    except Exception as e:
        print(f"Error in image pipeline: {e}")
        job.status = "failed"
        job.error_message = str(e)
        db.commit()
    finally:
        db.close()

@celery_app.task(bind=True, name="app.tasks.gen_images.generate_images_task")
def generate_images_task(self, job_id: str):
    """Generate image variations via Nano Banana for each asset slot."""
    asyncio.run(_run_image_pipeline(job_id))
    return f"Image generation finished for {job_id}"
