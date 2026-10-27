from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, ConfigDict
from app.schemas.common import DataQualityStatus, SourceCategory, SurveillanceState, ValueType
from app.schemas.alert import AlertResponse


class KpiCardData(BaseModel):
    title: str
    metric_key: str
    value: Optional[float] = None
    display_value: str
    unit: str
    status: SurveillanceState  # NORMAL, WARNING, DATA_UNAVAILABLE
    timestamp: Optional[datetime] = None
    received_at: Optional[datetime] = None
    source: Optional[SourceCategory] = None
    quality_status: DataQualityStatus
    value_type: ValueType
    threshold: Optional[float] = None
    is_threshold_exceeded: bool = False


class DashboardResponse(BaseModel):
    well_code: str
    field_name: str
    well_status: str
    latest_timestamp: Optional[datetime] = None
    surveillance_state: SurveillanceState
    kpis: List[KpiCardData]
    active_alerts: List[AlertResponse]
    configured_wc_threshold: float
    rate_limit_info: dict

    model_config = ConfigDict(from_attributes=True)
