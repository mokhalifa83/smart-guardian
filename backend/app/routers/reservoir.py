from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.core.security import verify_read_only_boundary
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.pvt_engine import PVTEngine
from app.services.reservoir.virtual_separator_pvt import (
    VirtualSeparatorPVTFoundation,
    SeparatorConditionsSuite,
    SeparatorStageCondition as PVTSeparatorStageCondition
)
from app.services.reservoir.chan_service import ChanService
from app.services.reservoir.darcy_engine import DarcyRadialFlowEngine
from app.services.reservoir.productivity_index import ProductivityIndexEngine
from app.services.reservoir.vogel_engine import VogelIPREngine
from app.services.reservoir.material_balance import MaterialBalanceEngine
from app.services.reservoir.vrr_engine import VoidageReplacementEngine
from app.services.reservoir.decline_engine import DeclineEngine
from app.services.reservoir.well_test_engine import WellTestEngine
from app.services.reservoir.aquifer_engine import AquiferEngine
from app.services.reservoir.fractional_flow_engine import FractionalFlowEngine
from app.services.reservoir.buckley_leverett_engine import BuckleyLeverettEngine
from app.services.reservoir.waterflood_engine import WaterfloodEngine
from app.services.reservoir.sweep_engine import SweepEngine
from app.services.reservoir.wc_calibration import WaterCutCalibrationEngine
from app.services.reservoir.well_allocation import WellAllocationEngine
from app.services.reservoir.separator_service import VirtualSeparatorService
from app.services.reservoir.reserves_engine import ReservesEngine
from app.services.reservoir.gas_reservoir_engine import GasReservoirEngine
from app.services.reservoir.reservoir_engine import ReservoirEngineeringOrchestrator
from app.services.reservoir.evidence_model import UnifiedEngineeringEvidence
from app.services.opcua_client import ReadOnlyOPCUAClient, ReadOnlyViolationError
from app.services.edge_connector import EdgeConnector
from app.services.reconciliation_service import VirtualSeparatorReconciliationService
from app.services.daily_report_service import DailyReportService, DailyReservoirReport
from app.services.reservoir.integration_contracts import Step2CIntegrationRegistry, Step2CConnectorReadiness

from app.schemas.reservoir import (
    PVTCalculationRequest,
    SeparatorFoundationRequest,
    ChanDiagnosticRequest,
    DarcyCalculationRequest,
    ProductivityIndexRequest,
    VogelCalculationRequest,
    MaterialBalanceRequest,
    VRRCalculationRequest,
    DeclineAnalysisRequest,
    DrawdownTestRequest,
    HornerBuildupRequest,
    AquiferCalculationRequest,
    FractionalFlowRequest,
    BuckleyLeverettRequest,
    WaterfloodSurveillanceRequest,
    SweepEfficiencyRequest,
    WaterCutCalibrationRequest,
    WellAllocationRequest,
    VirtualSeparatorTrainRequest,
    ReservesCalculationRequest,
    GasGIIPRequest,
    GasPzRequest,
    GasDeliverabilityRequest,
    GasPseudopressureRequest,
    GasTurbulenceRequest,
    WellDiagnosticOrchestrationRequest,
    ReservoirDepletionAuditRequest,
    VirtualSeparatorReconciliationRequest,
    EdgeTelemetryIngestRequest
)

router = APIRouter(prefix="/reservoir", tags=["Reservoir Intelligence Layer"])


# ============================================================
# STEP 2A ENDPOINTS: CORE RESERVOIR PHYSICS & SURVEILLANCE
# ============================================================

