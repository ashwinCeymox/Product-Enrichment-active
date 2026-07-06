from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask
from app.models.image_asset import ImageAsset

db = SessionLocal()
tasks = db.query(ScrapeTask).filter(ScrapeTask.task_name == "task-1").all()
for task in tasks:
    print(f"Task ID: {task.id}, Status: {task.status}")
    assets = db.query(ImageAsset).filter(ImageAsset.scrape_task_id == task.id).all()
    print(f" Assets count: {len(assets)}")
    for a in assets:
        print(f"  - {a.id}, name={a.asset_name}, status={a.status}")
