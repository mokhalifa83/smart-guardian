import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.session import Base


class AnalysisResult(Base):
    """
    Surveillance-level analysis results.
    Phase 1 strictly records surveillance observations (e.g., WATER_CUT_SURVEILLANCE, RATE_STABILITY).
    Strictly forbids declaring unsupported reservoir root causes (coning, channeling, cement failure)
    without multi-evidence diagnostic engines.
    """
    __tablename__ = "analysis_results"

    analysis_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    well_code = Column(String(50), ForeignKey("wells.well_code", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    analysis_type = Column(String(50), nullable=False, default="WATER_CUT_SURVEILLANCE")
    status = Column(String(50), nullable=False, default="NORMAL")  # NORMAL, WARNING, DATA_UNAVAILABLE
    observed_value = Column(Float, nullable=True)
    threshold = Column(Float, nullable=True)
    data_source = Column(String(50), nullable=False, default="SOFTWARE_API")
    data_quality = Column(String(50), nullable=False, default="VALID")
    diagnostic_details = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        Index("ix_analysis_results_well_type_time", "well_code", "analysis_type", "timestamp"),
    )

    well = relationship("Well", back_populates="analysis_results")
