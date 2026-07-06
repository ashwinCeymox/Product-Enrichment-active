"""
Active Fitness Product Enrichment API
Main FastAPI application entry point.

Run: uvicorn app.main:app --reload --port 8000
"""
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.database import Base, engine

# Import all models so they are registered with Base.metadata
import app.models  # noqa: F401

# Import routers
from app.routers import health, jobs, dashboard, images

# ── Create tables (dev convenience — use Alembic in production) ──
Base.metadata.create_all(bind=engine)

# ── App setup ────────────────────────────────────────────────────
app = FastAPI(
    title="Active Fitness Product Enrichment",
    description="AI-powered product data enrichment pipeline with human approval gates.",
    version="1.0.0",
)

# ── CORS (allow React dev server) ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Lock down in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Static files (for zip downloads, images) ─────────────────────
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

output_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
os.makedirs(output_dir, exist_ok=True)
app.mount("/output", StaticFiles(directory=output_dir), name="output")

# ── Register routers ─────────────────────────────────────────────
app.include_router(health.router)
app.include_router(jobs.router)
app.include_router(dashboard.router)
app.include_router(images.router)


@app.get("/", tags=["Root"])
async def root():
    return {
        "name": "Active Fitness Product Enrichment API",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


# ── Auto-recovery for orphaned image generation tasks ────────────
# When the server restarts (e.g. hot-reload), any background tasks
# generating images are killed mid-flight, leaving tasks stuck at
# "image_generation" status forever. This startup hook detects and
# re-dispatches them.

import threading
import asyncio
import time

def _recover_stuck_tasks():
    """Background thread that recovers tasks stuck in image_generation."""
    # Small delay to let the server fully start up
    time.sleep(3)
    
    from app.database import SessionLocal
    from app.models.scrape_task import ScrapeTask
    
    db = SessionLocal()
    try:
        stuck_tasks = db.query(ScrapeTask).filter(
            ScrapeTask.status == "image_generation"
        ).all()
        
        if not stuck_tasks:
            return
        
        print(f"\n[recovery] Found {len(stuck_tasks)} task(s) stuck in image_generation, re-dispatching...")
        
        for task in stuck_tasks:
            task_id = str(task.id)
            task_name = task.task_name
            print(f"[recovery]   → Re-dispatching: {task_name} ({task_id[:12]}...)")
            
            # Run image pipeline in a new thread for each task
            def _run_pipeline(tid):
                from app.tasks.gen_images import _run_image_pipeline
                try:
                    asyncio.run(_run_image_pipeline(tid))
                except Exception as e:
                    print(f"[recovery] Pipeline failed for {tid[:12]}...: {e}")
            
            t = threading.Thread(target=_run_pipeline, args=(task_id,), daemon=True)
            t.start()
            # Stagger launches to avoid overwhelming the API
            time.sleep(2)
        
        print(f"[recovery] All {len(stuck_tasks)} stuck task(s) re-dispatched.\n")
    except Exception as e:
        print(f"[recovery] Error during recovery: {e}")
    finally:
        db.close()


@app.on_event("startup")
async def startup_recover_tasks():
    """Launch recovery in a background thread so it doesn't block startup."""
    recovery_thread = threading.Thread(target=_recover_stuck_tasks, daemon=True)
    recovery_thread.start()

