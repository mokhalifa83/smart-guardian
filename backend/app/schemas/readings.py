from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import DataQualityStatus, SourceCategory, ValueType


class ProductionReadingCreate(BaseModel):
    well_code: str = Field(..., min_length=2, max_length=50)
    timestamp: datetime
    oil_rate: Optional[float] = Field(default=None, ge=0.0)
    water_rate: Optional[float] = Field(default=None, ge=0.0)
    gas_rate: Optional[float] = Field(default=None, ge=0.0)
    
    # Water Cut input (can be provided as percentage or fraction with explicit unit)
    wc_value: Optional[float] = None
    wc_unit: Optional[str] = Field(default=None, description="'%' or 'fraction'")
    
    # Ingestion metadata
    source: SourceCategory = SourceCategory.SOFTWARE_API
    source_system: Optional[str] = None
    source_record_id: Optional[str] = None
    quality_status: Optional[DataQualityStatus] = None
    is_data_unavailable: bool = False  # When external source explicitly reports unavailable measurement


class ProductionReadingResponse(BaseModel):
    well_code: str
    timestamp: datetime
    received_at: datetime
    oil_rate: Optional[float] = None
    water_rate: Optional[float] = None
    gas_rate: Optional[float] = None
    wc_percent: Optional[float] = None
    source: SourceCategory
    value_type: ValueType
    quality_status: DataQualityStatus
    validation_status: DataQualityStatus
    source_system: Optional[str] = None
    source_record_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
