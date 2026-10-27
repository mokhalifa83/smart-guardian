"""
Smart Guardian Reservoir Intelligence Layer - Vogel IPR Engine (Step 2A)
Reference: Vogel, J.V. (1968), "Inflow Performance Relationships for Solution-Gas Drive Wells",
Journal of Petroleum Technology, 20(1), 83-92.

Implements:
1. Canonical dimensionless Vogel IPR:
       q / qmax = 1 - 0.2 * (pwf / pr) - 0.8 * (pwf / pr)^2
2. qmax estimation from a validated production test point (qt, pwft):
       qmax = qt / [1 - 0.2 * (pwft / pr) - 0.8 * (pwft / pr)^2]
3. Full IPR curve coordinate generation for inflow-outflow nodal analysis.
4. Distinguishes measured q, calculated q, and estimated qmax.
"""

from typing import Optional, List, Dict, Any
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class VogelIPREngine:
    """
    Canonical Inflow Performance Relationship (IPR) Engine for Solution-Gas Drive Reservoirs.
    """

    @staticmethod
    def calculate_flow_rate_from_qmax(
        qmax_stbd: float,
        reservoir_pressure_psia: float,
        flowing_bhp_psia: float
    ) -> EngineeringResult:
        inputs = {
            "qmax_stbd": qmax_stbd,
            "reservoir_pressure_psia": reservoir_pressure_psia,
            "flowing_bhp_psia": flowing_bhp_psia
        }

        # 1. Physical validation
        if reservoir_pressure_psia <= 0.0:
            return EngineeringResult(
                model="Vogel (1968) IPR",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Reservoir pressure must be strictly positive (got {reservoir_pressure_psia} psia)"}
            )

        if flowing_bhp_psia < 0.0 or flowing_bhp_psia > reservoir_pressure_psia:
            return EngineeringResult(
                model="Vogel (1968) IPR",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Flowing BHP ({flowing_bhp_psia} psia) must be within [0, pr ({reservoir_pressure_psia} psia)]"}
            )

        if qmax_stbd <= 0.0:
            return EngineeringResult(
                model="Vogel (1968) IPR",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Maximum theoretical open-flow rate (qmax) must be strictly positive (got {qmax_stbd})"}
            )

        # Dimensionless pressure ratio
        p_ratio = flowing_bhp_psia / reservoir_pressure_psia
        dim_rate = 1.0 - 0.2 * p_ratio - 0.8 * (p_ratio ** 2)
        q = qmax_stbd * dim_rate

        return EngineeringResult(
            value=round(q, 2),
            unit="stb/d",
            model="Vogel (1968) Inflow Performance Relationship",
            correlation="Vogel (1968)",
            correlation_reference="Vogel, J.V. (1968), JPT, 20(1), 83-92, Trans. AIME, 243",
            inputs=inputs,
            assumptions=[
                "Solution-gas drive reservoir producing below bubble point pressure",
                "Two-phase gas-oil flow in the reservoir porous medium",
                "Skin factor s = 0 (undamaged wellbore baseline)"
            ],
            limitations=[
                "Applicable to saturated two-phase reservoirs (P <= Pb). For undersaturated reservoirs with Pwf > Pb, composite Vogel is required."
            ],
            evidence={
                "pwf_pr_ratio": round(p_ratio, 4),
                "dimensionless_flow_ratio_q_qmax": round(dim_rate, 4),
                "calculated_q_stbd": round(q, 2)
            },
            status=EngineeringStatus.VALID.value
        )

    @staticmethod
    def estimate_qmax_from_test(
        test_rate_stbd: float,
        test_flowing_bhp_psia: float,
        reservoir_pressure_psia: float
    ) -> EngineeringResult:
        inputs = {
            "test_rate_stbd": test_rate_stbd,
            "test_flowing_bhp_psia": test_flowing_bhp_psia,
            "reservoir_pressure_psia": reservoir_pressure_psia
        }

        # Validate physics
        if reservoir_pressure_psia <= 0.0:
            return EngineeringResult(
                model="Vogel (1968) qmax Estimation",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Reservoir pressure pr must be strictly positive"}
            )

        if test_flowing_bhp_psia < 0.0 or test_flowing_bhp_psia >= reservoir_pressure_psia:
            return EngineeringResult(
                model="Vogel (1968) qmax Estimation",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Test flowing BHP ({test_flowing_bhp_psia}) must be strictly less than reservoir pressure ({reservoir_pressure_psia}) and >= 0"}
            )

        if test_rate_stbd <= 0.0:
            return EngineeringResult(
                model="Vogel (1968) qmax Estimation",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Test rate must be positive (got {test_rate_stbd})"}
            )

        p_ratio = test_flowing_bhp_psia / reservoir_pressure_psia
        denominator = 1.0 - 0.2 * p_ratio - 0.8 * (p_ratio ** 2)

        if denominator <= 0.0:
            return EngineeringResult(
                model="Vogel (1968) qmax Estimation",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Vogel polynomial denominator evaluated to non-positive"}
            )

        qmax = test_rate_stbd / denominator

        return EngineeringResult(
            value=round(qmax, 2),
            unit="stb/d",
            model="Vogel (1968) Maximum Flow Capacity (qmax)",
            correlation="Vogel (1968)",
            correlation_reference="Vogel, J.V. (1968), JPT, 20(1), 83-92",
            inputs=inputs,
            assumptions=["Measured test point represents stabilized pseudo-steady state reservoir conditions"],
            limitations=["Estimate sensitive to test BHP accuracy. High skin creates apparent qmax reduction."],
            evidence={
                "measured_test_rate_stbd": test_rate_stbd,
                "measured_test_bhp_psia": test_flowing_bhp_psia,
                "estimated_qmax_stbd": round(qmax, 2),
                "pwf_pr_ratio": round(p_ratio, 4)
            },
            status=EngineeringStatus.VALID.value
        )

    @classmethod
    def generate_ipr_curve(
        cls,
        qmax_stbd: float,
        reservoir_pressure_psia: float,
        num_points: int = 11
    ) -> EngineeringResult:
        """
        Generates full canonical IPR curve coordinates (Pwf vs q) from Pwf = pr down to Pwf = 0.
        """
        if qmax_stbd <= 0 or reservoir_pressure_psia <= 0:
            return EngineeringResult(
                model="Vogel IPR Curve Generation",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs={"qmax_stbd": qmax_stbd, "pr_psia": reservoir_pressure_psia},
                evidence={"error": "qmax and pr must be strictly positive"}
            )

        points = []
        dp = reservoir_pressure_psia / (num_points - 1)
        for i in range(num_points):
            pwf = round(reservoir_pressure_psia - i * dp, 1)
            pwf = max(0.0, pwf)
            q_res = cls.calculate_flow_rate_from_qmax(qmax_stbd, reservoir_pressure_psia, pwf)
            points.append({
                "pwf_psia": pwf,
                "flow_rate_stbd": q_res.value
            })

        return EngineeringResult(
            value=points,
            unit="ipr_coordinates",
            model="Vogel (1968) IPR Curve",
            correlation="Vogel (1968)",
            correlation_reference="Vogel, J.V. (1968), JPT, 20(1), 83-92",
            inputs={"qmax_stbd": qmax_stbd, "reservoir_pressure_psia": reservoir_pressure_psia},
            evidence={"points_count": len(points), "coordinates": points},
            status=EngineeringStatus.VALID.value
        )
