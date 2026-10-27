import pytest
import math
from datetime import datetime, timezone, timedelta
from app.services.reservoir.chan_engine import ChanDiagnosticEngine, ProductionTimePoint
from app.services.reservoir.contracts import EngineeringStatus


def test_chan_wor_calculation():
    # 75% WC -> WOR = 0.75 / 0.25 = 3.0
    res_wc = ChanDiagnosticEngine.calculate_single_wor(water_cut_pct=75.0)
    assert res_wc.status == EngineeringStatus.VALID.value
    assert float(res_wc.value) == 3.0

    # Rates: qo = 200, qw = 800 -> WOR = 4.0
    res_rates = ChanDiagnosticEngine.calculate_single_wor(oil_rate=200.0, water_rate=800.0)
    assert res_rates.status == EngineeringStatus.VALID.value
    assert float(res_rates.value) == 4.0


def test_chan_rule_16_wc_100_percent_undefined_wor():
    """
    Rule 16: At WC = 100% or qo = 0, WOR is infinite/undefined.
    Must return UNDEFINED_WOR. NEVER replaces denominator with arbitrary epsilon.
    """
    # Test with WC = 100%
    res_100 = ChanDiagnosticEngine.calculate_single_wor(water_cut_pct=100.0)
    assert res_100.status == EngineeringStatus.UNDEFINED_WOR.value
    assert res_100.value is None
    assert "ZERO_OIL_RATE_WC_100" in res_100.evidence["condition"]

    # Test with qo = 0
    res_qo_zero = ChanDiagnosticEngine.calculate_single_wor(oil_rate=0.0, water_rate=500.0)
    assert res_qo_zero.status == EngineeringStatus.UNDEFINED_WOR.value
    assert res_qo_zero.value is None


def test_chan_chronological_ordering_and_deduplication():
    """
    Verifies that Chan engine sorts disordered timestamps and eliminates duplicates.
    """
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t1 = t0 + timedelta(days=10)
    t2 = t0 + timedelta(days=20)

    # Supply out of order with a duplicate
    raw_points = [
        ProductionTimePoint(timestamp=t2, oil_rate=400.0, water_rate=1200.0),
        ProductionTimePoint(timestamp=t0, oil_rate=800.0, water_rate=200.0),
        ProductionTimePoint(timestamp=t1, oil_rate=600.0, water_rate=600.0),
        ProductionTimePoint(timestamp=t1, oil_rate=600.0, water_rate=600.0),  # Duplicate
    ]

    res = ChanDiagnosticEngine.compute_chan_diagnostic_series(raw_points, well_code="W-TEST")
    assert res.status == EngineeringStatus.VALID.value
    plot_pts = res.evidence["plot_points"]
    # Exactly 3 deduplicated points sorted chronologically
    assert len(plot_pts) == 3
    assert plot_pts[0]["elapsed_days"] < plot_pts[1]["elapsed_days"] < plot_pts[2]["elapsed_days"]


def test_chan_channeling_pattern_detection():
    """
    Simulates rapid channeling breakthrough (steep slope in WOR and WOR').
    """
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    # Steep exponential rise in water cut
    pts = [
        ProductionTimePoint(timestamp=t0 + timedelta(days=5), water_cut_pct=10.0),
        ProductionTimePoint(timestamp=t0 + timedelta(days=15), water_cut_pct=35.0),
        ProductionTimePoint(timestamp=t0 + timedelta(days=30), water_cut_pct=85.0),
        ProductionTimePoint(timestamp=t0 + timedelta(days=45), water_cut_pct=96.0),
    ]

    res = ChanDiagnosticEngine.compute_chan_diagnostic_series(pts, t_zero=t0)
    assert res.status == EngineeringStatus.VALID.value
    assert res.evidence["observed_pattern"] == "CHANNELING_PATTERN_INDICATED"
    assert res.evidence["log_log_wor_slope"] >= 1.8


def test_chan_coning_pattern_detection():
    """
    Simulates bottom-water coning with gradual slope.
    """
    t0 = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    pts = [
        ProductionTimePoint(timestamp=t0 + timedelta(days=10), water_cut_pct=20.0),
        ProductionTimePoint(timestamp=t0 + timedelta(days=30), water_cut_pct=28.0),
        ProductionTimePoint(timestamp=t0 + timedelta(days=60), water_cut_pct=38.0),
        ProductionTimePoint(timestamp=t0 + timedelta(days=120), water_cut_pct=50.0),
    ]

    res = ChanDiagnosticEngine.compute_chan_diagnostic_series(pts, t_zero=t0)
    assert res.status == EngineeringStatus.VALID.value
    assert res.evidence["observed_pattern"] == "CONING_PATTERN_INDICATED"
    assert 0.3 <= res.evidence["log_log_wor_slope"] < 1.8
