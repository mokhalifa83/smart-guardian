from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.services.reservoir.contracts import EngineeringResult
from app.services.reservoir.chan_engine import ProductionTimePoint


class PVTCalculationRequest(BaseModel):
    pressure_psia: float = Field(..., gt=0, description="Reservoir or separator absolute pressure in psia")
    temperature_f: float = Field(..., description="Temperature in Fahrenheit")
    api_gravity: float = Field(default=35.0, ge=10.0, le=65.0, description="Oil stock-tank API gravity")
    gas_gravity: float = Field(default=0.75, ge=0.55, le=1.75, description="Gas specific gravity (air=1.0)")
    rs: Optional[float] = Field(default=None, ge=0, description="Solution GOR (scf/stb)")
    bubble_point_psia: Optional[float] = Field(default=None, gt=0)
    correlation: str = Field(default="Standing", description="'Standing' or 'Vasquez-Beggs'")


class SeparatorFoundationRequest(BaseModel):
    base_bo: float = Field(default=1.25, gt=0)
    stage_1_pressure_psia: float = Field(default=100.0, gt=0)
    stage_1_temperature_f: float = Field(default=80.0)
    correlation_name: Optional[str] = "UNSPECIFIED"


class ChanDiagnosticRequest(BaseModel):
    well_code: str = Field(default="WELL-001")
    points: Optional[List[ProductionTimePoint]] = None


class DarcyCalculationRequest(BaseModel):
    permeability_md: float = Field(..., gt=0)
    thickness_ft: float = Field(..., gt=0)
    reservoir_pressure_psia: float = Field(..., gt=0)
    flowing_bhp_psia: float = Field(..., ge=0)
    viscosity_cp: float = Field(..., gt=0)
    bo_rb_stb: float = Field(default=1.25, gt=0)
    drainage_radius_ft: float = Field(default=1000.0, gt=0)
    wellbore_radius_ft: float = Field(default=0.354, gt=0)
    skin: float = Field(default=0.0)


class ProductivityIndexRequest(BaseModel):
    flow_rate_stbd: float = Field(..., ge=0)
    reservoir_pressure_psia: float = Field(..., gt=0)
    flowing_bhp_psia: float = Field(..., ge=0)


class VogelCalculationRequest(BaseModel):
    reservoir_pressure_psia: float = Field(..., gt=0)
    test_rate_stbd: Optional[float] = Field(default=None, gt=0)
    test_flowing_bhp_psia: Optional[float] = Field(default=None, ge=0)
    qmax_stbd: Optional[float] = Field(default=None, gt=0)
    flowing_bhp_psia: Optional[float] = Field(default=None, ge=0)


class MaterialBalanceRequest(BaseModel):
    initial_pressure_psia: float = Field(..., gt=0)
    current_pressure_psia: float = Field(..., gt=0)
    initial_bo: float = Field(..., gt=0)
    current_bo: float = Field(..., gt=0)
    initial_bg: float = Field(..., gt=0)
    current_bg: float = Field(..., gt=0)
    initial_rs: float = Field(..., ge=0)
    current_rs: float = Field(..., ge=0)
    initial_swi: float = Field(default=0.20, ge=0.0, le=1.0)
    np_stb: float = Field(..., ge=0)
    wp_stb: float = Field(default=0.0, ge=0)
    gp_mscf: Optional[float] = Field(default=None, ge=0)
    rp_scf_stb: Optional[float] = Field(default=None, ge=0)
    bw_rb_stb: float = Field(default=1.02, gt=0)
    m_gas_cap_ratio: float = Field(default=0.0, ge=0.0)
    cf_pore_compressibility: float = Field(default=3.5e-6, gt=0)
    cw_water_compressibility: float = Field(default=3.0e-6, gt=0)
    we_water_influx_rb: float = Field(default=0.0, ge=0)
    n_stb_estimate: Optional[float] = Field(default=None, gt=0)


class VRRCalculationRequest(BaseModel):
    produced_oil_stb: float = Field(..., ge=0)
    produced_water_bbl: float = Field(..., ge=0)
    produced_gas_scf: Optional[float] = Field(default=None, ge=0)
    injected_water_bbl: float = Field(default=0.0, ge=0)
    injected_gas_scf: float = Field(default=0.0, ge=0)
    bo_rb_stb: float = Field(default=1.25, gt=0)
    bw_rb_stb: float = Field(default=1.02, gt=0)
    bg_rb_scf: float = Field(default=0.00095, gt=0)
    rs_scf_stb: float = Field(default=500.0, ge=0)
    time_window_days: Optional[float] = Field(default=30.0, gt=0)
    is_instantaneous_rate: bool = False


