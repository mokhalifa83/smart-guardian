from typing import List, Optional
from fastapi import APIRouter, Depends, status, Query, Response
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.readings import ProductionReading
from app.models.manual import ManualReading
from app.schemas.readings import ProductionReadingCreate, ProductionReadingResponse
from app.schemas.manual import ManualReadingCreate, ManualReadingResponse
from app.services.ingestion import IngestionService
from app.core.security import verify_read_only_boundary

router = APIRouter(prefix="/readings", tags=["Readings Ingestion"])


@router.post("", response_model=ProductionReadingResponse, status_code=status.HTTP_201_CREATED)
async def ingest_production_reading(
    payload: ProductionReadingCreate,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest automatic production reading (REST or MQTT bridge).
    Enforces validation, duplicate suppression, idempotency, and DATA_UNAVAILABLE preservation.
    """
    verify_read_only_boundary()
    reading, is_duplicate = await IngestionService.ingest_production_reading(db, payload)
    if is_duplicate:
        response.status_code = status.HTTP_200_OK
    return reading


@router.post("/manual", response_model=ManualReadingResponse, status_code=status.HTTP_201_CREATED)
async def ingest_manual_reading(
    payload: ManualReadingCreate,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingest manual engineering entry (Oil API Gravity, Manual Water Cut, Manual Pressure).
    Preserves engineer identity (entered_by), timestamp, unit, and validation status.
    """
    verify_read_only_boundary()
    manual, is_duplicate = await IngestionService.ingest_manual_reading(db, payload)
    if is_duplicate:
        response.status_code = status.HTTP_200_OK
    return manual


@router.get("", response_model=List[ProductionReadingResponse])
async def list_production_readings(
    well_code: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Query time-series production surveillance records."""
    stmt = select(ProductionReading)
    if well_code:
        stmt = stmt.where(ProductionReading.well_code == well_code)
    stmt = stmt.order_by(desc(ProductionReading.timestamp)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.get("/manual", response_model=List[ManualReadingResponse])
async def list_manual_readings(
    well_code: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Query manual operator readings."""
    stmt = select(ManualReading)
    if well_code:
        stmt = stmt.where(ManualReading.well_code == well_code)
    stmt = stmt.order_by(desc(ManualReading.timestamp)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