@router.post("/pvt/calculate", response_model=EngineeringResult)
async def calculate_pvt_packet(payload: PVTCalculationRequest):
    """
    Computes comprehensive canonical black-oil PVT properties:
    Bo, Bg, Bw, Rs, Z-factor, co, cw, and cf using validated literature correlations
    (Standing, Vasquez-Beggs, Sutton, Hall-Yarborough, McCain, Newman).
    """
    verify_read_only_boundary()
    rs_val = payload.rs
    if rs_val is None:
        rs_res = PVTEngine.calculate_solution_gor_rs(
            pressure_psia=payload.pressure_psia,
            temperature_f=payload.temperature_f,
            gas_gravity=payload.gas_gravity,
            api_gravity=payload.api_gravity,
            correlation=payload.correlation
        )
        if rs_res.status != EngineeringStatus.VALID.value:
            return rs_res
        rs_val = float(rs_res.value)

    bo_res = PVTEngine.calculate_oil_fvf_bo(
        pressure_psia=payload.pressure_psia,
        temperature_f=payload.temperature_f,
        gas_gravity=payload.gas_gravity,
        api_gravity=payload.api_gravity,
        rs=rs_val,
        bubble_point_psia=payload.bubble_point_psia,
        correlation=payload.correlation
    )
    if bo_res.status != EngineeringStatus.VALID.value:
        return bo_res

    bg_res = PVTEngine.calculate_gas_fvf_bg(
        pressure_psia=payload.pressure_psia,
        temperature_f=payload.temperature_f,
        gas_gravity=payload.gas_gravity
    )
    if bg_res.status != EngineeringStatus.VALID.value:
        return bg_res

    bw_res = PVTEngine.calculate_water_fvf_bw(
        pressure_psia=payload.pressure_psia,
        temperature_f=payload.temperature_f
    )
    z_res = PVTEngine.calculate_z_factor_hall_yarborough(
        pressure_psia=payload.pressure_psia,
        temperature_f=payload.temperature_f,
        gas_gravity=payload.gas_gravity
    )

    return EngineeringResult(
        value={
            "Bo_rb_stb": bo_res.value,
            "Bg_rb_scf": bg_res.value,
            "Bw_rb_stb": bw_res.value,
            "Rs_scf_stb": rs_val,
            "Z_factor": z_res.value
        },
        unit="black_oil_pvt_packet",
        model=f"PVT Packet ({payload.correlation})",
        correlation=payload.correlation,
        correlation_reference="Standing (1947/1977), Vasquez-Beggs (1980), Hall-Yarborough (1973), McCain (1991)",
        inputs=payload.model_dump(),
        evidence={
            "bo_details": bo_res.evidence,
            "bg_details": bg_res.evidence,
            "bw_details": bw_res.evidence,
            "z_details": z_res.evidence
        },
        status=EngineeringStatus.VALID.value
    )


@router.post("/separator/foundation", response_model=EngineeringResult)
@router.post("/pvt/separator-foundation", response_model=EngineeringResult)
async def evaluate_separator_foundation(payload: SeparatorFoundationRequest):
    """
    Evaluates separator stage conditions and applies validated PVT corrections.
    """
    verify_read_only_boundary()
    stage = PVTSeparatorStageCondition(
        stage_name="STAGE_1_SEPARATOR",
        pressure_psia=payload.stage_1_pressure_psia,
        temperature_f=payload.stage_1_temperature_f
    )
    return VirtualSeparatorPVTFoundation.apply_separator_pvt_correction(
        raw_bo=payload.base_bo,
        stage_conditions=stage,
        correlation_name=payload.correlation_name or "UNSPECIFIED"
    )


@router.post("/chan/diagnostics", response_model=EngineeringResult)
async def compute_chan_diagnostics(payload: ChanDiagnosticRequest, db: AsyncSession = Depends(get_db)):
    """
    Computes Chan (1995) diagnostic plots: WOR and logarithmic derivative WOR' = d(WOR)/d(ln(t)).
    """
    verify_read_only_boundary()
    if payload.points and len(payload.points) >= 2:
        from app.services.reservoir.chan_engine import ChanDiagnosticEngine
        return ChanDiagnosticEngine.compute_chan_diagnostic_series(
            history=payload.points,
            well_code=payload.well_code
        )
    return await ChanService.get_well_chan_diagnostics(db=db, well_code=payload.well_code)


@router.post("/darcy/radial-flow", response_model=EngineeringResult)
async def calculate_darcy_flow(payload: DarcyCalculationRequest):
    """
    Semi-steady state radial Darcy inflow equation.
    """
    verify_read_only_boundary()
    return DarcyRadialFlowEngine.calculate_semi_steady_state(
        permeability_md=payload.permeability_md,
        thickness_ft=payload.thickness_ft,
        reservoir_pressure_psia=payload.reservoir_pressure_psia,
        flowing_bhp_psia=payload.flowing_bhp_psia,
        viscosity_cp=payload.viscosity_cp,
        bo_rb_stb=payload.bo_rb_stb,
        drainage_radius_ft=payload.drainage_radius_ft,
        wellbore_radius_ft=payload.wellbore_radius_ft,
        skin=payload.skin
    )


