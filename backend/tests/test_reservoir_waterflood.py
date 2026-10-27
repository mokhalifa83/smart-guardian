import pytest
from datetime import datetime, timezone, timedelta
from app.services.reservoir.waterflood_engine import WaterfloodEngine, WaterfloodObservationPoint
from app.services.reservoir.contracts import EngineeringStatus


def test_waterflood_canonical_vrr_and_hall_diagnostic():
    """
    Surveillance history with 4 observation points.
    Verifies that canonical VRR is computed and Hall plot integral evaluates.
    """
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    pts = [
        WaterfloodObservationPoint(
            timestamp=t0 + timedelta(days=0),
            injection_rate_bpd=1000.0,
            wellhead_injection_pressure_psia=2200.0,
            offset_oil_rate_stbd=600.0,
            offset_water_rate_bpd=200.0,
            water_cut_pct=25.0
        ),
        WaterfloodObservationPoint(
            timestamp=t0 + timedelta(days=30),
            injection_rate_bpd=1000.0,
            wellhead_injection_pressure_psia=2250.0,
            offset_oil_rate_stbd=620.0,
            offset_water_rate_bpd=220.0,
            water_cut_pct=26.0
        ),
        WaterfloodObservationPoint(
            timestamp=t0 + timedelta(days=60),
            injection_rate_bpd=1050.0,
            wellhead_injection_pressure_psia=2300.0,
            offset_oil_rate_stbd=650.0,
            offset_water_rate_bpd=250.0,
            water_cut_pct=27.5
        ),
        WaterfloodObservationPoint(
            timestamp=t0 + timedelta(days=90),
            injection_rate_bpd=1100.0,
            wellhead_injection_pressure_psia=2350.0,
            offset_oil_rate_stbd=680.0,
            offset_water_rate_bpd=300.0,
            water_cut_pct=30.0
        ),
    ]

    res = WaterfloodEngine.analyze_waterflood_surveillance(
        history=pts,
        bo_rb_stb=1.25,
        bw_rb_stb=1.02,
        bg_rb_scf=0.00095,
        rs_scf_stb=500.0
    )

    assert res.status == EngineeringStatus.VALID.value
    # Canonical VRR must be evaluated
    assert res.value["canonical_vrr"] is not None
    assert res.value["canonical_vrr"] > 0
    # Hall plot pattern must be determined
    assert "hall_pattern" in res.value
    assert res.evidence["canonical_vrr_result"] is not None
    assert "hall_diagnostic" in res.evidence


def test_waterflood_insufficient_data():
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    pts = [
        WaterfloodObservationPoint(
            timestamp=t0,
            injection_rate_bpd=1000.0,
            offset_oil_rate_stbd=500.0
        )
    ]
    res = WaterfloodEngine.analyze_waterflood_surveillance(history=pts)
    assert res.status == EngineeringStatus.INSUFFICIENT_DATA.value
