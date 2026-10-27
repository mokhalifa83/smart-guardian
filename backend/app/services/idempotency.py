import hashlib
from datetime import datetime
from typing import Optional


class IdempotencyService:
    """
    Computes composite idempotency hashes for incoming events.
    Ensures network retries, MQTT retries, or control-room re-sends do not create duplicate records.
    Distinguishes legitimate readings across different sources and measurement types.
    """

    @staticmethod
    def generate_hash(
        well_code: str,
        timestamp: datetime,
        source: str,
        measurement_type: str,
        source_record_id: Optional[str] = None
    ) -> str:
        # Standardize timestamp to ISO string in UTC
        ts_str = timestamp.isoformat()
        
        # Base string incorporates well_code, timestamp, source, and measurement_type
        base = f"{well_code.strip().upper()}|{ts_str}|{source.strip().upper()}|{measurement_type.strip().upper()}"
        if source_record_id:
            base += f"|{source_record_id.strip()}"

        return hashlib.sha256(base.encode("utf-8")).hexdigest()