# ============================================================
# STEP 2B SCHEMAS: SURVEILLANCE, DYNAMICS & VIRTUAL SEPARATOR
# ============================================================

from app.services.reservoir.decline_engine import ProductionRatePoint
from app.services.reservoir.well_test_engine import WellTestGaugePoint
from app.services.reservoir.aquifer_engine import AquiferPressureStep
from app.services.reservoir.fractional_flow_engine import CoreRelPermPoint
from app.services.reservoir.waterflood_engine import WaterfloodObservationPoint
from app.services.reservoir.wc_calibration import LabWaterCutSample, LiveWaterCutObservation
from app.services.reservoir.well_allocation import ChokeAllocationInputs
from app.models.virtual_separator import SeparatorStageCondition


class DeclineAnalysisRequest(BaseModel):
    well_code: Optional[str] = "WELL-001"
    model_type: str = Field(default="EXPONENTIAL", description="EXPONENTIAL, HARMONIC, or HYPERBOLIC")
    history: List[ProductionRatePoint] = Field(..., min_length=3)
    forecast_horizon_days: Optional[float] = Field(default=365.0, gt=0)
    economic_limit_rate_stbd: Optional[float] = Field(default=None, gt=0)


class DrawdownTestRequest(BaseModel):
    well_code: Optional[str] = "WELL-001"
    initial_pressure_psia: float = Field(..., gt=0)
    flow_rate_stbd: float = Field(..., gt=0)
    formation_thickness_ft: float = Field(..., gt=0)
    porosity_fraction: float = Field(..., gt=0, le=1.0)
    total_compressibility_psi: float = Field(..., gt=0)
    viscosity_cp: float = Field(..., gt=0)
    bo_rb_stb: float = Field(default=1.20, gt=0)
    wellbore_radius_ft: float = Field(default=0.354, gt=0)
    gauge_points: List[WellTestGaugePoint] = Field(..., min_length=3)


class HornerBuildupRequest(BaseModel):
    well_code: Optional[str] = "WELL-001"
    producing_time_tp_hours: float = Field(..., gt=0)
    flow_rate_stbd: float = Field(..., gt=0)
    formation_thickness_ft: float = Field(..., gt=0)
    porosity_fraction: float = Field(..., gt=0, le=1.0)
    total_compressibility_psi: float = Field(..., gt=0)
    viscosity_cp: float = Field(..., gt=0)
    bo_rb_stb: float = Field(default=1.20, gt=0)
    wellbore_radius_ft: float = Field(default=0.354, gt=0)
    flowing_pwf_at_shutin_psia: Optional[float] = Field(default=None, gt=0)
    gauge_points: List[WellTestGaugePoint] = Field(..., min_length=3)


class AquiferCalculationRequest(BaseModel):
    model_type: str = Field(default="FETKOVICH", description="FETKOVICH, SCHILTHUIS, or VAN_EVERDINGEN_HURST")
    initial_pressure_psia: float = Field(..., gt=0)
    pressure_history: List[AquiferPressureStep] = Field(..., min_length=2)
    permeability_md: float = Field(default=100.0, gt=0)
    formation_thickness_ft: float = Field(default=50.0, gt=0)
    porosity_fraction: float = Field(default=0.20, gt=0, le=1.0)
    total_compressibility_psi: float = Field(default=7.0e-6, gt=0)
    water_viscosity_cp: float = Field(default=0.50, gt=0)
    reservoir_radius_ft: float = Field(default=2000.0, gt=0)
    aquifer_radius_ft: float = Field(default=10000.0, gt=0)
    encroachment_angle_deg: float = Field(default=360.0, gt=0, le=360.0)
    water_influx_constant_c: Optional[float] = Field(default=None, gt=0)