@router.post("/productivity-index/calculate", response_model=EngineeringResult)
@router.post("/productivity-index", response_model=EngineeringResult)
async def calculate_productivity_index(payload: ProductivityIndexRequest):
    """
    Computes well Productivity Index J = q / (pr - pwf) with zero-drawdown protection.
    """
    verify_read_only_boundary()
    return ProductivityIndexEngine.calculate_pi(
        flow_rate_stbd=payload.flow_rate_stbd,
        reservoir_pressure_psia=payload.reservoir_pressure_psia,
        flowing_bhp_psia=payload.flowing_bhp_psia
    )


@router.post("/vogel/calculate", response_model=EngineeringResult)
@router.post("/vogel/ipr", response_model=EngineeringResult)
async def calculate_vogel_ipr(payload: VogelCalculationRequest):
    """
    Vogel (1968) dimensionless IPR for solution-gas drive reservoirs below bubble point.
    """
    verify_read_only_boundary()
    if payload.qmax_stbd is not None:
        if payload.flowing_bhp_psia is not None:
            return VogelIPREngine.calculate_vogel_rate(
                qmax_stbd=payload.qmax_stbd,
                reservoir_pressure_psia=payload.reservoir_pressure_psia,
                flowing_bhp_psia=payload.flowing_bhp_psia
            )
        return VogelIPREngine.generate_ipr_curve(
            qmax_stbd=payload.qmax_stbd,
            reservoir_pressure_psia=payload.reservoir_pressure_psia
        )
    elif payload.test_rate_stbd is not None and payload.test_flowing_bhp_psia is not None:
        return VogelIPREngine.estimate_qmax_from_test(
            test_rate_stbd=payload.test_rate_stbd,
            test_flowing_bhp_psia=payload.test_flowing_bhp_psia,
            reservoir_pressure_psia=payload.reservoir_pressure_psia
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either qmax_stbd or (test_rate_stbd and test_flowing_bhp_psia) must be provided."
        )


@router.post("/material-balance", response_model=EngineeringResult)
@router.post("/material-balance/havlena-odeh", response_model=EngineeringResult)
async def calculate_material_balance(payload: MaterialBalanceRequest):
    """
    General Havlena-Odeh (1963) Straight Line Material Balance Engine.
    """
    verify_read_only_boundary()
    return MaterialBalanceEngine.calculate_single_state(
        initial_pressure_psia=payload.initial_pressure_psia,
        initial_bo=payload.initial_bo,
        initial_bg=payload.initial_bg,
        initial_rs=payload.initial_rs,
        initial_swi=payload.initial_swi,
        current_pressure_psia=payload.current_pressure_psia,
        current_bo=payload.current_bo,
        current_bg=payload.current_bg,
        current_rs=payload.current_rs,
        np_stb=payload.np_stb,
        wp_stb=payload.wp_stb,
        gp_mscf=payload.gp_mscf,
        rp_scf_stb=payload.rp_scf_stb,
        bw_rb_stb=payload.bw_rb_stb,
        m_gas_cap_ratio=payload.m_gas_cap_ratio,
        cf_pore_compressibility=payload.cf_pore_compressibility,
        cw_water_compressibility=payload.cw_water_compressibility,
        we_water_influx_rb=payload.we_water_influx_rb,
        n_stb_estimate=payload.n_stb_estimate
    )


@router.post("/vrr", response_model=EngineeringResult)
async def calculate_voidage_replacement_ratio(payload: VRRCalculationRequest):
    """
    Evaluates Voidage Replacement Ratio (VRR) converting surface volumes to in-situ reservoir volumes via PVT.
    """
    verify_read_only_boundary()
    return VoidageReplacementEngine.calculate_vrr(
        produced_oil_stb=payload.produced_oil_stb,
        produced_water_bbl=payload.produced_water_bbl,
        produced_gas_scf=payload.produced_gas_scf,
        injected_water_bbl=payload.injected_water_bbl,
        injected_gas_scf=payload.injected_gas_scf,
        bo_rb_stb=payload.bo_rb_stb,
        bw_rb_stb=payload.bw_rb_stb,
        bg_rb_scf=payload.bg_rb_scf,
        rs_scf_stb=payload.rs_scf_stb,
        time_window_days=payload.time_window_days,
        is_instantaneous_rate=payload.is_instantaneous_rate
    )


