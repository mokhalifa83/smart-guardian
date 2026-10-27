from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.common import DataQualityStatus, SourceCategory, SurveillanceState


class AnalysisResultResponse(BaseModel):
    analysis_id: str
    well_code: str
    timestamp: datetime
    analysis_type: str
    status: SurveillanceState
    observed_value: Optional[float] = None
    threshold: Optional[float] = None
    data_source: SourceCategory
    data_quality: DataQualityStatus
    diagnostic_details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
