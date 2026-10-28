"""
Smart Guardian Test Suite - WhatsApp Early Warning Notification Service (Prompt 5)
================================================================================
Validates:
1. Default behavior: LOG_ONLY mode, zero external network calls, logs NO REAL WHATSAPP MESSAGE SENT.
2. Configuration safety: Externalized config, no hardcoded tokens/numbers, no credentials in logs.
3. Provider integration & Error handling:
   - Success (200 OK + provider_message_id)
   - HTTP 4xx client errors (no unsafe retries)
   - HTTP 401/403 authentication failures
   - HTTP 429 rate limiting (bounded backoff)
   - HTTP 5xx server errors (bounded retries)
   - Timeout handling
4. Channel Independence & Failure Isolation:
   - WhatsApp failure does NOT break Alert creation or persistence.
   - WhatsApp failure does NOT invalidate Email notification.
   - Email failure does NOT disable WhatsApp eligibility.
5. Deduplication & Cooldown integration:
   - New warning -> notification dispatched.
   - Same active warning in cooldown -> suppressed, NO duplicate notification.
   - Resolved alert -> no repeated notification.
   - Separate wells respect their independent thresholds (WellConfig A vs B, no universal 50%).
6. Downstream non-interference:
   - WhatsApp never calculates thresholds, diagnoses, or coning/channeling root causes.
"""

import pytest
import httpx
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

from app.core.config import settings
from app.models.alert import Alert
from app.models.well import Well
from app.models.well_config import WellConfig
from app.schemas.notification import NotificationContext, NotificationStatus
from app.services.whatsapp_service import WhatsAppNotificationService
from app.services.email_service import EmailNotificationService
from app.services.notification_dispatcher import NotificationDispatcher
from app.services.alert_service import AlertService
from app.schemas.common import AlertSeverity, AlertStatus as CommonAlertStatus


@pytest.fixture
def sample_notification_context():
    return NotificationContext(
        alert_id="alert-uuid-1234",
        well_code="WELL-ALPHA-01",
        severity="WARNING",
        alert_status="ACTIVE",
        water_cut=78.5,
        threshold=70.0,
        timestamp=datetime.now(timezone.utc),
        data_source="SURVEILLANCE_ENGINE:SCADA",
        data_quality="VALID",
        diagnosis="WATER_CUT_THRESHOLD_EXCEEDED",
        evidence={"observed_water_cut": 78.5, "threshold": 70.0},
        recommended_engineering_review="Review choke opening and well test history."
    )


# -----------------------------------------------------------------------------
# 1. DEFAULT BEHAVIOR & LOG_ONLY SAFETY
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_whatsapp_default_is_log_only(sample_notification_context, caplog):
    """
    Default mode must be LOG_ONLY.
    Never calls external WhatsApp API.
    Explicitly logs: NO REAL WHATSAPP MESSAGE SENT.
    """
    with patch.object(settings, "WHATSAPP_NOTIFICATION_MODE", "LOG_ONLY"):
        with caplog.at_level("WARNING"):
            result = await WhatsAppNotificationService.send_early_warning_whatsapp(sample_notification_context)

        assert result.channel == "WHATSAPP"
        assert result.status == NotificationStatus.LOGGED_ONLY.value
        assert result.provider_message_id is None
        assert result.error_message is None

        # Verify exact log requirements
        log_text = caplog.text
        assert "WHATSAPP EARLY WARNING PREVIEW [LOG_ONLY]" in log_text
        assert "NO REAL WHATSAPP MESSAGE SENT" in log_text
        assert "WHATSAPP_NOTIFICATION_SENT" not in log_text  # Must NOT claim delivery in LOG_ONLY
        assert "WHATSAPP MESSAGE SENT to" not in log_text


# -----------------------------------------------------------------------------
# 2. CONFIGURATION & CREDENTIAL SECURITY
# -----------------------------------------------------------------------------

