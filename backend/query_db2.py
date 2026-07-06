from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask
from app.models.image_asset import ImageAsset

db = SessionLocal()
tasks = db.query(ScrapeTask).order_by(ScrapeTask.created_at.desc()).limit(10).all()
for task in tasks:
    print(f"Task: {task.task_name}, Status: {task.status}")
    assets = db.query(ImageAsset).filter(ImageAsset.scrape_task_id == task.id).all()
    for a in assets:
        print(f" - {a.id}, status={a.status}")
