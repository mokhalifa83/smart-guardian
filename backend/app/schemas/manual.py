from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.common import DataQualityStatus, MeasurementType, SourceCategory


class ManualReadingCreate(BaseModel):
    well_code: str = Field(..., min_length=2, max_length=50)
    measurement_type: MeasurementType
    value: Optional[float] = None
    unit: str = Field(..., description="Engineering unit, e.g., '%', 'fraction', 'psi', 'bar', 'degAPI'")
    timestamp: datetime
    entered_by: str = Field(..., min_length=2, max_length=100, description="Engineer or Operator identifier")
    is_data_unavailable: bool = False


class ManualReadingResponse(BaseModel):
    id: str
    well_code: str
    measurement_type: MeasurementType
    value: Optional[float] = None
    unit: str
    timestamp: datetime
    source: SourceCategory
    entered_by: str
    validation_status: DataQualityStatus
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
