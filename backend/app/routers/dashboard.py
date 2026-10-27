from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.well import Well
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_model=DashboardResponse)
async def get_dashboard(
    well_code: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve real-time surveillance dashboard summary for the specified well.
    If no well_code is provided, defaults to the first active field well.
    Returns real backend KPI values and state (NORMAL, WARNING, DATA_UNAVAILABLE).
    """
    if not well_code:
        stmt = select(Well).order_by(Well.well_code).limit(1)
        first_well = (await db.execute(stmt)).scalar_one_or_none()
        if not first_well:
            # Seed default demo well if platform is completely empty
            default_well = Well(well_code="WELL-001", field_name="North Dome Field", status="ACTIVE")
            db.add(default_well)
            await db.commit()
            well_code = "WELL-001"
        else:
            well_code = first_well.well_code

    return await DashboardService.get_dashboard_summary(db, well_code)
