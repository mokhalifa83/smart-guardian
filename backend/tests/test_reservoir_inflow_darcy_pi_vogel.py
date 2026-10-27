import pytest
from app.services.reservoir.darcy_engine import DarcyRadialFlowEngine
from app.services.reservoir.productivity_index import ProductivityIndexEngine
from app.services.reservoir.vogel_engine import VogelIPREngine
from app.services.reservoir.contracts import EngineeringStatus


# -------------------------------------------------------------
# Darcy Radial Flow Tests
# -------------------------------------------------------------

def test_darcy_flow_valid():
    """
    Standard radial Darcy flow test case:
    k = 50 md, h = 30 ft, pr = 3500 psia, pwf = 2500 psia (drawdown = 1000 psi)
    mu = 1.5 cp, Bo = 1.25 rb/stb
    re = 1000 ft, rw = 0.354 ft (ln(1000/0.354) ~ 7.946)
    geo_term = 7.946 - 0.75 = 7.196
    q = (50 * 30 * 1000) / (141.2 * 1.5 * 1.25 * 7.196) = 1500000 / 1904.6 = ~787.5 stb/d
    """
    res = DarcyRadialFlowEngine.calculate_flow_rate(
        permeability_md=50.0,
        thickness_ft=30.0,
        reservoir_pressure_psia=3500.0,
        flowing_bhp_psia=2500.0,
        viscosity_cp=1.5,
        bo_rb_stb=1.25,
        drainage_radius_ft=1000.0,
        wellbore_radius_ft=0.354,
        skin=0.0
    )
    assert res.status == EngineeringStatus.VALID.value
    assert res.value is not None
    assert 750.0 <= float(res.value) <= 820.0
    assert res.unit == "stb/d"


def test_darcy_flow_invalid_inputs():
    # Permeability <= 0
    res_k = DarcyRadialFlowEngine.calculate_flow_rate(
        permeability_md=-10.0, thickness_ft=30.0, reservoir_pressure_psia=3500.0,
        flowing_bhp_psia=2500.0, viscosity_cp=1.5, bo_rb_stb=1.25,
        drainage_radius_ft=1000.0, wellbore_radius_ft=0.354
    )
    assert res_k.status == EngineeringStatus.OUT_OF_RANGE.value

    # pr <= pwf
    res_p = DarcyRadialFlowEngine.calculate_flow_rate(
        permeability_md=50.0, thickness_ft=30.0, reservoir_pressure_psia=2500.0,
        flowing_bhp_psia=3000.0, viscosity_cp=1.5, bo_rb_stb=1.25,
        drainage_radius_ft=1000.0, wellbore_radius_ft=0.354
    )
    assert res_p.status == EngineeringStatus.OUT_OF_RANGE.value

    # re <= rw
    res_geo = DarcyRadialFlowEngine.calculate_flow_rate(
        permeability_md=50.0, thickness_ft=30.0, reservoir_pressure_psia=3500.0,
        flowing_bhp_psia=2500.0, viscosity_cp=1.5, bo_rb_stb=1.25,
        drainage_radius_ft=0.2, wellbore_radius_ft=0.354
    )
    assert res_geo.status == EngineeringStatus.OUT_OF_RANGE.value


# -------------------------------------------------------------
# Productivity Index (PI) Tests
# -------------------------------------------------------------

def test_pi_valid_and_zero_drawdown():
    # Valid: q = 500 stb/d, pr = 3000 psia, pwf = 2500 psia (drawdown = 500 psi) -> J = 1.0 stb/d/psi
    res = ProductivityIndexEngine.calculate_pi(500.0, 3000.0, 2500.0)
    assert res.status == EngineeringStatus.VALID.value
    assert float(res.value) == 1.0
    assert res.unit == "stb/d/psi"

    # Zero drawdown: pr == pwf (3000 == 3000) -> ZERO_DRAWDOWN (no division by zero)
    res_zero = ProductivityIndexEngine.calculate_pi(0.0, 3000.0, 3000.0)
    assert res_zero.status == EngineeringStatus.ZERO_DRAWDOWN.value
    assert res_zero.value is None


# -------------------------------------------------------------
# Vogel IPR Tests
# -------------------------------------------------------------

def test_vogel_ipr_boundaries_and_calculation():
    """
    Vogel equation: q/qmax = 1 - 0.2*(pwf/pr) - 0.8*(pwf/pr)^2
    At pwf = pr: q/qmax = 1 - 0.2 - 0.8 = 0.0 (shut-in)
    At pwf = 0: q/qmax = 1 - 0 - 0 = 1.0 (maximum open flow)
    At pwf = 0.5 pr: q/qmax = 1 - 0.2*(0.5) - 0.8*(0.25) = 1 - 0.1 - 0.2 = 0.70
    """
    pr = 3000.0
    qmax = 1000.0

    # Boundary 1: Pwf = Pr -> q = 0
    res_pr = VogelIPREngine.calculate_flow_rate_from_qmax(qmax, pr, 3000.0)
    assert res_pr.status == EngineeringStatus.VALID.value
    assert float(res_pr.value) == 0.0

    # Boundary 2: Pwf = 0 -> q = qmax
    res_zero = VogelIPREngine.calculate_flow_rate_from_qmax(qmax, pr, 0.0)
    assert res_zero.status == EngineeringStatus.VALID.value
    assert float(res_zero.value) == 1000.0

    # Intermediate: Pwf = 1500 (0.5 pr) -> q = 0.70 * 1000 = 700 stb/d
    res_mid = VogelIPREngine.calculate_flow_rate_from_qmax(qmax, pr, 1500.0)
    assert res_mid.status == EngineeringStatus.VALID.value
    assert float(res_mid.value) == 700.0


def test_vogel_qmax_estimation_from_test_point():
    """
    Test well tested at qt = 700 stb/d with pwf = 1500 psia in a pr = 3000 psia reservoir.
    Vogel formula should calculate qmax = 1000 stb/d!
    """
    res = VogelIPREngine.estimate_qmax_from_test(
        test_rate_stbd=700.0,
        test_flowing_bhp_psia=1500.0,
        reservoir_pressure_psia=3000.0
    )
    assert res.status == EngineeringStatus.VALID.value
    assert float(res.value) == pytest.approx(1000.0, rel=1e-3)
