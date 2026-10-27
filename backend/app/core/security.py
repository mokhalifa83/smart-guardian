from typing import Optional
from fastapi import HTTPException, Security, status, Header
from fastapi.security import APIKeyHeader
from app.core.config import settings
from app.core.logging import logger

api_key_header_scheme = APIKeyHeader(name=settings.API_KEY_HEADER, auto_error=False)


# Global dynamic state for Supervisory Operational Control & Field Write Mode
_supervisory_control_state = {
    "enabled": False,
    "authorized_by": None,
    "authorized_at": None,
    "reason": None
}


def get_supervisory_control_status():
    return dict(_supervisory_control_state)


def set_supervisory_control_mode(enabled: bool, operator: str = "Chief Operator", reason: str = "Authorized field maintenance"):
    from datetime import datetime, timezone
    _supervisory_control_state["enabled"] = enabled
    _supervisory_control_state["authorized_by"] = operator if enabled else None
    _supervisory_control_state["authorized_at"] = datetime.now(timezone.utc).isoformat() if enabled else None
    _supervisory_control_state["reason"] = reason if enabled else None
    logger.info(
        f"SUPERVISORY CONTROL MODE CHANGED: enabled={enabled} by={operator}",
        extra={"structured_data": {"event": "CONTROL_MODE_CHANGED", "enabled": enabled, "operator": operator}}
    )
    return get_supervisory_control_status()


def verify_read_only_boundary(command_type: Optional[str] = None):
    """
    SAFETY & SUPERVISORY CONTROL ENFORCEMENT:
    When supervisory control is enabled by an authorized petroleum engineer or chief operator,
    operational writes and setpoint adjustments are permitted with audit logging.
    When disabled (standard surveillance mode), field control commands are blocked at the boundary.
    """
    if _supervisory_control_state["enabled"]:
        # Supervisory write mode active
        return True

    if not settings.ALLOW_FIELD_CONTROL_COMMANDS:
        forbidden_commands = {
            "valve_control", "choke_control", "pump_control", 
            "well_shutdown", "injection_control", "actuation"
        }
        if command_type and command_type.lower() in forbidden_commands:
            logger.critical(
                "BLOCKED SAFETY VIOLATION: Unauthorized attempt to send control command in Read-Only mode",
                extra={"structured_data": {"command_type": command_type, "violation": "READ_ONLY_BARRIER"}}
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Safety Barrier Violation: System is in Read-Only Surveillance Mode. To execute control commands or modify setpoints, enable Supervisory Control Mode."
            )



async def get_api_key(api_key: Optional[str] = Security(api_key_header_scheme)) -> Optional[str]:
    """
    Validates API key if configured and present. In dev mode without keys, permits authenticated read.
    """
    if not settings.API_KEYS or len(settings.API_KEYS) == 0:
        return "unauthenticated-dev"

    if api_key and api_key in settings.API_KEYS:
        return api_key

    # For Phase 1 development and test convenience, allow anonymous read when header is not supplied,
    # but when header is provided and invalid, reject.
    if api_key and api_key not in settings.API_KEYS:
        logger.warning("Invalid API Key provided", extra={"structured_data": {"event": "AUTH_FAILED"}})
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key"
        )
    return "anonymous"
