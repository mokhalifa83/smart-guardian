import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.session import Base


class ManualReading(Base):
    """
    Stores engineer/operator manual field entries (e.g. manual shake-out water cut, API gravity, wellhead pressure).
    Strictly preserves who entered the value, when, and original unit.
    """
    __tablename__ = "manual_readings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    well_code = Column(String(50), ForeignKey("wells.well_code", ondelete="CASCADE"), nullable=False, index=True)
    measurement_type = Column(String(50), nullable=False)  # WATER_CUT, OIL_API_GRAVITY, PRESSURE, etc.
    value = Column(Float, nullable=True)  # Null when explicitly recorded as DATA_UNAVAILABLE
    unit = Column(String(20), nullable=False)  # %, fraction, psi, bar, degAPI
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String(50), nullable=False, default="MANUAL")
    entered_by = Column(String(100), nullable=False)
    validation_status = Column(String(50), nullable=False, default="VALID")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    idempotency_hash = Column(String(64), nullable=True, index=True)

    __table_args__ = (
        Index("ix_manual_readings_well_type_time", "well_code", "measurement_type", "timestamp"),
    )

    well = relationship("Well", back_populates="manual_readings")
