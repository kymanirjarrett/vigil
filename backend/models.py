from sqlalchemy import Column, Integer, String, DateTime, UniqueConstraint
from sqlalchemy.sql import func
from database import Base


class AnomalyEvent(Base):
    __tablename__ = "anomaly_events"

    id          = Column(Integer, primary_key=True, index=True)
    job_name    = Column(String, nullable=False, index=True)
    run_id      = Column(String, nullable=False)
    type        = Column(String, nullable=False)    # DURATION_SPIKE | CONSECUTIVE_FAILURES
    severity    = Column(String, nullable=False)    # warning | critical
    message     = Column(String, nullable=False)
    detected_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("run_id", "type", name="uq_anomaly_run_type"),
    )


class AlertLog(Base):
    __tablename__ = "alert_log"

    id              = Column(Integer, primary_key=True, index=True)
    recipient       = Column(String, nullable=False)
    job_name        = Column(String, nullable=False)
    anomaly_count   = Column(Integer, nullable=False)
    sent_at         = Column(DateTime(timezone=True), server_default=func.now())
    sendgrid_status = Column(Integer, nullable=True)
