import pytest
from app.services.reservoir.fractional_flow_engine import FractionalFlowEngine, CoreRelPermPoint
from app.services.reservoir.contracts import EngineeringStatus


def test_fractional_flow_corey_model():
    """
    Corey power-law relative permeability:
    Swc = 0.20, Sor = 0.25, krw_endpoint = 0.35, kro_endpoint = 0.85, nw = 2.0, no = 2.5.
    mu_w = 0.5 cp, mu_o = 2.0 cp.
    """
    res = FractionalFlowEngine.calculate_corey_model(
        sw_connate=0.20,
        so_residual=0.25,
        krw_endpoint=0.35,
        kro_endpoint=0.85,
        nw_exponent=2.0,
        no_exponent=2.5,
        water_viscosity_cp=0.50,
        oil_viscosity_cp=2.0
    )

    assert res.status == EngineeringStatus.VALID.value
    # End-point mobility ratio: (0.35 / 0.5) / (0.85 / 2.0) = 0.70 / 0.425 = 1.647
    assert res.value["end_point_mobility_ratio_M"] == pytest.approx(1.647, rel=0.01)
    pts = res.evidence["curve_points"]
    assert len(pts) == 50
    # At Swc = 0.20, fw = 0.0
    assert pts[0]["fw"] == 0.0
    # At 1 - Sor = 0.75, fw = 1.0
    assert pts[-1]["fw"] == 1.0
    # Explicit assumption: NOT direct core laboratory measurements
    assert any("NOT direct core laboratory measurements" in a for a in res.assumptions)


def test_fractional_flow_from_core_data():
    """
    Tests evaluation of fractional flow directly from laboratory core measurements.
    """
    core_pts = [
        CoreRelPermPoint(sw_fraction=0.22, krw=0.00, kro=0.90),
        CoreRelPermPoint(sw_fraction=0.35, krw=0.04, kro=0.55),
        CoreRelPermPoint(sw_fraction=0.50, krw=0.12, kro=0.25),
        CoreRelPermPoint(sw_fraction=0.65, krw=0.24, kro=0.08),
        CoreRelPermPoint(sw_fraction=0.75, krw=0.38, kro=0.00),
    ]

    res = FractionalFlowEngine.calculate_from_core_data(
        core_points=core_pts,
        water_viscosity_cp=0.50,
        oil_viscosity_cp=2.0
    )

    assert res.status == EngineeringStatus.VALID.value
    pts = res.evidence["curve_points"]
    assert len(pts) == 5
    assert pts[0]["fw"] == 0.0
    assert pts[-1]["fw"] == 1.0


def test_fractional_flow_boundary_violation():
    """
    Swc + Sor >= 1.0 must be rejected.
    """
    res = FractionalFlowEngine.calculate_corey_model(
        sw_connate=0.60,
        so_residual=0.50,  # 0.60 + 0.50 = 1.10 > 1.0
        krw_endpoint=0.3,
        kro_endpoint=0.8,
        nw_exponent=2,
        no_exponent=2,
        water_viscosity_cp=1,
        oil_viscosity_cp=1
    )
    assert res.status == EngineeringStatus.INVALID_INPUT.value
