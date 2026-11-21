"""
SQLAlchemy ORM Models for MergeGuard AI
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, Text, DateTime
from .database import Base


class UserRecord(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    username = Column(String(64), unique=True, index=True, nullable=False)
    full_name = Column(String(128), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(32), default="engineer", nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)


class PredictionRecord(Base):
    __tablename__ = "prediction_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    project_name = Column(String(255), index=True, nullable=False, default="mergeguard/demo-repo")
    mr_iid = Column(Integer, index=True, nullable=True)
    mr_title = Column(String(512), nullable=True)
    
    risk_score = Column(Integer, nullable=False)
    risk_level = Column(String(32), nullable=False, index=True)
    defect_probability = Column(Float, nullable=False)
    
    # Serialized JSON representations
    metrics_json = Column(Text, nullable=False)
    risk_factors_json = Column(Text, nullable=False)
    mitigating_factors_json = Column(Text, nullable=False)
    recommendations_json = Column(Text, nullable=False)
    
    created_by_user = Column(String(128), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
