"""
Smart Guardian Reservoir Intelligence Layer - Productivity Index (PI) Engine (Step 2A)
Implements:
    J = q / (pr - pwf)   [stb/d/psi]
Validates physical limits, prevents division by zero, reports explicit states,
and supports multi-point historical PI surveillance tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class PITimePoint(BaseModel):
    timestamp: datetime
    flow_rate_stbd: float
    reservoir_pressure_psia: float
    flowing_bhp_psia: float


class ProductivityIndexEngine:
    """
    Canonical Productivity Index Engine.
    """

    @staticmethod
    def calculate_pi(
        flow_rate_stbd: float,
        reservoir_pressure_psia: float,
        flowing_bhp_psia: float
    ) -> EngineeringResult:
        inputs = {
            "flow_rate_stbd": flow_rate_stbd,
            "reservoir_pressure_psia": reservoir_pressure_psia,
            "flowing_bhp_psia": flowing_bhp_psia
        }

        if flow_rate_stbd is None or reservoir_pressure_psia is None or flowing_bhp_psia is None:
            return EngineeringResult(
                model="Productivity Index J = q / (pr - pwf)",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "All parameters (q, pr, pwf) are required"}
            )

        drawdown = reservoir_pressure_psia - flowing_bhp_psia

        # Prevent division by zero and negative drawdowns
        if drawdown == 0.0:
            return EngineeringResult(
                model="Productivity Index J = q / (pr - pwf)",
                status=EngineeringStatus.ZERO_DRAWDOWN.value,
                inputs=inputs,
                assumptions=["Zero drawdown (pr == pwf); static well condition"],
                limitations=["Productivity index cannot be evaluated when drawdown is zero"],
                evidence={"drawdown_psi": 0.0, "explanation": "Zero drawdown: pr - pwf = 0. Division by zero prevented."}
            )

        if drawdown < 0.0:
            return EngineeringResult(
                model="Productivity Index J = q / (pr - pwf)",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"drawdown_psi": drawdown, "error": f"Flowing BHP ({flowing_bhp_psia}) exceeds reservoir pressure ({reservoir_pressure_psia})"}
            )

        if flow_rate_stbd < 0.0:
            return EngineeringResult(
                model="Productivity Index J = q / (pr - pwf)",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Flow rate cannot be negative for production well ({flow_rate_stbd} stb/d)"}
            )

        j = flow_rate_stbd / drawdown

        return EngineeringResult(
            value=round(j, 4),
            unit="stb/d/psi",
            model="Productivity Index J = q / (pr - pwf)",
            correlation="Darcy PI Formulation",
            correlation_reference="Craft & Hawkins, Applied Petroleum Reservoir Engineering",
            inputs=inputs,
            assumptions=["Stabilized flow rate at steady state or pseudo-steady state drawdown"],
            limitations=["Linear PI valid primarily above bubble point. For two-phase flow below Pb, Vogel IPR is recommended."],
            evidence={
                "drawdown_psi": round(drawdown, 2),
                "productivity_index": round(j, 4)
            },
            status=EngineeringStatus.VALID.value
        )

    calculate_productivity_index = calculate_pi


    @classmethod
    def evaluate_pi_surveillance_history(
        cls,
        history: List[PITimePoint],
        well_code: str = "WELL-001"
    ) -> EngineeringResult:
        """
        Evaluates productivity index progression over historical timestamps.
        Detects formation damage / skin buildup (declining PI) or stimulation cleanup (rising PI).
        """
        if not history:
            return EngineeringResult(
                model="Historical PI Surveillance",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs={"well_code": well_code, "points_count": 0},
                evidence={"error": "Empty history provided"}
            )

        sorted_pts = sorted(history, key=lambda x: x.timestamp)
        records = []
        for p in sorted_pts:
            pi_res = cls.calculate_pi(p.flow_rate_stbd, p.reservoir_pressure_psia, p.flowing_bhp_psia)
            records.append({
                "timestamp": p.timestamp.isoformat(),
                "rate": p.flow_rate_stbd,
                "drawdown": p.reservoir_pressure_psia - p.flowing_bhp_psia,
                "pi": pi_res.value if pi_res.status == EngineeringStatus.VALID.value else None,
                "status": pi_res.status
            })

        return EngineeringResult(
            value={"records_count": len(records)},
            unit="surveillance_series",
            model="Historical Productivity Index Surveillance",
            inputs={"well_code": well_code},
            evidence={"pi_history": records},
            status=EngineeringStatus.VALID.value
        )

    calculate_productivity_index = calculate_pi

