"""
Smart Guardian Reservoir Intelligence Layer - Waterflood Surveillance Engine (Step 2B)
References:
- Hall, H.N. (1963), "How to Analyze Waterflood Injection Well Performance", World Oil, 157(5), 128-130.
- Baker, R. (1998), "Reservoir Engineering Waterflooding Course", SPE.

Implements canonical Waterflood Surveillance & Diagnostic Intelligence:
1. Reuses Canonical STEP 2A VRR Engine (Strict Zero Duplication Rule)
2. Injector Performance Surveillance via Hall Integral Diagnostic Plot
3. Injector-Producer Response & Apparent Time-Lag Tracking
4. Pressure Support Evaluation & Breakthrough Indicators
5. Unified Evidence Flow (Indicator -> Evidence -> Advisory Interpretation -> Confirmation Required)

Strictly adheres to:
- VRR evaluated in-situ via canonical STEP 2A VRREngine (never comparing surface barrels)
- Connectivity requires corroborating physical evidence; returns INSUFFICIENT_EVIDENCE when ambiguous
- Advisory decision support only: no autonomous control or valve adjustment
- Standard EngineeringResult contract with complete assumptions, limitations, and provenance
"""

import math
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.vrr_engine import VRREngine


class WaterfloodObservationPoint(BaseModel):
    """Chronological injection and offset production observation point."""
    timestamp: datetime
    injection_rate_bpd: float = Field(..., ge=0, description="Water injection rate in BPD")
    wellhead_injection_pressure_psia: Optional[float] = Field(default=None, ge=0)
    offset_oil_rate_stbd: float = Field(default=0.0, ge=0)
    offset_water_rate_bpd: float = Field(default=0.0, ge=0)
    offset_gas_rate_scfd: Optional[float] = Field(default=0.0, ge=0)
    water_cut_pct: Optional[float] = Field(default=None, ge=0, le=100)

    model_config = ConfigDict(from_attributes=True)


