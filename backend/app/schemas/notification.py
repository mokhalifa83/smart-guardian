from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class NotificationChannel(str, Enum):
    EMAIL = "EMAIL"
    WHATSAPP = "WHATSAPP"


class NotificationStatus(str, Enum):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    LOGGED_ONLY = "LOGGED_ONLY"


class NotificationContext(BaseModel):
    """
    Canonical Notification Event / Context Contract.
    Produced exclusively by the Alert / Surveillance architecture.
    Both Email and WhatsApp consume this structured context without re-inferring diagnoses or thresholds.
    """
    alert_id: str
    well_code: str
    severity: str
    alert_status: str
    water_cut: Optional[float] = None
    threshold: Optional[float] = None
    timestamp: datetime
    data_source: str = "SURVEILLANCE_ENGINE"
    data_quality: str = "VALID"
    analysis_result: Optional[str] = None
    diagnosis: str = "INSUFFICIENT_EVIDENCE"
    evidence: Dict[str, Any] = Field(default_factory=dict)
    recommended_engineering_review: str = "Review choke opening and well test history before physical field intervention."
    notification_eligibility: bool = True
    notification_metadata: Dict[str, Any] = Field(default_factory=dict)


class NotificationDeliveryResult(BaseModel):
    """Result of a single notification channel dispatch."""
    channel: str
    status: str  # PENDING, SENT, FAILED, SKIPPED, LOGGED_ONLY
    recipient: str
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class NotificationRecordResponse(BaseModel):
    """Audit schema for external API."""
    notification_id: str
    alert_id: str
    well_code: str
    channel: str
    recipient: str
    status: str
    provider_message_id: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    sent_at: Optional[datetime] = None
