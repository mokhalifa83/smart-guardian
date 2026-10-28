"""
Smart Guardian Reservoir Intelligence Layer - Engineering Decision Support & Human Governance Engines
=====================================================================================================
Implements:
22. Engineering Decision Support Engine (Actionable Engineering Recommendations)
23. Engineering Options Engine (Intervention Trade-Off Comparison)
30. Decision Support Layer Engine (Multi-Criteria Decision Matrix MCDA)
31. Human Approval Engine (Operational Safety Boundary & Audit Trail Enforcement)
"""

import math
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.physics_guardrails import PhysicsGuardrails


class EngineeringDecisionSupportEngine:
    """
    22. Engineering Decision Support Engine.
    Synthesizes surveillance diagnostic signals into prioritized, actionable interventions.
    """
    ENGINE_NAME = "Engineering Decision Support Engine"
    SPE_REFERENCE = "SPE-112217: Intelligent Well Surveillance and Actionable Decision Workflows"

    @classmethod
    def generate_recommendations(
        cls,
        well_code: str,
        water_cut_pct: Optional[float],
        wc_diagnostic_pattern: Optional[str],
        gor_scf_stb: Optional[float],
        flowing_bhp_psia: Optional[float],
        pump_fillage_pct: Optional[float] = None
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={"water_cut_pct": water_cut_pct},
            calculation_name=cls.ENGINE_NAME,
            model_name="Expert System Petroleum Decision Tree",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        recommendations = []
        priority = "LOW"

        if wc_diagnostic_pattern == "WATER_CONING_RAPID_BREAKTHROUGH":
            recommendations.append("CHOKE_THROTTLING: Reduce choke opening to decrease drawdown below critical coning rate.")
            priority = "HIGH"
        elif wc_diagnostic_pattern == "WATER_CHANNELING_OR_FRACTURE_FLOW":
            recommendations.append("WATER_SHUTOFF_CEMENT_SQUEEZE: Run RST/pulsed-neutron log to isolate high-permeability watered-out thief zone.")
            priority = "HIGH"

        if pump_fillage_pct and pump_fillage_pct < 60.0:
            recommendations.append("ARTIFICIAL_LIFT_OPTIMIZATION: Lower VSD frequency or reduce SPM to prevent pump fluid pound.")
            priority = "CRITICAL"

        if not recommendations:
            recommendations.append("MAINTAIN_CURRENT_SURVEILLANCE: Well is operating within physical baseline envelope.")

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=priority,
            unit="Priority",
            model="Expert System Petroleum Decision Tree",
            status=EngineeringStatus.VALID.value,
            evidence={
                "well_code": well_code,
                "urgency_priority": priority,
                "recommended_actions": recommendations,
                "diagnostics_reviewed": {
                    "water_cut_pct": water_cut_pct,
                    "chan_pattern": wc_diagnostic_pattern,
                    "producing_gor": gor_scf_stb
                }
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class EngineeringOptionsEngine:
    """
    23. Engineering Options Engine.
    Models competing intervention scenarios (e.g., Choke Adjustment vs Gas Lift vs Water Shutoff)
    comparing incremental recovery vs intervention cost.
    """
    ENGINE_NAME = "Engineering Options Engine"
    SPE_REFERENCE = "SPE Decision Risk and Management Committee Best Practices"

    @classmethod
    def compare_scenarios(
        cls,
        current_oil_rate_stbd: float,
        scenarios: List[Dict[str, Any]]
    ) -> EngineeringResult:
        if not scenarios:
            return EngineeringResult(
                calculation_name=cls.ENGINE_NAME,
                value=None,
                model="Comparative Intervention Trade-Off Analysis",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                warnings=["At least one engineering option scenario is required for comparison."]
            )

        evaluated_options = []
        for opt in scenarios:
            name = opt.get("name", "Unnamed Option")
            capex = opt.get("intervention_cost_usd", 0.0)
            gain_bpd = opt.get("expected_gain_bpd", 0.0)
            duration_months = opt.get("benefit_duration_months", 12.0)

            total_incremental_stb = gain_bpd * (duration_months * 30.4)
            # Net revenue assuming $75/bbl netback
            revenue = total_incremental_stb * 75.0
            roi_ratio = (revenue / capex) if capex > 0 else 999.0

            evaluated_options.append({
                "option_name": name,
                "expected_oil_gain_bpd": gain_bpd,
                "intervention_cost_usd": capex,
                "incremental_barrels_stb": round(total_incremental_stb, 0),
                "estimated_roi_ratio": round(roi_ratio, 2)
            })

        evaluated_options.sort(key=lambda x: x["estimated_roi_ratio"], reverse=True)
        recommended = evaluated_options[0]

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=recommended["option_name"],
            model="Comparative Intervention Trade-Off Analysis",
            status=EngineeringStatus.VALID.value,
            evidence={
                "top_ranked_option": recommended["option_name"],
                "ranked_options": evaluated_options
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class DecisionSupportLayerEngine:
    """
    30. Decision Support Layer Engine.
    Multi-Criteria Decision Analysis (MCDA) weighting production gain, reservoir longevity, and safety risk.
    """
    ENGINE_NAME = "Decision Support Layer Engine"
    SPE_REFERENCE = "SPE-146603: Multi-Criteria Decision Analysis in Hydrocarbon Asset Management"

    @classmethod
    def rank_interventions_mcda(
        cls,
        options: List[Dict[str, Any]],
        weight_production: float = 0.50,
        weight_cost: float = 0.30,
        weight_safety: float = 0.20
    ) -> EngineeringResult:
        if not options:
            return EngineeringResult(
                calculation_name=cls.ENGINE_NAME,
                value=None,
                model="MCDA Weighted Petroleum Ranking",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                warnings=["Options list must not be empty."]
            )

        ranked = []
        for opt in options:
            score_prod = opt.get("production_score", 5.0)  # 1 to 10
            score_cost = opt.get("cost_efficiency_score", 5.0) # 1 to 10
            score_safety = opt.get("safety_score", 10.0) # 1 to 10

            composite_score = (
                score_prod * weight_production +
                score_cost * weight_cost +
                score_safety * weight_safety
            )

            ranked.append({
                "action": opt.get("action_name"),
                "composite_score": round(composite_score, 2),
                "details": opt
            })

        ranked.sort(key=lambda x: x["composite_score"], reverse=True)

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=ranked[0]["action"],
            model="MCDA Weighted Petroleum Ranking",
            status=EngineeringStatus.VALID.value,
            evidence={
                "recommended_action": ranked[0]["action"],
                "composite_rankings": ranked
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class HumanApprovalEngine:
    """
    31. Human Approval Engine.
    Operational Safety Barrier Governance.
    Ensures that NO physical field intervention, choke alteration, or supervisory setpoint
    is executed autonomously without explicit human engineering sign-off and audit provenance.
    """
    ENGINE_NAME = "Human Approval Engine"
    SPE_REFERENCE = "ISA-84 / IEC 61511: Functional Safety and Safety Instrumented Systems for Process Industry"

    @classmethod
    def request_or_verify_approval(
        cls,
        action_id: str,
        action_type: str,
        target_well: str,
        proposed_setpoint: Any,
        approver_engineer_name: Optional[str] = None,
        approver_badge: Optional[str] = None,
        operational_justification: Optional[str] = None
    ) -> EngineeringResult:
        is_approved = bool(approver_engineer_name and approver_badge and operational_justification)

        status_text = "APPROVED_READY_FOR_SUPERVISORY_DISPATCH" if is_approved else "PENDING_ENGINEER_APPROVAL"

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=status_text,
            model="Industrial Safety Boundary Human-in-the-Loop Governance",
            status=EngineeringStatus.VALID.value,
            evidence={
                "action_id": action_id,
                "action_type": action_type,
                "target_well": target_well,
                "proposed_setpoint": proposed_setpoint,
                "is_authorized": is_approved,
                "approver_engineer": approver_engineer_name,
                "approver_badge": approver_badge,
                "operational_justification": operational_justification,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "safety_barrier_status": "LOCKED_PREVENTING_AUTONOMOUS_ACTUATION" if not is_approved else "UNLOCKED_WITH_AUDIT_TRAIL"
            },
            correlation_reference=cls.SPE_REFERENCE,
            assumptions=["ISA-99 / IEC 62443 zone segregation prevents autonomous field actuation without engineer sign-off."]
        )
