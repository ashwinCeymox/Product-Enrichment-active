from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask
from app.models.image_asset import ImageAsset

db = SessionLocal()
task = db.query(ScrapeTask).order_by(ScrapeTask.created_at.desc()).first()
print(f"Task: {task.task_name}, Status: {task.status}, Error: {task.error_message}")
assets = db.query(ImageAsset).filter(ImageAsset.scrape_task_id == task.id).all()
print(f"Assets count: {len(assets)}")
for a in assets:
    print(f" - {a.id}, status={a.status}")
