from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask
from app.models.image_asset import ImageAsset

db = SessionLocal()
tasks = db.query(ScrapeTask).order_by(ScrapeTask.created_at.desc()).limit(3).all()
for t in tasks:
    print(f"Task: {t.task_name}, Status: {t.status}, Progress: {t.progress}")
    assets = db.query(ImageAsset).filter(ImageAsset.scrape_task_id == t.id).all()
    print(f" Assets: {len(assets)}")
