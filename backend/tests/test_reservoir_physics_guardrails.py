"""
Test Suite for Physics-Informed AI (PIAI) Guardrails & SPE Standards Verification
Validates:
1. Thermodynamic & PVT physical constraints (Standing, Vasquez-Beggs)
2. Inflow performance & hydraulic constraints (Vogel, Darcy)
3. Material balance mass conservation constraints (Havlena-Odeh)
4. Porous media saturation and relative permeability constraints (Buckley-Leverett)
5. Decline curve analysis constraints (Arps)
6. Strict Data Integrity policy: Explicit INSUFFICIENT_DATA and rejection of synthetic zeroes
"""

import pytest
from app.services.reservoir.physics_guardrails import PhysicsGuardrails
from app.services.reservoir.contracts import EngineeringStatus


def test_pvt_thermodynamic_guardrails():
    # Valid PVT
    is_valid, err = PhysicsGuardrails.validate_pvt_boundaries(
        bo=1.25, bg=0.005, bw=1.02, rs=450.0, reservoir_pressure_psia=3200.0, temperature_f=180.0
    )
    assert is_valid is True
    assert err is None

    # Unphysical Bo < 1.0 (Liquid expansion cannot contract below 1.0 at standard conditions)
    is_valid, err = PhysicsGuardrails.validate_pvt_boundaries(bo=0.85)
    assert is_valid is False
    assert "Bo (0.85 rb/stb) < 1.0" in err

    # Unphysical Rs < 0.0
    is_valid, err = PhysicsGuardrails.validate_pvt_boundaries(rs=-10.0)
    assert is_valid is False
    assert "Solution gas-oil ratio cannot be negative" in err


def test_inflow_hydraulics_guardrails():
    # Valid Drawdown
    is_valid, err = PhysicsGuardrails.validate_inflow_hydraulics(
        reservoir_pressure_psia=3000.0, flowing_bhp_psia=2200.0, flow_rate_stbd=800.0, qmax_stbd=1500.0
    )
    assert is_valid is True
    assert err is None

    # Unphysical Pwf > Pres (producing well cannot have negative drawdown)
    is_valid, err = PhysicsGuardrails.validate_inflow_hydraulics(
        reservoir_pressure_psia=2500.0, flowing_bhp_psia=2800.0
    )
    assert is_valid is False
    assert "Pwf (2800.0 psia) > Pres (2500.0 psia)" in err

    # Producing rate exceeding theoretical AOFP / Qmax
    is_valid, err = PhysicsGuardrails.validate_inflow_hydraulics(
        reservoir_pressure_psia=3000.0, flowing_bhp_psia=1500.0, flow_rate_stbd=2500.0, qmax_stbd=2000.0
    )
    assert is_valid is False
    assert "Rate (2500.0 STB/D) > AOFP / Qmax (2000.0 STB/D)" in err


def test_material_balance_conservation_guardrails():
    # Valid Material Balance (Np <= OOIP, indices sum ~ 1.0)
    indices = {"DDI": 0.45, "SDI": 0.25, "WDI": 0.20, "EDI": 0.10}
    is_valid, err = PhysicsGuardrails.validate_material_balance_conservation(
        np_stb=2_000_000.0, n_stb_ooip=10_000_000.0, recovery_factor=0.20, drive_indices=indices
    )
    assert is_valid is True
    assert err is None

    # Unphysical Np > OOIP (Cannot produce more oil than initially in place)
    is_valid, err = PhysicsGuardrails.validate_material_balance_conservation(
        np_stb=15_000_000.0, n_stb_ooip=10_000_000.0
    )
    assert is_valid is False
    assert "Cumulative production Np" in err
    assert "violates fundamental mass conservation" in err.lower()

    # Drive indices do not sum to unity
    unbalanced_indices = {"DDI": 0.10, "SDI": 0.10, "WDI": 0.10, "EDI": 0.10}
    is_valid, err = PhysicsGuardrails.validate_material_balance_conservation(
        np_stb=1_000_000.0, drive_indices=unbalanced_indices
    )
    assert is_valid is False
    assert "Drive indices must sum to unity" in err


def test_saturation_and_relative_perm_guardrails():
    # Valid
    is_valid, err = PhysicsGuardrails.validate_saturation_and_relative_perm(
        sw=0.45, swi=0.25, sor=0.20, krw=0.15, kro=0.65, water_cut_pct=40.0
    )
    assert is_valid is True
    assert err is None

    # Unphysical Sw > 1.0
    is_valid, err = PhysicsGuardrails.validate_saturation_and_relative_perm(sw=1.25)
    assert is_valid is False
    assert "Water saturation Sw" in err

    # Unphysical Water Cut > 100%
    is_valid, err = PhysicsGuardrails.validate_saturation_and_relative_perm(water_cut_pct=108.0)
    assert is_valid is False
    assert "Water Cut (108.0%) must be within [0.0%, 100.0%]" in err


def test_arps_decline_guardrails():
    # Valid Arps Hyperbolic
    is_valid, err = PhysicsGuardrails.validate_arps_decline_parameters(
        qi_stbd=1200.0, nominal_decline_di=0.15, b_factor=0.4
    )
    assert is_valid is True
    assert err is None

    # Unphysical negative b-factor
    is_valid, err = PhysicsGuardrails.validate_arps_decline_parameters(
        qi_stbd=1200.0, nominal_decline_di=0.15, b_factor=-0.5
    )
    assert is_valid is False
    assert "Arps b-factor (-0.5) cannot be negative" in err


def test_strict_data_integrity_no_synthetic_data():
    required_inputs = {
        "reservoir_pressure_psia": 3200.0,
        "permeability_md": None,  # Missing field measurement
        "thickness_ft": 45.0
    }

    result = PhysicsGuardrails.assert_strict_data_integrity(
        required_fields=required_inputs,
        calculation_name="Darcy Inflow Capacity",
        model_name="Radial Steady-State Darcy",
        spe_reference="Darcy (1856), Craft & Hawkins (1991)"
    )

    assert result is not None
    assert result.status == EngineeringStatus.INSUFFICIENT_DATA.value
    assert result.value is None
    assert "permeability_md" in result.limitations[0]
    assert "No synthetic or fabricated fallback values permitted" in result.assumptions[0]
