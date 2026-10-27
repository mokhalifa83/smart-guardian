import time
from collections import defaultdict
from typing import Dict, List
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger


class IngestionRateLimiter:
    """
    Infrastructure protection mechanism to throttle incoming data streams per source and per well.
    Prevents denial-of-service, control-room storming, or duplicate flood.
    Configurable via settings, does not encode engineering assumptions.
    """
    def __init__(self):
        # Maps key -> list of timestamp floats
        self._source_timestamps: Dict[str, List[float]] = defaultdict(list)
        self._well_timestamps: Dict[str, List[float]] = defaultdict(list)

    def _clean_old_entries(self, timestamps: List[float], window_seconds: float, now: float) -> List[float]:
        threshold = now - window_seconds
        return [ts for ts in timestamps if ts > threshold]

    def check_rate_limit(self, source: str, well_code: str) -> None:
        now = time.time()
        window_seconds = 60.0

        # Check source limit
        source_ts = self._clean_old_entries(self._source_timestamps[source], window_seconds, now)
        if len(source_ts) >= settings.RATE_LIMIT_PER_SOURCE_PER_MINUTE:
            logger.warning(
                f"Rate limit exceeded for source '{source}'",
                extra={"structured_data": {"source": source, "limit": settings.RATE_LIMIT_PER_SOURCE_PER_MINUTE}}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for ingestion source '{source}'. Maximum {settings.RATE_LIMIT_PER_SOURCE_PER_MINUTE} events/min."
            )
        source_ts.append(now)
        self._source_timestamps[source] = source_ts

        # Check well limit
        well_ts = self._clean_old_entries(self._well_timestamps[well_code], window_seconds, now)
        if len(well_ts) >= settings.RATE_LIMIT_PER_WELL_PER_MINUTE:
            logger.warning(
                f"Rate limit exceeded for well '{well_code}'",
                extra={"structured_data": {"well_code": well_code, "limit": settings.RATE_LIMIT_PER_WELL_PER_MINUTE}}
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for well '{well_code}'. Maximum {settings.RATE_LIMIT_PER_WELL_PER_MINUTE} events/min."
            )
        well_ts.append(now)
        self._well_timestamps[well_code] = well_ts


rate_limiter = IngestionRateLimiter()
