import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from app.database.session import Base


class NotificationRecord(Base):
    """
    Persistent audit record for outbound early warning notifications (Email & WhatsApp).
    Provides strict traceability:
    Notification -> Alert -> AnalysisResult -> Well.
    """
    __tablename__ = "notifications"

    notification_id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    alert_id = Column(String(36), ForeignKey("alerts.alert_id", ondelete="CASCADE"), nullable=False, index=True)
    well_code = Column(String(50), ForeignKey("wells.well_code", ondelete="CASCADE"), nullable=False, index=True)
    channel = Column(String(20), nullable=False)  # EMAIL, WHATSAPP
    recipient = Column(String(150), nullable=False)
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING, SENT, FAILED, SKIPPED, LOGGED_ONLY
    provider_message_id = Column(String(100), nullable=True)
    error_message = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    sent_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_notifications_alert_channel", "alert_id", "channel"),
        Index("ix_notifications_well_channel", "well_code", "channel"),
    )

    alert = relationship("Alert", back_populates="notifications")
    well = relationship("Well")
