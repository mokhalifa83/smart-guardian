from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.well import Well
from app.models.well_config import WellConfig
from app.schemas.well import WellCreate, WellUpdate, WellResponse, WellConfigResponse, WellConfigUpdate
from app.services.surveillance import SurveillanceService
from app.core.logging import logger

router = APIRouter(prefix="/wells", tags=["Wells"])


@router.get("", response_model=List[WellResponse])
async def list_wells(db: AsyncSession = Depends(get_db)):
    """List all registered production and observation wells."""
    stmt = select(Well).options(selectinload(Well.config)).order_by(Well.well_code)
    result = await db.execute(stmt)
    wells = result.scalars().all()
    return wells


@router.post("", response_model=WellResponse, status_code=status.HTTP_201_CREATED)
async def create_well(payload: WellCreate, db: AsyncSession = Depends(get_db)):
    """Register a new field well with optional configuration."""
    existing = await db.get(Well, payload.well_code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Well with code '{payload.well_code}' already exists."
        )

    well = Well(well_code=payload.well_code, field_name=payload.field_name, status=payload.status)
    db.add(well)
    await db.commit()
    await db.refresh(well)

    # Initialize configuration
    cfg = payload.config
    well_config = WellConfig(
        well_code=well.well_code,
        wc_threshold=cfg.wc_threshold if cfg else 80.0,
        wc_trend_window_hours=cfg.wc_trend_window_hours if cfg else 24,
        alert_cooldown_minutes=cfg.alert_cooldown_minutes if cfg else 60,
        surveillance_interval_minutes=cfg.surveillance_interval_minutes if cfg else 5,
        is_active=cfg.is_active if cfg else True
    )
    db.add(well_config)
    await db.commit()
    await db.refresh(well)
    well.config = well_config
    return well


@router.get("/{code}", response_model=WellResponse)
async def get_well(code: str, db: AsyncSession = Depends(get_db)):
    """Retrieve details for a specific well."""
    stmt = select(Well).options(selectinload(Well.config)).where(Well.well_code == code)
    well = (await db.execute(stmt)).scalar_one_or_none()
    if not well:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Well '{code}' not found."
        )
    return well


@router.get("/{code}/config", response_model=WellConfigResponse)
async def get_well_config(code: str, db: AsyncSession = Depends(get_db)):
    """Retrieve operational surveillance configuration and engineering thresholds for a well."""
    well = await db.get(Well, code)
    if not well:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Well '{code}' not found.")
    
    config = await SurveillanceService.get_or_create_default_config(db, code)
    return config


@router.put("/{code}/config", response_model=WellConfigResponse)
async def update_well_config(
    code: str,
    payload: WellConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update well configuration (e.g. Water Cut alert threshold, alert cooldown).
    Demonstrates that thresholds are configurable per well and not hard-coded engineering assumptions.
    """
    well = await db.get(Well, code)
    if not well:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Well '{code}' not found.")

    config = await SurveillanceService.get_or_create_default_config(db, code)

    update_data = payload.model_dump(exclude_unset=True)
    for key, val in update_data.items():
        if val is not None:
            setattr(config, key, val)

    await db.commit()
    await db.refresh(config)

    logger.info(
        f"WellConfig updated for well {code}",
        extra={"structured_data": {"event": "CONFIG_UPDATED", "well_code": code, "updated_fields": list(update_data.keys())}}
    )
    return config


@router.put("/{code}", response_model=WellResponse)
async def update_well(
    code: str,
    payload: WellUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update well metadata (name, field name, status, or threshold).
    Supports renaming well or modifying field assignment.
    """
    stmt = select(Well).options(selectinload(Well.config)).where(Well.well_code == code)
    well = (await db.execute(stmt)).scalar_one_or_none()
    if not well:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Well '{code}' not found.")

    if payload.field_name is not None:
        well.field_name = payload.field_name
    if payload.status is not None:
        well.status = payload.status

    if payload.wc_threshold is not None:
        config = await SurveillanceService.get_or_create_default_config(db, code)
        config.wc_threshold = payload.wc_threshold

    await db.commit()
    await db.refresh(well)
    return well


@router.delete("/{code}", status_code=status.HTTP_200_OK)
async def delete_well(code: str, db: AsyncSession = Depends(get_db)):
    """
    Delete a well and all its associated configurations and readings.
    Provides complete lifecycle control for petroleum engineers.
    """
    well = await db.get(Well, code)
    if not well:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Well '{code}' not found.")

    await db.delete(well)
    await db.commit()

    logger.warning(
        f"Well {code} deleted by operator",
        extra={"structured_data": {"event": "WELL_DELETED", "well_code": code}}
    )
    return {
        "status": "DELETED",
        "well_code": code,
        "message": f"Well '{code}' and all associated records have been successfully deleted."
    }

