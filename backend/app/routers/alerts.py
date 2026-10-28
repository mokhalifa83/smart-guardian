from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.session import get_db
from app.models.alert import Alert
from app.models.notification import NotificationRecord
from app.schemas.alert import AlertResponse, AlertAcknowledgeRequest, AlertResolveRequest
from app.schemas.notification import NotificationRecordResponse
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["Operational Alerts"])


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    well_code: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve operational alerts filtered by well or status."""
    stmt = select(Alert)
    if well_code:
        stmt = stmt.where(Alert.well_code == well_code)
    if status_filter:
        stmt = stmt.where(Alert.status == status_filter.upper())
    stmt = stmt.order_by(desc(Alert.timestamp)).limit(limit)
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.put("/{alert_id}/acknowledge", response_model=AlertResponse)
async def acknowledge_alert(
    alert_id: str,
    payload: AlertAcknowledgeRequest,
    db: AsyncSession = Depends(get_db)
):
    """Acknowledge an active alert by engineer/operator."""
    alert = await AlertService.acknowledge_alert(
        db=db,
        alert_id=alert_id,
        acknowledged_by=payload.acknowledged_by or "operator"
    )
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found."
        )
    return alert


@router.get("/{alert_id}/notifications", response_model=List[NotificationRecordResponse])
async def get_alert_notifications(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve audit history of outbound notifications for a specific alert."""
    stmt = select(NotificationRecord).where(NotificationRecord.alert_id == alert_id).order_by(desc(NotificationRecord.created_at))
    res = await db.execute(stmt)
    return list(res.scalars().all())


@router.put("/{alert_id}/resolve", response_model=AlertResponse)
async def resolve_alert(
    alert_id: str,
    payload: AlertResolveRequest,
    db: AsyncSession = Depends(get_db)
):
    """Resolve an operational alert with optional notes."""
    alert = await AlertService.resolve_alert(
        db=db,
        alert_id=alert_id,
        resolved_by=payload.resolved_by or "operator",
        resolution_notes=payload.resolution_notes
    )
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert '{alert_id}' not found."
        )
    return alert


@router.get("/{alert_id}/notifications", response_model=List[NotificationRecordResponse])
async def get_alert_notifications(
    alert_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Retrieve audit history of outbound notifications for a specific alert."""
    stmt = select(NotificationRecord).where(NotificationRecord.alert_id == alert_id).order_by(desc(NotificationRecord.created_at))
    res = await db.execute(stmt)
    return list(res.scalars().all())
