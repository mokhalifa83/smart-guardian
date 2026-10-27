import pytest
from datetime import datetime, timezone, timedelta
from app.services.validation import DataValidationService
from app.schemas.common import DataQualityStatus, MeasurementType


def test_normalize_water_cut_valid_percentage():
    norm, orig, unit, status, msg = DataValidationService.normalize_water_cut(75.5, "%")
    assert status == DataQualityStatus.VALID
    assert norm == 75.5
    assert orig == 75.5
    assert unit == "%"


def test_normalize_water_cut_valid_fraction():
    # 0.755 fraction must normalize to 75.5% while preserving original 0.755 and unit
    norm, orig, unit, status, msg = DataValidationService.normalize_water_cut(0.755, "fraction")
    assert status == DataQualityStatus.VALID
    assert norm == pytest.approx(75.5, rel=1e-3)
    assert orig == 0.755
    assert unit == "fraction"


def test_normalize_water_cut_missing_unit_rejection():
    # Crucial rule: Never guess unit silently!
    norm, orig, unit, status, msg = DataValidationService.normalize_water_cut(80.0, None)
    assert status == DataQualityStatus.INVALID
    assert norm is None


def test_normalize_water_cut_out_of_bounds_percentage():
    norm, orig, unit, status, msg = DataValidationService.normalize_water_cut(105.0, "%")
    assert status == DataQualityStatus.INVALID
    assert norm is None


def test_normalize_water_cut_out_of_bounds_fraction():
    norm, orig, unit, status, msg = DataValidationService.normalize_water_cut(1.5, "fraction")
    assert status == DataQualityStatus.INVALID
    assert norm is None


def test_normalize_water_cut_data_unavailable():
    # Crucial rule: Missing water cut must NEVER silently become WC = 0
    norm, orig, unit, status, msg = DataValidationService.normalize_water_cut(None, "%", is_unavailable=True)
    assert status == DataQualityStatus.DATA_UNAVAILABLE
    assert norm is None
    assert norm != 0.0


def test_validate_pressure():
    # Valid psi
    p, status, msg = DataValidationService.validate_pressure(250.0, "psi")
    assert status == DataQualityStatus.VALID
    assert p == 250.0

    # Valid bar converted to psi
    p_bar, status, msg = DataValidationService.validate_pressure(10.0, "bar")
    assert status == DataQualityStatus.VALID
    assert p_bar == pytest.approx(145.038, rel=1e-3)

    # Unavailable pressure
    p_unav, status, msg = DataValidationService.validate_pressure(None, "psi", is_unavailable=True)
    assert status == DataQualityStatus.DATA_UNAVAILABLE
    assert p_unav is None


def test_validate_rates():
    # Valid rate
    r, status, msg = DataValidationService.validate_rate(MeasurementType.OIL_RATE, 1200.0)
    assert status == DataQualityStatus.VALID
    assert r == 1200.0

    # Negative rate rejected
    r_neg, status, msg = DataValidationService.validate_rate(MeasurementType.OIL_RATE, -50.0)
    assert status == DataQualityStatus.INVALID
    assert r_neg is None


def test_calculate_water_cut():
    # WC = Water Rate / (Oil Rate + Water Rate)
    # e.g. 800 bpd water, 200 bpd oil -> 80%
    calc_wc, status, msg = DataValidationService.calculate_water_cut(200.0, 800.0)
    assert status == DataQualityStatus.VALID
    assert calc_wc == 80.0

    # Zero total liquid
    calc_zero, status, msg = DataValidationService.calculate_water_cut(0.0, 0.0)
    assert status == DataQualityStatus.DATA_UNAVAILABLE
    assert calc_zero is None


def test_validate_timestamp():
    now = datetime.now(timezone.utc)
    valid, status, msg = DataValidationService.validate_timestamp(now)
    assert valid is True
    assert status == DataQualityStatus.VALID

    future_ts = now + timedelta(days=2)
    valid, status, msg = DataValidationService.validate_timestamp(future_ts)
    assert valid is False
    assert status == DataQualityStatus.INVALID