# ============================================================
# STEP 2B ENDPOINTS: SURVEILLANCE, DYNAMICS & VIRTUAL SEPARATOR
# ============================================================

@router.post("/decline", response_model=EngineeringResult)
async def analyze_decline_curve(payload: DeclineAnalysisRequest):
    """
    Executes canonical Arps decline curve analysis (Exponential, Harmonic, Hyperbolic).
    """
    verify_read_only_boundary()
    return DeclineEngine.analyze_decline(
        history=payload.history,
        model_type=payload.model_type,
        forecast_horizon_days=payload.forecast_horizon_days,
        economic_limit_rate_stbd=payload.economic_limit_rate_stbd,
        well_code=payload.well_code
    )


@router.post("/well-test/drawdown", response_model=EngineeringResult)
async def analyze_drawdown_test(payload: DrawdownTestRequest):
    """
    Executes constant-rate drawdown transient analysis for permeability, skin, and flow efficiency.
    """
    verify_read_only_boundary()
    return WellTestEngine.analyze_drawdown(
        gauge_points=payload.gauge_points,
        initial_pressure_psia=payload.initial_pressure_psia,
        flow_rate_stbd=payload.flow_rate_stbd,
        formation_thickness_ft=payload.formation_thickness_ft,
        porosity_fraction=payload.porosity_fraction,
        total_compressibility_psi=payload.total_compressibility_psi,
        viscosity_cp=payload.viscosity_cp,
        bo_rb_stb=payload.bo_rb_stb,
        wellbore_radius_ft=payload.wellbore_radius_ft,
        well_code=payload.well_code
    )


@router.post("/well-test/horner", response_model=EngineeringResult)
async def analyze_horner_buildup_test(payload: HornerBuildupRequest):
    """
    Executes Horner (1951) pressure buildup analysis for extrapolated pressure p*, kh, and skin.
    """
    verify_read_only_boundary()
    return WellTestEngine.analyze_horner_buildup(
        gauge_points=payload.gauge_points,
        producing_time_tp_hours=payload.producing_time_tp_hours,
        flow_rate_stbd=payload.flow_rate_stbd,
        formation_thickness_ft=payload.formation_thickness_ft,
        porosity_fraction=payload.porosity_fraction,
        total_compressibility_psi=payload.total_compressibility_psi,
        viscosity_cp=payload.viscosity_cp,
        bo_rb_stb=payload.bo_rb_stb,
        wellbore_radius_ft=payload.wellbore_radius_ft,
        flowing_pwf_at_shutin_psia=payload.flowing_pwf_at_shutin_psia,
        well_code=payload.well_code
    )


@router.post("/aquifer", response_model=EngineeringResult)
async def calculate_aquifer_influx(payload: AquiferCalculationRequest):
    """
    Calculates water influx using Fetkovich (mandatory), Schilthuis, or Van Everdingen-Hurst models.
    """
    verify_read_only_boundary()
    model_type = payload.model_type.upper()
    if model_type == "FETKOVICH":
        return AquiferEngine.calculate_fetkovich(
            pressure_history=payload.pressure_history,
            initial_pressure_psia=payload.initial_pressure_psia,
            permeability_md=payload.permeability_md,
            formation_thickness_ft=payload.formation_thickness_ft,
            porosity_fraction=payload.porosity_fraction,
            total_compressibility_psi=payload.total_compressibility_psi,
            water_viscosity_cp=payload.water_viscosity_cp,
            reservoir_radius_ft=payload.reservoir_radius_ft,
            aquifer_radius_ft=payload.aquifer_radius_ft,
            encroachment_angle_deg=payload.encroachment_angle_deg
        )
    elif model_type == "SCHILTHUIS":
        c_const = payload.water_influx_constant_c or 10.0
        return AquiferEngine.calculate_schilthuis(
            pressure_history=payload.pressure_history,
            initial_pressure_psia=payload.initial_pressure_psia,
            water_influx_constant_c_stb_day_psi=c_const
        )
    elif model_type == "VAN_EVERDINGEN_HURST":
        return AquiferEngine.calculate_van_everdingen_hurst(
            pressure_history=payload.pressure_history,
            initial_pressure_psia=payload.initial_pressure_psia,
            permeability_md=payload.permeability_md,
            formation_thickness_ft=payload.formation_thickness_ft,
            porosity_fraction=payload.porosity_fraction,
            total_compressibility_psi=payload.total_compressibility_psi,
            water_viscosity_cp=payload.water_viscosity_cp,
            reservoir_radius_ft=payload.reservoir_radius_ft,
            encroachment_angle_deg=payload.encroachment_angle_deg
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported aquifer model: '{payload.model_type}'"
        )


