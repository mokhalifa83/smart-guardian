import pytest
from app.database.session import Base
from app.models.well import Well
from app.models.well_config import WellConfig
from app.models.readings import ProductionReading
from app.models.separator import SeparatorReading
from app.models.manual import ManualReading
from app.models.alert import Alert
from app.models.analysis import AnalysisResult


def test_models_metadata_registered():
    table_names = set(Base.metadata.tables.keys())
    expected = {
        "wells",
        "well_configs",
        "production_readings",
        "separator_readings",
        "manual_readings",
        "alerts",
        "analysis_results",
    }
    assert expected.issubset(table_names)


def test_timescaledb_primary_keys_include_timestamp():
    # TimescaleDB requires hypertable primary key to include the partitioning column (timestamp)
    prod_pk = [c.name for c in ProductionReading.__table__.primary_key.columns]
    assert "timestamp" in prod_pk
    assert "well_code" in prod_pk
    assert "source" in prod_pk

    sep_pk = [c.name for c in SeparatorReading.__table__.primary_key.columns]
    assert "timestamp" in sep_pk
    assert "well_code" in sep_pk
    assert "source" in sep_pk
