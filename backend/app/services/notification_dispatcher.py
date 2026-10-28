"""
Smart Guardian Notification Layer - Multi-Channel Notification Dispatcher
========================================================================
Implements the canonical downstream notification pipeline:
Alert Created
↓
Existing Notification Eligibility
↓
Existing Notification Event / Context
↓
┌──────────────────────┐
↓                      ↓
Email Notification     WhatsApp Notification
(PROMPT 4)              (PROMPT 5)
↓                      ↓
└──────────┬───────────┘
↓
Persistent Audit Storage & Dashboard Traceability

Enforces:
1. Strict Channel Independence: Failure in Email does not block WhatsApp; failure in WhatsApp does not block Email.
2. Failure Isolation: Notification failures never roll back Alert creation or persistence.
3. Cooldown & Deduplication: Notifications are only dispatched for authorized new/eligible alerts.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import logger
from app.models.alert import Alert
from app.models.analysis import AnalysisResult
from app.models.notification import NotificationRecord
from app.schemas.notification import NotificationContext, NotificationDeliveryResult
from app.services.email_service import EmailNotificationService
from app.services.whatsapp_service import WhatsAppNotificationService


class NotificationDispatcher:
    """
    Downstream Notification Dispatcher.
    Coordinates independent delivery to Email and WhatsApp channels with persistent audit logging.
    """

    @classmethod
    def build_notification_context(
        cls,
        alert: Alert,
        analysis: Optional[AnalysisResult] = None,
        diagnosis_override: Optional[str] = None
    ) -> NotificationContext:
        """
        Builds the canonical NotificationContext from authoritative Alert and Analysis entities.
        Does NOT invent missing data or unsupported diagnoses.
        """
        # Diagnosis: Use explicit diagnosis if established, otherwise default to neutral diagnostic condition
        diagnosis = diagnosis_override or (
            "WATER_CUT_THRESHOLD_EXCEEDED" if alert.alert_type == "WATER_CUT" else alert.alert_type
        )
        if analysis and analysis.status == "DATA_UNAVAILABLE":
            diagnosis = "DATA_UNAVAILABLE"

        # Evidence dictionary
        evidence: Dict[str, Any] = {
            "alert_message": alert.message,
            "threshold": alert.threshold,
            "observed_value": alert.value,
            "source": alert.source
        }
        if analysis and analysis.diagnostic_details:
            evidence["analysis_diagnostic"] = analysis.diagnostic_details

        return NotificationContext(
            alert_id=alert.alert_id,
            well_code=alert.well_code,
            severity=alert.severity,
            alert_status=alert.status,
            water_cut=alert.value,
            threshold=alert.threshold,
            timestamp=alert.timestamp,
            data_source=alert.source,
            data_quality=analysis.data_quality if analysis else "VALID",
            analysis_result=analysis.status if analysis else alert.severity,
            diagnosis=diagnosis,
            evidence=evidence,
            recommended_engineering_review="Review well test data and verify choke status before physical field intervention.",
            notification_eligibility=True,
            notification_metadata={"dispatched_at": datetime.now(timezone.utc).isoformat()}
        )

    @classmethod
    async def dispatch_alert_notifications(
        cls,
        db: AsyncSession,
        alert: Alert,
        analysis: Optional[AnalysisResult] = None,
        is_new_alert: bool = True
    ) -> Dict[str, NotificationDeliveryResult]:
        """
        Dispatches early warning notifications across all configured independent channels.
        Strictly enforces:
        - Downstream of alert cooldown: If is_new_alert is False, skips dispatch to prevent duplicate storms.
        - Failure isolation: Never rolls back database transactions if a delivery channel fails.
        """
        # Cooldown / Duplicate check: If not eligible, skip
        if not is_new_alert or alert.status != "ACTIVE":
            logger.info(
                f"Notification skipped for well {alert.well_code}: Alert {alert.alert_id} suppressed by cooldown or not active",
                extra={"structured_data": {"event": "NOTIFICATION_SKIPPED_COOLDOWN", "alert_id": alert.alert_id}}
            )
            return {}

        context = cls.build_notification_context(alert, analysis)
        results: Dict[str, NotificationDeliveryResult] = {}

        # -------------------------------------------------------------
        # Channel 1: Email Notification (Prompt 4)
        # -------------------------------------------------------------
        try:
            email_result = await EmailNotificationService.send_early_warning_email(context)
            results["EMAIL"] = email_result
        except Exception as exc:
            logger.error(f"Email dispatch unhandled exception: {exc}")
            results["EMAIL"] = NotificationDeliveryResult(
                channel="EMAIL",
                status="FAILED",
                recipient="control-room",
                error_message=str(exc)
            )

        # -------------------------------------------------------------
        # Channel 2: WhatsApp Notification (Prompt 5) - Supports Multiple Recipients
        # -------------------------------------------------------------
        whatsapp_recipients = settings.WHATSAPP_RECIPIENTS or ["+10000000000"]
        whatsapp_delivery_results = []
        for rec in whatsapp_recipients:
            try:
                wa_res = await WhatsAppNotificationService.send_early_warning_whatsapp(context, recipient_override=rec)
                whatsapp_delivery_results.append(wa_res)
            except Exception as exc:
                logger.error(f"WhatsApp dispatch unhandled exception for {rec}: {exc}")
                whatsapp_delivery_results.append(
                    NotificationDeliveryResult(
                        channel="WHATSAPP",
                        status="FAILED",
                        recipient=rec,
                        error_message=str(exc)
                    )
                )

        if whatsapp_delivery_results:
            results["WHATSAPP"] = whatsapp_delivery_results[0]

        # -------------------------------------------------------------
        # Persistent Notification Audit Records
        # -------------------------------------------------------------
        try:
            # Audit email result
            if "EMAIL" in results:
                email_res = results["EMAIL"]
                db.add(
                    NotificationRecord(
                        alert_id=alert.alert_id,
                        well_code=alert.well_code,
                        channel="EMAIL",
                        recipient=email_res.recipient,
                        status=email_res.status,
                        provider_message_id=email_res.provider_message_id,
                        error_message=email_res.error_message,
                        sent_at=email_res.timestamp if email_res.status in {"SENT", "LOGGED_ONLY"} else None
                    )
                )

            # Audit all WhatsApp recipient results
            for wa_res in whatsapp_delivery_results:
                db.add(
                    NotificationRecord(
                        alert_id=alert.alert_id,
                        well_code=alert.well_code,
                        channel="WHATSAPP",
                        recipient=wa_res.recipient,
                        status=wa_res.status,
                        provider_message_id=wa_res.provider_message_id,
                        error_message=wa_res.error_message,
                        sent_at=wa_res.timestamp if wa_res.status in {"SENT", "LOGGED_ONLY"} else None
                    )
                )

            await db.commit()
        except Exception as audit_exc:
            logger.error(f"Failed to record notification audit: {audit_exc}")
            # Failure to record audit must NOT rollback the already committed Alert

        return results
