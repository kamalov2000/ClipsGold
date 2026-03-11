"""
Celery application factory.

Two queues:
  - 'high'    → paid users (pro/team) — processed first
  - 'default' → free users

Start workers:
  # High-priority worker (paid)
  celery -A worker.celery_app worker -Q high,default --concurrency=2 -l info

  # Or single worker for both:
  celery -A worker.celery_app worker -Q high,default --concurrency=1 -l info

  # Monitor:
  celery -A worker.celery_app flower

Environment variables:
  REDIS_URL  — e.g. redis://localhost:6379/0  (default)
"""

import os
from celery import Celery
from dotenv import load_dotenv

load_dotenv()

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "clipsgold",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["worker.tasks"],
)

celery_app.conf.update(
    # Serialisation
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Reliability
    task_acks_late=True,               # ACK only after task completes (safe for idempotent tasks)
    task_reject_on_worker_lost=True,   # Re-queue if worker dies mid-task
    worker_prefetch_multiplier=1,      # One task at a time per worker (heavy FFmpeg jobs)

    # Routing
    task_default_queue="default",
    task_queues={
        "high": {"exchange": "high", "routing_key": "high"},
        "default": {"exchange": "default", "routing_key": "default"},
    },
    task_routes={
        "worker.tasks.render_clip_task": {"queue": "default"},  # overridden per-call for paid users
    },

    # Retries
    task_max_retries=3,
    task_soft_time_limit=1800,         # 30 min soft limit → raises SoftTimeLimitExceeded
    task_time_limit=2100,              # 35 min hard kill

    # Results
    result_expires=86400,              # Keep results 24h in Redis

    # Timezone
    timezone="UTC",
    enable_utc=True,
)
