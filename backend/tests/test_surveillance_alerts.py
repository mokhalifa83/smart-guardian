import pytest
from datetime import datetime, timezone
from app.services.surveillance import SurveillanceService
from app.services.alert_service import AlertService
from app.models.well import Well
from app.models.well_config import WellConfig
from app.models.alert import Alert
from app.schemas.common import DataQualityStatus, SourceCategory, SurveillanceState, AlertStatus, AlertSeverity


@pytest.mark.asyncio
async def test_water_cut_threshold_exceeded_creates_alert(db_session):
    well_code = "WELL-AL-01"
    well = Well(well_code=well_code, field_name="Ghawar", status="ACTIVE")
    db_session.add(well)
    # Configure threshold at 75%
    cfg = WellConfig(well_code=well_code, wc_threshold=75.0, alert_cooldown_minutes=60)
    db_session.add(cfg)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    # Observed water cut 82.5% > 75.0%
    state, analysis, alert = await SurveillanceService.evaluate_water_cut_surveillance(
        db=db_session,
        well_code=well_code,
        wc_percent=82.5,
        timestamp=now,
        source=SourceCategory.SOFTWARE_API,
        quality_status=DataQualityStatus.VALID
    )

    assert state == SurveillanceState.WARNING
    assert alert is not None
    assert alert.alert_type == "WATER_CUT"
    assert alert.severity == "WARNING"
    assert "WATER_CUT_THRESHOLD_EXCEEDED" in alert.message
    # Engineering principle: Verify NO unverified reservoir root-cause claims
    assert "CONING" not in alert.message
    assert "CHANNELING" not in alert.message
    assert "FRACTURE" not in alert.message
    assert "CEMENT FAILURE" not in alert.message


@pytest.mark.asyncio
async def test_water_cut_normal_no_alert(db_session):
    well_code = "WELL-AL-02"
    well = Well(well_code=well_code, field_name="Safaniya", status="ACTIVE")
    db_session.add(well)
    cfg = WellConfig(well_code=well_code, wc_threshold=80.0, alert_cooldown_minutes=60)
    db_session.add(cfg)
    await db_session.commit()

    now = datetime.now(timezone.utc)
    # Observed 45.0% < 80.0%
    state, analysis, alert = await SurveillanceService.evaluate_water_cut_surveillance(
        db=db_session,
        well_code=well_code,
        wc_percent=45.0,
        timestamp=now,
        source=SourceCategory.SOFTWARE_API,
        quality_status=DataQualityStatus.VALID
    )

    assert state == SurveillanceState.NORMAL
    assert alert is None
    assert analysis.status == "NORMAL"


@pytest.mark.asyncio
async def test_alert_cooldown_duplicate_suppression(db_session):
    well_code = "WELL-AL-03"
    well = Well(well_code=well_code, field_name="Zuluf", status="ACTIVE")
    db_session.add(well)
    cfg = WellConfig(well_code=well_code, wc_threshold=70.0, alert_cooldown_minutes=60)
    db_session.add(cfg)
    await db_session.commit()

    now = datetime.now(timezone.utc)

    # First exceedance -> generates alert
    state1, _, alert1 = await SurveillanceService.evaluate_water_cut_surveillance(
        db=db_session,
        well_code=well_code,
        wc_percent=85.0,
        timestamp=now,
        source=SourceCategory.SOFTWARE_API,
        quality_status=DataQualityStatus.VALID
    )
    assert alert1 is not None

    # Second exceedance within cooldown -> alert suppressed (returns existing active alert)
    state2, _, alert2 = await SurveillanceService.evaluate_water_cut_surveillance(
        db=db_session,
        well_code=well_code,
        wc_percent=86.0,
        timestamp=now,
        source=SourceCategory.SOFTWARE_API,
        quality_status=DataQualityStatus.VALID
    )
    assert alert2.alert_id == alert1.alert_id


@pytest.mark.asyncio
async def test_alert_acknowledgement_and_resolution_lifecycle(db_session):
    well_code = "WELL-AL-04"
    well = Well(well_code=well_code, field_name="Karan", status="ACTIVE")
    db_session.add(well)
    await db_session.commit()

    alert = await AlertService.create_or_suppress_alert(
        db=db_session,
        well_code=well_code,
        alert_type="WATER_CUT",
        severity=AlertSeverity.WARNING,
        message="Test alert",
        value=85.0,
        threshold=80.0,
        timestamp=datetime.now(timezone.utc),
        cooldown_minutes=60
    )
    assert alert.status == AlertStatus.ACTIVE.value

    # Acknowledge
    ack_alert = await AlertService.acknowledge_alert(db_session, alert.alert_id, "petroleum-eng-1")
    assert ack_alert.status == AlertStatus.ACKNOWLEDGED.value
    assert ack_alert.acknowledged_at is not None

    # Resolve
    res_alert = await AlertService.resolve_alert(db_session, alert.alert_id, "petroleum-eng-1", "Water shut-off initiated")
    assert res_alert.status == AlertStatus.RESOLVED.value
    assert res_alert.resolved_at is not None
