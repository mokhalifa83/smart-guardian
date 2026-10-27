"""
Smart Guardian Reservoir Intelligence Layer - Well Test Analysis Engine (Step 2B)
References:
- Horner, D.R. (1951), "Pressure Build-Up in Wells", Proc., Third World Pet. Cong., The Hague, II, 503-523.
- Bourdet, D., Whittle, T.M., Douglas, A.A., and Pirard, Y.M. (1983), "A New Set of Type Curves Simplifies Well Test Analysis", World Oil, 196(6), 95-106.

Implements canonical Pressure Transient Analysis (PTA):
1. Constant-Rate Drawdown Analysis
2. Pressure Buildup & Horner Analysis
3. Radial Flow Semilog Analysis (Permeability k, kh, Skin s, Pressure Drop due to Skin dP_skin)
4. Wellbore Storage & Boundary Diagnostic Indicators (Unit slope, sealing fault slope doubling, constant pressure recharge)

Strictly adheres to:
- Distinct separation of Observed Pressure Behavior, Engineering Interpretation, and Potential Root Cause
- Complete unit and sequence verification (positive flowing time, non-negative pressure)
- Standard EngineeringResult contract with explicit assumptions, limitations, and provenance
"""

import math
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class WellTestGaugePoint(BaseModel):
    """Chronological pressure gauge observation during well testing."""
    elapsed_time_hours: float = Field(..., gt=0, description="Elapsed time in hours since test start or shut-in")
    pressure_psia: float = Field(..., gt=0, description="Bottomhole pressure in psia")

    model_config = ConfigDict(from_attributes=True)


