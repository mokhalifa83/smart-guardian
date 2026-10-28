"""
Test Suite for the 36 Petroleum Engineering, Surveillance & Economics Engines
Validates:
1. Exact count of 36 registered engines with SPE citations
2. Group 1: Virtual Flow Metering (VFM) & Downhole Virtual Sensor
3. Group 2: Production, Pressure & Injection Surveillance
4. Group 3: Core Reservoir Physics & Nodal Analysis
5. Group 4: Artificial Lift & ESP Diagnostics (Motor Cooling, Gas Locking, Affinity)
6. Group 5: Surveillance Analytics & Physics-Informed AI (PIAI)
7. Group 6: Petroleum Economics, Accounting & Human Approval Governance
8. REST API /api/v1/reservoir/engines/catalog verification
"""

import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.services.reservoir.contracts import EngineeringStatus
from app.services.reservoir.engine_catalog import ENGINE_CATALOG_36, get_36_engines_catalog
from app.services.reservoir.virtual_metering_engine import (
    VirtualFlowMeteringEngine,
    DownholePressureVirtualSensorEngine,
    BottomHoleFlowingPressureEngine
)
from app.services.reservoir.surveillance_operations_engine import (
    ProductionEngine,
    PressureSurveillanceEngine,
    InjectionEngine,
    GORDiagnosticEngine,
    MatureFieldDepletionEngine
)
from app.services.reservoir.artificial_lift_engine import (
    MotorCoolingEngine,
    PumpOffDetectionEngine,
    GasLockingDetectionEngine,
    VSDAffinityEngine,
    PumpPerformanceEngine
)
from app.services.reservoir.nodal_analysis_engine import NodalAnalysisEngine, InjectionOptimizationEngine
from app.services.reservoir.ai_analytics_engine import (
    AnomalyDetectionEngine,
    PatternAnalysisEngine,
    EvidenceCorrelationEngine,
    PredictiveAILayerEngine,
    RootCauseEngine
)
from app.services.reservoir.petroleum_economics_engine import (
    OilAccountingEngine,
    JointVentureAccountingEngine,
    CAPEXEngine,
    OPEXEngine,
    PetroleumEconomicsEngine,
    StatisticalProbabilisticEngine
)
from app.services.reservoir.decision_governance_engine import (
    EngineeringDecisionSupportEngine,
    EngineeringOptionsEngine,
    HumanApprovalEngine
)


def test_36_engines_catalog_integrity():
    assert len(ENGINE_CATALOG_36) == 36
    catalog = get_36_engines_catalog()
    assert len(catalog) == 36

    # Verify each engine has a valid SPE reference and category
    for item in ENGINE_CATALOG_36:
        assert "spe_reference" in item and item["spe_reference"]
        assert "name" in item and item["name"]
        assert "category" in item and item["category"]
        assert "class" in item and item["class"] is not None


def test_virtual_flow_metering_engine():
    # Valid choke flow
    res = VirtualFlowMeteringEngine.estimate_rates(
        upstream_pressure_psia=1200.0,
        downstream_pressure_psia=500.0,
        choke_size_64ths=32.0,
        wellhead_temperature_f=120.0,
        water_cut_pct=25.0,
        producing_gor_scf_stb=400.0
    )
    assert res.status == EngineeringStatus.VALID.value
    assert res.value > 0.0
    assert "estimated_oil_rate_stbd" in res.evidence
    assert res.evidence["flow_regime"] == "CRITICAL_FLOW"

    # Missing telemetry -> INSUFFICIENT_DATA (no guessing)
    res_missing = VirtualFlowMeteringEngine.estimate_rates(
        upstream_pressure_psia=1200.0,
        downstream_pressure_psia=500.0,
        choke_size_64ths=None,
        wellhead_temperature_f=120.0,
        water_cut_pct=25.0,
        producing_gor_scf_stb=400.0
    )
    assert res_missing.status == EngineeringStatus.INSUFFICIENT_DATA.value


def test_downhole_virtual_sensor_and_pwf():
    # Downhole pressure estimation
    res = DownholePressureVirtualSensorEngine.estimate_downhole_pressure(
        wellhead_pressure_psia=350.0,
        true_vertical_depth_ft=7500.0,
        water_cut_pct=15.0,
        flow_rate_stbd=1200.0
    )
    assert res.status == EngineeringStatus.VALID.value
    assert res.value > 2000.0  # Hydrostatic column adds ~2500 psi
    assert "hydrostatic_delta_p_psi" in res.evidence


def test_surveillance_and_injection_engines():
    # Production Engine
    prod_res = ProductionEngine.evaluate_well_production(
        oil_rate_stbd=850.0,
        water_rate_stbd=150.0,
        gas_rate_mscfd=425.0,
        uptime_hours=23.5
    )
    assert prod_res.status == EngineeringStatus.VALID.value
    assert prod_res.evidence["water_cut_pct"] == 15.0

    # Injection Engine (Hall & II)
    inj_res = InjectionEngine.evaluate_injectivity(
        injection_rate_bpd=3000.0,
        wellhead_injection_pressure_psia=3800.0,
        reservoir_pressure_psia=3200.0
    )
    assert inj_res.status == EngineeringStatus.VALID.value
    assert inj_res.value == 5.0  # 3000 / (3800 - 3200) = 5.0 bpd/psi


