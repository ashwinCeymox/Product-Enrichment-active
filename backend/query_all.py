from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask

db = SessionLocal()
tasks = db.query(ScrapeTask).all()
for task in tasks:
    print(f"ID: {task.id}, Name: {task.task_name}, Status: {task.status}")
