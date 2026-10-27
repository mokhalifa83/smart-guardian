from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class EngineeringStatus(str, Enum):
    VALID = "VALID"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    OUT_OF_RANGE = "OUT_OF_RANGE"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"
    INVALID_INPUT = "INVALID_INPUT"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    CALIBRATION_REQUIRED = "CALIBRATION_REQUIRED"
    MODEL_NOT_VALIDATED = "MODEL_NOT_VALIDATED"
    UNDEFINED_WOR = "UNDEFINED_WOR"
    ZERO_DRAWDOWN = "ZERO_DRAWDOWN"
    UNDEFINED_VRR = "UNDEFINED_VRR"
    CORRELATION_SPECIFICATION_REQUIRED = "CORRELATION_SPECIFICATION_REQUIRED"
    NOT_CONFIGURED = "NOT_CONFIGURED"


class EngineeringResult(BaseModel):
    """
    Standard Canonical Engineering Result Contract.
    Mandatory for all Smart Guardian Reservoir Engineering Engines.
    Preserves value, unit, inputs, model, assumptions, limitations,
    evidence, status, provenance, and validity boundaries.
    """
    calculation_name: Optional[str] = None
    value: Optional[Any] = None
    unit: Optional[str] = None
    inputs: Dict[str, Any] = Field(default_factory=dict)
    model: str
    assumptions: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    evidence: Dict[str, Any] = Field(default_factory=dict)
    status: str = EngineeringStatus.VALID.value
    provenance: Dict[str, Any] = Field(default_factory=dict)
    validity_range: Optional[Dict[str, Any]] = None
    correlation: Optional[str] = None
    correlation_reference: Optional[str] = None
    calculation_timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    source_data_timestamp: Optional[datetime] = None
    input_quality: Optional[str] = None
    applicability: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    data_quality: Optional[str] = None
    source: Optional[str] = None
    timestamp: Optional[datetime] = None

    # Advisory Diagnostic Interpretation Fields
    observed_pattern: Optional[str] = None
    diagnostic_interpretation: Optional[str] = None
    potential_root_causes: List[str] = Field(default_factory=list)
    supporting_evidence: List[str] = Field(default_factory=list)
    conflicting_evidence: List[str] = Field(default_factory=list)
    required_confirmation: List[str] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