def test_artificial_lift_engines():
    # Motor Cooling Engine
    cool_res = MotorCoolingEngine.evaluate_cooling(
        liquid_rate_stbd=2500.0,
        casing_id_inches=6.276,
        motor_od_inches=4.56
    )
    assert cool_res.status == EngineeringStatus.VALID.value
    assert cool_res.value > 0.5  # Fluid velocity fps
    assert "cooling_state" in cool_res.evidence

    # Gas Locking Engine
    gas_lock = GasLockingDetectionEngine.evaluate_gas_lock_risk(
        pump_intake_pressure_psia=800.0,
        bubble_point_pressure_psia=1200.0,
        intake_free_gas_fraction=0.35
    )
    assert gas_lock.status == EngineeringStatus.VALID.value
    assert "lock_risk_state" in gas_lock.evidence

    # VSD Affinity Laws
    vsd_res = VSDAffinityEngine.calculate_frequency_shift(
        base_frequency_hz=50.0,
        target_frequency_hz=60.0,
        current_rate_stbd=1000.0,
        current_head_ft=4000.0,
        current_power_kw=75.0
    )
    assert vsd_res.status == EngineeringStatus.VALID.value
    assert vsd_res.value == 1200.0  # 1000 * (60/50) = 1200
    assert vsd_res.evidence["predicted_head_ft"] == 5760.0  # 4000 * 1.44 = 5760


def test_nodal_analysis_engine():
    nodal_res = NodalAnalysisEngine.solve_operating_point(
        reservoir_pressure_psia=3200.0,
        bubble_point_pressure_psia=2800.0,
        productivity_index_j=2.5,
        qmax_stbd=3000.0,
        wellhead_pressure_psia=200.0,
        true_vertical_depth_ft=6000.0
    )
    assert nodal_res.status == EngineeringStatus.VALID.value
    assert nodal_res.value > 0.0
    assert "operating_flowing_bhp_psia" in nodal_res.evidence


def test_ai_analytics_engines():
    # Anomaly Detection
    anom_res = AnomalyDetectionEngine.detect_anomalies(
        current_reading=45.0,
        baseline_mean=40.0,
        baseline_std=1.5,
        metric_name="Choke Temperature",
        physical_min=-20.0,
        physical_max=250.0
    )
    assert anom_res.status == EngineeringStatus.VALID.value
    assert anom_res.value == 3.33  # Z-Score (45-40)/1.5

    # Root Cause Engine
    root_res = RootCauseEngine.diagnose_root_cause(
        pi_trend_pct=-35.0,
        pressure_drop_pct=-4.0,
        tubing_head_loss_pct=10.0
    )
    assert root_res.status == EngineeringStatus.VALID.value
    assert root_res.value == "NEAR_WELLBORE_SKIN_DAMAGE"


def test_petroleum_economics_and_governance():
    # Oil Accounting (API MPMS 11.1)
    acct_res = OilAccountingEngine.calculate_net_standard_volume(
        gross_observed_volume_bbl=10000.0,
        observed_temp_f=85.0,
        observed_api_gravity=34.0,
        bsw_percentage=2.0
    )
    assert acct_res.status == EngineeringStatus.VALID.value
    assert acct_res.value < 10000.0  # Thermal contraction + BSW deduction

    # Monte Carlo Statistical Simulation
    mc_res = StatisticalProbabilisticEngine.simulate_prms_reserves(
        area_acres_min=500, area_acres_mode=640, area_acres_max=800,
        net_pay_ft_min=30, net_pay_ft_mode=45, net_pay_ft_max=60,
        porosity_min=0.15, porosity_mode=0.20, porosity_max=0.25,
        sw_min=0.20, sw_mode=0.25, sw_max=0.35,
        num_iterations=200
    )
    assert mc_res.status == EngineeringStatus.VALID.value
    assert "p90_1p_proved_eur_stb" in mc_res.evidence
    assert "p50_2p_probable_eur_stb" in mc_res.evidence
    assert mc_res.evidence["p10_3p_possible_eur_stb"] > mc_res.evidence["p90_1p_proved_eur_stb"]

    # Human Approval Engine
    gov_res = HumanApprovalEngine.request_or_verify_approval(
        action_id="ACT-CHK-01",
        action_type="CHOKE_ADJUSTMENT",
        target_well="WELL-001",
        proposed_setpoint="36/64ths",
        approver_engineer_name="Eng. Ahmed",
        approver_badge="ENG-7701",
        operational_justification="Prevent water coning breakthrough"
    )
    assert gov_res.status == EngineeringStatus.VALID.value
    assert gov_res.value == "APPROVED_READY_FOR_SUPERVISORY_DISPATCH"
    assert gov_res.evidence["is_authorized"] is True


@pytest.mark.asyncio
async def test_api_36_engines_catalog_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        res = await ac.get("/api/v1/reservoir/engines/catalog")
        assert res.status_code == 200
        data = res.json()
        assert data["total_engines"] == 36
        assert len(data["engines"]) == 36
        assert data["standards"] == "SPE Peer-Reviewed Literature & SPE-PRMS"