class FractionalFlowRequest(BaseModel):
    sw_connate: float = Field(default=0.20, ge=0.0, lt=1.0)
    so_residual: float = Field(default=0.25, ge=0.0, lt=1.0)
    krw_endpoint: float = Field(default=0.30, gt=0)
    kro_endpoint: float = Field(default=0.85, gt=0)
    nw_exponent: float = Field(default=2.0, gt=0)
    no_exponent: float = Field(default=2.5, gt=0)
    water_viscosity_cp: float = Field(default=0.50, gt=0)
    oil_viscosity_cp: float = Field(default=2.0, gt=0)
    core_points: Optional[List[CoreRelPermPoint]] = None


class BuckleyLeverettRequest(BaseModel):
    injection_rate_bpd: float = Field(default=1000.0, gt=0)
    cross_sectional_area_ft2: float = Field(default=20000.0, gt=0)
    length_between_wells_ft: float = Field(default=1500.0, gt=0)
    porosity_fraction: float = Field(default=0.20, gt=0, le=1.0)
    initial_water_saturation: float = Field(default=0.20, ge=0.0, lt=1.0)
    so_residual: float = Field(default=0.25, ge=0.0, lt=1.0)
    water_viscosity_cp: float = Field(default=0.50, gt=0)
    oil_viscosity_cp: float = Field(default=2.0, gt=0)


class WaterfloodSurveillanceRequest(BaseModel):
    injector_well_code: Optional[str] = "INJ-001"
    pattern_name: Optional[str] = "PATTERN-5SPOT-A"
    history: List[WaterfloodObservationPoint] = Field(..., min_length=2)
    bo_rb_stb: float = Field(default=1.25, gt=0)
    bw_rb_stb: float = Field(default=1.02, gt=0)
    bg_rb_scf: float = Field(default=0.00095, gt=0)
    rs_scf_stb: float = Field(default=500.0, ge=0)


class SweepEfficiencyRequest(BaseModel):
    sw_connate: float = Field(default=0.20, ge=0.0, lt=1.0)
    so_residual: float = Field(default=0.25, ge=0.0, lt=1.0)
    areal_sweep_ea: float = Field(default=0.75, ge=0.0, le=1.0)
    vertical_sweep_ei: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    permeability_layers_md: Optional[List[float]] = None
    v_dp_coefficient: Optional[float] = Field(default=None, ge=0.0, lt=1.0)
    mobility_ratio_m: float = Field(default=1.0, gt=0)


class WaterCutCalibrationRequest(BaseModel):
    lab_sample: LabWaterCutSample
    live_sample_reading: LiveWaterCutObservation
    current_live_reading: Optional[LiveWaterCutObservation] = None


class WellAllocationRequest(BaseModel):
    choke_inputs: ChokeAllocationInputs


class VirtualSeparatorTrainRequest(BaseModel):
    total_liquid_rate_stbd: float = Field(..., gt=0)
    water_cut_fraction: float = Field(..., ge=0.0, le=1.0)
    producing_gor_scf_stb: float = Field(..., ge=0)
    reservoir_pressure_psia: float = Field(..., gt=0)
    reservoir_temperature_f: float = Field(..., gt=0)
    gas_gravity: float = Field(default=0.75, gt=0)
    oil_api: float = Field(default=35.0, gt=0)
    stage_conditions: Optional[List[SeparatorStageCondition]] = None


# ============================================================
# STEP 2C SCHEMAS: RESERVES, GAS, ORCHESTRATION, FIELD & REPORTING
# ============================================================

class ReservesCalculationRequest(BaseModel):
    area_acres: float = Field(..., gt=0, description="Reservoir drainage area in acres")
    net_pay_ft: float = Field(..., gt=0, description="Average net pay thickness in feet")
    porosity: float = Field(..., gt=0.0, lt=1.0, description="Average effective porosity fraction")
    initial_water_sat: float = Field(..., ge=0.0, lt=1.0, description="Initial connate water saturation fraction")
    initial_oil_fvf_boi: float = Field(..., gt=0.0, description="Initial oil formation volume factor Boi (rb/STB)")
    recovery_factor: Optional[float] = Field(default=None, gt=0.0, le=1.0, description="Approved recovery factor fraction")
    cumulative_oil_np_stb: float = Field(default=0.0, ge=0.0, description="Cumulative oil production to date (STB)")
    economic_limit_bopd: Optional[float] = Field(default=None, ge=0.0, description="Economic rate limit (BOPD)")
    well_or_field_id: str = Field(default="FIELD_BLOCK_A")