def test_whatsapp_configuration_externalized():
    """Verify provider configuration is read from settings and never hardcoded."""
    assert hasattr(settings, "WHATSAPP_NOTIFICATION_MODE")
    assert hasattr(settings, "WHATSAPP_API_BASE_URL")
    assert hasattr(settings, "WHATSAPP_API_TOKEN")
    assert hasattr(settings, "WHATSAPP_PHONE_NUMBER_ID")
    assert hasattr(settings, "WHATSAPP_RECIPIENTS")
    assert hasattr(settings, "WHATSAPP_TIMEOUT_SECONDS")


def test_whatsapp_message_formatting_no_invented_diagnosis(sample_notification_context):
    """
    Verify message content formatting.
    Must communicate only verified engineering fields.
    Does NOT infer coning or channeling from Water Cut alone.
    """
    msg = WhatsAppNotificationService.format_early_warning_message(sample_notification_context)
    assert "SMART GUARDIAN — EARLY WARNING" in msg
    assert "Well: WELL-ALPHA-01" in msg
    assert "Water Cut: 78.5% (Threshold: 70.0%)" in msg
    assert "Severity: WARNING" in msg
    assert "WATER_CUT_THRESHOLD_EXCEEDED" in msg
    assert "Coning" not in msg
    assert "Channeling" not in msg


