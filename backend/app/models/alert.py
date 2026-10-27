import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.session import Base


class Alert(Base):
    """
    Structured operational alerts for production surveillance.
    Supports lifecycle: ACTIVE -> ACKNOWLEDGED -> RESOLVED.
    """
    __tablename__ = "alerts"

    alert_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    well_code = Column(String(50), ForeignKey("wells.well_code", ondelete="CASCADE"), nullable=False, index=True)
    alert_type = Column(String(50), nullable=False, default="WATER_CUT")  # WATER_CUT, PRESSURE_ANOMALY, RATE_DROP
    severity = Column(String(20), nullable=False, default="WARNING")  # INFO, WARNING, CRITICAL
    message = Column(String(500), nullable=False)
    value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)  # Event occurrence timestamp
    status = Column(String(20), nullable=False, default="ACTIVE")  # ACTIVE, ACKNOWLEDGED, RESOLVED
    source = Column(String(50), nullable=False, default="SURVEILLANCE_ENGINE")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_alerts_well_status_type", "well_code", "status", "alert_type"),
    )

    well = relationship("Well", back_populates="alerts")
