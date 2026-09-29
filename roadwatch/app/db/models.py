from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String

from app.db.database import Base

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    status = Column(String, default="processing")
    total_frames = Column(Integer, default=0)
    total_events = Column(Integer, default=0)
    risk_score = Column(Float, default=0.0)
    output_path = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class RiskEvent(Base):
    __tablename__ = "risk_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    run_id = Column(String, ForeignKey("analysis_runs.id"), index=True)
    frame_index = Column(Integer, nullable=False)
    object_a = Column(String, nullable=False)
    object_b = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)
    risk_score = Column(Float, nullable=False)
    estimated_ttc = Column(Float, nullable=True)
