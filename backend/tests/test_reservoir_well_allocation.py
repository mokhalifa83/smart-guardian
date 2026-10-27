import pytest
from app.services.reservoir.well_allocation import WellAllocationEngine, ChokeAllocationInputs
from app.services.reservoir.contracts import EngineeringStatus


def test_well_allocation_gilbert_correlation():
    """
    Gilbert correlation:
    Pwh = 800 psia, S = 32 (64ths), Rp = 600 scf/stb, WC = 0.30 (fraction).
    """
    inputs = ChokeAllocationInputs(
        wellhead_pressure_psia=800.0,
        choke_size_64ths=32.0,
        producing_gor_scf_stb=600.0,
        calibrated_wc_fraction=0.30,
        flowline_pressure_psia=350.0,  # 350 / 800 = 0.4375 <= 0.55 (critical flow)
        correlation_name="GILBERT"
    )

    res = WellAllocationEngine.calculate_choke_allocation(inputs)
    assert res.status == EngineeringStatus.VALID.value
    assert res.value["allocated_liquid_rate_stbd"] > 0
    # Oil rate = Liquid * (1 - 0.30)
    assert res.value["allocated_oil_rate_stbd"] == pytest.approx(res.value["allocated_liquid_rate_stbd"] * 0.70, rel=1e-3)
    # Water rate = Liquid * 0.30
    assert res.value["allocated_water_rate_bpd"] == pytest.approx(res.value["allocated_liquid_rate_stbd"] * 0.30, rel=1e-3)
    # Measurement classification must be Virtual Allocation / Engineering Estimate
    assert res.value["measurement_classification"] == "VIRTUAL_ALLOCATION_ENGINEERING_ESTIMATE"


def test_well_allocation_100_percent_wc_zero_oil_rate():
    """
    At WC = 1.0 (100%), allocated oil rate must be zero and WOR undefined.
    """
    inputs = ChokeAllocationInputs(
        wellhead_pressure_psia=600.0,
        choke_size_64ths=28.0,
        producing_gor_scf_stb=500.0,
        calibrated_wc_fraction=1.0,  # 100% Water Cut!
        flowline_pressure_psia=250.0,
        correlation_name="GILBERT"
    )

    res = WellAllocationEngine.calculate_choke_allocation(inputs)
    assert res.status == EngineeringStatus.VALID.value
    assert res.value["allocated_oil_rate_stbd"] == 0.0
    assert res.value["allocated_water_rate_bpd"] == res.value["allocated_liquid_rate_stbd"]
    assert res.value["wor"] is None
    assert "UNDEFINED_WOR" in res.evidence["wor_status"]


def test_well_allocation_unsupported_correlation():
    inputs = ChokeAllocationInputs(
        wellhead_pressure_psia=500.0,
        choke_size_64ths=20.0,
        producing_gor_scf_stb=400.0,
        calibrated_wc_fraction=0.20,
        correlation_name="INVENTED_CORRELATION"
    )
    res = WellAllocationEngine.calculate_choke_allocation(inputs)
    assert res.status == EngineeringStatus.NOT_APPLICABLE.value
