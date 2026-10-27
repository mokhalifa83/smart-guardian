"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C
Unified Engineering Evidence Model (evidence_model.py)

MANDATORY CANONICAL DIAGNOSTIC FLOW (Order 3, Section 10):
Calculation
  ↓
Indicator
  ↓
Observed Pattern
  ↓
Evidence
  ↓
Diagnostic Interpretation
  ↓
Potential Root Causes (Potential root cause != Confirmed root cause)
  ↓
Conflicting Evidence
  ↓
Required Confirmation (Logs, surveys, tests needed for confirmation)
  ↓
Decision Support (Advisory engineering recommendations - strictly non-autonomous)
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class UnifiedEngineeringEvidence(BaseModel):
    """
    Unified evidence container enforcing the complete Smart Guardian diagnostic chain.
    Standardized across all reservoir engineering disciplines.
    """
    discipline: str = Field(..., description="Engineering discipline (e.g., RESERVES, GAS_RESERVOIR, CHAN, WATERFLOOD, MATERIAL_BALANCE)")
    well_or_entity_id: str = Field(..., description="Well code, reservoir name, or pattern identifier")
    calculation: Dict[str, Any] = Field(..., description="Calculated metric name, numerical value, and engineering units")
    indicator: str = Field(..., description="Identified physical behavior indicator (e.g., WOR_DERIVATIVE_UPWARD, VRR_DEFICIT, WATER_DRIVE_CURVATURE)")
    observed_pattern: str = Field(..., description="Descriptive classification of pattern observed in field/historical data")
    evidence: Dict[str, Any] = Field(default_factory=dict, description="Structured quantitative facts and diagnostic parameters")
    diagnostic_interpretation: str = Field(..., description="Engineering diagnostic hypothesis based on current evidence")
    potential_root_causes: List[str] = Field(default_factory=list, description="Plausible physical root causes (NEVER presented as confirmed facts)")
    conflicting_evidence: List[str] = Field(default_factory=list, description="Observed facts or indicators that contradict the primary hypothesis")
    required_confirmation: List[str] = Field(default_factory=list, description="Specific field measurements, surveillance, or logs required for confirmation")
    decision_support: List[str] = Field(default_factory=list, description="Advisory, prioritized engineering surveillance recommendations")
    assumptions: List[str] = Field(default_factory=list, description="Explicit modeling assumptions")
    limitations: List[str] = Field(default_factory=list, description="Known analytical or physical boundaries")
    provenance: Dict[str, Any] = Field(default_factory=dict, description="Provenance tracking source, algorithm, and execution timestamp")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    model_config = ConfigDict(from_attributes=True)


class EvidenceChainBuilder:
    """
    Utility builder for standardizing EngineeringResult conversion into UnifiedEngineeringEvidence.
    Guarantees that potential root causes are never stated as confirmed facts without explicit confirmation.
    """

    @staticmethod
    def build_from_engineering_result(
        result: EngineeringResult,
        discipline: str,
        well_or_entity_id: str,
        indicator: str,
        decision_support: Optional[List[str]] = None
    ) -> UnifiedEngineeringEvidence:
        """Constructs a validated UnifiedEngineeringEvidence from an EngineeringResult."""
        calc_payload = {
            "name": result.calculation_name or result.model,
            "value": result.value,
            "unit": result.unit,
            "status": result.status
        }

        # Guard: explicitly ensure potential root cause is marked as potential
        validated_potential_causes = [
            cause if cause.startswith("POTENTIAL:") or cause.startswith("Potential") else f"POTENTIAL: {cause}"
            for cause in result.potential_root_causes
        ]

        # Guard: ensure confirmation requirements are listed if hypotheses exist
        required_conf = list(result.required_confirmation)
        if validated_potential_causes and not required_conf:
            required_conf.append("Acquire high-resolution production logging (PLT), pulsed-neutron log (RST), or pressure survey to confirm hypothesis.")

        return UnifiedEngineeringEvidence(
            discipline=discipline,
            well_or_entity_id=well_or_entity_id,
            calculation=calc_payload,
            indicator=indicator,
            observed_pattern=result.observed_pattern or "STANDARD_ANALYSIS_PATTERN",
            evidence=result.evidence,
            diagnostic_interpretation=result.diagnostic_interpretation or "Engineering calculation completed within standard criteria.",
            potential_root_causes=validated_potential_causes,
            conflicting_evidence=result.conflicting_evidence,
            required_confirmation=required_conf,
            decision_support=decision_support or [
                "Review field operational parameters and verify sensor calibration.",
                "Maintain real-time surveillance of rates, pressures, and water cut."
            ],
            assumptions=result.assumptions,
            limitations=result.limitations,
            provenance=result.provenance or {
                "source": "Smart Guardian Evidence Framework",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
