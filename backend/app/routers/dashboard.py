"""
Dashboard stats router.
Provides aggregate statistics across all pipeline tables.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.scrape_task import ScrapeTask
from app.models.extracted_product import ExtractedProduct
from app.models.image_asset import ImageAsset
from app.models.generated_page import GeneratedPage
from app.schemas.dashboard import (
    DashboardStats,
    PendingApprovalBreakdown,
    RecentActivityItem,
    RecentActivityResponse,
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
def get_dashboard_stats(db: Session = Depends(get_db)):
    total_jobs = db.query(ScrapeTask).count()
    completed = db.query(ScrapeTask).filter(ScrapeTask.status == "completed").count()
    failed = db.query(ScrapeTask).filter(ScrapeTask.status.in_(["failed", "aborted"])).count()

    # Pending approvals breakdown
    json_pending = db.query(ScrapeTask).filter(ScrapeTask.status == "waiting_for_approval").count()
    img_pending = db.query(ScrapeTask).filter(ScrapeTask.status.in_([
        "image_generation", 
        "image_generation_stopped",
        "image_generation_complete"
    ])).count()
    from app.models.generated_page import GeneratedPage
    html_pending = db.query(GeneratedPage).filter(GeneratedPage.status == "pending").count()

    return DashboardStats(
        total_jobs=total_jobs,
        pending_approvals=json_pending + img_pending + html_pending,
        approval_breakdown=PendingApprovalBreakdown(
            json_count=json_pending,
            image_count=img_pending,
            html_count=html_pending,
        ),
        completed=completed,
        failed=failed,
    )


@router.get("/recent-activity", response_model=RecentActivityResponse)
def get_recent_activity(limit: int = 20, db: Session = Depends(get_db)):
    tasks = (
        db.query(ScrapeTask)
        .order_by(ScrapeTask.created_at.desc())
        .limit(limit)
        .all()
    )
    items = [
        RecentActivityItem(
            job_id=t.id,
            task_name=t.task_name,
            source_url=t.url,
            status=t.status,
            progress=t.progress or 0,
            created_at=t.created_at,
            error_message=t.error_message,
        )
        for t in tasks
    ]
    return RecentActivityResponse(items=items)

@router.get("/error-logs", response_model=RecentActivityResponse)
def get_error_logs(limit: int = 100, db: Session = Depends(get_db)):
    tasks = (
        db.query(ScrapeTask)
        .filter(ScrapeTask.status.in_(["failed", "aborted"]))
        .order_by(ScrapeTask.created_at.desc())
        .limit(limit)
        .all()
    )
    items = [
        RecentActivityItem(
            job_id=t.id,
            task_name=t.task_name,
            source_url=t.url,
            status=t.status,
            progress=t.progress or 0,
            created_at=t.created_at,
            error_message=t.error_message,
        )
        for t in tasks
    ]
    return RecentActivityResponse(items=items)
