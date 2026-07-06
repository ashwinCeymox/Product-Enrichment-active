import sys
from app.database import SessionLocal
from app.models.scrape_task import ScrapeTask

db = SessionLocal()
job = db.query(ScrapeTask).first()
if job:
    print("Found job:", job.id)
    try:
        db.delete(job)
        db.commit()
        print("Deleted!")
    except Exception as e:
        print("Exception:")
        print(type(e).__name__, e)
        db.rollback()
else:
    print("No job")
