"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C Field-Integration Contracts (Step 2B)
Defines stable service contracts, data interfaces, and configuration schemas required
for future STEP 2C field systems integration (Control Room SCADA, OPC UA, Edge Connectors, InfluxDB).

CRITICAL ARCHITECTURAL SAFETY RULE (Section 32):
- STEP 2B does NOT instantiate live network connections to OPC UA, SCADA, DCS, or InfluxDB.
- STEP 2B does NOT deliver emails, WhatsApp alerts, or automated daily PDFs.
- These interfaces establish the typed boundaries that STEP 2C will implement.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class FieldDataSourceType(str, Enum):
    OPC_UA_READ_ONLY = "OPC_UA_READ_ONLY"
    SCADA_HISTORIAN = "SCADA_HISTORIAN"
    EDGE_CONNECTOR = "EDGE_CONNECTOR"
    INFLUXDB_TIMESERIES = "INFLUXDB_TIMESERIES"
    REST_TELEMETRY = "REST_TELEMETRY"
    MANUAL_OPERATOR = "MANUAL_OPERATOR"


class FieldSensorTelemetryContract(BaseModel):
    """Standardized schema for incoming real-time telemetry from external field systems."""
    well_code: str = Field(..., description="Unique field well identifier")
    timestamp: datetime = Field(..., description="Observation timestamp in UTC")
    source_type: FieldDataSourceType = Field(default=FieldDataSourceType.REST_TELEMETRY)
    sensor_tag: Optional[str] = None
    pressure_wh_psia: Optional[float] = Field(default=None, ge=0)
    temperature_wh_f: Optional[float] = Field(default=None)
    choke_size_64ths: Optional[float] = Field(default=None, ge=0)
    flowline_pressure_psia: Optional[float] = Field(default=None, ge=0)
    water_cut_raw: Optional[float] = Field(default=None, ge=0)
    is_water_cut_percentage: bool = True
    oil_rate_raw_stbd: Optional[float] = Field(default=None, ge=0)
    water_rate_raw_bpd: Optional[float] = Field(default=None, ge=0)
    gas_rate_raw_mscfd: Optional[float] = Field(default=None, ge=0)
    quality_flag: str = Field(default="GOOD", description="Field telemetry quality flag (GOOD, BAD, UNCERTAIN)")
    traceability_hash: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class Step2CConnectorReadiness(BaseModel):
    """Interface declaring readiness status for future STEP 2C field integration connectors."""
    connector_name: str
    target_system: str
    is_live_connection_active: bool = False  # Strictly False in Step 2B
    contract_version: str = "2.0-CONTRACT_READY"
    security_isolation: str = "READ_ONLY_BARRIER_ENFORCED"
    supported_protocols: List[str] = Field(default_factory=list)
    configuration_schema_defined: bool = True
    implementation_phase: str = "STEP_2C_PENDING_APPROVAL"

    model_config = ConfigDict(from_attributes=True)


class Step2CIntegrationRegistry:
    """
    Registry of field integration contracts for Smart Guardian.
    Exposes connector readiness without initiating live socket/network connections.
    """

    @classmethod
    def get_connector_contracts(cls) -> List[Step2CConnectorReadiness]:
        return [
            Step2CConnectorReadiness(
                connector_name="OPC_UA_SURVEILLANCE_CONNECTOR",
                target_system="Control Room DCS / SCADA (Yokogawa, Siemens, Wonderware)",
                is_live_connection_active=False,
                supported_protocols=["opc.tcp", "https"],
                security_isolation="STRICTLY_READ_ONLY_NO_CONTROL_COMMANDS"
            ),
            Step2CConnectorReadiness(
                connector_name="EDGE_TELEMETRY_CONNECTOR",
                target_system="Wellhead Edge RTU / Gateway",
                is_live_connection_active=False,
                supported_protocols=["MQTT", "HTTPS_REST"],
                security_isolation="ONE_WAY_TELEMETRY_INGESTION"
            ),
            Step2CConnectorReadiness(
                connector_name="TIMESERIES_HISTORIAN_CONNECTOR",
                target_system="InfluxDB / TimescaleDB Enterprise",
                is_live_connection_active=False,
                supported_protocols=["LineProtocol", "PostgreSQL_Wire"],
                security_isolation="APPEND_ONLY_TIMESERIES"
            )
        ]
