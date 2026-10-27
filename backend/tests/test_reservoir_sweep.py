import pytest
from app.services.reservoir.sweep_engine import SweepEngine
from app.services.reservoir.contracts import EngineeringStatus


def test_sweep_displacement_efficiency():
    """
    Swc = 0.20, Sor = 0.25 -> Soi = 0.80 -> ED = (0.80 - 0.25) / 0.80 = 0.6875
    """
    res = SweepEngine.calculate_displacement_efficiency(sw_connate=0.20, so_residual=0.25)
    assert res.status == EngineeringStatus.VALID.value
    assert res.value == pytest.approx(0.6875, abs=1e-4)


def test_sweep_vertical_dykstra_parsons_from_layers():
    """
    Layer permeabilities: 500, 300, 180, 100, 50 md.
    """
    layers = [500.0, 300.0, 180.0, 100.0, 50.0]
    res = SweepEngine.calculate_vertical_sweep_dykstra_parsons(
        permeability_layers_md=layers,
        mobility_ratio_m=1.2
    )
    assert res.status == EngineeringStatus.VALID.value
    assert 0.0 < res.value <= 1.0
    assert "v_dp_heterogeneity_coefficient" in res.evidence


def test_sweep_total_volumetric_synthesis():
    """
    ED = (1 - 0.20 - 0.25) / (1 - 0.20) = 0.6875
    EA = 0.80, EI = 0.70 -> Ev = 0.80 * 0.70 = 0.56
    ER = 0.6875 * 0.56 = 0.385
    """
    res = SweepEngine.calculate_total_volumetric_sweep(
        sw_connate=0.20,
        so_residual=0.25,
        areal_sweep_ea=0.80,
        vertical_sweep_ei=0.70
    )
    assert res.status == EngineeringStatus.VALID.value
    assert res.value["displacement_efficiency_ED"] == pytest.approx(0.6875, abs=1e-4)
    assert res.value["volumetric_sweep_efficiency_Ev"] == pytest.approx(0.56, abs=1e-4)
    assert res.value["overall_recovery_factor_ER"] == pytest.approx(0.385, abs=1e-4)
