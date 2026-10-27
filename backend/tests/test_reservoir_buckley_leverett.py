import pytest
from app.services.reservoir.buckley_leverett_engine import BuckleyLeverettEngine
from app.services.reservoir.contracts import EngineeringStatus


def test_buckley_leverett_analytical_displacement():
    """
    Standard Welge (1952) 1D displacement test.
    Injection rate = 1200 BPD, Area = 25000 sq ft, L = 1000 ft, phi = 0.22,
    Swi = 0.20, Sor = 0.25, mu_w = 0.5 cp, mu_o = 2.0 cp.
    """
    res = BuckleyLeverettEngine.calculate_displacement(
        injection_rate_bpd=1200.0,
        cross_sectional_area_ft2=25000.0,
        length_between_wells_ft=1000.0,
        porosity_fraction=0.22,
        initial_water_saturation=0.20,
        so_residual=0.25,
        water_viscosity_cp=0.50,
        oil_viscosity_cp=2.0
    )

    assert res.status == EngineeringStatus.VALID.value
    # Shock-front saturation Swf must be greater than Swi
    assert res.value["shock_front_saturation_swf"] > 0.20
    # Average water saturation at breakthrough must be greater than Swf
    assert res.value["average_saturation_at_breakthrough"] >= res.value["shock_front_saturation_swf"]
    # Time to breakthrough must be strictly positive
    assert res.value["time_to_breakthrough_days"] > 0
    # PVI at breakthrough is typically between 0.2 and 0.8
    assert 0.1 <= res.value["pore_volumes_injected_at_breakthrough"] <= 1.0
    # Mandatory disclaimer must be in assumptions
    assert any("NOT a full-field" in a for a in res.assumptions)


def test_buckley_leverett_invalid_inputs():
    """
    Validates physical boundary checking for saturation and geometry.
    """
    res = BuckleyLeverettEngine.calculate_displacement(
        injection_rate_bpd=-100.0,  # Invalid
        cross_sectional_area_ft2=25000.0,
        length_between_wells_ft=1000.0,
        porosity_fraction=0.22,
        initial_water_saturation=0.20,
        so_residual=0.25,
        water_viscosity_cp=0.50,
        oil_viscosity_cp=2.0
    )
    assert res.status == EngineeringStatus.INVALID_INPUT.value
