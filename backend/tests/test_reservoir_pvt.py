import pytest
import math
from app.services.reservoir.pvt_engine import PVTEngine
from app.services.reservoir.contracts import EngineeringStatus


def test_pvt_z_factor_hall_yarborough_reference():
    """
    Reference test for Hall-Yarborough Standing-Katz Z-factor.
    At P = 2000 psia, T = 150 F (609.67 R), gas_gravity = 0.65:
    Sutton gives Ppc ~ 669.9 psia, Tpc ~ 365.1 R
    Ppr ~ 2.98, Tpr ~ 1.67
    Standing-Katz chart Z is typically around 0.82 - 0.86.
    """
    res = PVTEngine.calculate_z_factor_hall_yarborough(
        pressure_psia=2000.0,
        temperature_f=150.0,
        gas_gravity=0.65
    )
    assert res.status == EngineeringStatus.VALID.value
    assert res.value is not None
    assert 0.80 <= float(res.value) <= 0.88
    assert res.unit == "dimensionless"
    assert "Rankine" in res.assumptions[1]


def test_pvt_bg_temperature_rankine_conversion():
    """
    Bg = 0.00504 * Z * T_R / P.
    Strictly verifies T_R = T_F + 459.67 is used and NOT raw Fahrenheit!
    At P = 2500 psia, T = 180 F (639.67 R), Z = 0.85:
    Bg = 0.00504 * (0.85 * 639.67) / 2500 = 0.001096 rb/scf.
    If raw 180 F was used: 0.00504 * (0.85 * 180) / 2500 = 0.000308 rb/scf (a catastrophic 3.5x error!)
    """
    res = PVTEngine.calculate_gas_fvf_bg(
        pressure_psia=2500.0,
        temperature_f=180.0,
        z_factor=0.85,
        unit="rb/scf"
    )
    assert res.status == EngineeringStatus.VALID.value
    expected_bg = 0.00504 * (0.85 * (180.0 + 459.67)) / 2500.0
    assert float(res.value) == pytest.approx(expected_bg, rel=1e-3)
    assert float(res.value) > 0.0010  # Confirms Rankine was used!


def test_pvt_bg_missing_input_and_no_zero_fallback():
    """
    Verifies that missing inputs return INSUFFICIENT_DATA and NEVER fallback to Bg = 0.
    """
    res = PVTEngine.calculate_gas_fvf_bg(
        pressure_psia=0.0,
        temperature_f=180.0,
        z_factor=0.85
    )
    assert res.status == EngineeringStatus.INSUFFICIENT_DATA.value
    assert res.value is None
    assert res.value != 0.0


def test_pvt_standing_rs_and_bubble_point():
    """
    Standing (1947) Rs reference test case:
    P = 3000 psia, T = 200 F, API = 35.0, gas_gravity = 0.80.
    """
    res = PVTEngine.calculate_bubble_point_and_rs(
        pressure_psia=3000.0,
        temperature_f=200.0,
        api_gravity=35.0,
        gas_gravity=0.80,
        correlation="Standing"
    )
    assert res.status == EngineeringStatus.VALID.value
    assert res.value is not None
    assert 500.0 <= float(res.value) <= 900.0
    assert res.unit == "scf/stb"


def test_pvt_vasquez_beggs_rs():
    """
    Vasquez & Beggs (1980) Rs reference test case.
    """
    res = PVTEngine.calculate_bubble_point_and_rs(
        pressure_psia=3000.0,
        temperature_f=200.0,
        api_gravity=35.0,
        gas_gravity=0.80,
        correlation="Vasquez-Beggs"
    )
    assert res.status == EngineeringStatus.VALID.value
    assert res.value is not None
    assert 500.0 <= float(res.value) <= 1000.0


def test_pvt_standing_bo_saturated_and_undersaturated():
    """
    Standing (1947) Bo evaluation.
    """
    # Saturated (P <= Pb)
    res_sat = PVTEngine.calculate_oil_fvf_bo(
        pressure_psia=2500.0,
        temperature_f=180.0,
        api_gravity=36.0,
        gas_gravity=0.75,
        rs=550.0,
        bubble_point_psia=2500.0
    )
    assert res_sat.status == EngineeringStatus.VALID.value
    assert 1.20 <= float(res_sat.value) <= 1.45

    # Undersaturated (P > Pb): Bo should decrease due to oil compression
    res_undersat = PVTEngine.calculate_oil_fvf_bo(
        pressure_psia=4000.0,
        temperature_f=180.0,
        api_gravity=36.0,
        gas_gravity=0.75,
        rs=550.0,
        bubble_point_psia=2500.0
    )
    assert res_undersat.status == EngineeringStatus.VALID.value
    assert float(res_undersat.value) < float(res_sat.value)


def test_pvt_mccain_bw_and_cw():
    """
    McCain (1991) Bw and cw tests.
    """
    bw_res = PVTEngine.calculate_water_fvf_bw(pressure_psia=3000.0, temperature_f=180.0)
    assert bw_res.status == EngineeringStatus.VALID.value
    assert 1.01 <= float(bw_res.value) <= 1.05

    cw_res = PVTEngine.calculate_water_compressibility(pressure_psia=3000.0, temperature_f=180.0)
    assert cw_res.status == EngineeringStatus.VALID.value
    assert 2.0e-6 <= float(cw_res.value) <= 5.0e-6


def test_pvt_newman_rock_compressibility():
    """
    Newman (1973) cf rock compressibility for porosity = 0.18 (18%).
    """
    cf_res = PVTEngine.calculate_rock_compressibility(porosity_fraction=0.18)
    assert cf_res.status == EngineeringStatus.VALID.value
    assert 1.0e-6 <= float(cf_res.value) <= 30.0e-6


def test_pvt_unsupported_correlation_safety_barrier():
    """
    Verifies that requesting an unknown/unspecified correlation does NOT invent an equation
    and safely returns CORRELATION_SPECIFICATION_REQUIRED.
    """
    res = PVTEngine.calculate_bubble_point_and_rs(
        pressure_psia=2000.0,
        temperature_f=150.0,
        api_gravity=35.0,
        gas_gravity=0.75,
        correlation="InventedCorrelation"
    )
    assert res.status == EngineeringStatus.CORRELATION_SPECIFICATION_REQUIRED.value
