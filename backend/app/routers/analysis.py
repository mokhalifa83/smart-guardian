from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.analysis import AnalysisResult
from app.schemas.analysis import AnalysisResultResponse

router = APIRouter(prefix="/analysis", tags=["Surveillance Analysis"])


@router.get("", response_model=List[AnalysisResultResponse])
async def list_analysis_results(
    well_code: Optional[str] = Query(None),
    analysis_type: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """
    Retrieve surveillance-level analysis history.
    Phase 1 strictly returns observation indicators without unverified root causes.
    """
    stmt = select(AnalysisResult)
    if well_code:
        stmt = stmt.where(AnalysisResult.well_code == well_code)
    if analysis_type:
        stmt = stmt.where(AnalysisResult.analysis_type == analysis_type)
    stmt = stmt.order_by(desc(AnalysisResult.timestamp)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())
