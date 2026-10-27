from datetime import datetime, timezone
from typing import Optional, Dict, Any, Tuple
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from app.models.well import Well
from app.models.readings import ProductionReading
from app.models.separator import SeparatorReading
from app.models.manual import ManualReading
from app.schemas.common import DataQualityStatus, SourceCategory, ValueType, MeasurementType
from app.schemas.readings import ProductionReadingCreate
from app.schemas.separator import SeparatorReadingCreate
from app.schemas.manual import ManualReadingCreate
from app.services.validation import DataValidationService
from app.services.idempotency import IdempotencyService
from app.services.surveillance import SurveillanceService
from app.core.rate_limiter import rate_limiter
from app.core.logging import logger


class IngestionService:
    """
    Robust Ingestion Service for Smart Guardian.
    Handles REST, MQTT-ready payloads, rate-limiting, validation, idempotency,
    provenance preservation, and DATA_UNAVAILABLE state protection.
    """

    @staticmethod
    async def _ensure_well_exists(db: AsyncSession, well_code: str) -> Well:
        well = await db.get(Well, well_code)
        if not well:
            # Auto-register well if new field source streams it
            well = Well(well_code=well_code, field_name="Default Field", status="ACTIVE")
            db.add(well)
            await db.commit()
            await db.refresh(well)
            # Also ensure default config exists
            await SurveillanceService.get_or_create_default_config(db, well_code)
        return well

    @classmethod
    async def ingest_production_reading(
        cls,
        db: AsyncSession,
        payload: ProductionReadingCreate
    ) -> Tuple[ProductionReading, bool]:
        """
        Ingests a production reading with rate-limiting, validation, and idempotency.
        Returns (reading, is_duplicate).
        """
        # 1. Rate Limiting Check
        rate_limiter.check_rate_limit(payload.source.value, payload.well_code)

        # 2. Well Existence
        await cls._ensure_well_exists(db, payload.well_code)

        # 3. Timestamp Validation
        ts_valid, ts_quality, ts_msg = DataValidationService.validate_timestamp(payload.timestamp)
        if not ts_valid:
            logger.warning(f"Rejected reading: {ts_msg}", extra={"structured_data": {"well": payload.well_code}})
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=ts_msg)

        # 4. Idempotency Check
        idem_hash = IdempotencyService.generate_hash(
            well_code=payload.well_code,
            timestamp=payload.timestamp,
            source=payload.source.value,
            measurement_type="PRODUCTION_READING",
            source_record_id=payload.source_record_id
        )

        existing_stmt = select(ProductionReading).where(
            and_(
                ProductionReading.well_code == payload.well_code,
                ProductionReading.timestamp == payload.timestamp,
                ProductionReading.source == payload.source.value
            )
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            logger.info(
                f"Idempotent duplicate reading detected for well {payload.well_code}",
                extra={"structured_data": {"well_code": payload.well_code, "idempotency_hash": idem_hash}}
            )
            return existing, True

        # 5. Engineering Validation & Unit Normalization
        # Water Cut validation:
        value_type = ValueType.MEASURED
        if payload.is_data_unavailable or (payload.wc_value is None and payload.water_rate is None):
            norm_wc, orig_wc, orig_unit, wc_status, wc_msg = DataValidationService.normalize_water_cut(
                None, payload.wc_unit, is_unavailable=True
            )
        elif payload.wc_value is not None:
            norm_wc, orig_wc, orig_unit, wc_status, wc_msg = DataValidationService.normalize_water_cut(
                payload.wc_value, payload.wc_unit, is_unavailable=False
            )
            if wc_status == DataQualityStatus.INVALID:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=wc_msg)
        else:
            # Derived/Calculated from phase rates
            norm_wc, wc_status, wc_msg = DataValidationService.calculate_water_cut(
                payload.oil_rate, payload.water_rate
            )
            value_type = ValueType.CALCULATED

        overall_quality = wc_status if wc_status != DataQualityStatus.VALID else ts_quality

        # 6. Persistence
        reading = ProductionReading(
            timestamp=payload.timestamp,
            well_code=payload.well_code,
            source=payload.source.value,
            oil_rate=payload.oil_rate,
            water_rate=payload.water_rate,
            gas_rate=payload.gas_rate,
            wc_percent=norm_wc,
            value_type=value_type.value,
            quality_status=overall_quality.value,
            validation_status=overall_quality.value,
            received_at=datetime.now(timezone.utc),
            source_system=payload.source_system,
            source_record_id=payload.source_record_id,
            idempotency_hash=idem_hash
        )
        db.add(reading)
        await db.commit()
        await db.refresh(reading)

        # 7. Production Surveillance Trigger
        await SurveillanceService.evaluate_water_cut_surveillance(
            db=db,
            well_code=payload.well_code,
            wc_percent=norm_wc,
            timestamp=payload.timestamp,
            source=payload.source,
            quality_status=overall_quality
        )

        logger.info(
            f"Successfully ingested production reading for well {payload.well_code}",
            extra={"structured_data": {
                "event": "READING_INGESTED",
                "well": payload.well_code,
                "wc_percent": norm_wc,
                "quality": overall_quality.value,
                "value_type": value_type.value
            }}
        )
        return reading, False

    @classmethod
    async def ingest_separator_reading(
        cls,
        db: AsyncSession,
        payload: SeparatorReadingCreate
    ) -> Tuple[SeparatorReading, bool]:
        """
        Ingests separator reading with physical range validation, unit normalization, and idempotency.
        """
        rate_limiter.check_rate_limit(payload.source.value, payload.well_code)
        await cls._ensure_well_exists(db, payload.well_code)

        ts_valid, ts_quality, ts_msg = DataValidationService.validate_timestamp(payload.timestamp)
        if not ts_valid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=ts_msg)

        idem_hash = IdempotencyService.generate_hash(
            well_code=payload.well_code,
            timestamp=payload.timestamp,
            source=payload.source.value,
            measurement_type="SEPARATOR_READING",
            source_record_id=payload.source_record_id
        )

        existing_stmt = select(SeparatorReading).where(
            and_(
                SeparatorReading.well_code == payload.well_code,
                SeparatorReading.timestamp == payload.timestamp,
                SeparatorReading.source == payload.source.value
            )
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            return existing, True

        # Validation
        norm_wc, orig_wc, orig_unit, wc_status, wc_msg = DataValidationService.normalize_water_cut(
            payload.water_cut, payload.wc_unit, is_unavailable=payload.is_data_unavailable
        )
        if wc_status == DataQualityStatus.INVALID:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=wc_msg)

        # Validate pressure if provided
        validated_pressure = None
        if payload.pressure is not None:
            validated_pressure, p_status, p_msg = DataValidationService.validate_pressure(payload.pressure, "psi")
            if p_status == DataQualityStatus.INVALID:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=p_msg)

        overall_quality = wc_status if wc_status != DataQualityStatus.VALID else ts_quality

        reading = SeparatorReading(
            timestamp=payload.timestamp,
            well_code=payload.well_code,
            source=payload.source.value,
            pressure=validated_pressure,
            flow_rate=payload.flow_rate,
            water_cut=norm_wc,
            original_wc_value=orig_wc,
            original_wc_unit=orig_unit,
            oil_rate=payload.oil_rate,
            water_rate=payload.water_rate,
            gas_rate=payload.gas_rate,
            value_type=ValueType.MEASURED.value,
            quality_status=overall_quality.value,
            validation_status=overall_quality.value,
            received_at=datetime.now(timezone.utc),
            source_system=payload.source_system,
            source_record_id=payload.source_record_id,
            idempotency_hash=idem_hash
        )
        db.add(reading)
        await db.commit()
        await db.refresh(reading)

        # Trigger surveillance on separator water cut
        await SurveillanceService.evaluate_water_cut_surveillance(
            db=db,
            well_code=payload.well_code,
            wc_percent=norm_wc,
            timestamp=payload.timestamp,
            source=payload.source,
            quality_status=overall_quality
        )

        return reading, False

    @classmethod
    async def ingest_manual_reading(
        cls,
        db: AsyncSession,
        payload: ManualReadingCreate
    ) -> Tuple[ManualReading, bool]:
        """
        Ingests manual input preserving who entered the value, when, and original unit.
        """
        rate_limiter.check_rate_limit("MANUAL", payload.well_code)
        await cls._ensure_well_exists(db, payload.well_code)

        ts_valid, ts_quality, ts_msg = DataValidationService.validate_timestamp(payload.timestamp)
        if not ts_valid:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=ts_msg)

        idem_hash = IdempotencyService.generate_hash(
            well_code=payload.well_code,
            timestamp=payload.timestamp,
            source="MANUAL",
            measurement_type=payload.measurement_type.value,
            source_record_id=payload.entered_by
        )

        existing_stmt = select(ManualReading).where(
            and_(
                ManualReading.well_code == payload.well_code,
                ManualReading.timestamp == payload.timestamp,
                ManualReading.measurement_type == payload.measurement_type.value,
                ManualReading.entered_by == payload.entered_by
            )
        )
        existing = (await db.execute(existing_stmt)).scalar_one_or_none()
        if existing:
            return existing, True

        # Validation per measurement type
        val_status = DataQualityStatus.VALID
        if payload.is_data_unavailable or payload.value is None:
            val_status = DataQualityStatus.DATA_UNAVAILABLE
        elif payload.measurement_type == MeasurementType.WATER_CUT or payload.measurement_type == MeasurementType.MANUAL_WATER_CUT:
            _, _, _, wc_status, wc_msg = DataValidationService.normalize_water_cut(payload.value, payload.unit)
            if wc_status == DataQualityStatus.INVALID:
                raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=wc_msg)
            val_status = wc_status

        manual_entry = ManualReading(
            well_code=payload.well_code,
            measurement_type=payload.measurement_type.value,
            value=payload.value if val_status != DataQualityStatus.DATA_UNAVAILABLE else None,
            unit=payload.unit,
            timestamp=payload.timestamp,
            source=SourceCategory.MANUAL.value,
            entered_by=payload.entered_by,
            validation_status=val_status.value,
            created_at=datetime.now(timezone.utc),
            idempotency_hash=idem_hash
        )
        db.add(manual_entry)
        await db.commit()
        await db.refresh(manual_entry)

        # If manual reading is water cut and valid, run surveillance
        if (payload.measurement_type in {MeasurementType.WATER_CUT, MeasurementType.MANUAL_WATER_CUT}):
            norm_val = payload.value
            if payload.unit in {"fraction", "frac"} and payload.value is not None:
                norm_val = payload.value * 100.0
            await SurveillanceService.evaluate_water_cut_surveillance(
                db=db,
                well_code=payload.well_code,
                wc_percent=norm_val,
                timestamp=payload.timestamp,
                source=SourceCategory.MANUAL,
                quality_status=val_status
            )

        return manual_entry, False