@router.post("/fractional-flow", response_model=EngineeringResult)
async def calculate_fractional_flow(payload: FractionalFlowRequest):
    """
    Evaluates fractional flow fw(Sw) and mobility ratio via Corey model or core laboratory points.
    """
    verify_read_only_boundary()
    if payload.core_points:
        return FractionalFlowEngine.calculate_from_core_data(
            core_points=payload.core_points,
            water_viscosity_cp=payload.water_viscosity_cp,
            oil_viscosity_cp=payload.oil_viscosity_cp
        )
    return FractionalFlowEngine.calculate_corey_model(
        sw_connate=payload.sw_connate,
        so_residual=payload.so_residual,
        krw_endpoint=payload.krw_endpoint,
        kro_endpoint=payload.kro_endpoint,
        nw_exponent=payload.nw_exponent,
        no_exponent=payload.no_exponent,
        water_viscosity_cp=payload.water_viscosity_cp,
        oil_viscosity_cp=payload.oil_viscosity_cp
    )


@router.post("/buckley-leverett", response_model=EngineeringResult)
async def calculate_buckley_leverett(payload: BuckleyLeverettRequest):
    """
    Analytical 1D Buckley-Leverett frontal advance displacement and breakthrough timing.
    """
    verify_read_only_boundary()
    return BuckleyLeverettEngine.calculate_displacement(
        injection_rate_bpd=payload.injection_rate_bpd,
        cross_sectional_area_ft2=payload.cross_sectional_area_ft2,
        length_between_wells_ft=payload.length_between_wells_ft,
        porosity_fraction=payload.porosity_fraction,
        initial_water_saturation=payload.initial_water_saturation,
        so_residual=payload.so_residual,
        water_viscosity_cp=payload.water_viscosity_cp,
        oil_viscosity_cp=payload.oil_viscosity_cp
    )


@router.post("/waterflood", response_model=EngineeringResult)
async def analyze_waterflood_pattern(payload: WaterfloodSurveillanceRequest):
    """
    Waterflood pattern surveillance integrating canonical VRR and Hall diagnostic plot.
    """
    verify_read_only_boundary()
    return WaterfloodEngine.analyze_waterflood_surveillance(
        history=payload.history,
        bo_rb_stb=payload.bo_rb_stb,
        bw_rb_stb=payload.bw_rb_stb,
        bg_rb_scf=payload.bg_rb_scf,
        rs_scf_stb=payload.rs_scf_stb,
        pattern_name=payload.pattern_name,
        injector_well_code=payload.injector_well_code
    )


@router.post("/sweep", response_model=EngineeringResult)
async def calculate_sweep_efficiency(payload: SweepEfficiencyRequest):
    """
    Calculates microscopic displacement (ED), vertical sweep (EI), and volumetric sweep (Ev).
    """
    verify_read_only_boundary()
    ei = payload.vertical_sweep_ei
    if ei is None:
        ei_res = SweepEngine.calculate_vertical_sweep_dykstra_parsons(
            permeability_layers_md=payload.permeability_layers_md,
            v_dp_coefficient=payload.v_dp_coefficient,
            mobility_ratio_m=payload.mobility_ratio_m
        )
        if ei_res.status != EngineeringStatus.VALID.value:
            return ei_res
        ei = float(ei_res.value)

    return SweepEngine.calculate_total_volumetric_sweep(
        sw_connate=payload.sw_connate,
        so_residual=payload.so_residual,
        areal_sweep_ea=payload.areal_sweep_ea,
        vertical_sweep_ei=ei
    )