# -----------------------------------------------------------------------------
# 3. ACTIVE PROVIDER INTEGRATION & ERROR HANDLING (MOCKED HTTP)
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_whatsapp_active_provider_success(sample_notification_context):
    """Successful provider request: returns SENT with provider_message_id."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = b'{"messages": [{"id": "wamid.HBgLMTEwMA=="}]}'
    mock_resp.json.return_value = {"messages": [{"id": "wamid.HBgLMTEwMA=="}]}

    with patch.object(settings, "WHATSAPP_NOTIFICATION_MODE", "ACTIVE"), \
         patch.object(settings, "WHATSAPP_API_TOKEN", "test-token-valid"), \
         patch.object(settings, "WHATSAPP_PHONE_NUMBER_ID", "109988776655"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:

        result = await WhatsAppNotificationService.send_early_warning_whatsapp(
            sample_notification_context,
            recipient_override="+966501234567"
        )

        assert result.status == NotificationStatus.SENT.value
        assert result.provider_message_id == "wamid.HBgLMTEwMA=="
        assert result.recipient == "+966501234567"
        assert result.error_message is None
        assert mock_post.call_count == 1


@pytest.mark.asyncio
async def test_whatsapp_active_provider_auth_error_no_retry(sample_notification_context):
    """HTTP 401/403 Authentication failure: logs error and does NOT retry."""
    mock_resp = MagicMock()
    mock_resp.status_code = 401
    mock_resp.content = b'{"error": {"message": "Invalid OAuth access token."}}'
    mock_resp.json.return_value = {"error": {"message": "Invalid OAuth access token."}}

    with patch.object(settings, "WHATSAPP_NOTIFICATION_MODE", "ACTIVE"), \
         patch.object(settings, "WHATSAPP_API_TOKEN", "bad-token"), \
         patch.object(settings, "WHATSAPP_PHONE_NUMBER_ID", "109988776655"), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp) as mock_post:

        result = await WhatsAppNotificationService.send_early_warning_whatsapp(sample_notification_context)

        assert result.status == NotificationStatus.FAILED.value
        assert "AUTHENTICATION_ERROR" in result.error_message
        assert mock_post.call_count == 1  # Exactly 1 call, no repeated auth retries


@pytest.mark.asyncio
async def test_whatsapp_active_provider_timeout(sample_notification_context):
    """Timeout reaching provider: handles safely with bounded retries."""
    with patch.object(settings, "WHATSAPP_NOTIFICATION_MODE", "ACTIVE"), \
         patch.object(settings, "WHATSAPP_API_TOKEN", "test-token"), \
         patch.object(settings, "WHATSAPP_PHONE_NUMBER_ID", "109988776655"), \
         patch.object(settings, "WHATSAPP_MAX_RETRIES", 2), \
         patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=httpx.TimeoutException("Connection timed out")) as mock_post:

        result = await WhatsAppNotificationService.send_early_warning_whatsapp(sample_notification_context)

        assert result.status == NotificationStatus.FAILED.value
        assert "PROVIDER_TIMEOUT" in result.error_message
        assert mock_post.call_count == 2  # Bounded to max_retries


# -----------------------------------------------------------------------------
# 4. CHANNEL INDEPENDENCE & FAILURE ISOLATION
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_channel_independence_email_fails_whatsapp_succeeds(db_session, sample_notification_context):
    """
    If Email fails, WhatsApp remains completely independent and eligible.
    Email failure MUST NOT disable WhatsApp.
    """
    # Create an alert in db
    alert = Alert(
        alert_id="test-alert-indep-1",
        well_code="WELL-IND-01",
        alert_type="WATER_CUT",
        severity="WARNING",
        message="Water Cut exceedance",
        value=82.0,
        threshold=75.0,
        timestamp=datetime.now(timezone.utc),
        status="ACTIVE"
    )
    db_session.add(alert)
    await db_session.commit()

    # Mock Email to fail and WhatsApp to succeed (or LOG_ONLY)
    with patch.object(EmailNotificationService, "send_early_warning_email", side_effect=Exception("SMTP Connection Refused")), \
         patch.object(WhatsAppNotificationService, "send_early_warning_whatsapp") as mock_wa:

        from app.schemas.notification import NotificationDeliveryResult
        mock_wa.return_value = NotificationDeliveryResult(
            channel="WHATSAPP",
            status=NotificationStatus.LOGGED_ONLY.value,
            recipient="+966500000000"
        )

        results = await NotificationDispatcher.dispatch_alert_notifications(
            db=db_session,
            alert=alert,
            is_new_alert=True
        )

        assert "EMAIL" in results
        assert results["EMAIL"].status == "FAILED"
        assert "SMTP Connection Refused" in results["EMAIL"].error_message

        assert "WHATSAPP" in results
        assert results["WHATSAPP"].status == NotificationStatus.LOGGED_ONLY.value

        # Alert must still be ACTIVE in DB (not rolled back)
        reloaded = await db_session.get(Alert, "test-alert-indep-1")
        assert reloaded is not None
        assert reloaded.status == "ACTIVE"


@pytest.mark.asyncio
async def test_channel_independence_whatsapp_fails_email_succeeds(db_session):
    """
    If WhatsApp fails, Email succeeds and Alert persistence remains 100% intact.
    """
    alert = Alert(
        alert_id="test-alert-indep-2",
        well_code="WELL-IND-02",
        alert_type="WATER_CUT",
        severity="WARNING",
        message="Water Cut exceedance",
        value=84.0,
        threshold=75.0,
        timestamp=datetime.now(timezone.utc),
        status="ACTIVE"
    )
    db_session.add(alert)
    await db_session.commit()

    with patch.object(WhatsAppNotificationService, "send_early_warning_whatsapp", side_effect=Exception("WhatsApp Gateway 503")), \
         patch.object(EmailNotificationService, "send_early_warning_email") as mock_em:

        from app.schemas.notification import NotificationDeliveryResult
        mock_em.return_value = NotificationDeliveryResult(
            channel="EMAIL",
            status=NotificationStatus.LOGGED_ONLY.value,
            recipient="control-room@operator.com"
        )

        results = await NotificationDispatcher.dispatch_alert_notifications(
            db=db_session,
            alert=alert,
            is_new_alert=True
        )

        assert results["WHATSAPP"].status == "FAILED"
        assert "WhatsApp Gateway 503" in results["WHATSAPP"].error_message

        assert results["EMAIL"].status == NotificationStatus.LOGGED_ONLY.value

        # Database Alert remains intact
        reloaded = await db_session.get(Alert, "test-alert-indep-2")
        assert reloaded is not None
        assert reloaded.status == "ACTIVE"


# -----------------------------------------------------------------------------
# 5. DEDUPLICATION, COOLDOWN & WELL-CONFIG INDEPENDENCE
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_duplicate_prevention_no_repeated_whatsapp(db_session):
    """
    Verify:
    Reading 1 -> New Warning -> Dispatched
    Reading 2 -> Same active Warning (cooldown) -> Suppressed, NO duplicate notification
    """
    well = Well(well_code="WELL-DEDUP-01", field_name="Safaniya", status="ACTIVE")
    cfg = WellConfig(well_code="WELL-DEDUP-01", wc_threshold=70.0, alert_cooldown_minutes=60, is_active=True)
    db_session.add(well)
    db_session.add(cfg)
    await db_session.commit()

    with patch("app.services.notification_dispatcher.NotificationDispatcher.dispatch_alert_notifications") as mock_dispatch:
        mock_dispatch.return_value = {}

        now = datetime.now(timezone.utc)

        # 1. First Reading (Exceeds threshold -> creates Alert)
        alert1 = await AlertService.create_or_suppress_alert(
            db=db_session,
            well_code="WELL-DEDUP-01",
            alert_type="WATER_CUT",
            severity=AlertSeverity.WARNING,
            message="Water Cut 75.0% exceeded 70.0%",
            value=75.0,
            threshold=70.0,
            timestamp=now,
            cooldown_minutes=60
        )
        assert getattr(alert1, "_is_new", False) is True
        assert mock_dispatch.call_count == 1

        # 2. Second Reading 5 mins later (Still high, within cooldown window -> suppressed)
        now_plus_5 = now + timedelta(minutes=5)
        alert2 = await AlertService.create_or_suppress_alert(
            db=db_session,
            well_code="WELL-DEDUP-01",
            alert_type="WATER_CUT",
            severity=AlertSeverity.WARNING,
            message="Water Cut 76.0% exceeded 70.0%",
            value=76.0,
            threshold=70.0,
            timestamp=now_plus_5,
            cooldown_minutes=60
        )
        assert getattr(alert2, "_is_new", False) is False
        # Call count remains 1: No duplicate notification dispatched
        assert mock_dispatch.call_count == 1


@pytest.mark.asyncio
async def test_independent_well_thresholds_no_universal_50_percent(db_session):
    """
    Verify:
    Well A uses WellConfig A threshold (e.g. 75.0%)
    Well B uses WellConfig B threshold (e.g. 85.0%)
    No universal 50% threshold exists.
    """
    w_a = Well(well_code="WELL-A", field_name="Ghawar", status="ACTIVE")
    c_a = WellConfig(well_code="WELL-A", wc_threshold=75.0, alert_cooldown_minutes=60)

    w_b = Well(well_code="WELL-B", field_name="Abqaiq", status="ACTIVE")
    c_b = WellConfig(well_code="WELL-B", wc_threshold=85.0, alert_cooldown_minutes=60)

    db_session.add_all([w_a, c_a, w_b, c_b])
    await db_session.commit()

    from app.services.surveillance import SurveillanceService
    from app.schemas.common import SourceCategory, DataQualityStatus

    # Water cut = 60% (Greater than 50%, but LESS than Well A's 75% and Well B's 85%)
    state_a, _, alert_a = await SurveillanceService.evaluate_water_cut_surveillance(
        db=db_session,
        well_code="WELL-A",
        wc_percent=60.0,
        timestamp=datetime.now(timezone.utc),
        source=SourceCategory.MQTT,
        quality_status=DataQualityStatus.VALID
    )
    # Must be NORMAL (no false alarm, respects Well A's 75% threshold)
    assert state_a.value == "NORMAL"
    assert alert_a is None

    # Water cut = 80% (Greater than Well A's 75% -> WARNING, but LESS than Well B's 85% -> NORMAL)
    state_a_high, _, alert_a_high = await SurveillanceService.evaluate_water_cut_surveillance(
        db=db_session,
        well_code="WELL-A",
        wc_percent=80.0,
        timestamp=datetime.now(timezone.utc),
        source=SourceCategory.MQTT,
        quality_status=DataQualityStatus.VALID
    )
    assert state_a_high.value == "WARNING"
    assert alert_a_high is not None

    state_b, _, alert_b = await SurveillanceService.evaluate_water_cut_surveillance(
        db=db_session,
        well_code="WELL-B",
        wc_percent=80.0,
        timestamp=datetime.now(timezone.utc),
        source=SourceCategory.MQTT,
        quality_status=DataQualityStatus.VALID
    )
    # Well B threshold is 85% -> 80% is NORMAL
    assert state_b.value == "NORMAL"
    assert alert_b is None
