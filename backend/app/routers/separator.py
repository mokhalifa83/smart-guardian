from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.separator import SeparatorReading
from app.schemas.separator import SeparatorReadingCreate, SeparatorReadingResponse
from app.services.ingestion import IngestionService
from app.core.security import verify_read_only_boundary

router = APIRouter(prefix="/separator-data", tags=["Separator Telemetry"])


@router.post("", response_model=SeparatorReadingResponse, status_code=status.HTTP_201_CREATED)
async def ingest_separator_data(
    payload: SeparatorReadingCreate,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest separator telemetry (pressure, total flow rate, water cut, phase rates).
    Normalizes % vs fraction, preserves original source values, and triggers surveillance.
    """
    verify_read_only_boundary()
    reading, is_duplicate = await IngestionService.ingest_separator_reading(db, payload)
    if is_duplicate:
        response.status_code = status.HTTP_200_OK
    return reading


@router.get("", response_model=List[SeparatorReadingResponse])
async def list_separator_data(
    well_code: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Query time-series separator telemetry."""
    stmt = select(SeparatorReading)
    if well_code:
        stmt = stmt.where(SeparatorReading.well_code == well_code)
    stmt = stmt.order_by(desc(SeparatorReading.timestamp)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