@router.post("/virtual-separator", response_model=EngineeringResult)
async def process_virtual_separator(payload: VirtualSeparatorTrainRequest):
    """
    Executes multi-stage separation train, Bo raw vs corrected, and 3-phase splits.
    """
    verify_read_only_boundary()
    return VirtualSeparatorService.process_separation_train(
        total_liquid_rate_stbd=payload.total_liquid_rate_stbd,
        water_cut_fraction=payload.water_cut_fraction,
        producing_gor_scf_stb=payload.producing_gor_scf_stb,
        reservoir_pressure_psia=payload.reservoir_pressure_psia,
        reservoir_temperature_f=payload.reservoir_temperature_f,
        gas_gravity=payload.gas_gravity,
        oil_api=payload.oil_api,
        stage_conditions=payload.stage_conditions
    )


@router.post("/well-allocation", response_model=EngineeringResult)
async def calculate_well_allocation(payload: WellAllocationRequest):
    """
    Calculates allocated phase rates from wellhead choke telemetry (Gilbert, Ros, Baxendell, Achong).
    """
    verify_read_only_boundary()
    return WellAllocationEngine.calculate_choke_allocation(payload.choke_inputs)


@router.post("/wc-calibration", response_model=EngineeringResult)
async def calibrate_water_cut(payload: WaterCutCalibrationRequest):
    """
    Dual-truth water cut calibration: determines calibration factor CF and applies to live telemetry.
    """
    verify_read_only_boundary()
    cf_res = WaterCutCalibrationEngine.calculate_calibration_factor(
        lab_sample=payload.lab_sample,
        live_observation_at_sample=payload.live_sample_reading
    )
    if cf_res.status != EngineeringStatus.VALID.value:
        return cf_res

    cf_val = float(cf_res.value["calibration_factor"])
    if payload.current_live_reading:
        return WaterCutCalibrationEngine.apply_calibration(
            current_live_reading=payload.current_live_reading,
            calibration_factor=cf_val,
            calibration_timestamp=payload.lab_sample.timestamp
        )
    return cf_res


@router.get("/integration/connectors", response_model=List[Step2CConnectorReadiness])
async def list_step2c_integration_connectors():
    """
    Lists field integration contract readiness for future STEP 2C.
    All live connections are strictly declared inactive in STEP 2B.
    """
    verify_read_only_boundary()
    return Step2CIntegrationRegistry.get_connector_contracts()


# ============================================================
# STEP 2C ENDPOINTS: RESERVES, GAS, ORCHESTRATION, FIELD & REPORTING
# ============================================================

@router.post("/reserves/oil", response_model=EngineeringResult)
async def calculate_oil_reserves(payload: ReservesCalculationRequest):
    """
    Computes volumetric OOIP / STOIIP, EUR, Remaining Commercial Reserves, and Unrecoverable Resources.
    Distinguishes in-place resources from commercial reserves according to SPE-PRMS standards.
    """
    verify_read_only_boundary()
    return ReservesEngine.calculate_oil_reserves_and_resources(
        area_acres=payload.area_acres,
        net_pay_ft=payload.net_pay_ft,
        porosity=payload.porosity,
        initial_water_sat=payload.initial_water_sat,
        initial_oil_fvf_boi=payload.initial_oil_fvf_boi,
        recovery_factor=payload.recovery_factor,
        cumulative_oil_np_stb=payload.cumulative_oil_np_stb,
        economic_limit_bopd=payload.economic_limit_bopd,
        well_or_field_id=payload.well_or_field_id
    )


@router.post("/reserves/gas", response_model=EngineeringResult)
async def calculate_gas_giip(payload: GasGIIPRequest):
    """
    Calculates volumetric Original Gas In Place (GIIP / OGIP) in Mscf.
    """
    verify_read_only_boundary()
    return ReservesEngine.calculate_giip_volumetric(
        area_acres=payload.area_acres,
        net_pay_ft=payload.net_pay_ft,
        porosity=payload.porosity,
        initial_water_sat=payload.initial_water_sat,
        initial_gas_fvf_bgi=payload.initial_gas_fvf_bgi,
        bgi_unit=payload.bgi_unit,
        well_or_field_id=payload.well_or_field_id
    )