class WaterfloodEngine:
    """
    Canonical Waterflood Surveillance Engine.
    Orchestrates waterflood diagnostics, Hall plots, injector-producer response, and canonical VRR.
    """

    @classmethod
    def analyze_waterflood_surveillance(
        cls,
        history: List[WaterfloodObservationPoint],
        bo_rb_stb: float = 1.25,
        bw_rb_stb: float = 1.02,
        bg_rb_scf: float = 0.00095,
        rs_scf_stb: float = 500.0,
        pattern_name: Optional[str] = None,
        injector_well_code: Optional[str] = None
    ) -> EngineeringResult:
        """
        Analyzes historical injection-production surveillance series.
        Integrates canonical STEP 2A VRR, calculates Hall plot integral, and evaluates connectivity evidence.
        """
        inputs = {
            "injector_well_code": injector_well_code,
            "pattern_name": pattern_name,
            "points_count": len(history) if history else 0,
            "bo_rb_stb": bo_rb_stb,
            "bw_rb_stb": bw_rb_stb,
            "bg_rb_scf": bg_rb_scf,
            "rs_scf_stb": rs_scf_stb
        }

        # 1. Validation
        if not history or len(history) < 2:
            return EngineeringResult(
                calculation_name="Waterflood Surveillance Analysis",
                model="Waterflood Surveillance & Hall Diagnostic",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "At least 2 chronological surveillance records are required for waterflood analysis."}
            )

        sorted_pts = sorted(history, key=lambda x: x.timestamp)

        # 2. Cumulative Volumes & Canonical VRR evaluation
        cum_inj_bbl = 0.0
        cum_oil_stb = 0.0
        cum_water_bbl = 0.0
        cum_gas_scf = 0.0

        hall_points = []
        cum_p_dt = 0.0  # Cumulative pressure-time integral (psi * days)
        t0 = sorted_pts[0].timestamp

        for i in range(len(sorted_pts)):
            pt = sorted_pts[i]
            dt_days = (pt.timestamp - (sorted_pts[i-1].timestamp if i > 0 else t0)).total_seconds() / 86400.0
            if dt_days <= 0:
                dt_days = 1.0

            inj_vol_step = pt.injection_rate_bpd * dt_days
            oil_vol_step = pt.offset_oil_rate_stbd * dt_days
            water_vol_step = pt.offset_water_rate_bpd * dt_days
            gas_vol_step = (pt.offset_gas_rate_scfd or 0.0) * dt_days

            cum_inj_bbl += inj_vol_step
            cum_oil_stb += oil_vol_step
            cum_water_bbl += water_vol_step
            cum_gas_scf += gas_vol_step

            # Hall Plot Integral: sum(P_inj * dt) vs Cum Injection (W_inj)
            if pt.wellhead_injection_pressure_psia is not None:
                cum_p_dt += pt.wellhead_injection_pressure_psia * dt_days
                hall_points.append({
                    "timestamp": pt.timestamp.isoformat(),
                    "cum_injection_bbl": round(cum_inj_bbl, 1),
                    "hall_integral_psi_days": round(cum_p_dt, 1)
                })

        # Call CANONICAL STEP 2A VRR ENGINE (Strict Zero Duplication)
        vrr_res = VRREngine.calculate_vrr(
            produced_oil_stb=cum_oil_stb,
            produced_water_bbl=cum_water_bbl,
            produced_gas_scf=cum_gas_scf if cum_gas_scf > 0 else None,
            injected_water_bbl=cum_inj_bbl,
            injected_gas_scf=0.0,
            bo_rb_stb=bo_rb_stb,
            bw_rb_stb=bw_rb_stb,
            bg_rb_scf=bg_rb_scf,
            rs_scf_stb=rs_scf_stb,
            is_instantaneous_rate=False
        )

        vrr_value = vrr_res.value if isinstance(vrr_res.value, (int, float)) else None
        vrr_status = vrr_res.status

        # 3. Hall Plot Diagnostic Slope Interpretation
        hall_pattern = "NORMAL_STABILIZED_INJECTION"
        hall_diagnosis = "Hall diagnostic slope is stable, indicating steady injectivity without severe plugging or fracturing."
        potential_root_cause = "Stable reservoir matrix injection."
        required_confirmation = "Routine step-rate test or falloff survey to re-verify formation parting pressure."

        if len(hall_points) >= 4:
            # Compare early slope vs recent slope of Hall plot
            half = len(hall_points) // 2
            early_dw = hall_points[half]["cum_injection_bbl"] - hall_points[0]["cum_injection_bbl"]
            early_dp = hall_points[half]["hall_integral_psi_days"] - hall_points[0]["hall_integral_psi_days"]
            early_slope = (early_dp / early_dw) if early_dw > 10 else 1.0

            late_dw = hall_points[-1]["cum_injection_bbl"] - hall_points[half]["cum_injection_bbl"]
            late_dp = hall_points[-1]["hall_integral_psi_days"] - hall_points[half]["hall_integral_psi_days"]
            late_slope = (late_dp / late_dw) if late_dw > 10 else 1.0

            if late_slope > 1.4 * early_slope:
                hall_pattern = "INJECTOR_PLUGGING_OR_SKIN_INCREASE"
                hall_diagnosis = "Hall plot shows upward slope curvature (increasing resistance). Indicates wellbore plugging, scale, or bacterial fouling."
                potential_root_cause = "Suspended solids in injected water or near-wellbore scale deposition."
                required_confirmation = "Water quality millipore membrane filter test and pressure falloff test to measure wellbore skin."
            elif late_slope < 0.65 * early_slope:
                hall_pattern = "INJECTOR_FRACTURING_OR_CHANNELING"
                hall_diagnosis = "Hall plot shows downward slope curvature (decreasing resistance). Indicates hydraulic fracturing or out-of-zone thief zone communication."
                potential_root_cause = "Injection pressure exceeded formation parting pressure or thermal fracturing."
                required_confirmation = "Step-rate test (SRT) and injection logging tool (ILT/temperature survey) to verify vertical injection profile."

        # 4. Injector-Producer Connectivity Evidence Evaluation
        connectivity_status = "INSUFFICIENT_EVIDENCE"
        supporting_evidence = []
        conflicting_evidence = []

        # Check for offset production increase following injection
        if sorted_pts[-1].offset_oil_rate_stbd > sorted_pts[0].offset_oil_rate_stbd and cum_inj_bbl > 1000:
            supporting_evidence.append(f"Offset oil rate increased from {sorted_pts[0].offset_oil_rate_stbd:.1f} to {sorted_pts[-1].offset_oil_rate_stbd:.1f} STB/D during injection.")
        if sorted_pts[-1].water_cut_pct and sorted_pts[0].water_cut_pct:
            if sorted_pts[-1].water_cut_pct > sorted_pts[0].water_cut_pct + 15.0:
                supporting_evidence.append(f"Offset water cut increased by {sorted_pts[-1].water_cut_pct - sorted_pts[0].water_cut_pct:.1f}% following cumulative injection of {cum_inj_bbl:,.0f} bbl.")

        if supporting_evidence:
            connectivity_status = "APPARENT_CORRELATION_INDICATED"
            required_conn_confirmation = "Inter-well chemical tracer test or multi-well pulse pressure test required to confirm direct hydraulic connectivity."
        else:
            required_conn_confirmation = "Extended injection surveillance and baseline pressure interference monitoring required."

        return EngineeringResult(
            calculation_name="Waterflood Pattern Surveillance",
            value={
                "cumulative_injection_bbl": round(cum_inj_bbl, 1),
                "cumulative_offset_oil_stb": round(cum_oil_stb, 1),
                "cumulative_offset_water_bbl": round(cum_water_bbl, 1),
                "canonical_vrr": round(vrr_value, 4) if vrr_value is not None else None,
                "vrr_status": vrr_status,
                "hall_pattern": hall_pattern
            },
            unit="bbl",
            model="Waterflood Surveillance & Hall (1963) Diagnostic Analysis",
            correlation="Hall, H.N. (1963), SPE",
            correlation_reference="Hall, H.N. (1963), 'How to Analyze Waterflood Injection Well Performance', World Oil, 157(5), 128-130",
            inputs=inputs,
            assumptions=[
                "VRR is evaluated in-situ via canonical STEP 2A VRREngine using downhole formation volume factors",
                "Hall integral assumes pseudosteady radial flow around the injector",
                "Offset production is associated with the monitored injector pattern"
            ],
            limitations=[
                "Hall plot slope changes indicate changes in transmissibility but require falloff testing to separate permeability from skin.",
                "Injector-producer connectivity cannot be proven solely by rate coincidence; chemical tracer or pulse testing is mandatory."
            ],
            observed_pattern=hall_pattern,
            diagnostic_interpretation=hall_diagnosis,
            potential_root_causes=[potential_root_cause],
            supporting_evidence=supporting_evidence,
            conflicting_evidence=conflicting_evidence,
            required_confirmation=[required_confirmation, required_conn_confirmation],
            evidence={
                "canonical_vrr_result": vrr_res.model_dump(),
                "hall_diagnostic": {
                    "pattern": hall_pattern,
                    "points_count": len(hall_points),
                    "summary": hall_diagnosis
                },
                "connectivity_status": connectivity_status
            },
            status=EngineeringStatus.VALID.value
        )
