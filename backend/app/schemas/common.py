from enum import Enum
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DataQualityStatus(str, Enum):
    VALID = "VALID"
    INVALID = "INVALID"
    STALE = "STALE"
    MISSING = "MISSING"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class SourceCategory(str, Enum):
    MANUAL = "MANUAL"
    SOFTWARE_API = "SOFTWARE_API"
    MQTT = "MQTT"
    CALCULATED = "CALCULATED"
    DERIVED = "DERIVED"


class ValueType(str, Enum):
    MEASURED = "MEASURED"
    CALCULATED = "CALCULATED"
    DERIVED = "DERIVED"


class AlertSeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class AlertStatus(str, Enum):
    ACTIVE = "ACTIVE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class SurveillanceState(str, Enum):
    NORMAL = "NORMAL"
    WARNING = "WARNING"
    DATA_UNAVAILABLE = "DATA_UNAVAILABLE"


class MeasurementType(str, Enum):
    WATER_CUT = "WATER_CUT"
    SEPARATOR_PRESSURE = "SEPARATOR_PRESSURE"
    FLOW_RATE = "FLOW_RATE"
    OIL_RATE = "OIL_RATE"
    WATER_RATE = "WATER_RATE"
    GAS_RATE = "GAS_RATE"
    OIL_API_GRAVITY = "OIL_API_GRAVITY"
    MANUAL_WATER_CUT = "MANUAL_WATER_CUT"
    MANUAL_PRESSURE = "MANUAL_PRESSURE"


class ProvenanceRecord(BaseModel):
    """
    Standard data contract making provenance, timestamps, source, and quality status visible.
    """
    well_code: str
    value: Optional[float] = None
    unit: Optional[str] = None
    timestamp: datetime
    received_at: datetime
    source: SourceCategory
    quality_status: DataQualityStatus
    value_type: ValueType
    source_system: Optional[str] = None
    source_record_id: Optional[str] = None
    entered_by: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)