@router.post("/gas/pz", response_model=EngineeringResult)
async def calculate_gas_pz(payload: GasPzRequest):
    """
    Computes gas material balance (p/z vs Gp linear regression), OGIP extrapolation,
    abandonment EUR, and detects water-drive curvature.
    Uses canonical Hall-Yarborough Z-factor from PVTEngine.
    """
    verify_read_only_boundary()
    return GasReservoirEngine.calculate_pz_material_balance(
        history=payload.history,
        temperature_f=payload.temperature_f,
        gas_gravity=payload.gas_gravity,
        abandonment_pressure_psia=payload.abandonment_pressure_psia,
        reservoir_name=payload.reservoir_name
    )


@router.post("/gas/deliverability", response_model=EngineeringResult)
async def calculate_gas_deliverability(payload: GasDeliverabilityRequest):
    """
    Calculates gas deliverability IPR using Rawlins & Schellhardt Backpressure Equation.
    Also computes Absolute Open Flow (AOF) potential at Pwf = 0.
    """
    verify_read_only_boundary()
    return GasReservoirEngine.calculate_gas_deliverability_ipr(
        reservoir_pressure_pr_psia=payload.reservoir_pressure_pr_psia,
        flowing_pressure_pwf_psia=payload.flowing_pressure_pwf_psia,
        c_coefficient=payload.c_coefficient,
        n_exponent=payload.n_exponent,
        well_code=payload.well_code
    )


@router.post("/gas/pseudopressure", response_model=EngineeringResult)
async def calculate_gas_pseudopressure(payload: GasPseudopressureRequest):
    """
    Computes real gas pseudo-pressure m(p) integral: 2 * Integral [ p / (mu_g * z) ] dp
    using canonical PVTEngine (Hall-Yarborough Z-factor and Lee et al. gas viscosity).
    """
    verify_read_only_boundary()
    return GasReservoirEngine.calculate_real_gas_pseudopressure(
        pressure_psia=payload.pressure_psia,
        temperature_f=payload.temperature_f,
        gas_gravity=payload.gas_gravity,
        p_base_psia=payload.p_base_psia,
        num_intervals=payload.num_intervals
    )


@router.post("/gas/nondarcy-turbulence", response_model=EngineeringResult)
async def calculate_gas_turbulence(payload: GasTurbulenceRequest):
    """
    Calculates non-Darcy turbulence drawdown partition using Forchheimer formulation.
    """
    verify_read_only_boundary()
    return GasReservoirEngine.calculate_nondarcy_turbulence_factor(
        reservoir_pressure_pr_psia=payload.reservoir_pressure_pr_psia,
        flowing_pressure_pwf_psia=payload.flowing_pressure_pwf_psia,
        gas_rate_qg_mscfd=payload.gas_rate_qg_mscfd,
        laminar_coefficient_a=payload.laminar_coefficient_a,
        turbulent_coefficient_b=payload.turbulent_coefficient_b,
        well_code=payload.well_code
    )


@router.post("/orchestration/well-diagnostic")
async def orchestrate_well_diagnostic(payload: WellDiagnosticOrchestrationRequest):
    """
    Multi-discipline orchestrator for well performance diagnostic:
    inflow IPR/PI, Chan WOR diagnostic, Water Cut calibration, and choke allocation.
    """
    verify_read_only_boundary()
    return ReservoirEngineeringOrchestrator.orchestrate_well_performance_diagnostic(
        well_code=payload.well_code,
        reservoir_pressure_psia=payload.reservoir_pressure_psia,
        flowing_pressure_pwf_psia=payload.flowing_pressure_pwf_psia,
        test_liquid_rate_stbd=payload.test_liquid_rate_stbd,
        bubble_point_psia=payload.bubble_point_psia,
        chan_data=payload.chan_data,
        wc_calibration_data=payload.wc_calibration_data,
        allocation_data=payload.allocation_data
    )


@router.post("/orchestration/depletion-audit")
async def orchestrate_depletion_audit(payload: ReservoirDepletionAuditRequest):
    """
    Multi-discipline orchestrator for reservoir depletion:
    Static Volumetric Reserves vs Dynamic Material Balance (Havlena-Odeh) vs Aquifer vs VRR.
    Triggers engineering audit alert if deviation > 15%.
    """
    verify_read_only_boundary()
    return ReservoirEngineeringOrchestrator.orchestrate_reservoir_depletion_audit(
        reservoir_name=payload.reservoir_name,
        volumetric_params=payload.volumetric_params,
        mbe_history=payload.mbe_history,
        aquifer_params=payload.aquifer_params,
        vrr_history=payload.vrr_history
    )


