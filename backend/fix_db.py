from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask

db = SessionLocal()
tasks = db.query(ScrapeTask).filter(ScrapeTask.status == "image_generation").all()
for t in tasks:
    t.status = "failed"
    t.error_message = "Task interrupted by server restart."
db.commit()
print(f"Fixed {len(tasks)} tasks.")
