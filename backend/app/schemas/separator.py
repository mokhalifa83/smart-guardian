from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import DataQualityStatus, SourceCategory, ValueType


class SeparatorReadingCreate(BaseModel):
    well_code: str = Field(..., min_length=2, max_length=50)
    timestamp: datetime
    pressure: Optional[float] = Field(default=None, description="Separator Pressure in psi")
    flow_rate: Optional[float] = Field(default=None, description="Gross liquid flow rate in bpd")
    
    # Water Cut
    water_cut: Optional[float] = Field(default=None, description="Water Cut value")
    wc_unit: Optional[str] = Field(default="%", description="'%' or 'fraction'")
    
    oil_rate: Optional[float] = Field(default=None, ge=0.0)
    water_rate: Optional[float] = Field(default=None, ge=0.0)
    gas_rate: Optional[float] = Field(default=None, ge=0.0)

    source: SourceCategory = SourceCategory.SOFTWARE_API
    source_system: Optional[str] = None
    source_record_id: Optional[str] = None
    quality_status: Optional[DataQualityStatus] = None
    is_data_unavailable: bool = False


class SeparatorReadingResponse(BaseModel):
    well_code: str
    timestamp: datetime
    received_at: datetime
    pressure: Optional[float] = None
    flow_rate: Optional[float] = None
    water_cut: Optional[float] = None  # Normalized to percentage
    original_wc_value: Optional[float] = None
    original_wc_unit: Optional[str] = None
    oil_rate: Optional[float] = None
    water_rate: Optional[float] = None
    gas_rate: Optional[float] = None
    source: SourceCategory
    value_type: ValueType
    quality_status: DataQualityStatus
    validation_status: DataQualityStatus
    source_system: Optional[str] = None
    source_record_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