@router.post("/reconciliation/virtual-separator", response_model=EngineeringResult)
async def reconcile_virtual_separator(payload: VirtualSeparatorReconciliationRequest):
    """
    Reconciles real-time Virtual Separator estimates against Certified Reference Measurements.
    Derives calibration factor and triggers alert when deviation exceeds tolerance.
    """
    verify_read_only_boundary()
    return VirtualSeparatorReconciliationService.reconcile_virtual_vs_reference(
        entity_code=payload.entity_code,
        virtual_oil_rate_stbd=payload.virtual_oil_rate_stbd,
        virtual_water_cut_pct=payload.virtual_water_cut_pct,
        reference_oil_rate_stbd=payload.reference_oil_rate_stbd,
        reference_water_cut_pct=payload.reference_water_cut_pct,
        tolerance_pct=payload.tolerance_pct,
        virtual_gas_rate_mscfd=payload.virtual_gas_rate_mscfd,
        reference_gas_rate_mscfd=payload.reference_gas_rate_mscfd
    )


@router.get("/field/opcua/tags")
async def read_opcua_field_tags():
    """
    Reads field sensor tags from read-only OPC UA client.
    Technical safety barrier strictly blocks write commands.
    """
    verify_read_only_boundary()
    client = ReadOnlyOPCUAClient(simulation_mode=True)
    client.connect()
    try:
        return client.read_all_tags()
    finally:
        client.disconnect()


@router.post("/field/edge/ingest")
async def ingest_edge_telemetry(payload: EdgeTelemetryIngestRequest):
    """
    Validates and ingests read-only wellhead telemetry from edge gateways.
    Blocks any reverse control commands.
    """
    verify_read_only_boundary()
    connector = EdgeConnector()
    telemetry, quality = connector.validate_and_parse_telemetry(
        raw_telemetry=payload.raw_telemetry,
        signature_hash=payload.signature_hash
    )
    return {
        "status": "INGESTED",
        "quality_flag": quality,
        "telemetry": telemetry.model_dump()
    }


@router.get("/reports/daily", response_model=DailyReservoirReport)
async def get_daily_reservoir_report(
    field_name: str = Query("FIELD_ALPHA"),
    report_date: Optional[str] = Query(None)
):
    """
    Retrieves or generates standardized 08:00 Reservoir Engineering Daily Surveillance Report.
    """
    verify_read_only_boundary()
    return DailyReportService.generate_daily_report(
        field_name=field_name,
        report_date=report_date
    )


# ============================================================
# SUPERVISORY OPERATIONAL WRITE & CONTROL MODE ENDPOINTS
# ============================================================

@router.get("/field/mode")
async def get_field_control_mode():
    """Returns current operational field boundary mode (READ_ONLY vs SUPERVISORY_WRITE)."""
    from app.core.security import get_supervisory_control_status
    return get_supervisory_control_status()


@router.post("/field/mode/toggle")
async def toggle_field_control_mode(
    enabled: bool = Query(...),
    operator: str = Query("Chief Operator"),
    reason: str = Query("Authorized engineering intervention")
):
    """
    Toggles between strictly Read-Only Surveillance Mode and Supervisory Operational Write Mode.
    Provides full read and write function with complete audit tracking.
    """
    from app.core.security import set_supervisory_control_mode
    return set_supervisory_control_mode(enabled=enabled, operator=operator, reason=reason)


@router.post("/field/opcua/write")
async def write_opcua_field_tag(
    tag_node_id: str = Query(...),
    value: float = Query(...),
    operator_signature: str = Query("Chief Engineer")
):
    """
    Writes a new setpoint or parameter to the OPC UA field connection.
    Permitted when Supervisory Operational Mode is activated.
    """
    client = ReadOnlyOPCUAClient(simulation_mode=True)
    client.connect()
    try:
        return client.write_tag(tag_node_id=tag_node_id, value=value, operator_signature=operator_signature)
    finally:
        client.disconnect()


