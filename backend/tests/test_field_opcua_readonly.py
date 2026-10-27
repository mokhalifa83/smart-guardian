"""
Test Suite for Step 2C Read-Only OPC UA Client (test_field_opcua_readonly.py)
Validates:
1. Technical read-only safety barrier
2. Tag reads succeed cleanly in read-only mode
3. Any write attempt MUST raise ReadOnlyViolationError
4. Any control command attempt MUST raise ReadOnlyViolationError
"""

import pytest
from app.services.opcua_client import ReadOnlyOPCUAClient, ReadOnlyViolationError


def test_opcua_read_success():
    client = ReadOnlyOPCUAClient(simulation_mode=True)
    assert client.connect() is True

    try:
        tag_data = client.read_tag("ns=2;s=Wellhead.Pressure")
        assert tag_data["status"] == "GOOD"
        assert tag_data["access_level"] == "CURRENT_READ_ONLY"
        assert tag_data["value"] > 0

        all_tags = client.read_all_tags()
        assert len(all_tags) >= 5
        assert "WELLHEAD_PRESSURE" in all_tags
        assert "WATER_CUT_METER" in all_tags
    finally:
        client.disconnect()


def test_opcua_write_attempt_raises_readonly_violation():
    """
    CRITICAL SAFETY REQUIREMENT:
    Any write attempt to OPC UA field connection MUST be blocked with ReadOnlyViolationError.
    """
    client = ReadOnlyOPCUAClient(simulation_mode=True)
    client.connect()

    try:
        with pytest.raises(ReadOnlyViolationError) as exc_info:
            client.write_tag("ns=2;s=Wellhead.ChokeOpening", 45.0)

        assert "READ_ONLY_VIOLATION" in str(exc_info.value)
        assert "strictly forbidden" in str(exc_info.value)
    finally:
        client.disconnect()


def test_opcua_command_execution_raises_readonly_violation():
    """
    CRITICAL SAFETY REQUIREMENT:
    Any command execution (e.g. emergency shutdown, choke command) MUST be blocked.
    """
    client = ReadOnlyOPCUAClient(simulation_mode=True)
    client.connect()

    try:
        with pytest.raises(ReadOnlyViolationError) as exc_info:
            client.execute_command("EMERGENCY_SHUTDOWN_WELL", {"choke": 0})

        assert "READ_ONLY_VIOLATION" in str(exc_info.value)
        assert "Autonomous field control is disabled" in str(exc_info.value)
    finally:
        client.disconnect()
