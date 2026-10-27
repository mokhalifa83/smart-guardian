import uuid
from datetime import datetime, timezone
from typing import Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.well_config import WellConfig
from app.models.analysis import AnalysisResult
from app.models.alert import Alert
from app.schemas.common import AlertSeverity, DataQualityStatus, SourceCategory, SurveillanceState
from app.services.alert_service import AlertService
from app.core.logging import logger


class SurveillanceService:
    """
    Phase 1 Production Surveillance Engine.
    Executes surveillance rules based strictly on configured per-well operational thresholds.
    Strictly forbids declaring unsupported reservoir root causes (coning, channeling, cement failure)
    based solely on threshold exceedance.
    """

    @staticmethod
    async def get_or_create_default_config(db: AsyncSession, well_code: str) -> WellConfig:
        config = await db.get(WellConfig, well_code)
        if not config:
            config = WellConfig(
                well_code=well_code,
                wc_threshold=80.0,
                wc_trend_window_hours=24,
                alert_cooldown_minutes=60,
                surveillance_interval_minutes=5,
                is_active=True
            )
            db.add(config)
            await db.commit()
            await db.refresh(config)
        return config

    @classmethod
    async def evaluate_water_cut_surveillance(
        cls,
        db: AsyncSession,
        well_code: str,
        wc_percent: Optional[float],
        timestamp: datetime,
        source: SourceCategory,
        quality_status: DataQualityStatus
    ) -> Tuple[SurveillanceState, Optional[AnalysisResult], Optional[Alert]]:
        """
        Evaluates Water Cut surveillance for a well.
        Handles:
        1. DATA_UNAVAILABLE: Records analysis state as DATA_UNAVAILABLE without triggering false alarms.
        2. VALID reading exceeding configured threshold: Triggers WATER_CUT_THRESHOLD_EXCEEDED warning alert.
        3. VALID reading within threshold: Records NORMAL status.
        """
        config = await cls.get_or_create_default_config(db, well_code)

        # Case 1: Data is unavailable
        if quality_status == DataQualityStatus.DATA_UNAVAILABLE or wc_percent is None:
            analysis = AnalysisResult(
                analysis_id=str(uuid.uuid4()),
                well_code=well_code,
                timestamp=timestamp,
                analysis_type="WATER_CUT_SURVEILLANCE",
                status=SurveillanceState.DATA_UNAVAILABLE.value,
                observed_value=None,
                threshold=config.wc_threshold,
                data_source=source.value,
                data_quality=quality_status.value,
                diagnostic_details="Water Cut data is unavailable from source. Surveillance state: DATA_UNAVAILABLE.",
                created_at=datetime.now(timezone.utc)
            )
            db.add(analysis)
            await db.commit()
            await db.refresh(analysis)
            return SurveillanceState.DATA_UNAVAILABLE, analysis, None

        # Case 2: Water Cut exceeds configured threshold
        if wc_percent > config.wc_threshold:
            surveillance_state = SurveillanceState.WARNING
            diagnostic_msg = (
                f"Surveillance Condition: WATER_CUT_THRESHOLD_EXCEEDED. "
                f"Observed Water Cut {wc_percent:.1f}% exceeds well configured threshold {config.wc_threshold:.1f}%. "
                f"[Phase 1 Surveillance: Diagnostic root-cause reserved for multi-evidence engineering engines]"
            )

            # Persist analysis result
            analysis = AnalysisResult(
                analysis_id=str(uuid.uuid4()),
                well_code=well_code,
                timestamp=timestamp,
                analysis_type="WATER_CUT_SURVEILLANCE",
                status=surveillance_state.value,
                observed_value=wc_percent,
                threshold=config.wc_threshold,
                data_source=source.value,
                data_quality=quality_status.value,
                diagnostic_details=diagnostic_msg,
                created_at=datetime.now(timezone.utc)
            )
            db.add(analysis)

            # Trigger structured alert with duplicate suppression
            alert_msg = (
                f"Well {well_code}: Water Cut ({wc_percent:.1f}%) exceeded configured threshold ({config.wc_threshold:.1f}%). "
                f"Condition: WATER_CUT_THRESHOLD_EXCEEDED."
            )
            alert = await AlertService.create_or_suppress_alert(
                db=db,
                well_code=well_code,
                alert_type="WATER_CUT",
                severity=AlertSeverity.WARNING,
                message=alert_msg,
                value=wc_percent,
                threshold=config.wc_threshold,
                timestamp=timestamp,
                cooldown_minutes=config.alert_cooldown_minutes,
                source=f"SURVEILLANCE_ENGINE:{source.value}"
            )
            await db.commit()
            await db.refresh(analysis)
            return surveillance_state, analysis, alert

        # Case 3: Water Cut within normal bounds
        surveillance_state = SurveillanceState.NORMAL
        analysis = AnalysisResult(
            analysis_id=str(uuid.uuid4()),
            well_code=well_code,
            timestamp=timestamp,
            analysis_type="WATER_CUT_SURVEILLANCE",
            status=surveillance_state.value,
            observed_value=wc_percent,
            threshold=config.wc_threshold,
            data_source=source.value,
            data_quality=quality_status.value,
            diagnostic_details=f"Water Cut {wc_percent:.1f}% is within acceptable operational limit (< {config.wc_threshold:.1f}%).",
            created_at=datetime.now(timezone.utc)
        )
        db.add(analysis)
        await db.commit()
        await db.refresh(analysis)
        return surveillance_state, analysis, None
