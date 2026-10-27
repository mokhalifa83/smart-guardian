from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict
from app.schemas.common import AlertSeverity, AlertStatus


class AlertResponse(BaseModel):
    alert_id: str
    well_code: str
    alert_type: str
    severity: AlertSeverity
    message: str
    value: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: datetime
    status: AlertStatus
    source: str
    created_at: datetime
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AlertAcknowledgeRequest(BaseModel):
    acknowledged_by: Optional[str] = "operator"


class AlertResolveRequest(BaseModel):
    resolved_by: Optional[str] = "operator"
    resolution_notes: Optional[str] = None
