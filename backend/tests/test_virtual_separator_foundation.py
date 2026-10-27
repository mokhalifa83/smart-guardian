import pytest
from datetime import datetime, timezone
from app.services.reservoir.virtual_separator_pvt import (
    VirtualSeparatorPVTFoundation,
    SeparatorConditionsSuite,
    SeparatorStageCondition,
    ConfigurableEconomicContext
)
from app.services.reservoir.contracts import EngineeringStatus


def test_separator_conditions_defaults_traceability():
    """
    Verifies separator condition interface tags default values as CONFIGURED,
    distinct from MEASURED field values.
    """
    suite = VirtualSeparatorPVTFoundation.get_default_separator_conditions()
    assert suite.stage_1.pressure_psia == 100.0
    assert suite.stage_1.temperature_f == 80.0
    assert suite.stage_1.source == "CONFIGURED"
    assert not suite.stage_1.is_measured
    assert suite.stock_tank.pressure_psia == 14.7


def test_separator_correction_rule_12_barrier():
    """
    Rule 12: DO NOT INVENT A GUESSED CORRECTION.
    Verifies that requesting an unspecified or uncalibrated separator correction
    strictly returns CORRELATION_SPECIFICATION_REQUIRED.
    """
    suite = VirtualSeparatorPVTFoundation.get_default_separator_conditions()
    res = VirtualSeparatorPVTFoundation.evaluate_separator_condition_correction(
        base_bo=1.28,
        sep_conditions=suite,
        correlation_name="UNSPECIFIED"
    )
    assert res.status == EngineeringStatus.CORRELATION_SPECIFICATION_REQUIRED.value
    assert "CORRELATION_SPECIFICATION_REQUIRED" in res.evidence["status_code"]


def test_flash_interface_no_arbitrary_rs_summation():
    """
    Rule 13: Flash calculation interface strictly rejects arbitrary additive Rs summation
    (Rs_total != Rs1 + Rs2 + Rs_stock) and documents reference basis.
    """
    suite = VirtualSeparatorPVTFoundation.get_default_separator_conditions()
    res = VirtualSeparatorPVTFoundation.evaluate_flash_calculation_interface(
        pvt_inputs={"pressure": 2500.0, "temperature": 180.0},
        sep_conditions=suite,
        reference_basis="DIFFERENTIAL_LIBERATION"
    )
    assert res.status == EngineeringStatus.VALID.value
    assert "Arbitrary additive stage Rs summation" in res.assumptions[1]


def test_dual_water_cut_separation_and_calibration():
    """
    Rule 17: Preserves WC_Live and WC_Lab as distinct observations without overwriting.
    """
    now = datetime.now(timezone.utc)
    record = VirtualSeparatorPVTFoundation.reconcile_dual_water_cut(
        wc_live_percent=82.4,
        wc_lab_percent=79.1,
        well_code="WELL-TEST-SEP",
        timestamp=now
    )
    # Both are preserved independently
    assert record.wc_live_percent == 82.4
    assert record.wc_lab_percent == 79.1
    assert record.calibration_status == "NOT_CONFIGURED"
    assert record.wc_live_source == "FIELD_MULTIPHASE_METER"
    assert record.wc_lab_source == "LAB_CENTRIFUGE"


def test_configurable_economic_benchmark():
    """
    Rule 33: Rental cost benchmarks ($15,000/day, $25,000/day) are configurable economic parameters,
    not hard-coded engineering facts.
    """
    econ = ConfigurableEconomicContext(test_separator_daily_rental_usd=18500.0)
    assert econ.test_separator_daily_rental_usd == 18500.0
    assert econ.is_assumption is True
    assert econ.currency == "USD"
