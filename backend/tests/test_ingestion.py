import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from app.services.ingestion import IngestionService
from app.schemas.common import DataQualityStatus, SourceCategory, MeasurementType
from app.schemas.readings import ProductionReadingCreate
from app.schemas.separator import SeparatorReadingCreate
from app.schemas.manual import ManualReadingCreate
from app.models.readings import ProductionReading
from app.models.well import Well


@pytest.mark.asyncio
async def test_ingest_production_reading_valid(db_session):
    now = datetime.now(timezone.utc)
    payload = ProductionReadingCreate(
        well_code="WELL-TEST-01",
        timestamp=now,
        oil_rate=450.0,
        water_rate=150.0,
        gas_rate=320.0,
        wc_value=25.0,
        wc_unit="%",
        source=SourceCategory.SOFTWARE_API,
        source_system="Historian-PI"
    )

    reading, is_duplicate = await IngestionService.ingest_production_reading(db_session, payload)
    assert not is_duplicate
    assert reading.well_code == "WELL-TEST-01"
    assert reading.wc_percent == 25.0
    assert reading.quality_status == DataQualityStatus.VALID.value
    assert reading.source == "SOFTWARE_API"


@pytest.mark.asyncio
async def test_ingest_production_reading_idempotency_retry(db_session):
    now = datetime.now(timezone.utc)
    payload = ProductionReadingCreate(
        well_code="WELL-TEST-02",
        timestamp=now,
        oil_rate=500.0,
        water_rate=200.0,
        wc_value=28.5,
        wc_unit="%",
        source=SourceCategory.SOFTWARE_API
    )

    # First attempt
    reading1, is_duplicate1 = await IngestionService.ingest_production_reading(db_session, payload)
    assert not is_duplicate1

    # Second attempt with same payload (e.g. network retry)
    reading2, is_duplicate2 = await IngestionService.ingest_production_reading(db_session, payload)
    assert is_duplicate2
    assert reading1.idempotency_hash == reading2.idempotency_hash


@pytest.mark.asyncio
async def test_ingest_production_reading_data_unavailable_preservation(db_session):
    now = datetime.now(timezone.utc)
    # External source reports Water Cut is unavailable
    payload = ProductionReadingCreate(
        well_code="WELL-TEST-03",
        timestamp=now,
        oil_rate=300.0,
        is_data_unavailable=True,
        source=SourceCategory.SOFTWARE_API
    )

    reading, _ = await IngestionService.ingest_production_reading(db_session, payload)
    # Crucial requirement: Must never silently become WC = 0!
    assert reading.wc_percent is None
    assert reading.wc_percent != 0.0
    assert reading.quality_status == DataQualityStatus.DATA_UNAVAILABLE.value


@pytest.mark.asyncio
async def test_ingest_separator_reading_fraction_normalization(db_session):
    now = datetime.now(timezone.utc)
    payload = SeparatorReadingCreate(
        well_code="WELL-TEST-04",
        timestamp=now,
        pressure=420.0,
        flow_rate=1500.0,
        water_cut=0.65,
        wc_unit="fraction",
        source=SourceCategory.SOFTWARE_API
    )

    reading, is_dup = await IngestionService.ingest_separator_reading(db_session, payload)
    assert not is_dup
    # Normalized to 65.0%
    assert reading.water_cut == pytest.approx(65.0, rel=1e-3)
    # Original fraction and unit preserved
    assert reading.original_wc_value == 0.65
    assert reading.original_wc_unit == "fraction"


@pytest.mark.asyncio
async def test_ingest_manual_reading_provenance(db_session):
    now = datetime.now(timezone.utc)
    payload = ManualReadingCreate(
        well_code="WELL-TEST-05",
        measurement_type=MeasurementType.MANUAL_WATER_CUT,
        value=32.0,
        unit="%",
        timestamp=now,
        entered_by="Eng. Sarah Al-Otaibi"
    )

    manual, is_dup = await IngestionService.ingest_manual_reading(db_session, payload)
    assert not is_dup
    assert manual.entered_by == "Eng. Sarah Al-Otaibi"
    assert manual.source == "MANUAL"
    assert manual.value == 32.0
    assert manual.validation_status == DataQualityStatus.VALID.value
