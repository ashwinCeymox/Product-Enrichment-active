"""
Job creation & management router.
Merged from backend/routes/jobs.py and fastapi endpoints/job_structure/main.py.

Endpoints:
  POST /jobs           — create job (single or multi-URL)
  POST /jobs/upload-csv — CSV batch upload
  GET  /jobs           — list/filter jobs
  GET  /jobs/{batch_id} — get batch details
  POST /jobs/stop      — stop all pending/in-progress jobs
"""
import csv
import io
import time
import uuid
from datetime import date
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import HttpUrl, ValidationError
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scrape_task import ScrapeTask
from app.schemas.jobs import (
    BatchSubmitResponse,
    JobListResponse,
    JobResponse,
    MultiURLRequest,
    PriorityEnum,
    SingleURLRequest,
    TaskPercentage,
    TaskStatus,
)

router = APIRouter(prefix="/jobs", tags=["Jobs"])


# ── Celery import with fallback ──────────────────────────────────
try:
    from app.tasks.scrape import process_scrape
    from app.tasks.gen_images import generate_images_task
    CELERY_AVAILABLE = True
except ImportError:
    CELERY_AVAILABLE = False


# ── Helpers ──────────────────────────────────────────────────────
def _dispatch(task_id: str, background_tasks: BackgroundTasks) -> str:
    """Attempt Celery dispatch; fall back to BackgroundTasks."""
    if CELERY_AVAILABLE:
        try:
            result = process_scrape.delay(task_id)
            return result.id
        except Exception as e:
            print(f"[Jobs] Celery unavailable ({e}), using local fallback")

    fallback_id = f"local-{task_id}-{int(time.time())}"
    background_tasks.add_task(process_scrape, task_id)
    return fallback_id


def _validate_urls(raw: List[str]) -> tuple[List[str], List[str]]:
    valid, invalid = [], []
    for raw_url in raw:
        raw_url = raw_url.strip()
        if not raw_url:
            continue
        try:
            HttpUrl(raw_url)
            valid.append(raw_url)
        except (ValidationError, ValueError):
            invalid.append(raw_url)
    return valid, invalid


def _build_jobs(
    db: Session,
    *,
    urls: List[str],
    priority: Optional[str],
    task_name: str,
    scheduled_date: Optional[date],
    created_by: Optional[str],
    product_type: str,
    background_tasks: BackgroundTasks,
) -> tuple[str, List[ScrapeTask]]:
    """Insert one ScrapeTask per URL under a shared batch_id."""
    batch_id = str(uuid.uuid4())
    jobs: List[ScrapeTask] = []

    for url in urls:
        job = ScrapeTask(
            batch_id=batch_id,
            task_name=task_name,
            priority=priority or "low",
            url=url,
            product_type=product_type,
            status="pending",
            progress=0,
            scheduled_date=scheduled_date,
            created_by=created_by,
            activity_log=[{"timestamp": time.time(), "action": "created", "detail": f"Job created for {url}"}],
        )
        db.add(job)
        jobs.append(job)

    db.commit()
    for job in jobs:
        db.refresh(job)

    # Dispatch jobs that are not scheduled for a future date
    for job in jobs:
        if scheduled_date and scheduled_date > date.today():
            job.status = "pending"
            job.append_activity("scheduled", f"Scheduled for {scheduled_date}")
        else:
            celery_id = _dispatch(job.id, background_tasks)
            job.celery_task_id = celery_id
            job.status = "queued"
            job.append_activity("queued", "Dispatched to worker")
        db.commit()

    return batch_id, jobs


# ── Routes ───────────────────────────────────────────────────────

@router.post(
    "",
    response_model=BatchSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit one or more URLs for processing",
)
def create_job(
    payload: MultiURLRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    valid_urls = [str(u) for u in payload.urls]
    batch_id, jobs = _build_jobs(
        db,
        urls=valid_urls,
        task_name=payload.task_name,
        priority=payload.priority,
        scheduled_date=payload.scheduled_date,
        created_by=payload.created_by,
        product_type=payload.product_type,
        background_tasks=background_tasks,
    )
    return BatchSubmitResponse(
        batch_id=batch_id,
        task_name=payload.task_name,
        total_urls=len(valid_urls),
        submitted=len(jobs),
        skipped=0,
        skipped_urls=[],
        jobs=jobs,
        message=f"{len(jobs)} URL job(s) submitted successfully.",
    )


@router.post(
    "/upload-csv",
    response_model=BatchSubmitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a CSV file containing URLs",
)
async def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    task_name: str = Query(...),
    url_column: str = Query("url"),
    priority: Optional[PriorityEnum] = Query(PriorityEnum.low),
    product_type: str = Query("simple"),
    scheduled_date: Optional[date] = Query(None),
    created_by: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=415, detail="Only .csv files are accepted.")

    raw_bytes = await file.read()
    try:
        text = raw_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded.")

    df = pd.read_csv(io.StringIO(text))

    # Find the URL column
    if url_column in df.columns:
        column = url_column
    elif len(df.columns) == 1:
        column = df.columns[0]
    else:
        raise HTTPException(
            status_code=422,
            detail=f"Column '{url_column}' not found. Available: {list(df.columns)}",
        )

    raw_urls = df[column].dropna().drop_duplicates().astype(str).str.strip().tolist()
    if not raw_urls:
        raise HTTPException(status_code=400, detail="CSV file contains no URL values.")

    valid_urls, invalid_urls = _validate_urls(raw_urls)
    if not valid_urls:
        raise HTTPException(status_code=422, detail="No valid URLs found in CSV.")

    batch_id, jobs = _build_jobs(
        db,
        urls=valid_urls,
        task_name=task_name,
        priority=priority,
        scheduled_date=scheduled_date,
        created_by=created_by,
        product_type=product_type,
        background_tasks=background_tasks,
    )

    return BatchSubmitResponse(
        batch_id=batch_id,
        task_name=task_name,
        total_urls=len(raw_urls),
        submitted=len(jobs),
        skipped=len(invalid_urls),
        skipped_urls=invalid_urls,
        jobs=jobs,
        message=f"{len(jobs)} URL(s) submitted; {len(invalid_urls)} skipped.",
    )


