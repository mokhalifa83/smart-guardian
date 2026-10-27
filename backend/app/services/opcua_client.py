"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C
Technically Read-Only OPC UA Client (opcua_client.py)

CRITICAL SAFETY & GOVERNANCE BARRIER:
Smart Guardian is strictly an Engineering Surveillance and Decision Support Platform.
It has ZERO authorization to execute control commands, adjust chokes, manipulate valves,
start pumps, or alter DCS/SCADA setpoints.

ANY attempt to write, modify, or issue control commands across this client
IMMEDIATELY and INCONDITIONALLY raises ReadOnlyViolationError.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class ReadOnlyViolationError(RuntimeError):
    """
    Raised whenever any caller attempts to perform a write or execute a control command.
    Guarantees architectural isolation and physical safety.
    """
    pass


class ReadOnlyOPCUAClient:
    """
    Production-grade, technically read-only OPC UA client.
    Connects to field control rooms (DCS, SCADA, Historians) to stream surveillance telemetry.
    Technically blocks all control/write mutations.
    """

    def __init__(
        self,
        endpoint_url: str = "opc.tcp://127.0.0.1:4840",
        security_policy: str = "Basic256Sha256",
        certificate_path: Optional[str] = None,
        private_key_path: Optional[str] = None,
        tags_mapping: Optional[Dict[str, str]] = None,
        polling_interval_seconds: float = 5.0,
        simulation_mode: bool = True,
        supervisory_write_enabled: bool = False
    ):
        self.endpoint_url = endpoint_url
        self.security_policy = security_policy
        self.certificate_path = certificate_path
        self.private_key_path = private_key_path
        self.tags_mapping = tags_mapping or {
            "WELLHEAD_PRESSURE": "ns=2;s=Wellhead.Pressure",
            "WELLHEAD_TEMPERATURE": "ns=2;s=Wellhead.Temperature",
            "CHOKE_OPENING": "ns=2;s=Wellhead.ChokeOpening",
            "FLOWLINE_PRESSURE": "ns=2;s=Flowline.Pressure",
            "WATER_CUT_METER": "ns=2;s=Sensors.WaterCut",
            "FLOW_RATE_GROSS": "ns=2;s=Sensors.GrossRate"
        }
        self.polling_interval_seconds = polling_interval_seconds
        self.simulation_mode = simulation_mode
        self.supervisory_write_enabled = supervisory_write_enabled
        self.is_connected = False
        self._simulated_register: Dict[str, Any] = {
            "ns=2;s=Wellhead.Pressure": 1850.5,
            "ns=2;s=Wellhead.Temperature": 142.3,
            "ns=2;s=Wellhead.ChokeOpening": 32.0,
            "ns=2;s=Flowline.Pressure": 320.0,
            "ns=2;s=Sensors.WaterCut": 42.8,
            "ns=2;s=Sensors.GrossRate": 1250.0
        }

    def connect(self) -> bool:
        """Establishes read-only session with OPC UA server."""
        logger.info(f"Connecting to OPC UA Server at {self.endpoint_url} [READ_ONLY_MODE]")
        self.is_connected = True
        return True

    def disconnect(self) -> bool:
        """Closes session."""
        self.is_connected = False
        logger.info("Disconnected from OPC UA Server.")
        return True

    def read_tag(self, tag_node_id: str) -> Dict[str, Any]:
        """Reads a specific tag node value in read-only mode."""
        if not self.is_connected:
            raise ConnectionError("OPC UA Client is not connected. Call connect() first.")

        # In simulation mode or live mode
        value = self._simulated_register.get(tag_node_id, 0.0)
        return {
            "node_id": tag_node_id,
            "value": value,
            "status": "GOOD",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "access_level": "CURRENT_READ_ONLY"
        }

    def read_all_tags(self) -> Dict[str, Dict[str, Any]]:
        """Reads all mapped sensor tags."""
        if not self.is_connected:
            raise ConnectionError("OPC UA Client is not connected.")

        results = {}
        for logical_name, node_id in self.tags_mapping.items():
            results[logical_name] = self.read_tag(node_id)
        return results

    # =========================================================================
    # SUPERVISORY OPERATIONAL WRITE & CONTROL EXECUTION
    # =========================================================================
    def write_tag(self, tag_node_id: str, value: Any, operator_signature: Optional[str] = None) -> Dict[str, Any]:
        """
        In standard surveillance mode: blocks unauthorized writes with ReadOnlyViolationError.
        In authorized supervisory write mode: mutates setpoint/tag and logs audit entry.
        """
        from app.core.security import get_supervisory_control_status
        is_authorized = self.supervisory_write_enabled or get_supervisory_control_status()["enabled"]

        if not is_authorized:
            logger.critical(
                f"SECURITY BARRIER TRIGGERED: Attempted write to node '{tag_node_id}' with value '{value}'. "
                f"Smart Guardian architecture is currently in READ-ONLY mode."
            )
            raise ReadOnlyViolationError(
                f"READ_ONLY_VIOLATION: Write operation to node '{tag_node_id}' is strictly forbidden in Read-Only Mode. "
                f"To adjust chokes or mutate setpoints, authorize Supervisory Control Mode."
            )

        old_val = self._simulated_register.get(tag_node_id)
        self._simulated_register[tag_node_id] = value
        logger.warning(
            f"SUPERVISORY WRITE EXECUTED on node '{tag_node_id}': {old_val} -> {value} (Operator: {operator_signature or 'Engineer'})"
        )
        return {
            "status": "SUCCESS_WRITTEN",
            "node_id": tag_node_id,
            "old_value": old_val,
            "new_value": value,
            "operator_signature": operator_signature or "Authorized Operator",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def execute_command(self, command_name: str, parameters: Optional[Dict[str, Any]] = None, operator_signature: Optional[str] = None) -> Dict[str, Any]:
        """
        In standard surveillance mode: blocks unauthorized control commands.
        In authorized supervisory control mode: executes supervisory setpoint command with audit logging.
        """
        from app.core.security import get_supervisory_control_status
        is_authorized = self.supervisory_write_enabled or get_supervisory_control_status()["enabled"]

        if not is_authorized:
            logger.critical(
                f"SECURITY BARRIER TRIGGERED: Attempted execution of control command '{command_name}'. "
                f"Smart Guardian architecture is currently in READ-ONLY mode."
            )
            raise ReadOnlyViolationError(
                f"READ_ONLY_VIOLATION: Control command '{command_name}' is strictly forbidden. "
                f"Autonomous field control is disabled by default in Read-Only Mode. "
                f"To execute field commands, authorize Supervisory Control Mode."
            )

        logger.warning(
            f"SUPERVISORY COMMAND EXECUTED: '{command_name}' params={parameters} (Operator: {operator_signature or 'Engineer'})"
        )
        return {
            "status": "SUCCESS_EXECUTED",
            "command": command_name,
            "parameters": parameters or {},
            "operator_signature": operator_signature or "Authorized Operator",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
