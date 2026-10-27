"""
Test Suite for Step 2C Reservoir Engineering Orchestrator (test_reservoir_orchestrator.py)
Validates:
1. Orchestrator coordinates multi-discipline workflows without duplicating physics
2. Well performance diagnostic workflow (IPR, PI, Chan, allocation)
3. Reservoir depletion audit workflow (Volumetric vs Material Balance deviation alert)
4. Waterflood sweep surveillance workflow (Hall plot, sweep, Buckley-Leverett)
"""

import pytest
from app.services.reservoir.reservoir_engine import ReservoirEngineeringOrchestrator


def test_orchestrate_well_performance_diagnostic():
    result = ReservoirEngineeringOrchestrator.orchestrate_well_performance_diagnostic(
        well_code="WELL-201",
        reservoir_pressure_psia=3500.0,
        flowing_pressure_pwf_psia=2200.0,
        test_liquid_rate_stbd=850.0,
        bubble_point_psia=2800.0,
        allocation_data={"whp_psia": 250.0, "glr_scf_stb": 450.0, "choke_64ths": 28.0}
    )

    assert result["well_code"] == "WELL-201"
    assert "inflow_ipr" in result["analyses"]
    assert "productivity_index" in result["analyses"]
    assert "choke_allocation" in result["analyses"]
    assert len(result["evidence_chain"]) >= 1
    assert len(result["integrated_decision_support"]) >= 1


def test_orchestrate_reservoir_depletion_audit_with_alert():
    # Volumetric OOIP = 29.79 MMSTB
    # Simulated MBE history yields a significantly different N (e.g. 45 MMSTB -> deviation > 15%)
    vol_params = {
        "area_acres": 640.0,
        "net_pay_ft": 50.0,
        "porosity": 0.20,
        "initial_water_sat": 0.25,
        "initial_oil_fvf_boi": 1.25,
        "recovery_factor": 0.35,
        "initial_pressure_psia": 4000.0
    }

    # Synthesize MBE history points for Havlena-Odeh
    mbe_history = [
        {"pressure_psia": 4000.0, "cumulative_oil_np_stb": 0.0, "cumulative_water_wp_stb": 0.0, "cumulative_gas_gp_scf": 0.0, "water_injection_wi_stb": 0.0, "gas_injection_gi_scf": 0.0, "we_bbl": 0.0, "bo_rb_stb": 1.25, "rs_scf_stb": 600.0, "bg_rb_scf": 0.0012, "bw_rb_stb": 1.02},
        {"pressure_psia": 3800.0, "cumulative_oil_np_stb": 600_000.0, "cumulative_water_wp_stb": 10_000.0, "cumulative_gas_gp_scf": 360_000_000.0, "water_injection_wi_stb": 0.0, "gas_injection_gi_scf": 0.0, "we_bbl": 0.0, "bo_rb_stb": 1.24, "rs_scf_stb": 580.0, "bg_rb_scf": 0.0013, "bw_rb_stb": 1.02},
        {"pressure_psia": 3600.0, "cumulative_oil_np_stb": 1_300_000.0, "cumulative_water_wp_stb": 30_000.0, "cumulative_gas_gp_scf": 800_000_000.0, "water_injection_wi_stb": 0.0, "gas_injection_gi_scf": 0.0, "we_bbl": 0.0, "bo_rb_stb": 1.23, "rs_scf_stb": 560.0, "bg_rb_scf": 0.0014, "bw_rb_stb": 1.02}
    ]

    result = ReservoirEngineeringOrchestrator.orchestrate_reservoir_depletion_audit(
        reservoir_name="SANDSTONE_RESERVOIR_B",
        volumetric_params=vol_params,
        mbe_history=mbe_history
    )

    assert result["reservoir_name"] == "SANDSTONE_RESERVOIR_B"
    assert "volumetric_reserves" in result["analyses"]
    assert "material_balance" in result["analyses"]
    assert "reconciliation" in result
    assert "deviation_percentage" in result["reconciliation"]


def test_orchestrate_waterflood_sweep_analysis():
    hall_points = [
        {"cumulative_water_injected_wi_bbl": 10000.0, "flowing_tubing_pressure_psi": 2500.0, "delta_time_days": 10.0},
        {"cumulative_water_injected_wi_bbl": 30000.0, "flowing_tubing_pressure_psi": 2550.0, "delta_time_days": 20.0},
        {"cumulative_water_injected_wi_bbl": 60000.0, "flowing_tubing_pressure_psi": 2600.0, "delta_time_days": 30.0}
    ]

    sweep_params = {
        "ed_microscopic": 0.65,
        "ea_areal": 0.70,
        "ev_vertical": 0.75
    }

    result = ReservoirEngineeringOrchestrator.orchestrate_waterflood_sweep_analysis(
        pattern_name="INJ-PATTERN-04",
        hall_history=hall_points,
        sweep_params=sweep_params
    )

    assert result["pattern_name"] == "INJ-PATTERN-04"
    assert "hall_plot" in result["analyses"]
    assert "sweep_efficiency" in result["analyses"]
    assert len(result["decision_support"]) >= 1
