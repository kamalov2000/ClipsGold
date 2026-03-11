"""
Celery worker configuration for ClipsGold background tasks.
Handles async rendering, video processing, and cleanup jobs.
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

# Initialize Celery app
celery_app = Celery(
    "clipsgold",
    broker=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
    backend=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # 55 minutes soft limit
    worker_prefetch_multiplier=1,  # One task at a time per worker
    worker_max_tasks_per_child=50,  # Restart worker after 50 tasks (prevent memory leaks)
)

# Import tasks from main.py
# This makes all @celery_app.task decorated functions discoverable
try:
    from main import (
        # Add task imports here as they're created
        # For now, worker will handle render queue tasks manually
    )
except ImportError as e:
    print(f"[WARN] Warning: Could not import tasks from main.py: {e}")
    print("Worker will run but no tasks will be registered yet.")

if __name__ == "__main__":
    celery_app.start()
