from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.database.session import Base


class WellConfig(Base):
    __tablename__ = "well_configs"

    well_code = Column(String(50), ForeignKey("wells.well_code", ondelete="CASCADE"), primary_key=True, index=True)
    wc_threshold = Column(Float, nullable=False, default=80.0)  # Configurable per well, not a universal law!
    wc_trend_window_hours = Column(Integer, nullable=False, default=24)
    alert_cooldown_minutes = Column(Integer, nullable=False, default=60)
    surveillance_interval_minutes = Column(Integer, nullable=False, default=5)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    well = relationship("Well", back_populates="config")
