"""
Database Configuration & Session Management
Supports PostgreSQL (production/docker/k8s) and SQLite (local zero-dependency development).
Uses deterministic absolute paths to avoid working-directory drift.
"""

import os
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_SQLITE_PATH = (PROJECT_ROOT / "mergeguard.db").resolve()

DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH}")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency to yield database sessions per request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