class WellTestEngine:
    """
    Canonical Well Test & Pressure Transient Analysis Engine.
    Single Source of Truth for Horner analysis, drawdown, skin, permeability, and flow regimes.
    """

    @classmethod
    def analyze_drawdown(
        cls,
        gauge_points: List[WellTestGaugePoint],
        initial_pressure_psia: float,
        flow_rate_stbd: float,
        formation_thickness_ft: float,
        porosity_fraction: float,
        total_compressibility_psi: float,
        viscosity_cp: float,
        bo_rb_stb: float,
        wellbore_radius_ft: float = 0.354,
        well_code: Optional[str] = None
    ) -> EngineeringResult:
        """
        Executes semi-log drawdown analysis on flowing bottomhole pressure records.
        """
        inputs = {
            "well_code": well_code,
            "test_type": "DRAWDOWN",
            "initial_pressure_psia": initial_pressure_psia,
            "flow_rate_stbd": flow_rate_stbd,
            "formation_thickness_ft": formation_thickness_ft,
            "porosity_fraction": porosity_fraction,
            "viscosity_cp": viscosity_cp,
            "bo_rb_stb": bo_rb_stb,
            "points_count": len(gauge_points) if gauge_points else 0
        }

        # 1. Validation
        if not gauge_points or len(gauge_points) < 3:
            return EngineeringResult(
                calculation_name="Drawdown Well Test Analysis",
                model="Drawdown Semi-log Radial Flow",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "At least 3 gauge points are required for drawdown semi-log slope evaluation."}
            )

        if flow_rate_stbd <= 0 or formation_thickness_ft <= 0 or viscosity_cp <= 0 or bo_rb_stb <= 0 or porosity_fraction <= 0 or total_compressibility_psi <= 0:
            return EngineeringResult(
                calculation_name="Drawdown Well Test Analysis",
                model="Drawdown Semi-log Radial Flow",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={"error": "Reservoir fluid and rock properties (h, phi, ct, mu, Bo, rate) must be strictly positive."}
            )

        # Sort by elapsed time
        sorted_pts = sorted(gauge_points, key=lambda x: x.elapsed_time_hours)
        times = [p.elapsed_time_hours for p in sorted_pts]
        pressures = [p.pressure_psia for p in sorted_pts]

        # Drawdown: pwf = pi - m * log10(t) - C
        # Fit pwf vs log10(t)
        log_times = [math.log10(t) for t in times]
        n = len(times)
        mean_x = sum(log_times) / n
        mean_y = sum(pressures) / n
        ss_xx = sum((xi - mean_x) ** 2 for xi in log_times)
        ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(log_times, pressures))

        if ss_xx < 1e-9:
            return EngineeringResult(
                calculation_name="Drawdown Well Test Analysis",
                model="Drawdown Semi-log Radial Flow",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "Insufficient time variation across gauge points."}
            )

        slope = ss_xy / ss_xx
        m_drawdown = abs(slope)  # psi/cycle

        if m_drawdown < 1e-5:
            return EngineeringResult(
                calculation_name="Drawdown Well Test Analysis",
                model="Drawdown Semi-log Radial Flow",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Observed slope is near zero; radial flow regime not developed."}
            )

        # Calculate kh and k
        # m = 162.6 * q * B * mu / (k * h)
        kh = (162.6 * flow_rate_stbd * bo_rb_stb * viscosity_cp) / m_drawdown
        permeability_md = kh / formation_thickness_ft

        # Intercept at 1 hr: p_1hr = mean_y - slope * (mean_x - log10(1)) = mean_y - slope * mean_x
        p_1hr = mean_y - slope * mean_x

        # Skin factor:
        # s = 1.151 * [ (pi - p_1hr)/m - log10(k / (phi * mu * ct * rw^2)) + 3.23 ]
        diff_term = (initial_pressure_psia - p_1hr) / m_drawdown
        group_term = permeability_md / (porosity_fraction * viscosity_cp * total_compressibility_psi * (wellbore_radius_ft ** 2))
        if group_term <= 0:
            return EngineeringResult(
                calculation_name="Drawdown Well Test Analysis",
                model="Drawdown Semi-log Radial Flow",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Non-physical parameter combination for skin evaluation."}
            )

        skin = 1.151 * (diff_term - math.log10(group_term) + 3.23)
        delta_p_skin = 0.869 * m_drawdown * skin

        flow_efficiency = None
        drawdown_total = initial_pressure_psia - pressures[-1]
        if drawdown_total > 0:
            flow_efficiency = (drawdown_total - delta_p_skin) / drawdown_total

        return EngineeringResult(
            calculation_name="Drawdown Well Test Analysis",
            value={
                "permeability_thickness_md_ft": round(kh, 2),
                "permeability_md": round(permeability_md, 2),
                "skin_factor": round(skin, 2),
                "delta_p_skin_psi": round(delta_p_skin, 2),
                "flow_efficiency": round(flow_efficiency, 3) if flow_efficiency is not None else None,
                "semilog_slope_m_psi_cycle": round(m_drawdown, 2),
                "p_1hr_psia": round(p_1hr, 2)
            },
            unit="md",
            model="Constant-Rate Drawdown Radial Flow Analysis",
            correlation="Semi-log Radial Flow Formulation",
            correlation_reference="Horner (1951), Earlougher, R.C. Jr. (1977), 'Advances in Well Test Analysis', SPE Monograph 5",
            inputs=inputs,
            assumptions=[
                "Constant flow rate prior to and during the transient test interval",
                "Single-phase, slightly compressible, laminar Darcy flow",
                "Infinite-acting radial flow regime developed during analysis window"
            ],
            limitations=[
                "Wellbore storage effects can mask early radial flow and distort the semi-log straight line.",
                "Drawdown rates in field operations are rarely strictly constant; rate normalization is required for multi-rate tests."
            ],
            evidence={
                "observed_behavior": f"Semi-log slope m = {m_drawdown:.2f} psi/cycle across {len(gauge_points)} gauge readings.",
                "interpretation": f"Calculated formation permeability k = {permeability_md:.2f} md, Skin s = {skin:.2f}.",
                "skin_diagnosis": "Stimulated wellbore" if skin < -0.5 else ("Near-wellbore damage indicated" if skin > 2.0 else "Neutral near-wellbore condition")
            },
            status=EngineeringStatus.VALID.value
        )

    @classmethod
    def analyze_horner_buildup(
        cls,
        gauge_points: List[WellTestGaugePoint],
        producing_time_tp_hours: float,
        flow_rate_stbd: float,
        formation_thickness_ft: float,
        porosity_fraction: float,
        total_compressibility_psi: float,
        viscosity_cp: float,
        bo_rb_stb: float,
        wellbore_radius_ft: float = 0.354,
        flowing_pwf_at_shutin_psia: Optional[float] = None,
        well_code: Optional[str] = None
    ) -> EngineeringResult:
        """
        Executes canonical Horner (1951) pressure buildup analysis on shut-in gauge records.
        Evaluates slope m, kh, k, skin s, extrapolated reservoir pressure p*, and boundary indications.
        """
        inputs = {
            "well_code": well_code,
            "test_type": "BUILDUP_HORNER",
            "producing_time_tp_hours": producing_time_tp_hours,
            "flow_rate_stbd": flow_rate_stbd,
            "formation_thickness_ft": formation_thickness_ft,
            "porosity_fraction": porosity_fraction,
            "viscosity_cp": viscosity_cp,
            "bo_rb_stb": bo_rb_stb,
            "points_count": len(gauge_points) if gauge_points else 0
        }

        # 1. Validation
        if not gauge_points or len(gauge_points) < 3:
            return EngineeringResult(
                calculation_name="Horner Buildup Well Test Analysis",
                model="Horner (1951) Pressure Buildup",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "At least 3 shut-in pressure gauge observations are required for Horner analysis."}
            )

        if producing_time_tp_hours <= 0 or flow_rate_stbd <= 0 or formation_thickness_ft <= 0 or viscosity_cp <= 0 or bo_rb_stb <= 0 or porosity_fraction <= 0 or total_compressibility_psi <= 0:
            return EngineeringResult(
                calculation_name="Horner Buildup Well Test Analysis",
                model="Horner (1951) Pressure Buildup",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={"error": "Producing time tp and reservoir/fluid properties must be strictly positive."}
            )

        sorted_pts = sorted(gauge_points, key=lambda x: x.elapsed_time_hours)
        dt_list = [p.elapsed_time_hours for p in sorted_pts]
        p_list = [p.pressure_psia for p in sorted_pts]

        pwf_shutin = flowing_pwf_at_shutin_psia if flowing_pwf_at_shutin_psia is not None else p_list[0]

        # Horner Time Ratio: HR = (tp + dt) / dt
        hr_list = [(producing_time_tp_hours + dt) / dt for dt in dt_list]
        log_hr = [math.log10(hr) for hr in hr_list]

        # Horner straight line: pws = p* - m * log10((tp + dt)/dt)
        # Linear regression of pws vs log10(HR)
        n = len(log_hr)
        mean_x = sum(log_hr) / n
        mean_y = sum(p_list) / n
        ss_xx = sum((xi - mean_x) ** 2 for xi in log_hr)
        ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(log_hr, p_list))

        if ss_xx < 1e-9:
            return EngineeringResult(
                calculation_name="Horner Buildup Well Test Analysis",
                model="Horner (1951) Pressure Buildup",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "Insufficient shut-in time variation across gauge points."}
            )

        slope_horner = ss_xy / ss_xx
        # In Horner plot, pws decreases as (tp+dt)/dt increases, so slope is negative
        m_horner = abs(slope_horner)  # psi/cycle

        if m_horner < 1e-5:
            return EngineeringResult(
                calculation_name="Horner Buildup Well Test Analysis",
                model="Horner (1951) Pressure Buildup",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Horner semi-log slope m is near zero; buildup transient not resolved."}
            )

        # Extrapolated reservoir pressure p* at HR = 1 (infinite shut-in, log10(1) = 0)
        p_star = mean_y - slope_horner * mean_x

        # kh and k
        kh = (162.6 * flow_rate_stbd * bo_rb_stb * viscosity_cp) / m_horner
        permeability_md = kh / formation_thickness_ft

        # Pressure at dt = 1 hr on the straight line:
        # HR_1hr = (tp + 1.0) / 1.0 = tp + 1.0
        log_hr_1hr = math.log10(producing_time_tp_hours + 1.0)
        p_1hr = p_star + slope_horner * log_hr_1hr  # slope_horner is negative

        # Skin factor:
        # s = 1.151 * [ (p_1hr - pwf_shutin)/m - log10(k / (phi * mu * ct * rw^2)) + 3.23 ]
        diff_term = (p_1hr - pwf_shutin) / m_horner
        group_term = permeability_md / (porosity_fraction * viscosity_cp * total_compressibility_psi * (wellbore_radius_ft ** 2))
        if group_term <= 0:
            return EngineeringResult(
                calculation_name="Horner Buildup Well Test Analysis",
                model="Horner (1951) Pressure Buildup",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Non-physical parameter combination for skin evaluation."}
            )

        skin = 1.151 * (diff_term - math.log10(group_term) + 3.23)
        delta_p_skin = 0.869 * m_horner * skin

        # Boundary & Flow Regime Diagnostic Evidence
        observed_pattern = "INFINITE_ACTING_RADIAL_FLOW"
        potential_root_cause = "Homogeneous unbounded radial drainage during analysis window."
        required_confirmation = "Multi-rate test or interference testing to confirm compartment boundaries."

        # Diagnostic check for slope changes (early vs late)
        if len(p_list) >= 6:
            half = len(p_list) // 2
            early_m = abs((p_list[half] - p_list[0]) / (log_hr[half] - log_hr[0])) if abs(log_hr[half] - log_hr[0]) > 1e-4 else m_horner
            late_m = abs((p_list[-1] - p_list[half]) / (log_hr[-1] - log_hr[half])) if abs(log_hr[-1] - log_hr[half]) > 1e-4 else m_horner

            if late_m >= 1.7 * early_m:
                observed_pattern = "LATE_TIME_SLOPE_DOUBLING_INDICATED"
                potential_root_cause = "Possible sealing fault or impermeable lateral reservoir boundary."
                required_confirmation = "Geological fault mapping, seismic tie-in, and extended buildup test required before concluding fault presence."
            elif late_m <= 0.4 * early_m:
                observed_pattern = "LATE_TIME_DERIVATIVE_DROP_INDICATED"
                potential_root_cause = "Possible constant pressure boundary or strong aquifer / injector support."
                required_confirmation = "Material balance water influx analysis and offset injection history review required."

        return EngineeringResult(
            calculation_name="Horner Buildup Well Test Analysis",
            value={
                "permeability_thickness_md_ft": round(kh, 2),
                "permeability_md": round(permeability_md, 2),
                "skin_factor": round(skin, 2),
                "delta_p_skin_psi": round(delta_p_skin, 2),
                "extrapolated_pressure_p_star_psia": round(p_star, 2),
                "horner_slope_m_psi_cycle": round(m_horner, 2),
                "p_1hr_psia": round(p_1hr, 2)
            },
            unit="md",
            model="Horner (1951) Pressure Buildup Analysis",
            correlation="Horner Semi-log Buildup Formulation",
            correlation_reference="Horner, D.R. (1951), 'Pressure Build-Up in Wells', Proc. 3rd World Pet. Cong., II, 503-523",
            inputs=inputs,
            assumptions=[
                "Single stabilized rate prior to shut-in (effective producing time tp = Np / q)",
                "Infinite-acting radial flow regime identified on middle time region (MTR)",
                "Negligible phase redistribution in wellbore during shut-in"
            ],
            limitations=[
                "Wellbore storage (afterflow) distorts the early time region (ETR); straight line must be selected strictly from the middle time region.",
                "Slope doubling is an indicator of possible boundary geometry but requires geological corroboration."
            ],
            observed_pattern=observed_pattern,
            diagnostic_interpretation=f"Formation permeability k = {permeability_md:.2f} md, Skin = {skin:.2f}, Extrapolated p* = {p_star:.2f} psia.",
            potential_root_causes=[potential_root_cause],
            required_confirmation=[required_confirmation],
            evidence={
                "observed_pressure_behavior": f"Horner slope m = {m_horner:.2f} psi/cycle, p* = {p_star:.2f} psia.",
                "engineering_interpretation": f"Effective permeability = {permeability_md:.2f} md, Near-wellbore skin = {skin:.2f}.",
                "damage_status": "Severely damaged" if skin > 5.0 else ("Damaged" if skin > 2.0 else ("Stimulated" if skin < -1.0 else "Normal/Neutral"))
            },
            status=EngineeringStatus.VALID.value
        )
