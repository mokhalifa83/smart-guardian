"""
Smart Guardian Notification Layer - WhatsApp Early Warning Notification Service (Prompt 5)
========================================================================================
Act as a Senior Full-Stack Engineer + Real-Time Alerting Engineer + WhatsApp Integration Engineer.
Provides WhatsApp as an additional independent notification channel consuming canonical NotificationContext.

Architecture Rules:
1. Downstream consumer only: Does NOT create alerts, thresholds, diagnoses, or calculate eligibility.
2. Safe Default: WHATSAPP_NOTIFICATION_MODE = "LOG_ONLY". Never calls external API in LOG_ONLY.
3. Explicit logging in LOG_ONLY: "NO REAL WHATSAPP MESSAGE SENT".
4. Provider: WhatsApp Business Platform / Cloud API (Meta Graph API) via externalized configuration.
5. Independent Channel: WhatsApp delivery status is completely independent from Email delivery status.
6. Failure Isolated: Provider failure or timeout does NOT invalidate Alert creation or Email.
7. Security: Zero hardcoded credentials, zero secret leakage in logs or exceptions.
"""

import asyncio
import re
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.schemas.notification import NotificationContext, NotificationDeliveryResult, NotificationStatus


class WhatsAppNotificationService:
    """
    Canonical WhatsApp Early Warning Notification Service.
    Acts as a secure, production-grade communication adapter for an already-authorized NotificationContext.
    """

    @classmethod
    def format_early_warning_message(cls, context: NotificationContext) -> str:
        """
        Formats concise, operational, and evidence-based message text.
        Preserves the strict distinction:
        Observed Measurement -> Analysis Result -> Diagnostic Interpretation -> Required Confirmation.
        Does NOT fabricate root causes or unsupported diagnoses.
        """
        wc_str = f"{context.water_cut:.1f}%" if context.water_cut is not None else "DATA_UNAVAILABLE"
        thresh_str = f"{context.threshold:.1f}%" if context.threshold is not None else "N/A"
        ts_str = context.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

        # Compile supporting evidence summary safely without leaking internal memory references
        evidence_summary = "Threshold exceedance detected by surveillance engine."
        if context.evidence:
            details = [f"{k}: {v}" for k, v in context.evidence.items() if isinstance(v, (str, int, float, bool))]
            if details:
                evidence_summary = ", ".join(details[:3])

        message_lines = [
            "SMART GUARDIAN — EARLY WARNING",
            f"Well: {context.well_code}",
            f"Water Cut: {wc_str} (Threshold: {thresh_str})",
            f"Severity: {context.severity}",
            f"Diagnosis: {context.diagnosis}",
            f"Timestamp: {ts_str}",
            f"Data Source: {context.data_source}",
            f"Data Quality: {context.data_quality}",
            f"Supporting Evidence: {evidence_summary}",
            f"Recommended Engineering Review: {context.recommended_engineering_review}"
        ]
        return "\n".join(message_lines)

    @classmethod
    async def send_early_warning_whatsapp(
        cls,
        notification_context: NotificationContext,
        recipient_override: Optional[str] = None
    ) -> NotificationDeliveryResult:
        """
        Preferred interface:
        Consumes the already-authorized structured notification context produced by the Alert architecture.
        Executes delivery independently from other notification channels.
        """
        # Determine target recipient(s)
        recipients = [recipient_override] if recipient_override else settings.WHATSAPP_RECIPIENTS
        target_recipient = recipients[0] if recipients else "+10000000000"  # Fallback dummy for logging if unconfigured

        mode = (settings.WHATSAPP_NOTIFICATION_MODE or settings.NOTIFICATION_MODE).upper()

        logger.info(
            f"WHATSAPP_NOTIFICATION_REQUESTED for well {notification_context.well_code}",
            extra={"structured_data": {
                "event": "WHATSAPP_NOTIFICATION_REQUESTED",
                "well_code": notification_context.well_code,
                "alert_id": notification_context.alert_id,
                "severity": notification_context.severity,
                "notification_mode": mode
            }}
        )

        # -------------------------------------------------------------
        # 1. SAFE DEFAULT: LOG_ONLY MODE
        # -------------------------------------------------------------
        if mode == "LOG_ONLY" or not settings.WHATSAPP_API_TOKEN or not settings.WHATSAPP_PHONE_NUMBER_ID:
            # Explicitly log LOG_ONLY warning and state NO REAL WHATSAPP MESSAGE SENT
            logger.warning(
                f"WHATSAPP EARLY WARNING PREVIEW [LOG_ONLY]: "
                f"Well {notification_context.well_code} "
                f"WC={notification_context.water_cut}% "
                f"NO REAL WHATSAPP MESSAGE SENT",
                extra={"structured_data": {
                    "event": "WHATSAPP_NOTIFICATION_LOGGED",
                    "well_code": notification_context.well_code,
                    "alert_id": notification_context.alert_id,
                    "severity": notification_context.severity,
                    "water_cut": notification_context.water_cut,
                    "recipient": target_recipient,
                    "notification_mode": "LOG_ONLY"
                }}
            )
            return NotificationDeliveryResult(
                channel="WHATSAPP",
                status=NotificationStatus.LOGGED_ONLY.value,
                recipient=target_recipient,
                provider_message_id=None,
                error_message=None,
                timestamp=datetime.now(timezone.utc)
            )

        # -------------------------------------------------------------
        # 2. ACTIVE PRODUCTION DELIVERY: WhatsApp Business Cloud API
        # -------------------------------------------------------------
        message_body = cls.format_early_warning_message(notification_context)
        endpoint = f"{settings.WHATSAPP_API_BASE_URL.rstrip('/')}/{settings.WHATSAPP_PHONE_NUMBER_ID}/messages"

        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json"
        }

        # Sanitize recipient phone number to digits only (e.g. +46-73-557-02-41 -> 46735570241)
        clean_recipient = re.sub(r"\D", "", target_recipient)

        # Build payload: Text message format (or template format if configured)
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_recipient,
            "type": "text",
            "text": {
                "preview_url": False,
                "body": message_body
            }
        }

        timeout = httpx.Timeout(settings.WHATSAPP_TIMEOUT_SECONDS)
        max_retries = max(1, settings.WHATSAPP_MAX_RETRIES)
        last_error: Optional[str] = None

        for attempt in range(1, max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(endpoint, json=payload, headers=headers)

                    # Handle 2xx Success
                    if response.status_code in {200, 201, 202}:
                        resp_json = response.json() if response.content else {}
                        messages_arr = resp_json.get("messages", [])
                        provider_msg_id = messages_arr[0].get("id") if messages_arr else None

                        logger.info(
                            f"WHATSAPP_NOTIFICATION_SENT: Well {notification_context.well_code} to {target_recipient}",
                            extra={"structured_data": {
                                "event": "WHATSAPP_NOTIFICATION_SENT",
                                "well_code": notification_context.well_code,
                                "alert_id": notification_context.alert_id,
                                "recipient": target_recipient,
                                "provider_message_id": provider_msg_id,
                                "http_status": response.status_code
                            }}
                        )
                        return NotificationDeliveryResult(
                            channel="WHATSAPP",
                            status=NotificationStatus.SENT.value,
                            recipient=target_recipient,
                            provider_message_id=provider_msg_id,
                            error_message=None,
                            timestamp=datetime.now(timezone.utc)
                        )

                    # Handle 401/403 Authentication Error - Do NOT retry
                    elif response.status_code in {401, 403}:
                        last_error = f"AUTHENTICATION_ERROR: HTTP {response.status_code} - Invalid or expired WhatsApp API token."
                        logger.error(
                            "WHATSAPP_NOTIFICATION_FAILED: Provider authentication failed (check WHATSAPP_API_TOKEN)",
                            extra={"structured_data": {
                                "event": "WHATSAPP_NOTIFICATION_FAILED",
                                "well_code": notification_context.well_code,
                                "alert_id": notification_context.alert_id,
                                "http_status": response.status_code
                            }}
                        )
                        break

                    # Handle 429 Rate Limit - Wait if retries remaining
                    elif response.status_code == 429:
                        last_error = "RATE_LIMITED: WhatsApp API request limit exceeded."
                        logger.warning(
                            "WHATSAPP_PROVIDER_RATE_LIMITED: Throttled by provider.",
                            extra={"structured_data": {
                                "event": "WHATSAPP_PROVIDER_RATE_LIMITED",
                                "well_code": notification_context.well_code,
                                "attempt": attempt
                            }}
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(1.0 * attempt)
                            continue
                        break

                    # Handle 4xx Client Error - Do NOT retry (bad recipient, invalid json)
                    elif 400 <= response.status_code < 500:
                        last_error = f"INVALID_REQUEST: HTTP {response.status_code} - Client request rejected by provider."
                        logger.error(
                            f"WHATSAPP_NOTIFICATION_FAILED: Client error HTTP {response.status_code}",
                            extra={"structured_data": {
                                "event": "WHATSAPP_NOTIFICATION_FAILED",
                                "well_code": notification_context.well_code,
                                "http_status": response.status_code
                            }}
                        )
                        break

                    # Handle 5xx Server Error - Bounded retry
                    else:
                        last_error = f"PROVIDER_UNAVAILABLE: HTTP {response.status_code} server error."
                        logger.warning(
                            f"WHATSAPP_PROVIDER_5XX: HTTP {response.status_code} on attempt {attempt}/{max_retries}",
                            extra={"structured_data": {
                                "event": "WHATSAPP_PROVIDER_5XX",
                                "well_code": notification_context.well_code,
                                "attempt": attempt
                            }}
                        )
                        if attempt < max_retries:
                            await asyncio.sleep(0.5 * attempt)
                            continue

            except httpx.TimeoutException:
                last_error = "PROVIDER_TIMEOUT: Request timed out reaching WhatsApp API gateway."
                logger.warning(
                    f"WHATSAPP_PROVIDER_TIMEOUT on attempt {attempt}/{max_retries}",
                    extra={"structured_data": {
                        "event": "WHATSAPP_PROVIDER_TIMEOUT",
                        "well_code": notification_context.well_code,
                        "attempt": attempt
                    }}
                )
                if attempt < max_retries:
                    await asyncio.sleep(0.5 * attempt)
                    continue

            except Exception as exc:
                last_error = f"COMMUNICATION_ERROR: {type(exc).__name__}"
                logger.error(
                    f"WHATSAPP_NOTIFICATION_FAILED: Unexpected error: {type(exc).__name__}",
                    extra={"structured_data": {
                        "event": "WHATSAPP_NOTIFICATION_FAILED",
                        "well_code": notification_context.well_code,
                        "error_type": type(exc).__name__
                    }}
                )
                break

        # If loop finishes without returning success, record failure safely
        return NotificationDeliveryResult(
            channel="WHATSAPP",
            status=NotificationStatus.FAILED.value,
            recipient=target_recipient,
            provider_message_id=None,
            error_message=last_error or "Unknown delivery error",
            timestamp=datetime.now(timezone.utc)
        )
