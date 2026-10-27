from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime
from sqlalchemy.orm import relationship
from app.database.session import Base


class Well(Base):
    __tablename__ = "wells"

    well_code = Column(String(50), primary_key=True, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    status = Column(String(50), nullable=False, default="ACTIVE")  # ACTIVE, SHUT_IN, SUSPENDED, DRILLING
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    config = relationship("WellConfig", back_populates="well", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    production_readings = relationship("ProductionReading", back_populates="well", cascade="all, delete-orphan", lazy="selectin")
    separator_readings = relationship("SeparatorReading", back_populates="well", cascade="all, delete-orphan", lazy="selectin")
    manual_readings = relationship("ManualReading", back_populates="well", cascade="all, delete-orphan", lazy="selectin")
    alerts = relationship("Alert", back_populates="well", cascade="all, delete-orphan", lazy="selectin")
    analysis_results = relationship("AnalysisResult", back_populates="well", cascade="all, delete-orphan", lazy="selectin")
