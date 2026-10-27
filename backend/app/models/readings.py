from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, PrimaryKeyConstraint, Index
from sqlalchemy.orm import relationship
from app.database.session import Base


class ProductionReading(Base):
    """
    Time-series production reading table (TimescaleDB hypertable partitioned on timestamp).
    Stores canonical production surveillance records.
    Never stores 0 or defaults for missing water cut; preserves DATA_UNAVAILABLE.
    """
    __tablename__ = "production_readings"

    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    well_code = Column(String(50), ForeignKey("wells.well_code", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False, default="SOFTWARE_API")  # SOFTWARE_API, MANUAL, MQTT, CALCULATED, DERIVED

    oil_rate = Column(Float, nullable=True)          # bpd / stb/d
    water_rate = Column(Float, nullable=True)        # bpd
    gas_rate = Column(Float, nullable=True)          # mscfd
    wc_percent = Column(Float, nullable=True)        # Water cut normalized percentage [0-100]

    value_type = Column(String(50), nullable=False, default="MEASURED")  # MEASURED, CALCULATED, DERIVED
    quality_status = Column(String(50), nullable=False, default="VALID")  # VALID, INVALID, STALE, MISSING, DATA_UNAVAILABLE
    validation_status = Column(String(50), nullable=False, default="VALID")  # VALID, INVALID, STALE, MISSING, DATA_UNAVAILABLE
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    source_system = Column(String(100), nullable=True)
    source_record_id = Column(String(100), nullable=True)
    idempotency_hash = Column(String(64), nullable=True, index=True)

    # Composite primary key required by TimescaleDB hypertable
    __table_args__ = (
        PrimaryKeyConstraint("timestamp", "well_code", "source", name="pk_production_readings"),
        Index("ix_prod_readings_well_time", "well_code", "timestamp"),
    )

    well = relationship("Well", back_populates="production_readings")
