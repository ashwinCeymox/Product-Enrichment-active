from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask

db = SessionLocal()
task = db.query(ScrapeTask).filter(ScrapeTask.id == "262efd48-90cf-4da4-beca-c425c6ada289").first()
print(f"Error: {task.error_message}")
