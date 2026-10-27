"""
Smart Guardian Reservoir Intelligence Layer - Virtual Separator PVT Foundation (Step 2A)
Implements:
1. Separator Condition Interface (Stage 1, Stage 2, Stock-tank with provenance: MEASURED vs CONFIGURED)
2. PVT Correction Interface (with strict CORRELATION_SPECIFICATION_REQUIRED barrier)
3. Flash / Separator Calculation Interface (preserves reference basis, strictly forbids arbitrary Rs summing)
4. Dual Water Cut Interface (WC_Live vs WC_Lab independent tracking with calibration metadata)
5. Configurable Economic Parameters (Test Separator rental benchmark, never hard-coded)

Note: Full flash thermodynamics and separator fluid simulations are deferred to Step 2B.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class SeparatorStageCondition(BaseModel):
    """
    Structured condition for a single separation stage.
    Distinguishes MEASURED from CONFIGURED defaults.
    """
    stage_name: str  # e.g., "STAGE_1_HP", "STAGE_2_LP", "STOCK_TANK"
    pressure_psia: float
    temperature_f: float
    source: str = "CONFIGURED"  # MEASURED, CONFIGURED, MANUAL, CALCULATED
    is_measured: bool = False
    notes: Optional[str] = None


class SeparatorConditionsSuite(BaseModel):
    """
    Multi-stage separator operating conditions interface.
    """
    stage_1: SeparatorStageCondition
    stage_2: Optional[SeparatorStageCondition] = None
    stock_tank: SeparatorStageCondition

    model_config = ConfigDict(from_attributes=True)


class DualWaterCutRecord(BaseModel):
    """
    Dual Water Cut Observation Interface.
    Maintains strict separation between real-time field sensors (WC_Live)
    and physical laboratory bottle/centrifuge measurements (WC_Lab).
    """
    well_code: str
    timestamp: datetime
    wc_live_percent: Optional[float] = None
    wc_live_source: Optional[str] = None  # e.g. "Roxar", "Agar", "Coriolis"
    wc_lab_percent: Optional[float] = None
    wc_lab_source: Optional[str] = None   # e.g. "2mL Centrifuge", "Karl Fischer"
    wc_selected_percent: Optional[float] = None
    calibration_status: str = "NOT_CONFIGURED"  # NOT_CONFIGURED, APPLIED, PENDING_VERIFICATION
    calibration_method: Optional[str] = None
    calibration_factor: Optional[float] = None
    calibration_bias: Optional[float] = None
    calibration_timestamp: Optional[datetime] = None
    calibration_source: Optional[str] = None


class ConfigurableEconomicContext(BaseModel):
    """
    Configurable Economic Parameters for Virtual Separator Surveillance.
    Replaces hard-coded rental fees ($15,000/day, $25,000/day) with traceable business configurations.
    """
    test_separator_daily_rental_usd: float = 15000.0
    currency: str = "USD"
    source: str = "OPERATIONAL_BUDGET_ESTIMATE"
    effective_date: str = "2026-01-01"
    is_assumption: bool = True
    notes: str = "Configurable field rental baseline; not a hard-coded engineering law."


class VirtualSeparatorPVTFoundation:
    """
    Canonical Virtual Separator Foundation Interface.
    """

    @staticmethod
    def get_default_separator_conditions() -> SeparatorConditionsSuite:
        """
        Provides explicit, traceable default separator operating conditions.
        Clearly tags values as CONFIGURED, never hidden or represented as measured field data.
        """
        return SeparatorConditionsSuite(
            stage_1=SeparatorStageCondition(
                stage_name="STAGE_1_HP",
                pressure_psia=100.0,
                temperature_f=80.0,
                source="CONFIGURED",
                is_measured=False,
                notes="Standard 100 psia baseline for Standing/Vasquez-Beggs separator calibration"
            ),
            stage_2=SeparatorStageCondition(
                stage_name="STAGE_2_LP",
                pressure_psia=35.0,
                temperature_f=75.0,
                source="CONFIGURED",
                is_measured=False,
                notes="Intermediate stage baseline"
            ),
            stock_tank=SeparatorStageCondition(
                stage_name="STOCK_TANK",
                pressure_psia=14.7,
                temperature_f=60.0,
                source="CONFIGURED",
                is_measured=False,
                notes="Standard stock tank condition (14.7 psia, 60 F)"
            )
        )

    @classmethod
    def evaluate_separator_condition_correction(
        cls,
        base_bo: Optional[float] = None,
        sep_conditions: Optional[Any] = None,
        correlation_name: Optional[str] = None,
        raw_bo: Optional[float] = None,
        stage_conditions: Optional[Any] = None
    ) -> EngineeringResult:
        """
        Evaluates separator-condition corrections to Bo.
        MANDATORY RULE ENFORCEMENT:
        If a specific empirical correction equation (e.g. Al-Marhoun separator correction)
        is not explicitly defined with validated parameters, it strictly returns:
        CORRELATION_SPECIFICATION_REQUIRED.
        It NEVER invents a guessed polynomial correction.
        """
        effective_bo = base_bo if base_bo is not None else (raw_bo if raw_bo is not None else 1.25)
        cond = sep_conditions if sep_conditions is not None else stage_conditions

        if isinstance(cond, SeparatorStageCondition):
            suite = SeparatorConditionsSuite(
                stage_1=cond,
                stock_tank=SeparatorStageCondition(
                    stage_name="STOCK_TANK",
                    pressure_psia=14.7,
                    temperature_f=60.0,
                    source="CONFIGURED",
                    is_measured=False
                )
            )
        elif isinstance(cond, SeparatorConditionsSuite):
            suite = cond
        else:
            suite = cls.get_default_separator_conditions()

        inputs = {
            "base_bo": effective_bo,
            "sep_stage_1_psia": suite.stage_1.pressure_psia,
            "sep_stage_1_f": suite.stage_1.temperature_f,
            "correlation_requested": correlation_name
        }

        if correlation_name is None or correlation_name.strip().upper() == "UNSPECIFIED":
            return EngineeringResult(
                model="Separator Bo Correction Interface",
                status=EngineeringStatus.CORRELATION_SPECIFICATION_REQUIRED.value,
                inputs=inputs,
                assumptions=["Separator condition correction requires explicit published formulation"],
                limitations=["No guessed correlation permitted; requires explicit correlation name and coefficients"],
                evidence={
                    "rule": "RULE 12: DO NOT IMPLEMENT A GUESSED CORRECTION",
                    "status_code": "CORRELATION_SPECIFICATION_REQUIRED",
                    "message": "Specific Al-Marhoun or Glaso separator correction formulation must be explicitly specified before execution."
                }
            )

        # If a correlation is requested but not in validated catalog:
        return EngineeringResult(
            model="Separator Bo Correction Interface",
            status=EngineeringStatus.CORRELATION_SPECIFICATION_REQUIRED.value,
            inputs=inputs,
            evidence={
                "error": f"Correlation '{correlation_name}' is not yet calibrated with reference fluid coefficients. Sub-component stopped safely."
            }
        )

    apply_separator_pvt_correction = evaluate_separator_condition_correction

    @staticmethod
    def evaluate_flash_calculation_interface(
        pvt_inputs: Dict[str, Any],
        sep_conditions: SeparatorConditionsSuite,
        reference_basis: str = "DIFFERENTIAL_LIBERATION"
    ) -> EngineeringResult:
        """
        Flash / Separator Calculation Interface.
        Enforces Rule 13: Strictly forbids arbitrary summation of stage Rs values
        (Rs_total != Rs_sep1 + Rs_sep2 + Rs_stock) without a thermodynamically validated flash formulation.
        Full flash simulation belongs to Step 2B.
        """
        inputs = {
            "pvt_inputs": pvt_inputs,
            "reference_basis": reference_basis,
            "sep_stages_count": 2 if sep_conditions.stage_2 else 1
        }

        assumptions = [
            f"Reference basis: {reference_basis}",
            "Arbitrary additive stage Rs summation (Rs1 + Rs2 + Rs_stock) is strictly prohibited.",
            "Thermodynamic phase flash calculations are deferred to Step 2B (Virtual Separator)."
        ]

        return EngineeringResult(
            model="Virtual Separator Flash Calculation Interface",
            status=EngineeringStatus.VALID.value,
            inputs=inputs,
            assumptions=assumptions,
            limitations=["Phase 2A provides canonical interface contracts only; full EOS flash is deferred to Phase 2B."],
            evidence={
                "interface_ready": True,
                "stage_1_psia": sep_conditions.stage_1.pressure_psia,
                "stock_tank_psia": sep_conditions.stock_tank.pressure_psia,
                "step_2b_deferred": ["Peng-Robinson EOS flash", "Component split factors", "Virtual multi-phase metering"]
            }
        )

    @staticmethod
    def reconcile_dual_water_cut(
        wc_live_percent: Optional[float],
        wc_lab_percent: Optional[float],
        well_code: str,
        timestamp: datetime,
        calibration_factor: Optional[float] = None
    ) -> DualWaterCutRecord:
        """
        Reconciles Dual Water Cut inputs without overwriting either source.
        Preserves live sensor telemetry and laboratory centrifuge observations independently.
        """
        # Determine selection and calibration status
        cal_status = "NOT_CONFIGURED"
        selected_wc = None

        if calibration_factor is not None and wc_live_percent is not None:
            # If validated calibration factor is configured:
            selected_wc = wc_live_percent * calibration_factor
            cal_status = "APPLIED"
        elif wc_live_percent is not None:
            selected_wc = wc_live_percent
            cal_status = "NOT_CONFIGURED"
        elif wc_lab_percent is not None:
            selected_wc = wc_lab_percent
            cal_status = "LAB_ONLY"

        return DualWaterCutRecord(
            well_code=well_code,
            timestamp=timestamp,
            wc_live_percent=wc_live_percent,
            wc_live_source="FIELD_MULTIPHASE_METER",
            wc_lab_percent=wc_lab_percent,
            wc_lab_source="LAB_CENTRIFUGE",
            wc_selected_percent=selected_wc,
            calibration_status=cal_status,
            calibration_factor=calibration_factor
        )
