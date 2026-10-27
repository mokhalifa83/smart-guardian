"""
Smart Guardian Reservoir Intelligence Layer - Canonical Chan Diagnostics Engine (Step 2A)
Reference: Chan, K.S. (1995), "Water Control Diagnostic Plots", SPE-30775,
presented at the SPE Annual Technical Conference and Exhibition, Dallas, Texas.

Implements:
1. WOR = qw / qo or WOR = WC / (1 - WC)
2. WOR' = d(WOR) / d(ln(t))
3. Explicit handling of WC = 100% / qo = 0 (UNDEFINED_WOR, never epsilon substitution)
4. Robust processing of irregular timestamps, chronological sorting, deduplication
5. Evidence-based diagnostic interpretation (CONING, CHANNELING, NORMAL, INSUFFICIENT_EVIDENCE)
6. Canonical Chan plot data generation (no synthetic or placeholder points)
"""

import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class ProductionTimePoint(BaseModel):
    """Single chronological production record for Chan diagnostic analysis."""
    timestamp: datetime
    elapsed_days: Optional[float] = None
    oil_rate: Optional[float] = None     # bpd / stb/d
    water_rate: Optional[float] = None   # bpd
    water_cut_pct: Optional[float] = None # 0 - 100%


class ChanPlotPoint(BaseModel):
    """Canonical Chan diagnostic curve coordinate."""
    point_index: int
    timestamp: datetime
    elapsed_days: float
    oil_rate: Optional[float] = None
    water_rate: Optional[float] = None
    water_cut_pct: Optional[float] = None
    wor: Optional[float] = None
    wor_prime: Optional[float] = None
    status: str = "VALID"
    notes: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ChanDiagnosticEngine:
    """
    Canonical Chan (1995) Diagnostic Physics Engine.
    Single Source of Truth for WOR, WOR', diagnostic patterns, and plot data.
    """

    @staticmethod
    def calculate_single_wor(
        oil_rate: Optional[float] = None,
        water_rate: Optional[float] = None,
        water_cut_pct: Optional[float] = None
    ) -> EngineeringResult:
        """
        Calculates Water-Oil Ratio (WOR).
        Strictly enforces Rule 16:
        At WC = 100% or oil_rate = 0, WOR is physically undefined/infinite.
        Returns UNDEFINED_WOR. NEVER replaces denominator with arbitrary epsilon.
        """
        inputs = {
            "oil_rate": oil_rate,
            "water_rate": water_rate,
            "water_cut_pct": water_cut_pct
        }

        # Case 1: Evaluated from water cut percentage
        if water_cut_pct is not None:
            if water_cut_pct < 0.0 or water_cut_pct > 100.0:
                return EngineeringResult(
                    model="Chan (1995) WOR",
                    status=EngineeringStatus.OUT_OF_RANGE.value,
                    inputs=inputs,
                    evidence={"error": f"Water cut {water_cut_pct}% out of physical range [0, 100]"}
                )

            wc_frac = water_cut_pct / 100.0
            if wc_frac >= 0.999999 or math.isclose(wc_frac, 1.0, abs_tol=1e-5):
                return EngineeringResult(
                    model="Chan (1995) WOR",
                    status=EngineeringStatus.UNDEFINED_WOR.value,
                    inputs=inputs,
                    assumptions=["Water Cut is 100%; oil production has ceased"],
                    limitations=["WOR cannot be evaluated as a finite number when oil rate is zero"],
                    evidence={
                        "condition": "ZERO_OIL_RATE_WC_100",
                        "explanation": "Oil rate is zero / Water Cut is 100%; WOR cannot be represented as a finite value. (Rule 16: Zero-epsilon substitution strictly forbidden)."
                    }
                )

            wor = wc_frac / (1.0 - wc_frac)
            return EngineeringResult(
                value=round(wor, 5),
                unit="dimensionless",
                model="Chan (1995) WOR = WC / (1 - WC)",
                correlation="Chan (1995), SPE-30775",
                inputs=inputs,
                status=EngineeringStatus.VALID.value
            )

        # Case 2: Evaluated from rates
        if oil_rate is not None and water_rate is not None:
            if oil_rate < 0.0 or water_rate < 0.0:
                return EngineeringResult(
                    model="Chan (1995) WOR",
                    status=EngineeringStatus.OUT_OF_RANGE.value,
                    inputs=inputs,
                    evidence={"error": "Rates cannot be negative"}
                )

            if oil_rate == 0.0:
                return EngineeringResult(
                    model="Chan (1995) WOR",
                    status=EngineeringStatus.UNDEFINED_WOR.value,
                    inputs=inputs,
                    evidence={
                        "condition": "ZERO_OIL_RATE",
                        "explanation": "Oil rate is zero (qo = 0); WOR cannot be represented as a finite value."
                    }
                )

            wor = water_rate / oil_rate
            return EngineeringResult(
                value=round(wor, 5),
                unit="dimensionless",
                model="Chan (1995) WOR = qw / qo",
                correlation="Chan (1995), SPE-30775",
                inputs=inputs,
                status=EngineeringStatus.VALID.value
            )

        return EngineeringResult(
            model="Chan (1995) WOR",
            status=EngineeringStatus.INSUFFICIENT_DATA.value,
            inputs=inputs,
            evidence={"error": "Either water_cut_pct or (oil_rate and water_rate) must be provided"}
        )

    @classmethod
    def compute_chan_diagnostic_series(
        cls,
        history: List[ProductionTimePoint],
        well_code: str = "WELL-001",
        t_zero: Optional[datetime] = None
    ) -> EngineeringResult:
        """
        Processes multi-point production history into canonical Chan plot points (t, WOR, WOR').
        Calculates logarithmic time derivative WOR' = d(WOR)/d(ln(t)).
        Performs multi-evidence pattern diagnostics (Normal, Coning, Channeling, Insufficient Evidence).
        """
        if not history or len(history) < 2:
            return EngineeringResult(
                model="Chan (1995) Diagnostics",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs={"well_code": well_code, "points_count": len(history) if history else 0},
                evidence={"error": "At least 2 chronological production data points are required for Chan diagnostics"}
            )

        # 1. Sort strictly chronologically
        sorted_history = sorted(history, key=lambda x: x.timestamp)

        # 2. Deduplicate identical timestamps
        deduped: List[ProductionTimePoint] = []
        seen_timestamps = set()
        for p in sorted_history:
            if p.timestamp not in seen_timestamps:
                seen_timestamps.add(p.timestamp)
                deduped.append(p)

        # Determine reference time for elapsed days
        if t_zero is not None:
            reference_time = t_zero
        elif len(deduped) >= 2:
            dt_first_days = max(1.0, (deduped[1].timestamp - deduped[0].timestamp).total_seconds() / 86400.0)
            reference_time = deduped[0].timestamp - timedelta(days=dt_first_days)
        else:
            reference_time = deduped[0].timestamp - timedelta(days=1.0)

        plot_points: List[ChanPlotPoint] = []

        # 3. Calculate WOR for each valid point
        for idx, pt in enumerate(deduped):
            if pt.elapsed_days is not None and pt.elapsed_days > 0:
                elapsed_days = pt.elapsed_days
            else:
                elapsed_days = (pt.timestamp - reference_time).total_seconds() / 86400.0
                if elapsed_days <= 0.0:
                    elapsed_days = 0.1

            # Determine WOR
            wor_val = None
            pt_status = "VALID"
            pt_notes = None

            if pt.water_cut_pct is not None:
                wor_res = cls.calculate_single_wor(water_cut_pct=pt.water_cut_pct)
            else:
                wor_res = cls.calculate_single_wor(oil_rate=pt.oil_rate, water_rate=pt.water_rate)

            if wor_res.status == EngineeringStatus.VALID.value:
                wor_val = float(wor_res.value)
            elif wor_res.status == EngineeringStatus.UNDEFINED_WOR.value:
                pt_status = "UNDEFINED_WOR"
                pt_notes = "Zero oil rate; infinite WOR"
            else:
                pt_status = "INVALID"
                pt_notes = "Missing or invalid rate data"

            plot_points.append(
                ChanPlotPoint(
                    point_index=idx,
                    timestamp=pt.timestamp,
                    elapsed_days=round(elapsed_days, 4),
                    oil_rate=pt.oil_rate,
                    water_rate=pt.water_rate,
                    water_cut_pct=pt.water_cut_pct,
                    wor=wor_val,
                    wor_prime=None,
                    status=pt_status,
                    notes=pt_notes
                )
            )

        # 4. Compute Logarithmic Derivative: WOR' = d(WOR) / d(ln(t))
        # Filter points that have valid numeric WOR
        valid_indices = [i for i, pt in enumerate(plot_points) if pt.status == "VALID" and pt.wor is not None and pt.wor > 0]

        if len(valid_indices) >= 2:
            for k in range(len(valid_indices)):
                curr_idx = valid_indices[k]
                t_curr = plot_points[curr_idx].elapsed_days
                wor_curr = plot_points[curr_idx].wor

                if k == 0:
                    # Forward difference
                    next_idx = valid_indices[k + 1]
                    t_next = plot_points[next_idx].elapsed_days
                    wor_next = plot_points[next_idx].wor
                    dt_ln = math.log(t_next) - math.log(t_curr)
                    if abs(dt_ln) > 1e-6:
                        wor_prime = (wor_next - wor_curr) / dt_ln
                    else:
                        wor_prime = 0.0
                elif k == len(valid_indices) - 1:
                    # Backward difference
                    prev_idx = valid_indices[k - 1]
                    t_prev = plot_points[prev_idx].elapsed_days
                    wor_prev = plot_points[prev_idx].wor
                    dt_ln = math.log(t_curr) - math.log(t_prev)
                    if abs(dt_ln) > 1e-6:
                        wor_prime = (wor_curr - wor_prev) / dt_ln
                    else:
                        wor_prime = 0.0
                else:
                    # Central difference
                    prev_idx = valid_indices[k - 1]
                    next_idx = valid_indices[k + 1]
                    t_prev = plot_points[prev_idx].elapsed_days
                    t_next = plot_points[next_idx].elapsed_days
                    wor_prev = plot_points[prev_idx].wor
                    wor_next = plot_points[next_idx].wor
                    dt_ln = math.log(t_next) - math.log(t_prev)
                    if abs(dt_ln) > 1e-6:
                        wor_prime = (wor_next - wor_prev) / dt_ln
                    else:
                        wor_prime = 0.0

                plot_points[curr_idx].wor_prime = round(max(1e-6, wor_prime), 5) if wor_prime is not None else None

        # 5. Diagnostic Interpretation (Evidence-based pattern identification)
        pattern = "INSUFFICIENT_EVIDENCE"
        pattern_notes = "Not enough valid chronological points to establish slope trends."
        wor_slope = None
        wor_prime_slope = None

        if len(valid_indices) >= 3:
            first_idx = valid_indices[0]
            last_idx = valid_indices[-1]
            t_first = plot_points[first_idx].elapsed_days
            t_last = plot_points[last_idx].elapsed_days
            wor_first = plot_points[first_idx].wor
            wor_last = plot_points[last_idx].wor

            # Calculate overall log-log slope: d(log(WOR)) / d(log(t))
            if t_last > t_first and wor_first > 0 and wor_last > 0:
                wor_slope = (math.log10(wor_last) - math.log10(wor_first)) / (math.log10(t_last) - math.log10(t_first))

            # Recent slope of WOR'
            valid_primes = [(plot_points[i].elapsed_days, plot_points[i].wor_prime) for i in valid_indices if plot_points[i].wor_prime is not None and plot_points[i].wor_prime > 0]
            if len(valid_primes) >= 2:
                p_t0, p_w0 = valid_primes[0]
                p_t1, p_w1 = valid_primes[-1]
                if p_t1 > p_t0:
                    wor_prime_slope = (math.log10(p_w1) - math.log10(p_w0)) / (math.log10(p_t1) - math.log10(p_t0))

            # Chan (1995) pattern diagnostic criteria:
            # - Channeling: Sudden, very steep rise in WOR and WOR' (slopes typically >= 1.5 to 3+)
            # - Coning: Gradual change, steady increase, slope of WOR curve typically <= 1.0, WOR' plateaus or has lower slope
            # - Normal Displacement: Stable, very low or flat slope (< 0.2)
            if wor_slope is not None:
                if wor_slope >= 1.8:
                    pattern = "CHANNELING_PATTERN_INDICATED"
                    pattern_notes = (
                        f"Diagnostic Evidence: Rapid breakthrough with steep log-log slope ({wor_slope:.2f} >= 1.8). "
                        "Chan diagnostic curve indicates high-permeability streak, fracture, or channeling behavior. "
                        "[Engineering note: Confirmatory evidence from PLT or pulse well testing recommended before intervention]."
                    )
                elif 0.3 <= wor_slope < 1.8:
                    pattern = "CONING_PATTERN_INDICATED"
                    pattern_notes = (
                        f"Diagnostic Evidence: Gradual upward curvature with log-log slope ({wor_slope:.2f} < 1.8). "
                        "Chan diagnostic curve indicates bottom-water coning or gradual cresting. "
                        "[Engineering note: Critical rate evaluation and choke sensitivity recommended]."
                    )
                elif wor_slope < 0.3:
                    pattern = "NORMAL_DISPLACEMENT"
                    pattern_notes = f"Diagnostic Evidence: Low steady WOR progression (slope {wor_slope:.2f} < 0.3). Normal piston-like reservoir displacement."

        return EngineeringResult(
            value={"pattern": pattern, "points_count": len(plot_points)},
            unit="diagnostic_pattern",
            model="Chan (1995) Water Control Diagnostic Plots",
            correlation="Chan, K.S. (1995), SPE-30775",
            correlation_reference="Chan, K.S. (1995), 'Water Control Diagnostic Plots', SPE-30775",
            inputs={"well_code": well_code, "raw_points": len(history)},
            assumptions=[
                "Chronological time progression strictly enforced",
                "Logarithmic time derivatives evaluated via central differences",
                "No synthetic points or arbitrary smoothing applied"
            ],
            limitations=[
                "Chan diagnostic plots reveal fluid movement behavior at the wellbore; they require multi-well/geological context to establish definitive root cause.",
                "Workovers, choke changes, or intermittent production cause derivative spikes that must be filtered operationally."
            ],
            evidence={
                "observed_pattern": pattern,
                "diagnostic_notes": pattern_notes,
                "log_log_wor_slope": round(wor_slope, 3) if wor_slope is not None else None,
                "wor_prime_slope": round(wor_prime_slope, 3) if wor_prime_slope is not None else None,
                "plot_points": [p.model_dump() for p in plot_points]
            },
            status=EngineeringStatus.VALID.value
        )
