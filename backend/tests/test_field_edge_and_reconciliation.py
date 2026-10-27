"""
Test Suite for Step 2C Edge Connector, Transport, Reconciliation, and Daily Report
Validates:
1. EdgeConnector one-way ingestion and rejection of control commands
2. InfluxDB Line Protocol conversion via TimeseriesTransportAdapter
3. Virtual Separator vs Reference reconciliation and alert triggering
4. DailyReportService 08:00 summary aggregation
"""

import pytest
from datetime import datetime, timezone
from app.services.edge_connector import EdgeConnector
from app.services.timeseries_transport import TimeseriesTransportAdapter
from app.services.reconciliation_service import VirtualSeparatorReconciliationService
from app.services.daily_report_service import DailyReportService
from app.services.opcua_client import ReadOnlyViolationError
from app.services.reservoir.contracts import EngineeringStatus


def test_edge_connector_ingestion_and_quality():
    connector = EdgeConnector()
    valid_payload = {
        "well_code": "PROD-01",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pressure_wh_psia": 1450.0,
        "temperature_wh_f": 135.0,
        "choke_size_64ths": 32.0,
        "water_cut_raw": 28.5,
        "oil_rate_raw_stbd": 850.0
    }

    telemetry, quality = connector.validate_and_parse_telemetry(valid_payload)
    assert quality == "GOOD"
    assert telemetry.well_code == "PROD-01"
    assert telemetry.pressure_wh_psia == 1450.0
    assert telemetry.traceability_hash is not None


def test_edge_connector_rejects_control_payload():
    connector = EdgeConnector()
    control_payload = {
        "well_code": "PROD-01",
        "command": "SET_CHOKE_OPENING",
        "setpoint": 48.0
    }

    with pytest.raises(ReadOnlyViolationError) as exc_info:
        connector.validate_and_parse_telemetry(control_payload)

    assert "READ_ONLY_VIOLATION" in str(exc_info.value)


def test_timeseries_influx_line_protocol():
    connector = EdgeConnector()
    payload = {
        "well_code": "WELL-X",
        "timestamp": "2026-10-26T12:00:00Z",
        "pressure_wh_psia": 1200.0,
        "water_cut_raw": 15.0
    }
    telemetry, _ = connector.validate_and_parse_telemetry(payload)
    line = TimeseriesTransportAdapter.format_to_influx_line_protocol(telemetry)

    assert line.startswith("field_telemetry,well_code=WELL-X")
    assert "pressure_wh_psia=1200.0" in line
    assert "water_cut_raw=15.0" in line


def test_virtual_separator_reconciliation_excellent_and_alert():
    # Case 1: Excellent agreement (< 5%)
    res_exc = VirtualSeparatorReconciliationService.reconcile_virtual_vs_reference(
        entity_code="SEP-01",
        virtual_oil_rate_stbd=1020.0,
        virtual_water_cut_pct=30.0,
        reference_oil_rate_stbd=1000.0,
        reference_water_cut_pct=29.5
    )
    assert res_exc.status == EngineeringStatus.VALID.value
    assert res_exc.evidence["reconciliation_status"] == "EXCELLENT_AGREEMENT"
    assert res_exc.evidence["derived_calibration_factor"] < 1.0

    # Case 2: Calibration required (> 10%)
    res_cal = VirtualSeparatorReconciliationService.reconcile_virtual_vs_reference(
        entity_code="SEP-01",
        virtual_oil_rate_stbd=1250.0,
        virtual_water_cut_pct=30.0,
        reference_oil_rate_stbd=1000.0,
        reference_water_cut_pct=25.0,
        tolerance_pct=10.0
    )
    assert res_cal.status == EngineeringStatus.CALIBRATION_REQUIRED.value
    assert res_cal.evidence["reconciliation_status"] == "CALIBRATION_REQUIRED"
    assert len(res_cal.warnings) >= 1


def test_daily_report_service_generation():
    report = DailyReportService.generate_daily_report(
        field_name="NORTH_DOME_FIELD",
        vrr_value=1.04
    )
    assert report.field_name == "NORTH_DOME_FIELD"
    assert report.reporting_standard_time == "08:00 UTC"
    assert report.production_summary["oil_rate_stbd"] > 0
    assert report.reservoir_surveillance["field_vrr"] == 1.04
    assert report.reservoir_surveillance["vrr_status"] == "BALANCED"
    assert len(report.engineering_recommendations) >= 2
