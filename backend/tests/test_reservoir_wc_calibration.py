import pytest
from datetime import datetime, timezone, timedelta
from app.services.reservoir.wc_calibration import (
    WaterCutCalibrationEngine,
    LabWaterCutSample,
    LiveWaterCutObservation
)
from app.services.reservoir.contracts import EngineeringStatus


def test_wc_calibration_factor_and_application():
    """
    Lab measurement: WC = 30.0% (fraction 0.30)
    Live sensor reading at sampling: WC = 25.0% (fraction 0.25)
    Calibration factor CF = 0.30 / 0.25 = 1.20
    Current live reading: WC = 40.0% -> Calibrated WC_Final = 40.0% * 1.20 = 48.0%
    """
    t0 = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    lab = LabWaterCutSample(
        sample_id="SAMPLE-LAB-01",
        timestamp=t0,
        well_code="WELL-WC-01",
        water_cut_value=30.0,
        is_percentage=True
    )
    live_sample = LiveWaterCutObservation(
        timestamp=t0,
        well_code="WELL-WC-01",
        water_cut_value=25.0,
        is_percentage=True
    )

    cf_res = WaterCutCalibrationEngine.calculate_calibration_factor(
        lab_sample=lab,
        live_observation_at_sample=live_sample
    )
    assert cf_res.status == EngineeringStatus.VALID.value
    assert cf_res.value["calibration_factor"] == pytest.approx(1.20, abs=1e-4)

    # Apply to current telemetry (2 hours later)
    current_live = LiveWaterCutObservation(
        timestamp=t0 + timedelta(hours=2),
        well_code="WELL-WC-01",
        water_cut_value=40.0,
        is_percentage=True
    )
    apply_res = WaterCutCalibrationEngine.apply_calibration(
        current_live_reading=current_live,
        calibration_factor=1.20,
        calibration_timestamp=t0
    )
    assert apply_res.status == EngineeringStatus.VALID.value
    assert apply_res.value["wc_final_percent"] == pytest.approx(48.0, abs=1e-2)
    assert apply_res.value["wc_final_fraction"] == pytest.approx(0.48, abs=1e-4)


def test_wc_calibration_zero_denominator_protection():
    """
    Rule 23: Live WC at sample is 0.0% -> division by zero prevented.
    """
    t0 = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    lab = LabWaterCutSample(
        sample_id="SAMPLE-LAB-02",
        timestamp=t0,
        well_code="WELL-WC-01",
        water_cut_value=5.0,
        is_percentage=True
    )
    live_sample = LiveWaterCutObservation(
        timestamp=t0,
        well_code="WELL-WC-01",
        water_cut_value=0.0,  # Zero denominator!
        is_percentage=True
    )

    res = WaterCutCalibrationEngine.calculate_calibration_factor(
        lab_sample=lab,
        live_observation_at_sample=live_sample
    )
    assert res.status == EngineeringStatus.INVALID_INPUT.value
    assert "DENOMINATOR_NEAR_ZERO" in res.evidence["calibration_status"]


def test_wc_calibration_stale_sample_expiration():
    """
    Rule 23: Calibration factor > 72 hours old triggers CALIBRATION_REQUIRED.
    """
    t_cal = datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc)
    t_live = t_cal + timedelta(hours=96)  # 4 days later

    current_live = LiveWaterCutObservation(
        timestamp=t_live,
        well_code="WELL-WC-01",
        water_cut_value=35.0,
        is_percentage=True
    )

    res = WaterCutCalibrationEngine.apply_calibration(
        current_live_reading=current_live,
        calibration_factor=1.10,
        calibration_timestamp=t_cal,
        max_calibration_age_hours=72.0
    )
    assert res.status == EngineeringStatus.CALIBRATION_REQUIRED.value
    assert "STALE_CALIBRATION" in res.evidence["calibration_status"]


def test_wc_100_percent_undefined_wor_handling():
    """
    Rule 25: At WC = 100%, WOR must be UNDEFINED_WOR without arbitrary epsilon substitution.
    """
    t0 = datetime(2026, 1, 10, 10, 0, tzinfo=timezone.utc)
    current_live = LiveWaterCutObservation(
        timestamp=t0,
        well_code="WELL-WC-01",
        water_cut_value=100.0,
        is_percentage=True
    )

    res = WaterCutCalibrationEngine.apply_calibration(
        current_live_reading=current_live,
        calibration_factor=1.0,
        calibration_timestamp=t0
    )
    assert res.status == EngineeringStatus.VALID.value
    assert res.value["wc_final_fraction"] == 1.0
    assert res.value["wor"] is None
    assert res.value["wor_status"] == "UNDEFINED_WOR"