class GasGIIPRequest(BaseModel):
    area_acres: float = Field(..., gt=0)
    net_pay_ft: float = Field(..., gt=0)
    porosity: float = Field(..., gt=0.0, lt=1.0)
    initial_water_sat: float = Field(..., ge=0.0, lt=1.0)
    initial_gas_fvf_bgi: float = Field(..., gt=0.0)
    bgi_unit: str = Field(default="cuft_scf", description="'cuft_scf' or 'rb_scf'")
    well_or_field_id: str = Field(default="GAS_FIELD_ALPHA")


class GasPzRequest(BaseModel):
    history: List[Dict[str, float]] = Field(..., min_length=2, description="List of dicts with 'pressure_psia' and 'cumulative_gas_gp_mscf'")
    temperature_f: float = Field(..., description="Reservoir temperature in deg F")
    gas_gravity: float = Field(default=0.70, gt=0.0, description="Gas specific gravity")
    abandonment_pressure_psia: float = Field(default=500.0, gt=0.0)
    reservoir_name: str = Field(default="ALPHA_SAND")


class GasDeliverabilityRequest(BaseModel):
    reservoir_pressure_pr_psia: float = Field(..., gt=0.0)
    flowing_pressure_pwf_psia: float = Field(..., ge=0.0)
    c_coefficient: float = Field(..., gt=0.0, description="Flow coefficient C (Mscf/d / psi^2n)")
    n_exponent: float = Field(default=0.85, ge=0.5, le=1.0, description="Backpressure exponent n (0.5 to 1.0)")
    well_code: str = Field(default="GAS_PROD_01")


class GasPseudopressureRequest(BaseModel):
    pressure_psia: float = Field(..., gt=0.0)
    temperature_f: float = Field(...)
    gas_gravity: float = Field(default=0.70, gt=0.0)
    p_base_psia: float = Field(default=14.7, ge=0.0)
    num_intervals: int = Field(default=50, ge=10, le=500)


class GasTurbulenceRequest(BaseModel):
    reservoir_pressure_pr_psia: float = Field(..., gt=0.0)
    flowing_pressure_pwf_psia: float = Field(..., ge=0.0)
    gas_rate_qg_mscfd: float = Field(..., gt=0.0)
    laminar_coefficient_a: float = Field(..., gt=0.0)
    turbulent_coefficient_b: float = Field(..., ge=0.0)
    well_code: str = Field(default="GAS_PROD_01")


class WellDiagnosticOrchestrationRequest(BaseModel):
    well_code: str = Field(default="WELL-101")
    reservoir_pressure_psia: float = Field(..., gt=0.0)
    flowing_pressure_pwf_psia: float = Field(..., ge=0.0)
    test_liquid_rate_stbd: float = Field(..., gt=0.0)
    bubble_point_psia: float = Field(..., gt=0.0)
    chan_data: Optional[Dict[str, Any]] = None
    wc_calibration_data: Optional[Dict[str, Any]] = None
    allocation_data: Optional[Dict[str, Any]] = None


class ReservoirDepletionAuditRequest(BaseModel):
    reservoir_name: str = Field(default="RESERVOIR_MAIN_PAY")
    volumetric_params: Dict[str, Any] = Field(...)
    mbe_history: Optional[List[Dict[str, Any]]] = None
    aquifer_params: Optional[Dict[str, Any]] = None
    vrr_history: Optional[List[Dict[str, Any]]] = None


class VirtualSeparatorReconciliationRequest(BaseModel):
    entity_code: str = Field(default="WELL-101")
    virtual_oil_rate_stbd: float = Field(..., ge=0.0)
    virtual_water_cut_pct: float = Field(..., ge=0.0, le=100.0)
    reference_oil_rate_stbd: float = Field(..., gt=0.0)
    reference_water_cut_pct: float = Field(..., ge=0.0, le=100.0)
    tolerance_pct: float = Field(default=10.0, gt=0.0)
    virtual_gas_rate_mscfd: Optional[float] = None
    reference_gas_rate_mscfd: Optional[float] = None


class EdgeTelemetryIngestRequest(BaseModel):
    raw_telemetry: Dict[str, Any] = Field(...)
    signature_hash: Optional[str] = None


