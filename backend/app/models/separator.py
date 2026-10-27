from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, PrimaryKeyConstraint, Index
from sqlalchemy.orm import relationship
from app.database.session import Base


class SeparatorReading(Base):
    """
    Time-series separator reading table (TimescaleDB hypertable partitioned on timestamp).
    Stores test/production separator telemetry (pressure, total rate, water cut, individual phase rates).
    """
    __tablename__ = "separator_readings"

    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    well_code = Column(String(50), ForeignKey("wells.well_code", ondelete="CASCADE"), nullable=False, index=True)
    source = Column(String(50), nullable=False, default="SOFTWARE_API")

    pressure = Column(Float, nullable=True)     # psi
    flow_rate = Column(Float, nullable=True)    # total gross liquid rate bpd
    water_cut = Column(Float, nullable=True)    # normalized water cut percent [0-100]
    oil_rate = Column(Float, nullable=True)     # bpd
    water_rate = Column(Float, nullable=True)   # bpd
    gas_rate = Column(Float, nullable=True)     # mscfd

    # Original input provenance preservation
    original_wc_value = Column(Float, nullable=True)
    original_wc_unit = Column(String(20), nullable=True)
    value_type = Column(String(50), nullable=False, default="MEASURED")

    quality_status = Column(String(50), nullable=False, default="VALID")
    validation_status = Column(String(50), nullable=False, default="VALID")
    received_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    source_system = Column(String(100), nullable=True)
    source_record_id = Column(String(100), nullable=True)
    idempotency_hash = Column(String(64), nullable=True, index=True)

    __table_args__ = (
        PrimaryKeyConstraint("timestamp", "well_code", "source", name="pk_separator_readings"),
        Index("ix_sep_readings_well_time", "well_code", "timestamp"),
    )

    well = relationship("Well", back_populates="separator_readings")
