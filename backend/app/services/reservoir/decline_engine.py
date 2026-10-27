"""
Smart Guardian Reservoir Intelligence Layer - Decline Analysis Engine (Step 2B)
Reference: Arps, J.J. (1945), "Analysis of Decline Curves", Trans. AIME, 160, 228-247.

Implements canonical Arps empirical production decline curve analysis:
1. Exponential Decline (b = 0)
2. Harmonic Decline (b = 1)
3. Hyperbolic Decline (0 < b < 1)

Strictly adheres to:
- Real input validation (chronological timestamps, strictly positive rates)
- Least-squares parameter fitting with statistical goodness-of-fit (R^2, RMSE)
- Transparent forecasting without synthetic historical data
- Explicit EUR calculation ONLY when an economic/technical limit is explicitly configured (never invented)
- Standard EngineeringResult contract with complete assumptions and limitations
"""

import math
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class ProductionRatePoint(BaseModel):
    """Chronological production rate observation."""
    timestamp: datetime
    rate_stbd: float = Field(..., description="Oil or liquid production rate in STB/D")
    cumulative_days: Optional[float] = None

    model_config = ConfigDict(from_attributes=True)


class DeclineEngine:
    """
    Canonical Production Decline Curve Analysis Engine.
    Single Source of Truth for Arps decline physics, parameter estimation, EUR, and forecasting.
    """

    @staticmethod
    def calculate_rate(qi: float, di: float, b: float, t_days: float) -> float:
        """
        Evaluates production rate at elapsed time t_days.
        - b = 0: Exponential -> q(t) = qi * exp(-di * t)
        - b = 1: Harmonic    -> q(t) = qi / (1 + di * t)
        - 0 < b < 1: Hyperbolic -> q(t) = qi / ((1 + b * di * t) ** (1/b))
        """
        if t_days <= 0:
            return qi
        if abs(b) < 1e-5:
            # Exponential
            return qi * math.exp(-di * t_days)
        elif abs(b - 1.0) < 1e-5:
            # Harmonic
            return qi / (1.0 + di * t_days)
        else:
            # Hyperbolic
            denom = (1.0 + b * di * t_days)
            if denom <= 0:
                return 0.0
            return qi / (denom ** (1.0 / b))

    @staticmethod
    def calculate_cumulative(qi: float, di: float, b: float, q_target: float) -> float:
        """
        Evaluates cumulative production Np from initial rate qi down to target rate q_target.
        """
        if di <= 0 or q_target >= qi:
            return 0.0
        if abs(b) < 1e-5:
            # Exponential: Np = (qi - q) / di
            return (qi - q_target) / di
        elif abs(b - 1.0) < 1e-5:
            # Harmonic: Np = (qi / di) * ln(qi / q)
            return (qi / di) * math.log(qi / q_target)
        else:
            # Hyperbolic: Np = (qi^b / ((1-b)*di)) * [qi^(1-b) - q^(1-b)]
            term1 = (qi ** b) / ((1.0 - b) * di)
            term2 = (qi ** (1.0 - b)) - (q_target ** (1.0 - b))
            return term1 * term2

    @classmethod
    def fit_decline_parameters(
        cls,
        history: List[ProductionRatePoint],
        model_type: str = "EXPONENTIAL"
    ) -> Tuple[float, float, float, float, float]:
        """
        Fits Arps parameters (qi, di, b) to historical time series.
        Returns: (qi, di_per_day, b, r2, rmse)
        """
        # Sort chronologically and deduplicate
        sorted_pts = sorted(history, key=lambda x: x.timestamp)
        t0 = sorted_pts[0].timestamp
        t_days_list = []
        q_list = []

        for pt in sorted_pts:
            dt = (pt.timestamp - t0).total_seconds() / 86400.0
            if pt.rate_stbd > 0:
                t_days_list.append(dt)
                q_list.append(pt.rate_stbd)

        n = len(t_days_list)
        if n < 3:
            raise ValueError("At least 3 valid chronological points are required for decline fitting.")

        model_upper = model_type.upper()

        if model_upper == "EXPONENTIAL":
            # ln(q) = ln(qi) - di * t (Linear regression of ln(q) vs t)
            b = 0.0
            x = t_days_list
            y = [math.log(q) for q in q_list]
            mean_x = sum(x) / n
            mean_y = sum(y) / n
            ss_xx = sum((xi - mean_x) ** 2 for xi in x)
            ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))

            if ss_xx > 1e-9:
                slope = ss_xy / ss_xx
                intercept = mean_y - slope * mean_x
                di = max(1e-6, -slope)
                qi = math.exp(intercept)
            else:
                qi = q_list[0]
                di = 1e-4

        elif model_upper == "HARMONIC":
            # 1/q = (1/qi) + (di/qi) * t (Linear regression of 1/q vs t)
            b = 1.0
            x = t_days_list
            y = [1.0 / q for q in q_list]
            mean_x = sum(x) / n
            mean_y = sum(y) / n
            ss_xx = sum((xi - mean_x) ** 2 for xi in x)
            ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))

            if ss_xx > 1e-9:
                slope = max(1e-9, ss_xy / ss_xx)
                intercept = mean_y - slope * mean_x
                if intercept > 0:
                    qi = 1.0 / intercept
                    di = slope * qi
                else:
                    qi = q_list[0]
                    di = 1e-4
            else:
                qi = q_list[0]
                di = 1e-4

        elif model_upper == "HYPERBOLIC":
            # Grid search for optimal b in (0.05, 0.95) with best R^2
            best_r2 = -1e9
            best_params = (q_list[0], 0.001, 0.5)
            for b_cand in [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]:
                # Transform: y = q^(-b) = qi^(-b) + b * di * qi^(-b) * t
                y = [q ** (-b_cand) for q in q_list]
                x = t_days_list
                mean_x = sum(x) / n
                mean_y = sum(y) / n
                ss_xx = sum((xi - mean_x) ** 2 for xi in x)
                ss_xy = sum((xi - mean_x) * (yi - mean_y) for xi, yi in zip(x, y))
                if ss_xx > 1e-9:
                    slope = ss_xy / ss_xx
                    intercept = mean_y - slope * mean_x
                    if intercept > 0 and slope > 0:
                        qi_cand = intercept ** (-1.0 / b_cand)
                        di_cand = slope / (b_cand * (qi_cand ** (-b_cand)))
                        # Evaluate R2
                        pred = [cls.calculate_rate(qi_cand, di_cand, b_cand, t) for t in x]
                        mean_q = sum(q_list) / n
                        ss_tot = sum((q - mean_q) ** 2 for q in q_list)
                        ss_res = sum((q - p) ** 2 for q, p in zip(q_list, pred))
                        cand_r2 = 1.0 - (ss_res / ss_tot) if ss_tot > 1e-9 else 0.0
                        if cand_r2 > best_r2:
                            best_r2 = cand_r2
                            best_params = (qi_cand, di_cand, b_cand)
            qi, di, b = best_params
        else:
            raise ValueError(f"Unsupported decline model '{model_type}'. Choose EXPONENTIAL, HARMONIC, or HYPERBOLIC.")

        # Compute final R^2 and RMSE
        predicted = [cls.calculate_rate(qi, di, b, t) for t in t_days_list]
        mean_actual = sum(q_list) / n
        ss_tot = sum((q - mean_actual) ** 2 for q in q_list)
        ss_res = sum((q - p) ** 2 for q, p in zip(q_list, predicted))
        r2 = max(0.0, min(1.0, 1.0 - (ss_res / ss_tot))) if ss_tot > 1e-9 else 1.0
        rmse = math.sqrt(ss_res / n)

        return qi, di, b, r2, rmse

    @classmethod
    def analyze_decline(
        cls,
        history: List[ProductionRatePoint],
        model_type: str = "EXPONENTIAL",
        forecast_horizon_days: Optional[float] = None,
        economic_limit_rate_stbd: Optional[float] = None,
        well_code: Optional[str] = None
    ) -> EngineeringResult:
        """
        Executes Arps decline analysis on production rate time series.
        Fits model parameters, computes statistical fit, generates forecast, and estimates EUR.
        """
        inputs = {
            "well_code": well_code,
            "model_type": model_type,
            "points_count": len(history) if history else 0,
            "forecast_horizon_days": forecast_horizon_days,
            "economic_limit_rate_stbd": economic_limit_rate_stbd
        }
        model_upper = model_type.upper()

        # 1. Validation of inputs
        if not history or len(history) < 3:
            return EngineeringResult(
                calculation_name="Decline Curve Analysis",
                model="Arps Decline Curve Analysis",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "At least 3 valid chronological production rate observations are required for decline analysis."}
            )

        # Check for invalid non-positive rates
        invalid_pts = [p for p in history if p.rate_stbd <= 0]
        if invalid_pts:
            return EngineeringResult(
                calculation_name="Decline Curve Analysis",
                model="Arps Decline Curve Analysis",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={"error": f"Found {len(invalid_pts)} production records with non-positive flow rates."}
            )

        # 2. Parameter Fitting
        try:
            qi, di, b, r2, rmse = cls.fit_decline_parameters(history, model_type)
        except Exception as e:
            return EngineeringResult(
                calculation_name="Decline Curve Analysis",
                model="Arps Decline Curve Analysis",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={"error": f"Parameter fitting failed: {str(e)}"}
            )

        di_nominal_pct_year = (1.0 - math.exp(-di * 365.25)) * 100.0 if b == 0 else (di * 365.25 * 100.0)

        # 3. Forecast Generation
        forecast_series = []
        sorted_history = sorted(history, key=lambda x: x.timestamp)
        t0 = sorted_history[0].timestamp
        t_history_end = (sorted_history[-1].timestamp - t0).total_seconds() / 86400.0

        if forecast_horizon_days and forecast_horizon_days > 0:
            num_forecast_steps = 12
            step_days = forecast_horizon_days / num_forecast_steps
            for step in range(1, num_forecast_steps + 1):
                t_f = t_history_end + step * step_days
                q_f = cls.calculate_rate(qi, di, b, t_f)
                f_date = sorted_history[-1].timestamp + timedelta(days=step * step_days)
                forecast_series.append({
                    "timestamp": f_date.isoformat(),
                    "forecast_day": round(t_f, 1),
                    "forecast_rate_stbd": round(q_f, 2)
                })

        # 4. EUR Evaluation (ONLY when economic limit is explicitly configured)
        eur_stb = None
        remaining_reserves_stb = None
        eur_evidence = {}

        if economic_limit_rate_stbd is not None:
            if economic_limit_rate_stbd <= 0:
                return EngineeringResult(
                    calculation_name="Decline Curve Analysis",
                    model="Arps Decline Curve Analysis",
                    status=EngineeringStatus.INVALID_INPUT.value,
                    inputs=inputs,
                    evidence={"error": "Configured economic limit rate must be strictly positive."}
                )
            if economic_limit_rate_stbd >= qi:
                eur_stb = 0.0
                remaining_reserves_stb = 0.0
                eur_evidence = {"note": "Current rate is already at or below the economic limit."}
            else:
                total_ultimate_np = cls.calculate_cumulative(qi, di, b, economic_limit_rate_stbd)
                # Historical cumulative up to current day
                current_rate = sorted_history[-1].rate_stbd
                hist_np = cls.calculate_cumulative(qi, di, b, current_rate)
                remaining_reserves_stb = max(0.0, total_ultimate_np - hist_np)
                eur_stb = total_ultimate_np
                eur_evidence = {
                    "economic_limit_rate_stbd": economic_limit_rate_stbd,
                    "estimated_eur_stb": round(eur_stb, 2),
                    "estimated_remaining_stb": round(remaining_reserves_stb, 2)
                }
        else:
            eur_evidence = {"note": "EUR not evaluated: Economic limit rate was not configured. Platform policy forbids inventing an economic limit."}

        return EngineeringResult(
            calculation_name="Arps Decline Curve Analysis",
            value={
                "qi_stbd": round(qi, 2),
                "di_per_day": round(di, 6),
                "di_nominal_pct_year": round(di_nominal_pct_year, 2),
                "b_exponent": round(b, 3),
                "r_squared": round(r2, 4),
                "rmse_stbd": round(rmse, 2),
                "eur_stb": round(eur_stb, 2) if eur_stb is not None else None,
                "remaining_reserves_stb": round(remaining_reserves_stb, 2) if remaining_reserves_stb is not None else None
            },
            unit="STB/D",
            model=f"Arps (1945) {model_upper.capitalize()} Decline",
            correlation="Arps, J.J. (1945)",
            correlation_reference="Arps, J.J. (1945), 'Analysis of Decline Curves', Trans. AIME, 160, 228-247",
            inputs=inputs,
            assumptions=[
                "Constant operating conditions (choke, separator pressure, artificial lift)",
                "Boundary-dominated flow regime (depletion drive)",
                "Constant drainage area without inter-well interference"
            ],
            limitations=[
                "Arps empirical decline models are valid only after boundary-dominated flow is established.",
                "Hyperbolic decline with b > 1 indicates transient or multi-fractured horizontal flow and must not be extrapolated unconstrained.",
                "EUR forecasts require an explicitly verified operational/economic abandonment rate."
            ],
            evidence={
                "fit_statistics": {
                    "r_squared": round(r2, 4),
                    "rmse_stbd": round(rmse, 2),
                    "points_used": len(history)
                },
                "eur_evaluation": eur_evidence,
                "forecast_series": forecast_series
            },
            status=EngineeringStatus.VALID.value
        )


# Canonical aliases
DeclineCurveEngine = DeclineEngine

