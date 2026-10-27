import pytest
from fastapi import HTTPException
from app.core.security import verify_read_only_boundary


def test_safety_barrier_blocks_control_commands():
    # Valve control command must be blocked
    with pytest.raises(HTTPException) as exc_info:
        verify_read_only_boundary("valve_control")
    assert exc_info.value.status_code == 403
    assert "Safety Barrier Violation" in exc_info.value.detail

    # Pump control command must be blocked
    with pytest.raises(HTTPException) as exc_info:
        verify_read_only_boundary("pump_control")
    assert exc_info.value.status_code == 403

    # Choke adjustment must be blocked
    with pytest.raises(HTTPException) as exc_info:
        verify_read_only_boundary("choke_control")
    assert exc_info.value.status_code == 403

    # Well shutdown command must be blocked
    with pytest.raises(HTTPException) as exc_info:
        verify_read_only_boundary("well_shutdown")
    assert exc_info.value.status_code == 403


def test_safety_barrier_permits_read_only():
    # Read-only surveillance queries must be permitted
    verify_read_only_boundary(None)
