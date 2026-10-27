import pytest
import math
from app.services.reservoir.well_test_engine import WellTestEngine, WellTestGaugePoint
from app.services.reservoir.contracts import EngineeringStatus


def test_well_test_drawdown_radial_flow():
    """
    Standard Earlougher (1977) Drawdown Test Case:
    q = 250 STB/D, h = 50 ft, phi = 0.20, mu = 1.0 cp, Bo = 1.25 rb/stb, ct = 1.0e-5 1/psi, rw = 0.354 ft.
    Target slope m ~ 40 psi/cycle -> kh = 162.6 * 250 * 1.25 * 1.0 / 40 ~ 1270 md-ft -> k ~ 25.4 md.
    """
    # pwf(t) = 3000 - 40 * log10(t)
    points = [
        WellTestGaugePoint(elapsed_time_hours=1.0, pressure_psia=3000.0),
        WellTestGaugePoint(elapsed_time_hours=2.0, pressure_psia=3000.0 - 40.0 * math.log10(2.0)),
        WellTestGaugePoint(elapsed_time_hours=5.0, pressure_psia=3000.0 - 40.0 * math.log10(5.0)),
        WellTestGaugePoint(elapsed_time_hours=10.0, pressure_psia=3000.0 - 40.0 * math.log10(10.0)),
        WellTestGaugePoint(elapsed_time_hours=24.0, pressure_psia=3000.0 - 40.0 * math.log10(24.0)),
    ]

    res = WellTestEngine.analyze_drawdown(
        gauge_points=points,
        initial_pressure_psia=3200.0,
        flow_rate_stbd=250.0,
        formation_thickness_ft=50.0,
        porosity_fraction=0.20,
        total_compressibility_psi=1.0e-5,
        viscosity_cp=1.0,
        bo_rb_stb=1.25,
        wellbore_radius_ft=0.354
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value["semilog_slope_m_psi_cycle"] == pytest.approx(40.0, rel=0.01)
    assert res.value["permeability_thickness_md_ft"] == pytest.approx(1270.3, rel=0.05)
    assert res.value["permeability_md"] == pytest.approx(25.4, rel=0.05)
    assert res.value["skin_factor"] is not None


def test_well_test_horner_buildup():
    """
    Standard Horner (1951) Buildup Test:
    tp = 1000 hrs, q = 300 STB/D, h = 40 ft, phi = 0.18, ct = 1.2e-5, mu = 1.2 cp, Bo = 1.22.
    Horner slope m = 45 psi/cycle, p* ~ 3500 psia.
    pws = 3500 - 45 * log10((1000 + dt) / dt)
    """
    dt_hours = [1.0, 2.0, 4.0, 8.0, 16.0, 24.0, 48.0]
    points = []
    for dt in dt_hours:
        hr = (1000.0 + dt) / dt
        pws = 3500.0 - 45.0 * math.log10(hr)
        points.append(WellTestGaugePoint(elapsed_time_hours=dt, pressure_psia=pws))

    res = WellTestEngine.analyze_horner_buildup(
        gauge_points=points,
        producing_time_tp_hours=1000.0,
        flow_rate_stbd=300.0,
        formation_thickness_ft=40.0,
        porosity_fraction=0.18,
        total_compressibility_psi=1.2e-5,
        viscosity_cp=1.2,
        bo_rb_stb=1.22,
        flowing_pwf_at_shutin_psia=3100.0
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value["horner_slope_m_psi_cycle"] == pytest.approx(45.0, rel=0.02)
    assert res.value["extrapolated_pressure_p_star_psia"] == pytest.approx(3500.0, abs=5.0)
    assert res.value["permeability_md"] > 0
    assert "INFINITE_ACTING_RADIAL_FLOW" in res.observed_pattern


def test_well_test_boundary_slope_doubling_indicator():
    """
    Simulates late-time slope doubling indicating a potential sealing fault.
    """
    # Early slope m1 = 30, late slope m2 = 60
    points = [
        WellTestGaugePoint(elapsed_time_hours=1.0, pressure_psia=3200.0),
        WellTestGaugePoint(elapsed_time_hours=2.0, pressure_psia=3230.0),
        WellTestGaugePoint(elapsed_time_hours=4.0, pressure_psia=3260.0),
        WellTestGaugePoint(elapsed_time_hours=8.0, pressure_psia=3320.0),
        WellTestGaugePoint(elapsed_time_hours=16.0, pressure_psia=3380.0),
        WellTestGaugePoint(elapsed_time_hours=32.0, pressure_psia=3440.0),
    ]

    res = WellTestEngine.analyze_horner_buildup(
        gauge_points=points,
        producing_time_tp_hours=500.0,
        flow_rate_stbd=200.0,
        formation_thickness_ft=30.0,
        porosity_fraction=0.20,
        total_compressibility_psi=1.0e-5,
        viscosity_cp=1.0,
        bo_rb_stb=1.20
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.observed_pattern is not None
    assert "required_confirmation" in res.model_dump()


def test_well_test_insufficient_data():
    """
    Verifies rejection when fewer than 3 gauge points are provided.
    """
    points = [
        WellTestGaugePoint(elapsed_time_hours=1.0, pressure_psia=3000.0),
        WellTestGaugePoint(elapsed_time_hours=2.0, pressure_psia=3050.0)
    ]
    res = WellTestEngine.analyze_drawdown(
        gauge_points=points,
        initial_pressure_psia=3200.0,
        flow_rate_stbd=200.0,
        formation_thickness_ft=30.0,
        porosity_fraction=0.20,
        total_compressibility_psi=1.0e-5,
        viscosity_cp=1.0,
        bo_rb_stb=1.20
    )
    assert res.status == EngineeringStatus.INSUFFICIENT_DATA.value
