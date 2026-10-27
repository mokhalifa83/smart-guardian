import pytest
from datetime import datetime, timezone, timedelta
from app.services.reservoir.decline_engine import DeclineEngine, ProductionRatePoint
from app.services.reservoir.contracts import EngineeringStatus


def test_decline_exponential_fit_and_forecast():
    """
    Simulates exponential decline qi = 1000 STB/D, Di = 0.002 / day.
    """
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    # Synthetic generation of purely physical exponential points for test fixture
    history = [
        ProductionRatePoint(timestamp=t0 + timedelta(days=0), rate_stbd=1000.0),
        ProductionRatePoint(timestamp=t0 + timedelta(days=30), rate_stbd=941.76),
        ProductionRatePoint(timestamp=t0 + timedelta(days=60), rate_stbd=886.92),
        ProductionRatePoint(timestamp=t0 + timedelta(days=90), rate_stbd=835.27),
        ProductionRatePoint(timestamp=t0 + timedelta(days=180), rate_stbd=697.68),
    ]

    res = DeclineEngine.analyze_decline(
        history=history,
        model_type="EXPONENTIAL",
        forecast_horizon_days=180.0,
        economic_limit_rate_stbd=100.0,
        well_code="WELL-DEC-01"
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value["qi_stbd"] == pytest.approx(1000.0, rel=0.05)
    assert res.value["b_exponent"] == 0.0
    assert res.value["r_squared"] > 0.99
    assert res.value["eur_stb"] is not None
    assert res.value["eur_stb"] > 0
    assert len(res.evidence["forecast_series"]) == 12


def test_decline_harmonic_and_hyperbolic_fits():
    """
    Tests Harmonic (b=1) and Hyperbolic fitting workflows.
    """
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    # Harmonic decay: q = qi / (1 + Di * t) with qi = 800, Di = 0.005
    history = [
        ProductionRatePoint(timestamp=t0 + timedelta(days=0), rate_stbd=800.0),
        ProductionRatePoint(timestamp=t0 + timedelta(days=50), rate_stbd=640.0),
        ProductionRatePoint(timestamp=t0 + timedelta(days=100), rate_stbd=533.33),
        ProductionRatePoint(timestamp=t0 + timedelta(days=200), rate_stbd=400.0),
    ]

    res_harm = DeclineEngine.analyze_decline(history=history, model_type="HARMONIC")
    assert res_harm.status == EngineeringStatus.VALID.value
    assert res_harm.value["b_exponent"] == 1.0
    assert res_harm.value["r_squared"] > 0.98

    res_hyp = DeclineEngine.analyze_decline(history=history, model_type="HYPERBOLIC")
    assert res_hyp.status == EngineeringStatus.VALID.value
    assert 0.0 < res_hyp.value["b_exponent"] < 1.0


def test_decline_economic_limit_not_invented():
    """
    Rule 7: Platform must NOT invent an economic limit.
    If economic_limit_rate_stbd is omitted, EUR must be None with an explicit provenance note.
    """
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    history = [
        ProductionRatePoint(timestamp=t0 + timedelta(days=0), rate_stbd=500.0),
        ProductionRatePoint(timestamp=t0 + timedelta(days=30), rate_stbd=480.0),
        ProductionRatePoint(timestamp=t0 + timedelta(days=60), rate_stbd=460.0),
    ]

    res = DeclineEngine.analyze_decline(history=history, model_type="EXPONENTIAL")
    assert res.status == EngineeringStatus.VALID.value
    assert res.value["eur_stb"] is None
    assert "Economic limit rate was not configured" in res.evidence["eur_evaluation"]["note"]


def test_decline_insufficient_data_and_invalid_rates():
    """
    Verifies rejection of insufficient history (< 3 points) and negative rates.
    """
    t0 = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)
    # Only 2 points
    pts_few = [
        ProductionRatePoint(timestamp=t0, rate_stbd=500.0),
        ProductionRatePoint(timestamp=t0 + timedelta(days=30), rate_stbd=480.0)
    ]
    res_few = DeclineEngine.analyze_decline(history=pts_few)
    assert res_few.status == EngineeringStatus.INSUFFICIENT_DATA.value

    # Non-positive rate
    pts_invalid = [
        ProductionRatePoint(timestamp=t0, rate_stbd=500.0),
        ProductionRatePoint(timestamp=t0 + timedelta(days=30), rate_stbd=0.0),
        ProductionRatePoint(timestamp=t0 + timedelta(days=60), rate_stbd=400.0)
    ]
    res_invalid = DeclineEngine.analyze_decline(history=pts_invalid)
    assert res_invalid.status == EngineeringStatus.INVALID_INPUT.value
