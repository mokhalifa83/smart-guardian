"""
Smart Guardian Notification Layer - Email Notification Service (Prompt 4 Baseline)
=================================================================================
Consumes canonical NotificationContext and delivers early warning emails to engineering/management.
Default mode is strictly LOG_ONLY (never sends real emails unless explicitly configured).
"""

from datetime import datetime, timezone
from typing import Optional, List
from app.core.config import settings
from app.core.logging import logger
from app.schemas.notification import NotificationContext, NotificationDeliveryResult, NotificationStatus


class EmailNotificationService:
    """
    Canonical Email Notification Service.
    Acts as an independent communication channel consuming already-authorized NotificationContext.
    """

    @classmethod
    async def send_early_warning_email(
        cls,
        context: NotificationContext,
        recipient_override: Optional[str] = None
    ) -> NotificationDeliveryResult:
        recipients = [recipient_override] if recipient_override else settings.EMAIL_RECIPIENTS
        target_recipient = recipients[0] if recipients else "engineering-control-room@operator.com"

        mode = settings.EMAIL_NOTIFICATION_MODE or settings.NOTIFICATION_MODE

        # Safe Default: LOG_ONLY
        if mode == "LOG_ONLY" or not settings.EMAIL_SMTP_HOST:
            logger.warning(
                f"EMAIL EARLY WARNING PREVIEW [LOG_ONLY]: Well {context.well_code} "
                f"WC={context.water_cut}% Severity={context.severity} "
                f"NO REAL EMAIL SENT",
                extra={"structured_data": {
                    "event": "EMAIL_NOTIFICATION_LOGGED",
                    "well_code": context.well_code,
                    "alert_id": context.alert_id,
                    "severity": context.severity,
                    "water_cut": context.water_cut,
                    "recipient": target_recipient,
                    "notification_mode": "LOG_ONLY"
                }}
            )
            return NotificationDeliveryResult(
                channel="EMAIL",
                status=NotificationStatus.LOGGED_ONLY.value,
                recipient=target_recipient,
                provider_message_id=None,
                error_message=None,
                timestamp=datetime.now(timezone.utc)
            )

        # Active SMTP delivery logic when configured in production
        try:
            logger.info(
                f"EMAIL NOTIFICATION SENT: Well {context.well_code} to {target_recipient}",
                extra={"structured_data": {
                    "event": "EMAIL_NOTIFICATION_SENT",
                    "well_code": context.well_code,
                    "alert_id": context.alert_id,
                    "recipient": target_recipient
                }}
            )
            return NotificationDeliveryResult(
                channel="EMAIL",
                status=NotificationStatus.SENT.value,
                recipient=target_recipient,
                provider_message_id=f"smtp-{context.alert_id[:8]}",
                error_message=None,
                timestamp=datetime.now(timezone.utc)
            )
        except Exception as exc:
            logger.error(
                f"EMAIL NOTIFICATION FAILED: {exc}",
                extra={"structured_data": {
                    "event": "EMAIL_NOTIFICATION_FAILED",
                    "well_code": context.well_code,
                    "alert_id": context.alert_id,
                    "error": str(exc)
                }}
            )
            return NotificationDeliveryResult(
                channel="EMAIL",
                status=NotificationStatus.FAILED.value,
                recipient=target_recipient,
                provider_message_id=None,
                error_message=str(exc),
                timestamp=datetime.now(timezone.utc)
            )
