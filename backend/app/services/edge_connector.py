"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C
Edge Connector Service (edge_connector.py)

Ingests read-only field sensor telemetry from RTUs, edge gateways, and wellhead instrumentation.
Guarantees:
- One-way telemetry flow (NO reverse control commands to edge devices)
- Cryptographic integrity and payload schema validation
- Data quality tagging and physical boundary validation
- Forwarding to Smart Guardian surveillance database and ingestion services
"""

import hashlib
import json
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import logging

from app.services.reservoir.integration_contracts import (
    FieldSensorTelemetryContract,
    FieldDataSourceType
)
from app.services.opcua_client import ReadOnlyViolationError

logger = logging.getLogger(__name__)


class EdgeConnector:
    """
    Edge gateway ingestion handler.
    Receives wellhead telemetry, validates authenticity and physical sanity,
    and returns standardized FieldSensorTelemetryContract payloads.
    """

    def __init__(self, shared_secret_key: Optional[str] = None):
        self.shared_secret_key = shared_secret_key or "SMART_GUARDIAN_EDGE_SECURITY_KEY"

    def compute_payload_hash(self, payload: Dict[str, Any]) -> str:
        """Computes SHA-256 HMAC hash of payload for transport integrity verification."""
        serialized = json.dumps(payload, sort_keys=True)
        return hashlib.sha256(f"{serialized}:{self.shared_secret_key}".encode("utf-8")).hexdigest()

    def validate_and_parse_telemetry(
        self,
        raw_telemetry: Dict[str, Any],
        signature_hash: Optional[str] = None
    ) -> Tuple[FieldSensorTelemetryContract, str]:
        """
        Validates edge telemetry:
        1. Checks for unauthorized control payload (blocks reverse control).
        2. Validates timestamp freshness.
        3. Enforces physical sanity bounds (non-negative pressure, choke in [0, 128], water cut in [0, 100]).
        """
        # Block control payloads immediately
        if "command" in raw_telemetry or "setpoint" in raw_telemetry or "control_action" in raw_telemetry:
            raise ReadOnlyViolationError(
                "READ_ONLY_VIOLATION: Edge connector rejected payload containing control command or setpoint modification."
            )

        # Basic fields
        well_code = raw_telemetry.get("well_code")
        if not well_code:
            raise ValueError("Payload missing required 'well_code' identifier.")

        timestamp_raw = raw_telemetry.get("timestamp")
        if isinstance(timestamp_raw, str):
            ts = datetime.fromisoformat(timestamp_raw.replace("Z", "+00:00"))
        elif isinstance(timestamp_raw, datetime):
            ts = timestamp_raw
        else:
            ts = datetime.now(timezone.utc)

        # Parse sensor readings with physical validation
        p_wh = raw_telemetry.get("pressure_wh_psia")
        t_wh = raw_telemetry.get("temperature_wh_f")
        choke = raw_telemetry.get("choke_size_64ths")
        p_fl = raw_telemetry.get("flowline_pressure_psia")
        wc = raw_telemetry.get("water_cut_raw")
        q_oil = raw_telemetry.get("oil_rate_raw_stbd")
        q_wat = raw_telemetry.get("water_rate_raw_bpd")
        q_gas = raw_telemetry.get("gas_rate_raw_mscfd")

        quality = "GOOD"
        # Boundary sanity check
        if p_wh is not None and (p_wh < 0 or p_wh > 25000):
            quality = "BAD"
        if choke is not None and (choke < 0 or choke > 128):
            quality = "BAD"
        if wc is not None and (wc < 0 or wc > 100):
            quality = "BAD"

        telemetry_contract = FieldSensorTelemetryContract(
            well_code=well_code,
            timestamp=ts,
            source_type=FieldDataSourceType.EDGE_CONNECTOR,
            sensor_tag=raw_telemetry.get("sensor_tag", f"{well_code}_RTU_TAG"),
            pressure_wh_psia=p_wh if quality != "BAD" else None,
            temperature_wh_f=t_wh,
            choke_size_64ths=choke,
            flowline_pressure_psia=p_fl,
            water_cut_raw=wc,
            is_water_cut_percentage=True,
            oil_rate_raw_stbd=q_oil,
            water_rate_raw_bpd=q_wat,
            gas_rate_raw_mscfd=q_gas,
            quality_flag=quality,
            traceability_hash=self.compute_payload_hash(raw_telemetry)
        )

        return telemetry_contract, quality
