"""
Smart Guardian Reservoir Intelligence Layer - Artificial Lift & ESP / Rod Pump Engines
======================================================================================
Implements:
16. Motor Cooling Engine (ESP Submersible Motor Fluid Velocity >= 1.0 ft/s)
17. Pump-Off Detection Engine (Dynacard / Fluid Level Intake Starvation)
18. Gas Locking Detection Engine (Multiphase Free Gas Fraction & Vapor Lock)
19. VSD Affinity Engine (Centrifugal Pump Affinity Laws for Variable Speed Drive)
20. Pump Performance Engine (Head-Capacity H-Q Curve & Electrical-Hydraulic Efficiency)
"""

import math
from typing import Optional, Dict, Any, List
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.physics_guardrails import PhysicsGuardrails


class MotorCoolingEngine:
    """
    32. Motor Cooling Engine (Artificial Lift ESP).
    Calculates fluid velocity passing the submersible motor: v = q / Area_annulus.
    Industry standard requires velocity >= 1.0 ft/sec for adequate heat dissipation.
    """
    ENGINE_NAME = "Motor Cooling Engine"
    SPE_REFERENCE = "API RP 11S3: Recommended Practice for Electric Submersible Pump Installations"

    @classmethod
    def evaluate_cooling(
        cls,
        liquid_rate_stbd: Optional[float],
        casing_id_inches: Optional[float],
        motor_od_inches: Optional[float],
        motor_current_amps: Optional[float] = None,
        downhole_temp_f: Optional[float] = None
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "liquid_rate_stbd": liquid_rate_stbd,
                "casing_id_inches": casing_id_inches,
                "motor_od_inches": motor_od_inches
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Annular Fluid Velocity Motor Cooling Model",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        # Annular area A = pi/4 * (D_cas^2 - D_mot^2) in sq ft
        if casing_id_inches <= motor_od_inches:
            return EngineeringResult(
                calculation_name=cls.ENGINE_NAME,
                value=None,
                unit="ft/s",
                model="Annular Fluid Velocity Motor Cooling Model",
                status=EngineeringStatus.INVALID_INPUT.value,
                warnings=["Casing ID must be greater than Motor OD to allow fluid flow."]
            )

        area_sq_in = (math.pi / 4.0) * (math.pow(casing_id_inches, 2) - math.pow(motor_od_inches, 2))
        area_sq_ft = area_sq_in / 144.0

        # Flow rate in cu ft / sec: 1 STB = 5.615 cu ft
        q_cuft_sec = (liquid_rate_stbd * 5.615) / 86400.0
        velocity_fps = q_cuft_sec / area_sq_ft if area_sq_ft > 0 else 0.0

        is_adequate = velocity_fps >= 1.0
        thermal_state = "ADEQUATE_COOLING" if is_adequate else "OVERHEATING_RISK_LOW_VELOCITY"

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(velocity_fps, 2),
            unit="ft/s",
            model="Annular Fluid Velocity Motor Cooling Model",
            status=EngineeringStatus.VALID.value,
            evidence={
                "fluid_velocity_fps": round(velocity_fps, 2),
                "minimum_required_fps": 1.0,
                "cooling_state": thermal_state,
                "annular_area_sq_in": round(area_sq_in, 2)
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class PumpOffDetectionEngine:
    """
    33. Pump-Off Detection Engine.
    Detects incomplete pump fillage (fluid pound) in sucker rod pumps or intake cavitation in ESPs.
    """
    ENGINE_NAME = "Pump-Off Detection Engine"
    SPE_REFERENCE = "Gibbs, S.G. (1963) SPE-588: Computer Diagnosis of Sucker-Rod Pumping Systems"

    @classmethod
    def detect_pump_off(
        cls,
        pump_fillage_fraction: Optional[float],
        peak_polished_rod_load_lbs: Optional[float] = None,
        minimum_polished_rod_load_lbs: Optional[float] = None,
        motor_power_kw: Optional[float] = None
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={"pump_fillage_fraction": pump_fillage_fraction},
            calculation_name=cls.ENGINE_NAME,
            model_name="Dynacard Fillage Diagnostic Model",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        fillage = min(1.0, max(0.0, pump_fillage_fraction))
        severity = "NORMAL_FULL_BARREL"
        recommendation = "MAINTAIN_CURRENT_SPEED"

        if fillage < 0.60:
            severity = "SEVERE_PUMP_OFF_FLUID_POUND"
            recommendation = "REDUCE_STROKES_PER_MINUTE_OR_SHUT_IN_TIMER"
        elif fillage < 0.85:
            severity = "MODERATE_UNDER_FILLAGE"
            recommendation = "THROTTLE_CYCLE_TIME"

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(fillage * 100.0, 1),
            unit="%",
            model="Dynacard Fillage Diagnostic Model",
            status=EngineeringStatus.VALID.value,
            evidence={
                "fillage_percentage": round(fillage * 100.0, 1),
                "condition": severity,
                "action_advisory": recommendation
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class GasLockingDetectionEngine:
    """
    34. Gas Locking Detection Engine.
    Evaluates in-situ free gas fraction at pump intake. Free gas > 15-20% causes severe head degradation.
    """
    ENGINE_NAME = "Gas Locking Detection Engine"
    SPE_REFERENCE = "Lea, J.F. & Bearden, J.L. (1982) SPE-9218: Effect of Gaseous Fluids on Centrifugal Pumps"

    @classmethod
    def evaluate_gas_lock_risk(
        cls,
        pump_intake_pressure_psia: Optional[float],
        bubble_point_pressure_psia: Optional[float],
        intake_free_gas_fraction: Optional[float],
        gas_separator_efficiency: Optional[float] = 0.80
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "pump_intake_pressure_psia": pump_intake_pressure_psia,
                "intake_free_gas_fraction": intake_free_gas_fraction
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Multiphase Gas Interference & Vapor Lock Model",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        # Net free gas entering pump stage after downhole rotary gas separator
        sep_eff = gas_separator_efficiency or 0.80
        net_gas_fraction = intake_free_gas_fraction * (1.0 - sep_eff)

        status_text = "NORMAL_LIQUID_DOMINANT"
        if net_gas_fraction > 0.20:
            status_text = "CRITICAL_GAS_LOCK_IMMINENT"
        elif net_gas_fraction > 0.10:
            status_text = "DEGRADED_PUMP_HEAD_GAS_INTERFERENCE"

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(net_gas_fraction * 100.0, 1),
            unit="%",
            model="Multiphase Gas Interference & Vapor Lock Model",
            status=EngineeringStatus.VALID.value,
            evidence={
                "intake_free_gas_fraction_pct": round(intake_free_gas_fraction * 100.0, 1),
                "net_gas_entering_impellers_pct": round(net_gas_fraction * 100.0, 1),
                "lock_risk_state": status_text,
                "pip_vs_pb_differential_psi": (pump_intake_pressure_psia - bubble_point_pressure_psia) if bubble_point_pressure_psia else None
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class VSDAffinityEngine:
    """
    35. VSD Affinity Engine.
    Applies the fundamental Centrifugal Pump Affinity Laws for Variable Speed Drive adjustments:
    q2 = q1 * (N2 / N1)
    H2 = H1 * (N2 / N1)^2
    P2 = P1 * (N2 / N1)^3
    """
    ENGINE_NAME = "VSD Affinity Engine"
    SPE_REFERENCE = "Takacs, G. (2009) Electrical Submersible Pumps Manual, Gulf Publishing"

    @classmethod
    def calculate_frequency_shift(
        cls,
        base_frequency_hz: Optional[float],
        target_frequency_hz: Optional[float],
        current_rate_stbd: Optional[float],
        current_head_ft: Optional[float],
        current_power_kw: Optional[float]
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "base_frequency_hz": base_frequency_hz,
                "target_frequency_hz": target_frequency_hz,
                "current_rate_stbd": current_rate_stbd
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Hydraulic Centrifugal Affinity Laws",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        if base_frequency_hz <= 0 or target_frequency_hz <= 0:
            return EngineeringResult(
                calculation_name=cls.ENGINE_NAME,
                value=None,
                status=EngineeringStatus.OUT_OF_RANGE.value,
                model="Hydraulic Centrifugal Affinity Laws",
                warnings=["Electrical frequency must be strictly positive."]
            )

        ratio = target_frequency_hz / base_frequency_hz
        predicted_rate = current_rate_stbd * ratio
        predicted_head = (current_head_ft * math.pow(ratio, 2)) if current_head_ft is not None else None
        predicted_power = (current_power_kw * math.pow(ratio, 3)) if current_power_kw is not None else None

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(predicted_rate, 2),
            unit="STB/D",
            model="Hydraulic Centrifugal Affinity Laws",
            status=EngineeringStatus.VALID.value,
            evidence={
                "base_hz": base_frequency_hz,
                "target_hz": target_frequency_hz,
                "frequency_ratio": round(ratio, 3),
                "predicted_rate_stbd": round(predicted_rate, 2),
                "predicted_head_ft": round(predicted_head, 1) if predicted_head else None,
                "predicted_power_kw": round(predicted_power, 2) if predicted_power else None
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class PumpPerformanceEngine:
    """
    36. Pump Performance Engine.
    Evaluates pump operating point (operating rate vs head capacity curve), hydraulic power, and efficiency.
    """
    ENGINE_NAME = "Pump Performance Engine"
    SPE_REFERENCE = "API RP 11S2: Recommended Practice for Electric Submersible Pump Testing"

    @classmethod
    def evaluate_performance(
        cls,
        total_dynamic_head_ft: Optional[float],
        liquid_rate_stbd: Optional[float],
        fluid_specific_gravity: Optional[float] = 0.90,
        electric_power_kw: Optional[float] = None
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "total_dynamic_head_ft": total_dynamic_head_ft,
                "liquid_rate_stbd": liquid_rate_stbd
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Hydraulic Horsepower & Efficiency Analysis",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        # Hydraulic Horsepower: HHP = (q_gpm * Head_ft * SG) / 3960
        # 1 STB/D = 42 gal / 1440 min = 0.029167 gpm
        q_gpm = liquid_rate_stbd * (42.0 / 1440.0)
        sg = fluid_specific_gravity or 0.90
        hhp = (q_gpm * total_dynamic_head_ft * sg) / 3960.0
        hydraulic_power_kw = hhp * 0.7457

        overall_efficiency_pct = None
        if electric_power_kw and electric_power_kw > 0:
            overall_efficiency_pct = min(100.0, (hydraulic_power_kw / electric_power_kw) * 100.0)

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(hhp, 2),
            unit="HHP",
            model="Hydraulic Horsepower & Efficiency Analysis",
            status=EngineeringStatus.VALID.value,
            evidence={
                "hydraulic_horsepower_hhp": round(hhp, 2),
                "hydraulic_power_kw": round(hydraulic_power_kw, 2),
                "overall_system_efficiency_pct": round(overall_efficiency_pct, 1) if overall_efficiency_pct else None,
                "operating_rate_gpm": round(q_gpm, 2)
            },
            correlation_reference=cls.SPE_REFERENCE
        )
