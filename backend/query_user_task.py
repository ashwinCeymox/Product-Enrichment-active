from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask
db = SessionLocal()
tasks = db.query(ScrapeTask).filter(ScrapeTask.task_name == "task-1").all()
for t in tasks:
    if "example.com" not in t.url:
        print(f"ID: {t.id}, URL: {t.url}, Status: {t.status}, Error: {t.error_message}")
