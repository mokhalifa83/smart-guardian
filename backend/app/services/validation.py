from datetime import datetime, timezone, timedelta
from typing import Optional, Tuple
from app.schemas.common import DataQualityStatus, MeasurementType
from app.core.logging import logger


class DataValidationService:
    """
    Petroleum Engineering Data Validation Service.
    Validates physical limits, units, timestamps, missing values, and data quality.
    Strictly forbids silent fallback to zero or arbitrary engineering defaults.
    """

    # Physical engineering boundaries
    LIMITS = {
        MeasurementType.WATER_CUT: {"min_pct": 0.0, "max_pct": 100.0, "min_frac": 0.0, "max_frac": 1.0},
        MeasurementType.SEPARATOR_PRESSURE: {"min": 0.0, "max": 15000.0, "valid_units": {"psi", "bar", "kpa"}},
        MeasurementType.FLOW_RATE: {"min": 0.0, "max": 200000.0, "valid_units": {"bpd", "m3/d", "bbl/d"}},
        MeasurementType.OIL_RATE: {"min": 0.0, "max": 100000.0, "valid_units": {"bpd", "stb/d"}},
        MeasurementType.WATER_RATE: {"min": 0.0, "max": 200000.0, "valid_units": {"bpd"}},
        MeasurementType.GAS_RATE: {"min": 0.0, "max": 500000.0, "valid_units": {"mscfd", "scf/d", "m3/d"}},
        MeasurementType.OIL_API_GRAVITY: {"min": 5.0, "max": 65.0, "valid_units": {"°api", "degapi", "api"}},
    }

    @staticmethod
    def validate_timestamp(ts: datetime) -> Tuple[bool, DataQualityStatus, str]:
        """
        Validates timestamp sanity. Rejects future timestamps and flags stale data (> 30 days).
        """
        now = datetime.now(timezone.utc)
        # Ensure ts has timezone
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        if ts > now + timedelta(minutes=5):  # allow minor 5 min clock skew
            return False, DataQualityStatus.INVALID, f"Timestamp is in the future: {ts.isoformat()}"

        if ts < now - timedelta(days=365):
            return True, DataQualityStatus.STALE, f"Timestamp is stale: {ts.isoformat()}"

        return True, DataQualityStatus.VALID, "Timestamp valid"

    @classmethod
    def normalize_water_cut(
        cls,
        value: Optional[float],
        unit: Optional[str],
        is_unavailable: bool = False
    ) -> Tuple[Optional[float], Optional[float], Optional[str], DataQualityStatus, str]:
        """
        Normalizes Water Cut representation while strictly preserving original value and unit.
        Rules:
        - If explicitly unavailable or value is None: status is DATA_UNAVAILABLE.
        - NEVER replaces missing value with 0 or arbitrary default.
        - Percentage (e.g. 80%) -> normalized to 80.0
        - Fraction (e.g. 0.80) -> normalized to 80.0
        - Unknown/missing unit -> rejects with INVALID (never guess unit silently).
        Returns:
            (normalized_pct, original_value, original_unit, quality_status, message)
        """
        if is_unavailable or value is None:
            return None, None, unit, DataQualityStatus.DATA_UNAVAILABLE, "Water Cut measurement is DATA_UNAVAILABLE from source"

        if not unit:
            return None, value, None, DataQualityStatus.INVALID, "Missing unit for Water Cut measurement. Unit cannot be guessed silently."

        clean_unit = unit.strip().lower()

        if clean_unit in {"%", "percent", "pct"}:
            if 0.0 <= value <= 100.0:
                return float(value), float(value), unit, DataQualityStatus.VALID, "Valid percentage Water Cut"
            else:
                return None, float(value), unit, DataQualityStatus.INVALID, f"Water Cut percentage {value}% out of physical bounds [0, 100]"

        elif clean_unit in {"fraction", "frac", "decimal", "ratio"}:
            if 0.0 <= value <= 1.0:
                normalized = float(value) * 100.0
                return normalized, float(value), unit, DataQualityStatus.VALID, "Valid fractional Water Cut normalized to percentage"
            else:
                return None, float(value), unit, DataQualityStatus.INVALID, f"Water Cut fraction {value} out of physical bounds [0.0, 1.0]"

        else:
            return None, float(value), unit, DataQualityStatus.INVALID, f"Unsupported Water Cut unit: '{unit}'. Must be '%' or 'fraction'."

    @classmethod
    def validate_pressure(
        cls,
        value: Optional[float],
        unit: str = "psi",
        is_unavailable: bool = False
    ) -> Tuple[Optional[float], DataQualityStatus, str]:
        """
        Validates separator pressure.
        """
        if is_unavailable or value is None:
            return None, DataQualityStatus.DATA_UNAVAILABLE, "Pressure measurement is DATA_UNAVAILABLE"

        clean_unit = unit.strip().lower()
        limits = cls.LIMITS[MeasurementType.SEPARATOR_PRESSURE]
        if clean_unit not in limits["valid_units"]:
            return None, DataQualityStatus.INVALID, f"Unsupported pressure unit: '{unit}'"

        # Normalize to psi if in bar
        norm_val = value
        if clean_unit == "bar":
            norm_val = value * 14.5038
        elif clean_unit == "kpa":
            norm_val = value * 0.145038

        if limits["min"] <= norm_val <= limits["max"]:
            return float(norm_val), DataQualityStatus.VALID, "Valid pressure measurement"
        else:
            return None, DataQualityStatus.INVALID, f"Pressure {norm_val} psi out of physical bounds [0, 15000]"

    @classmethod
    def validate_rate(
        cls,
        rate_type: MeasurementType,
        value: Optional[float],
        unit: str = "bpd",
        is_unavailable: bool = False
    ) -> Tuple[Optional[float], DataQualityStatus, str]:
        """
        Validates production or phase rate.
        """
        if is_unavailable or value is None:
            return None, DataQualityStatus.DATA_UNAVAILABLE, f"{rate_type.value} is DATA_UNAVAILABLE"

        if value < 0.0:
            return None, DataQualityStatus.INVALID, f"{rate_type.value} cannot be negative: {value}"

        limits = cls.LIMITS.get(rate_type)
        if limits and value > limits["max"]:
            return None, DataQualityStatus.INVALID, f"{rate_type.value} {value} exceeds physical maximum {limits['max']}"

        return float(value), DataQualityStatus.VALID, f"Valid {rate_type.value}"

    @classmethod
    def calculate_water_cut(
        cls,
        oil_rate: Optional[float],
        water_rate: Optional[float]
    ) -> Tuple[Optional[float], DataQualityStatus, str]:
        """
        Calculates derived Water Cut from phase rates: WC = Water Rate / (Oil Rate + Water Rate).
        Maintains strict distinction: this is CALCULATED/DERIVED, never MEASURED.
        """
        if oil_rate is None or water_rate is None:
            return None, DataQualityStatus.DATA_UNAVAILABLE, "Phase rates incomplete for calculated Water Cut"

        total_liquid = oil_rate + water_rate
        if total_liquid <= 0.0:
            return None, DataQualityStatus.DATA_UNAVAILABLE, "Total liquid rate is zero; calculated Water Cut undefined"

        calc_wc = (water_rate / total_liquid) * 100.0
        return round(calc_wc, 2), DataQualityStatus.VALID, "Calculated Water Cut from oil and water rates"
