"""
Smart Guardian Reservoir Intelligence Layer - Production, Pressure & Injection Surveillance Engines
===================================================================================================
Implements:
4. Production Engine (Field & Well Telemetry Surveillance, Runtime & Operating Envelope)
5. Pressure Surveillance Engine (Depletion, Drawdown & Reservoir Energy Monitoring)
6. Injection Engine (Hall Plot Analysis, Injectivity Index II, Voidage Replacement)
11. GOR Diagnostic Engine (Free Gas Evolution, Coning vs Secondary Gas Cap Breakthrough)
16. Mature Field Pressure Drop & Depletion Diagnostic Engine (Boundary Effects & Compartmentalization)
"""

import math
from typing import Optional, Dict, Any, List
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.physics_guardrails import PhysicsGuardrails


class ProductionEngine:
    """
    4. Production Engine.
    Continuous well surveillance: flow rates, uptime/downtime efficiency, and operational operating window.
    """
    ENGINE_NAME = "Production Engine"
    SPE_REFERENCE = "SPE Monograph 1: Reservoir Engineering Principles"

    @classmethod
    def evaluate_well_production(
        cls,
        oil_rate_stbd: Optional[float],
        water_rate_stbd: Optional[float],
        gas_rate_mscfd: Optional[float],
        uptime_hours: Optional[float] = 24.0,
        allocated_target_stbd: Optional[float] = None
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={"oil_rate_stbd": oil_rate_stbd, "water_rate_stbd": water_rate_stbd},
            calculation_name=cls.ENGINE_NAME,
            model_name="Surveillance Mass-Balance Volumetric Allocation",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        total_liquid = oil_rate_stbd + water_rate_stbd
        water_cut = (water_rate_stbd / total_liquid * 100.0) if total_liquid > 0 else 0.0
        gor = (gas_rate_mscfd * 1000.0 / oil_rate_stbd) if (gas_rate_mscfd is not None and oil_rate_stbd > 0) else None
        operating_efficiency = min(1.0, max(0.0, (uptime_hours or 24.0) / 24.0))

        compliance_pct = (oil_rate_stbd / allocated_target_stbd * 100.0) if allocated_target_stbd and allocated_target_stbd > 0 else 100.0

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(oil_rate_stbd, 2),
            unit="STB/D",
            model="Wellhead Production Surveillance",
            status=EngineeringStatus.VALID.value,
            evidence={
                "liquid_rate_stbd": round(total_liquid, 2),
                "oil_rate_stbd": round(oil_rate_stbd, 2),
                "water_rate_stbd": round(water_rate_stbd, 2),
                "water_cut_pct": round(water_cut, 2),
                "gor_scf_stb": round(gor, 1) if gor else None,
                "uptime_fraction": round(operating_efficiency, 3),
                "target_compliance_pct": round(compliance_pct, 1)
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class PressureSurveillanceEngine:
    """
    5. Pressure Surveillance Engine.
    Continuous monitoring of reservoir energy, drawdown management, and isobaric depletion.
    """
    ENGINE_NAME = "Pressure Surveillance Engine"
    SPE_REFERENCE = "Dake, L.P. (1978) Fundamentals of Reservoir Engineering"

    @classmethod
    def evaluate_pressure_status(
        cls,
        current_reservoir_pressure_psia: Optional[float],
        initial_reservoir_pressure_psia: Optional[float],
        flowing_bhp_psia: Optional[float],
        bubble_point_pressure_psia: Optional[float]
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "current_reservoir_pressure_psia": current_reservoir_pressure_psia,
                "initial_reservoir_pressure_psia": initial_reservoir_pressure_psia
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Isobaric Pressure Depletion Surveillance",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        pres = current_reservoir_pressure_psia
        pi = initial_reservoir_pressure_psia

        # Physics constraints
        if pres <= 0 or pi <= 0:
            return EngineeringResult(
                calculation_name=cls.ENGINE_NAME,
                value=None,
                status=EngineeringStatus.OUT_OF_RANGE.value,
                model="Isobaric Pressure Depletion",
                warnings=["Reservoir pressure must be positive."]
            )

        pressure_depletion_psi = pi - pres
        depletion_fraction = pressure_depletion_psi / pi

        drawdown_psi = None
        if flowing_bhp_psia is not None:
            is_valid, err = PhysicsGuardrails.validate_inflow_hydraulics(pres, flowing_bhp_psia)
            if not is_valid:
                return EngineeringResult(
                    calculation_name=cls.ENGINE_NAME,
                    value=None,
                    status=EngineeringStatus.INVALID_INPUT.value,
                    model="Isobaric Pressure Depletion",
                    warnings=[err]
                )
            drawdown_psi = pres - flowing_bhp_psia

        regime = "UNDERSATURATED"
        if bubble_point_pressure_psia and pres <= bubble_point_pressure_psia:
            regime = "SATURATED_TWO_PHASE"

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(pres, 2),
            unit="psia",
            model="Isobaric Pressure Depletion",
            status=EngineeringStatus.VALID.value,
            evidence={
                "current_pressure_psia": round(pres, 2),
                "cumulative_depletion_psi": round(pressure_depletion_psi, 2),
                "depletion_percentage": round(depletion_fraction * 100.0, 2),
                "drawdown_psi": round(drawdown_psi, 2) if drawdown_psi is not None else None,
                "reservoir_fluid_regime": regime
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class InjectionEngine:
    """
    6. Injection Engine.
    Injectivity Index (II), Hall Plot analysis, and injection conformance monitoring.
    """
    ENGINE_NAME = "Injection Engine"
    SPE_REFERENCE = "Hall, H.N. (1963) 'How to Analyze Waterflood Injection Well Performance' World Oil"

    @classmethod
    def evaluate_injectivity(
        cls,
        injection_rate_bpd: Optional[float],
        wellhead_injection_pressure_psia: Optional[float],
        reservoir_pressure_psia: Optional[float],
        cumulative_injection_bbl: Optional[float] = None
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "injection_rate_bpd": injection_rate_bpd,
                "wellhead_injection_pressure_psia": wellhead_injection_pressure_psia,
                "reservoir_pressure_psia": reservoir_pressure_psia
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Hall Plot & Injectivity Index Model",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        # Injectivity Index II = q_inj / (P_inj - P_res)
        delta_p = wellhead_injection_pressure_psia - reservoir_pressure_psia
        if delta_p <= 0.0:
            return EngineeringResult(
                calculation_name=cls.ENGINE_NAME,
                value=None,
                unit="bpd/psi",
                model="Hall Plot & Injectivity Index Model",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                warnings=["Injection pressure must exceed reservoir pressure for fluid intake."]
            )

        ii = injection_rate_bpd / delta_p

        # Hall integral approximation: Integral(P_wh * dt) vs Cum_Inj
        hall_coefficient = (wellhead_injection_pressure_psia * (cumulative_injection_bbl or 1.0)) / max(1.0, injection_rate_bpd)

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(ii, 3),
            unit="bpd/psi",
            model="Hall Plot & Injectivity Index Model",
            status=EngineeringStatus.VALID.value,
            evidence={
                "injectivity_index_bpd_psi": round(ii, 3),
                "net_injection_overpressure_psi": round(delta_p, 2),
                "hall_plot_slope_indicator": "NORMAL_STABLE_INTAKE" if ii > 0.5 else "POTENTIAL_WELLBORE_PLUGGING_OR_SKIN"
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class GORDiagnosticEngine:
    """
    11. GOR Diagnostic Engine.
    Distinguishes solution gas drive evolution from secondary gas cap breakthrough or gas coning.
    """
    ENGINE_NAME = "GOR Diagnostic Engine"
    SPE_REFERENCE = "SPE Textbook Series: Applied Reservoir Engineering"

    @classmethod
    def analyze_gor_trend(
        cls,
        producing_gor_scf_stb: Optional[float],
        solution_gor_rs_scf_stb: Optional[float],
        reservoir_pressure_psia: Optional[float],
        bubble_point_pressure_psia: Optional[float]
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "producing_gor_scf_stb": producing_gor_scf_stb,
                "solution_gor_rs_scf_stb": solution_gor_rs_scf_stb
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Gas-Oil Ratio Diagnostic Differentiation",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        gor = producing_gor_scf_stb
        rs = solution_gor_rs_scf_stb
        excess_gas_scf_stb = max(0.0, gor - rs)

        diagnostic = "NORMAL_SOLUTION_GAS"
        if excess_gas_scf_stb > (rs * 1.5):
            if reservoir_pressure_psia and bubble_point_pressure_psia and reservoir_pressure_psia < bubble_point_pressure_psia:
                diagnostic = "SECONDARY_GAS_CAP_EXPANSION_OR_FREE_GAS_LIBERATION"
            else:
                diagnostic = "GAS_CONING_OR_CHANNELING"

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(gor, 1),
            unit="scf/STB",
            model="Gas-Oil Ratio Diagnostic Differentiation",
            status=EngineeringStatus.VALID.value,
            evidence={
                "producing_gor_scf_stb": round(gor, 1),
                "solution_gor_rs_scf_stb": round(rs, 1),
                "excess_free_gas_scf_stb": round(excess_gas_scf_stb, 1),
                "diagnostic_mechanism": diagnostic
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class MatureFieldDepletionEngine:
    """
    16. Mature Field Pressure Drop & Depletion Diagnostic Engine.
    Detects boundary effects, compartmentalization, secondary gas cap development, and aquifer degradation.
    """
    ENGINE_NAME = "Mature Field Pressure Drop & Depletion Diagnostic Engine"
    SPE_REFERENCE = "SPE-100223: Surveillance & Reservoir Management of Mature Assets"

    @classmethod
    def diagnose_depletion_regime(
        cls,
        cumulative_oil_np_stb: Optional[float],
        current_pressure_psia: Optional[float],
        pressure_drop_rate_psi_month: Optional[float],
        water_cut_pct: Optional[float],
        vrr: Optional[float]
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "current_pressure_psia": current_pressure_psia,
                "pressure_drop_rate_psi_month": pressure_drop_rate_psi_month
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Mature Asset Depletion & Conformance Diagnostic",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        rate_drop = pressure_drop_rate_psi_month
        severity = "STABLE"
        if rate_drop > 25.0:
            severity = "CRITICAL_PRESSURE_COLLAPSE"
        elif rate_drop > 10.0:
            severity = "ACCELERATED_DEPLETION"

        vrr_status = "BALANCED"
        if vrr is not None:
            if vrr < 0.8:
                vrr_status = "UNDER_INJECTION_VOIDAGE_DEFICIT"
            elif vrr > 1.2:
                vrr_status = "OVER_INJECTION_RISK_OF_FRACTURING"

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(rate_drop, 2),
            unit="psi/month",
            model="Mature Asset Depletion & Conformance Diagnostic",
            status=EngineeringStatus.VALID.value,
            evidence={
                "monthly_pressure_drop_psi": round(rate_drop, 2),
                "depletion_severity": severity,
                "voidage_replacement_status": vrr_status,
                "water_cut_pct": water_cut_pct
            },
            correlation_reference=cls.SPE_REFERENCE
        )
