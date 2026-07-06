from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask

db = SessionLocal()
tasks = db.query(ScrapeTask).filter(ScrapeTask.status.in_(["image_generation", "image_generation_complete", "image_generation_stopped"])).all()
for task in tasks:
    print(f"Queue Task: {task.task_name}, Status: {task.status}")
