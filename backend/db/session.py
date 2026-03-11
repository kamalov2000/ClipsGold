"""
Database session factory.
DATABASE_URL must be set in .env, e.g.:
  DATABASE_URL=postgresql+psycopg2://user:pass@localhost:5432/clipsgold
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./clipsgold_dev.db")

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    # SQLite doesn't support pool_size/max_overflow — handled by connect_args below
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Session:
    """FastAPI dependency: yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all tables (use Alembic in production for migrations)."""
    from db.models import Base
    Base.metadata.create_all(bind=engine)
