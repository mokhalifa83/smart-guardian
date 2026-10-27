"""
Test Suite for Step 2C Unified Engineering Evidence Model (test_reservoir_evidence_model.py)
Validates:
1. Strict canonical diagnostic sequence: Calculation -> Indicator -> Evidence -> Interpretation -> Root Causes -> Confirmation -> Decision Support
2. Potential root cause != Confirmed root cause enforcement
3. Required confirmation generation
"""

import pytest
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.evidence_model import UnifiedEngineeringEvidence, EvidenceChainBuilder


def test_unified_evidence_model_structure():
    evidence = UnifiedEngineeringEvidence(
        discipline="WATER_DIAGNOSTICS",
        well_or_entity_id="WELL-01",
        calculation={"name": "WOR_DERIVATIVE", "value": 1.25, "unit": "dimensionless"},
        indicator="WOR_DERIVATIVE_UPWARD_SLOPE",
        observed_pattern="CHAN_CONING_CHARACTERISTIC",
        evidence={"wor_slope": 1.25, "critical_rate_stbd": 850.0},
        diagnostic_interpretation="Water-oil ratio derivative exhibits late-time upward departure.",
        potential_root_causes=["POTENTIAL: Bottom water coning", "POTENTIAL: Channelling behind casing"],
        conflicting_evidence=["Static pressure build-up shows uniform depletion without gas cap expansion."],
        required_confirmation=["Run pulsed-neutron RST log across perforations."],
        decision_support=["Throttle choke by 15% to evaluate rate-sensitivity of water cut."],
        assumptions=["Radial flow geometry", "Constant mobilities"],
        limitations=["WOR derivative requires stabilized test separator rate measurements."],
        provenance={"engine": "ChanDiagnosticsEngine", "version": "Step2C-v1.2"}
    )

    assert evidence.discipline == "WATER_DIAGNOSTICS"
    assert evidence.well_or_entity_id == "WELL-01"
    assert len(evidence.potential_root_causes) == 2
    assert all("POTENTIAL" in c for c in evidence.potential_root_causes)
    assert len(evidence.required_confirmation) == 1
    assert len(evidence.decision_support) == 1


def test_evidence_chain_builder_enforces_potential_prefix_and_confirmation():
    raw_result = EngineeringResult(
        model="Chan Diagnostics",
        calculation_name="WOR_DERIVATIVE_SLOPE",
        value=0.85,
        unit="1/day",
        observed_pattern="WATER_CONING_TREND",
        diagnostic_interpretation="Water cut rising rapidly with cumulative oil production.",
        potential_root_causes=["Bottom-water coning across basal perforations"],  # Not prefixed
        required_confirmation=[],  # Empty
        status=EngineeringStatus.VALID.value
    )

    unified = EvidenceChainBuilder.build_from_engineering_result(
        result=raw_result,
        discipline="WATER_DIAGNOSTICS",
        well_or_entity_id="WELL-102",
        indicator="WOR_DERIVATIVE_INFLECTION"
    )

    # Verify builder prefixed POTENTIAL:
    assert len(unified.potential_root_causes) == 1
    assert unified.potential_root_causes[0].startswith("POTENTIAL:")

    # Verify builder automatically added confirmation requirement
    assert len(unified.required_confirmation) >= 1
    assert any("log" in req.lower() or "survey" in req.lower() for req in unified.required_confirmation)
