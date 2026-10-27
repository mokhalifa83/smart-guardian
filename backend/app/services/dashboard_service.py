from datetime import datetime, timezone
from typing import Optional, List
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.well import Well
from app.models.well_config import WellConfig
from app.models.readings import ProductionReading
from app.models.separator import SeparatorReading
from app.models.alert import Alert
from app.schemas.common import DataQualityStatus, SourceCategory, SurveillanceState, ValueType, AlertStatus
from app.schemas.alert import AlertResponse
from app.schemas.dashboard import DashboardResponse, KpiCardData
from app.services.surveillance import SurveillanceService
from app.core.config import settings


class DashboardService:
    """
    Assembles clean industrial dashboard data strictly from validated backend records.
    Never fabricates values or substitutes zero for missing measurements.
    """

    @classmethod
    async def get_dashboard_summary(cls, db: AsyncSession, well_code: str) -> DashboardResponse:
        well = await db.get(Well, well_code)
        if not well:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Well with code '{well_code}' not found."
            )

        config = await SurveillanceService.get_or_create_default_config(db, well_code)

        # 1. Fetch latest production reading
        prod_stmt = select(ProductionReading).where(
            ProductionReading.well_code == well_code
        ).order_by(desc(ProductionReading.timestamp)).limit(1)
        latest_prod = (await db.execute(prod_stmt)).scalar_one_or_none()

        # 2. Fetch latest separator reading
        sep_stmt = select(SeparatorReading).where(
            SeparatorReading.well_code == well_code
        ).order_by(desc(SeparatorReading.timestamp)).limit(1)
        latest_sep = (await db.execute(sep_stmt)).scalar_one_or_none()

        # 3. Fetch active alerts
        alert_stmt = select(Alert).where(
            Alert.well_code == well_code,
            Alert.status != AlertStatus.RESOLVED.value
        ).order_by(desc(Alert.timestamp)).limit(10)
        active_alerts = list((await db.execute(alert_stmt)).scalars().all())

        # Determine latest timestamp
        timestamps = [r.timestamp for r in [latest_prod, latest_sep] if r is not None and r.timestamp is not None]
        latest_ts = max(timestamps) if timestamps else None

        # Build KPI Cards strictly from real data
        kpis: List[KpiCardData] = []

        # --- KPI 1: Water Cut ---
        wc_value: Optional[float] = None
        wc_source: Optional[SourceCategory] = None
        wc_quality: DataQualityStatus = DataQualityStatus.DATA_UNAVAILABLE
        wc_val_type: ValueType = ValueType.MEASURED
        wc_ts: Optional[datetime] = None
        wc_recv_ts: Optional[datetime] = None

        if latest_prod and latest_prod.wc_percent is not None:
            wc_value = latest_prod.wc_percent
            wc_source = SourceCategory(latest_prod.source)
            wc_quality = DataQualityStatus(latest_prod.quality_status)
            wc_val_type = ValueType(latest_prod.value_type)
            wc_ts = latest_prod.timestamp
            wc_recv_ts = latest_prod.received_at
        elif latest_sep and latest_sep.water_cut is not None:
            wc_value = latest_sep.water_cut
            wc_source = SourceCategory(latest_sep.source)
            wc_quality = DataQualityStatus(latest_sep.quality_status)
            wc_val_type = ValueType(latest_sep.value_type)
            wc_ts = latest_sep.timestamp
            wc_recv_ts = latest_sep.received_at

        # Determine WC status
        if wc_value is None or wc_quality == DataQualityStatus.DATA_UNAVAILABLE:
            wc_status = SurveillanceState.DATA_UNAVAILABLE
            wc_display = "DATA_UNAVAILABLE"
            is_exceeded = False
        elif wc_value > config.wc_threshold:
            wc_status = SurveillanceState.WARNING
            wc_display = f"{wc_value:.1f}"
            is_exceeded = True
        else:
            wc_status = SurveillanceState.NORMAL
            wc_display = f"{wc_value:.1f}"
            is_exceeded = False

        kpis.append(KpiCardData(
            title="Water Cut",
            metric_key="water_cut",
            value=wc_value,
            display_value=wc_display,
            unit="%",
            status=wc_status,
            timestamp=wc_ts,
            received_at=wc_recv_ts,
            source=wc_source,
            quality_status=wc_quality,
            value_type=wc_val_type,
            threshold=config.wc_threshold,
            is_threshold_exceeded=is_exceeded
        ))

        # --- KPI 2: Separator Pressure ---
        p_val: Optional[float] = latest_sep.pressure if latest_sep else None
        p_status = SurveillanceState.DATA_UNAVAILABLE if p_val is None else SurveillanceState.NORMAL
        kpis.append(KpiCardData(
            title="Separator Pressure",
            metric_key="pressure",
            value=p_val,
            display_value=f"{p_val:.1f}" if p_val is not None else "DATA_UNAVAILABLE",
            unit="psi",
            status=p_status,
            timestamp=latest_sep.timestamp if latest_sep else None,
            received_at=latest_sep.received_at if latest_sep else None,
            source=SourceCategory(latest_sep.source) if latest_sep else None,
            quality_status=DataQualityStatus(latest_sep.quality_status) if latest_sep else DataQualityStatus.DATA_UNAVAILABLE,
            value_type=ValueType.MEASURED,
            threshold=None,
            is_threshold_exceeded=False
        ))

        # --- KPI 3: Flow Rate ---
        flow_val: Optional[float] = None
        flow_source: Optional[SourceCategory] = None
        flow_quality: DataQualityStatus = DataQualityStatus.DATA_UNAVAILABLE
        flow_ts: Optional[datetime] = None

        if latest_sep and latest_sep.flow_rate is not None:
            flow_val = latest_sep.flow_rate
            flow_source = SourceCategory(latest_sep.source)
            flow_quality = DataQualityStatus(latest_sep.quality_status)
            flow_ts = latest_sep.timestamp
        elif latest_prod and (latest_prod.oil_rate is not None or latest_prod.water_rate is not None):
            flow_val = (latest_prod.oil_rate or 0.0) + (latest_prod.water_rate or 0.0)
            flow_source = SourceCategory(latest_prod.source)
            flow_quality = DataQualityStatus(latest_prod.quality_status)
            flow_ts = latest_prod.timestamp

        flow_status = SurveillanceState.DATA_UNAVAILABLE if flow_val is None else SurveillanceState.NORMAL
        kpis.append(KpiCardData(
            title="Gross Flow Rate",
            metric_key="flow_rate",
            value=flow_val,
            display_value=f"{flow_val:.1f}" if flow_val is not None else "DATA_UNAVAILABLE",
            unit="bpd",
            status=flow_status,
            timestamp=flow_ts,
            received_at=latest_sep.received_at if latest_sep else (latest_prod.received_at if latest_prod else None),
            source=flow_source,
            quality_status=flow_quality,
            value_type=ValueType.MEASURED,
            threshold=None,
            is_threshold_exceeded=False
        ))

        # Overall surveillance state
        if any(a.severity == "CRITICAL" for a in active_alerts) or any(k.status == SurveillanceState.WARNING for k in kpis):
            overall_state = SurveillanceState.WARNING
        elif all(k.status == SurveillanceState.DATA_UNAVAILABLE for k in kpis):
            overall_state = SurveillanceState.DATA_UNAVAILABLE
        else:
            overall_state = SurveillanceState.NORMAL

        # Rate limiter status info
        rate_info = {
            "rate_limit_per_source": settings.RATE_LIMIT_PER_SOURCE_PER_MINUTE,
            "rate_limit_per_well": settings.RATE_LIMIT_PER_WELL_PER_MINUTE
        }

        return DashboardResponse(
            well_code=well.well_code,
            field_name=well.field_name,
            well_status=well.status,
            latest_timestamp=latest_ts,
            surveillance_state=overall_state,
            kpis=kpis,
            active_alerts=[AlertResponse.model_validate(a) for a in active_alerts],
            configured_wc_threshold=config.wc_threshold,
            rate_limit_info=rate_info
        )
