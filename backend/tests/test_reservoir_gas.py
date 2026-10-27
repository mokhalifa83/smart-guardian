"""
Test Suite for Step 2C Gas Reservoir Engineering Engine (test_reservoir_gas.py)
Validates:
1. Gas material balance p/z vs Gp linear regression and OGIP extrapolation
2. Water-drive curvature detection in p/z history
3. Rawlins & Schellhardt deliverability equation and AOF calculation
4. Real gas pseudo-pressure m(p) numerical integration using canonical PVTEngine
5. Non-Darcy turbulence partition (Forchheimer formulation)
"""

import pytest
from app.services.reservoir.gas_reservoir_engine import GasReservoirEngine
from app.services.reservoir.contracts import EngineeringStatus


def test_gas_pz_linear_depletion():
    # Synthetic volumetric gas reservoir history
    # Pressure drops from 3500 to 2200 psia with cumulative production Gp
    history = [
        {"pressure_psia": 3500.0, "cumulative_gas_gp_mscf": 0.0},
        {"pressure_psia": 3100.0, "cumulative_gas_gp_mscf": 1_000_000.0},
        {"pressure_psia": 2700.0, "cumulative_gas_gp_mscf": 2_100_000.0},
        {"pressure_psia": 2300.0, "cumulative_gas_gp_mscf": 3_200_000.0}
    ]

    res = GasReservoirEngine.calculate_pz_material_balance(
        history=history,
        temperature_f=180.0,
        gas_gravity=0.70,
        abandonment_pressure_psia=500.0
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value is not None
    assert res.value > 8_000_000  # OGIP in Mscf (> 8 Bscf)
    assert res.evidence["r_squared"] > 0.95
    assert res.evidence["eur_mscf"] > 0
    assert res.evidence["recovery_factor_at_abandonment"] > 0.70
    assert res.observed_pattern == "DEPLETION_DRIVE_LINEAR"


def test_gas_pz_water_drive_detection():
    # Late pressure stabilization deviating upwards from linear trend
    history = [
        {"pressure_psia": 4000.0, "cumulative_gas_gp_mscf": 0.0},
        {"pressure_psia": 3200.0, "cumulative_gas_gp_mscf": 2_000_000.0},
        {"pressure_psia": 3100.0, "cumulative_gas_gp_mscf": 4_000_000.0}
    ]

    res = GasReservoirEngine.calculate_pz_material_balance(
        history=history,
        temperature_f=200.0,
        gas_gravity=0.65,
        abandonment_pressure_psia=500.0
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.observed_pattern == "WATER_DRIVE_SUSPECTED_NON_LINEAR_PZ"
    assert any("water drive" in w.lower() for w in res.warnings)


def test_gas_deliverability_ipr_and_aof():
    # Pr = 3000 psia, Pwf = 2000 psia, C = 0.005 Mscfd/psi^2n, n = 0.85
    res = GasReservoirEngine.calculate_gas_deliverability_ipr(
        reservoir_pressure_pr_psia=3000.0,
        flowing_pressure_pwf_psia=2000.0,
        c_coefficient=0.005,
        n_exponent=0.85,
        well_code="GAS-01"
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value > 0
    assert res.unit == "Mscf/d"
    assert "aof_potential_mscfd" in res.evidence
    assert res.evidence["aof_potential_mscfd"] > res.value
    assert len(res.evidence["ipr_curve_points"]) == 5


def test_gas_deliverability_zero_drawdown():
    res = GasReservoirEngine.calculate_gas_deliverability_ipr(
        reservoir_pressure_pr_psia=2500.0,
        flowing_pressure_pwf_psia=2500.0,
        c_coefficient=0.005,
        n_exponent=0.85
    )
    assert res.status == EngineeringStatus.ZERO_DRAWDOWN.value
    assert res.value == 0.0


def test_gas_pseudopressure_integration():
    # Integral from 14.7 psia to 3000 psia at 160 F, gamma_g = 0.68
    res = GasReservoirEngine.calculate_real_gas_pseudopressure(
        pressure_psia=3000.0,
        temperature_f=160.0,
        gas_gravity=0.68,
        p_base_psia=14.7,
        num_intervals=25
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value > 100_000_000  # typical m(p) for 3000 psia is > 3e8 psia^2/cP
    assert res.unit == "psia^2/cP"
    assert res.evidence["upper_pressure_psia"] == 3000.0


def test_gas_nondarcy_turbulence():
    # Forchheimer: A = 0.05, B = 0.0001, qg = 2000 Mscfd
    # Lam = 0.05 * 2000 = 100
    # Turb = 0.0001 * 4,000,000 = 400
    # Total = 500, Turb frac = 400 / 500 = 0.80 (80%)
    res = GasReservoirEngine.calculate_nondarcy_turbulence_factor(
        reservoir_pressure_pr_psia=3000.0,
        flowing_pressure_pwf_psia=2500.0,
        gas_rate_qg_mscfd=2000.0,
        laminar_coefficient_a=0.05,
        turbulent_coefficient_b=0.0001
    )

    assert res.status == EngineeringStatus.VALID.value
    assert res.value == 0.80
    assert res.evidence["turbulence_percentage"] == 80.0
    assert res.observed_pattern == "TURBULENT_HIGH_VELOCITY_GAS_FLOW"
