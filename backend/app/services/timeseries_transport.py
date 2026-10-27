"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C
Time-Series Transport Adapter (timeseries_transport.py)

Provides interoperability with time-series historians (InfluxDB Line Protocol, TimescaleDB, OSI PI)
while strictly preserving TimescaleDB/PostgreSQL as the single canonical reservoir engineering database.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from app.services.reservoir.integration_contracts import FieldSensorTelemetryContract


class TimeseriesTransportAdapter:
    """
    Adapter converting typed telemetry into InfluxDB Line Protocol or external historian formats.
    Used for edge forwarding and historian export without bypassing canonical database storage.
    """

    @staticmethod
    def format_to_influx_line_protocol(
        telemetry: FieldSensorTelemetryContract,
        measurement_name: str = "field_telemetry"
    ) -> str:
        """
        Converts FieldSensorTelemetryContract to standard InfluxDB Line Protocol:
        measurement,tag_set field_set timestamp_ns
        """
        tags = f"well_code={telemetry.well_code},source={telemetry.source_type.value},quality={telemetry.quality_flag}"
        fields_list = []

        if telemetry.pressure_wh_psia is not None:
            fields_list.append(f"pressure_wh_psia={telemetry.pressure_wh_psia}")
        if telemetry.temperature_wh_f is not None:
            fields_list.append(f"temperature_wh_f={telemetry.temperature_wh_f}")
        if telemetry.choke_size_64ths is not None:
            fields_list.append(f"choke_size_64ths={telemetry.choke_size_64ths}")
        if telemetry.water_cut_raw is not None:
            fields_list.append(f"water_cut_raw={telemetry.water_cut_raw}")
        if telemetry.oil_rate_raw_stbd is not None:
            fields_list.append(f"oil_rate_raw_stbd={telemetry.oil_rate_raw_stbd}")
        if telemetry.water_rate_raw_bpd is not None:
            fields_list.append(f"water_rate_raw_bpd={telemetry.water_rate_raw_bpd}")
        if telemetry.gas_rate_raw_mscfd is not None:
            fields_list.append(f"gas_rate_raw_mscfd={telemetry.gas_rate_raw_mscfd}")

        if not fields_list:
            fields_list.append("status_ping=1.0")

        fields = ",".join(fields_list)
        ts_nanoseconds = int(telemetry.timestamp.timestamp() * 1e9)

        return f"{measurement_name},{tags} {fields} {ts_nanoseconds}"

    @classmethod
    def batch_export_to_line_protocol(
        cls,
        telemetry_batch: List[FieldSensorTelemetryContract],
        measurement_name: str = "field_telemetry"
    ) -> str:
        """Exports a batch of telemetry records as newline-delimited InfluxDB Line Protocol."""
        lines = [cls.format_to_influx_line_protocol(rec, measurement_name) for rec in telemetry_batch]
        return "\n".join(lines)