@router.get("/", response_model=JobListResponse, summary="List jobs with filtering")
def list_jobs(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    task_name: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    query = db.query(ScrapeTask)
    if task_name:
        query = query.filter(ScrapeTask.task_name == task_name)
    if status_filter:
        query = query.filter(ScrapeTask.status == status_filter)

    total = query.count()
    pending = query.filter(ScrapeTask.status.in_(["pending", "queued"])).count()
    processing = query.filter(ScrapeTask.status.in_(["processing", "scraping", "ai_processing"])).count()
    completed = query.filter(ScrapeTask.status == "success").count()
    failed = query.filter(ScrapeTask.status == "failed").count()

    jobs = query.order_by(ScrapeTask.created_at.desc()).offset(skip).limit(limit).all()
    return JobListResponse(
        total=total,
        remaining=pending + processing,
        pending=pending,
        processing=processing,
        completed=completed,
        failed=failed,
        jobs=jobs,
    )


@router.get("/{batch_id}", response_model=JobListResponse, summary="Get all jobs for a batch")
def get_batch_jobs(batch_id: str, db: Session = Depends(get_db)):
    jobs = db.query(ScrapeTask).filter(ScrapeTask.batch_id == batch_id).all()
    if not jobs:
        raise HTTPException(status_code=404, detail=f"No jobs found for batch '{batch_id}'")
    return JobListResponse(total=len(jobs), jobs=jobs)


@router.post("/stop", summary="Stop all pending/in-progress jobs")
def stop_all_jobs(db: Session = Depends(get_db)):
    count = (
        db.query(ScrapeTask)
        .filter(ScrapeTask.status.in_(["pending", "queued", "processing", "scraping"]))
        .update({"status": "failed", "error_message": "Stopped by user"}, synchronize_session=False)
    )
    db.commit()
    return {"status": "success", "stopped": count}


@router.get("/stats/percentage", response_model=TaskPercentage, summary="Get task completion percentage")
def get_task_percentage(task_name: str = Query(...), db: Session = Depends(get_db)):
    total = db.query(ScrapeTask).filter(ScrapeTask.task_name == task_name).count()
    completed = db.query(ScrapeTask).filter(
        ScrapeTask.task_name == task_name, ScrapeTask.status == "success"
    ).count()
    remaining = total - completed
    percentage = (completed / total * 100) if total > 0 else 0.0
    return TaskPercentage(task_name=task_name, percentage=percentage, remaining_count=remaining)


from app.schemas.jobs import ApprovalRequest

@router.post("/{job_id}/approve", summary="Approve JSON and send to Image Queue")
def approve_job(job_id: str, payload: ApprovalRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    job = db.query(ScrapeTask).filter(ScrapeTask.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if payload.product_data is not None:
        job.product_data = payload.product_data

    # After JSON approval, it goes to image queue
    job.status = "image_generation"
    job.append_activity("json_approved", "Admin approved the JSON payload, preparing images")
    db.commit()
    
    # Capture job_id as a plain string BEFORE the session closes
    job_id_str = str(job.id)
    
    # Use BackgroundTasks instead of Celery
    from app.tasks.gen_images import _run_image_pipeline
    import asyncio
    
    def run_async_pipeline():
        asyncio.run(_run_image_pipeline(job_id_str))
        
    background_tasks.add_task(run_async_pipeline)
            
    return {"status": "success", "message": "Job approved and sent to image generation"}

@router.post("/{job_id}/reject", summary="Reject JSON")
def reject_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScrapeTask).filter(ScrapeTask.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job.status = "failed"
    job.error_message = "Rejected by admin during JSON review"
    job.append_activity("json_rejected", "Admin rejected the JSON payload")
    db.commit()
    return {"status": "success", "message": "Job rejected"}


@router.delete("/{job_id}", summary="Abort a job or mark as hidden")
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = db.query(ScrapeTask).filter(ScrapeTask.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status not in ["success", "failed"]:
        job.status = "aborted"
        job.error_message = "Task aborted by user."
        db.commit()
        
    return {"status": "success", "message": "Job updated"}


@router.get("/stats/status", response_model=list[TaskStatus], summary="Get status breakdown by task")
def get_task_statuses(db: Session = Depends(get_db)):
    tasks = (
        db.query(
            ScrapeTask.task_name,
            func.count(ScrapeTask.id).label("total"),
            func.sum(case((ScrapeTask.status == "success", 1), else_=0)).label("completed"),
            ScrapeTask.status,
        )
        .group_by(ScrapeTask.task_name, ScrapeTask.status)
        .all()
    )

    return [
        TaskStatus(
            task_name=t.task_name,
            completed_percentage=int(round((t.completed / t.total) * 100)) if t.total else 0,
            status=t.status,
        )
        for t in tasks
    ]
