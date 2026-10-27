import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from sqlalchemy import select, and_, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.alert import Alert
from app.schemas.common import AlertSeverity, AlertStatus
from app.core.logging import logger


class AlertService:
    """
    Manages structured operational alerts, lifecycle transitions (ACTIVE -> ACKNOWLEDGED -> RESOLVED),
    and duplicate alert suppression using well-level configurable cooldown.
    """

    @staticmethod
    async def get_active_alerts(
        db: AsyncSession,
        well_code: Optional[str] = None,
        limit: int = 50
    ) -> List[Alert]:
        query = select(Alert).where(Alert.status != AlertStatus.RESOLVED.value)
        if well_code:
            query = query.where(Alert.well_code == well_code)
        query = query.order_by(desc(Alert.timestamp)).limit(limit)
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def create_or_suppress_alert(
        db: AsyncSession,
        well_code: str,
        alert_type: str,
        severity: AlertSeverity,
        message: str,
        value: Optional[float],
        threshold: Optional[float],
        timestamp: datetime,
        cooldown_minutes: int = 60,
        source: str = "SURVEILLANCE_ENGINE"
    ) -> Optional[Alert]:
        """
        Evaluates active alerts and cooldown window.
        Suppresses duplicates if an ACTIVE or ACKNOWLEDGED alert for the same condition already exists within cooldown.
        """
        now = datetime.now(timezone.utc)
        cooldown_cutoff = now - timedelta(minutes=cooldown_minutes)

        # Check for existing non-resolved alert
        query = (
            select(Alert)
            .where(
                and_(
                    Alert.well_code == well_code,
                    Alert.alert_type == alert_type,
                    Alert.status.in_([AlertStatus.ACTIVE.value, AlertStatus.ACKNOWLEDGED.value]),
                    Alert.created_at >= cooldown_cutoff
                )
            )
            .order_by(desc(Alert.created_at))
            .limit(1)
        )
        existing = (await db.execute(query)).scalar_one_or_none()

        if existing:
            logger.info(
                f"Alert suppressed due to cooldown ({cooldown_minutes}m) for well {well_code} [{alert_type}]",
                extra={"structured_data": {"well_code": well_code, "alert_type": alert_type, "existing_alert_id": existing.alert_id}}
            )
            return existing

        new_alert = Alert(
            alert_id=str(uuid.uuid4()),
            well_code=well_code,
            alert_type=alert_type,
            severity=severity.value,
            message=message,
            value=value,
            threshold=threshold,
            timestamp=timestamp,
            status=AlertStatus.ACTIVE.value,
            source=source,
            created_at=now
        )
        db.add(new_alert)
        await db.commit()
        await db.refresh(new_alert)

        logger.warning(
            f"NEW ALERT GENERATED: {message}",
            extra={"structured_data": {
                "event": "ALERT_CREATED",
                "alert_id": new_alert.alert_id,
                "well_code": well_code,
                "severity": severity.value,
                "value": value,
                "threshold": threshold
            }}
        )
        return new_alert

    @staticmethod
    async def acknowledge_alert(
        db: AsyncSession,
        alert_id: str,
        acknowledged_by: str = "operator"
    ) -> Optional[Alert]:
        alert = await db.get(Alert, alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.ACKNOWLEDGED.value
        alert.acknowledged_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(alert)

        logger.info(
            f"Alert {alert_id} acknowledged by {acknowledged_by}",
            extra={"structured_data": {"event": "ALERT_ACKNOWLEDGED", "alert_id": alert_id, "by": acknowledged_by}}
        )
        return alert

    @staticmethod
    async def resolve_alert(
        db: AsyncSession,
        alert_id: str,
        resolved_by: str = "operator",
        resolution_notes: Optional[str] = None
    ) -> Optional[Alert]:
        alert = await db.get(Alert, alert_id)
        if not alert:
            return None

        alert.status = AlertStatus.RESOLVED.value
        alert.resolved_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(alert)

        logger.info(
            f"Alert {alert_id} resolved by {resolved_by}. Notes: {resolution_notes}",
            extra={"structured_data": {"event": "ALERT_RESOLVED", "alert_id": alert_id, "by": resolved_by}}
        )
        return alert
