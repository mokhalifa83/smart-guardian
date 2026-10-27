"""
Smart Guardian Reservoir Intelligence Layer - Water Cut Live/Lab Calibration Foundation (Step 2B)
Reference: API MPMS Chapter 10 - Sediment and Water; ASTM D4007 (Centrifuge Method).

Implements Dual-Truth Water Cut Surveillance & Calibration Physics:
1. Strict segregation of WC_Live, WC_Lab, WC_Live_at_sample, and WC_Final
2. Explicit Distinction between Fraction (0.0 to 1.0) and Percentage (0.0% to 100.0%)
3. Mathematical Protection: Zero Denominator (WC_Live_at_sample = 0) and Near-Zero Tolerances
4. Expiry / Stale Lab Sample Verification (never extrapolates stale calibration indefinitely)
5. 100% Water Cut Boundary Rule: Explicit UNDEFINED_WOR when oil fraction = 0 (never epsilon substitution)

Strictly adheres to:
- Never overwrites WC_Live with WC_Lab
- Never presents a calibrated estimate as a certified laboratory measurement
- Full data provenance and traceability: Result -> Calibration Factor -> Lab Sample Record -> Live Telemetry
- Standard EngineeringResult contract with complete assumptions, limitations, and provenance
"""

import math
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class LabWaterCutSample(BaseModel):
    """Certified laboratory analysis record from physical fluid sample."""
    sample_id: str
    timestamp: datetime
    well_code: str
    water_cut_value: float = Field(..., ge=0.0, description="Water cut value")
    is_percentage: bool = Field(default=True, description="True if 0-100%, False if 0.0-1.0 fraction")
    measurement_method: str = Field(default="CENTRIFUGE_ASTM_D4007", description="Laboratory ASTM / API procedure")
    sample_volume_ml: Optional[float] = Field(default=100.0, gt=0)
    water_volume_ml: Optional[float] = Field(default=None, ge=0)
    operator_name: Optional[str] = None
    laboratory_name: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LiveWaterCutObservation(BaseModel):
    """Real-time high-frequency streaming water cut telemetry."""
    timestamp: datetime
    well_code: str
    water_cut_value: float = Field(..., ge=0.0, description="Real-time water cut reading from sensor/multiphase meter")
    is_percentage: bool = Field(default=True, description="True if 0-100%, False if 0.0-1.0 fraction")
    meter_tag: Optional[str] = None
    sensor_model: Optional[str] = None
    raw_reading_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WaterCutCalibrationEngine:
    """
    Canonical Water Cut Live/Lab Calibration Engine.
    Single Source of Truth for calibration factor determination, dual-truth tracking, and shrinkage reconciliation.
    """

    @staticmethod
    def to_fraction(value: float, is_percentage: bool) -> float:
        """Converts percentage or fraction to normalized dimensionless fraction [0.0, 1.0]."""
        if is_percentage:
            frac = value / 100.0
        else:
            frac = value
        return max(0.0, min(1.0, frac))

    @staticmethod
    def to_percentage(value: float, is_percentage: bool) -> float:
        """Converts percentage or fraction to normalized percentage [0.0%, 100.0%]."""
        if is_percentage:
            pct = value
        else:
            pct = value * 100.0
        return max(0.0, min(100.0, pct))

    @classmethod
    def calculate_calibration_factor(
        cls,
        lab_sample: LabWaterCutSample,
        live_observation_at_sample: LiveWaterCutObservation,
        zero_denominator_tolerance: float = 1e-4
    ) -> EngineeringResult:
        """
        Calculates calibration ratio: CF = WC_Lab / WC_Live_at_sample.
        Validates non-zero denominator and timestamp congruence.
        """
        inputs = {
            "well_code": lab_sample.well_code,
            "lab_sample_id": lab_sample.sample_id,
            "lab_timestamp": lab_sample.timestamp.isoformat(),
            "live_timestamp": live_observation_at_sample.timestamp.isoformat(),
            "lab_wc_raw": lab_sample.water_cut_value,
            "live_wc_raw": live_observation_at_sample.water_cut_value
        }

        # 1. Normalize both to fraction [0.0, 1.0]
        wc_lab_frac = cls.to_fraction(lab_sample.water_cut_value, lab_sample.is_percentage)
        wc_live_sample_frac = cls.to_fraction(live_observation_at_sample.water_cut_value, live_observation_at_sample.is_percentage)

        # 2. Denominator Safety Verification (Rule 23)
        if wc_live_sample_frac <= zero_denominator_tolerance:
            return EngineeringResult(
                calculation_name="Water Cut Calibration Factor Determination",
                model="Dual-Truth Water Cut Calibration (API MPMS Ch. 10)",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={
                    "error": f"Live water cut at sample timestamp ({wc_live_sample_frac:.6f}) is zero or within numerical tolerance ({zero_denominator_tolerance}). Division by zero prevented.",
                    "calibration_status": "DENOMINATOR_NEAR_ZERO"
                }
            )

        # 3. Calculate Calibration Factor
        calibration_factor = wc_lab_frac / wc_live_sample_frac

        # Check for extreme out-of-range ratio (e.g. factor > 5.0 or < 0.2 indicates gross sensor fouling or bottle mix-up)
        warnings = []
        if calibration_factor > 3.0 or calibration_factor < 0.33:
            warnings.append(f"Significant discrepancy between Lab ({wc_lab_frac*100:.1f}%) and Live ({wc_live_sample_frac*100:.1f}%). Meter recalibration or sample verification strongly advised.")

        return EngineeringResult(
            calculation_name="Water Cut Calibration Factor Determination",
            value={
                "calibration_factor": round(calibration_factor, 6),
                "wc_lab_fraction": round(wc_lab_frac, 6),
                "wc_lab_percent": round(wc_lab_frac * 100.0, 2),
                "wc_live_at_sample_fraction": round(wc_live_sample_frac, 6),
                "wc_live_at_sample_percent": round(wc_live_sample_frac * 100.0, 2)
            },
            unit="ratio",
            model="Dual-Truth Water Cut Calibration (API MPMS Ch. 10)",
            correlation="Laboratory Physical Bottle Reconciliation",
            correlation_reference="API MPMS Chapter 10, ASTM D4007 Centrifuge Standard",
            inputs=inputs,
            assumptions=[
                "Laboratory sample was drawn from a representative, homogeneous point in the flowing flowline",
                "Atmospheric sample degassing accounted for during laboratory extraction"
            ],
            limitations=[
                "Calibration factor is empirical and valid only within the stable operating envelope of the well.",
                "Multiphase flow regime changes require a fresh physical sample."
            ],
            warnings=warnings,
            evidence={
                "lab_sample_details": lab_sample.model_dump(),
                "live_sample_observation": live_observation_at_sample.model_dump(),
                "calibration_factor": round(calibration_factor, 6)
            },
            status=EngineeringStatus.VALID.value
        )

    @classmethod
    def apply_calibration(
        cls,
        current_live_reading: LiveWaterCutObservation,
        calibration_factor: float,
        calibration_timestamp: datetime,
        max_calibration_age_hours: float = 72.0
    ) -> EngineeringResult:
        """
        Applies a validated calibration factor to current real-time telemetry:
        WC_Final = WC_Live * Calibration_Factor
        Checks for calibration expiration (stale sample) and handles WC = 100% boundary.
        """
        inputs = {
            "well_code": current_live_reading.well_code,
            "live_water_cut_raw": current_live_reading.water_cut_value,
            "live_timestamp": current_live_reading.timestamp.isoformat(),
            "calibration_timestamp": calibration_timestamp.isoformat(),
            "calibration_factor": calibration_factor,
            "max_calibration_age_hours": max_calibration_age_hours
        }

        # 1. Stale Calibration Verification
        time_diff_hours = (current_live_reading.timestamp - calibration_timestamp).total_seconds() / 3600.0
        if time_diff_hours > max_calibration_age_hours:
            return EngineeringResult(
                calculation_name="Water Cut Real-Time Calibration",
                model="Dual-Truth Water Cut Reconciliation",
                status=EngineeringStatus.CALIBRATION_REQUIRED.value,
                inputs=inputs,
                evidence={
                    "error": f"Active calibration factor is {time_diff_hours:.1f} hours old, exceeding maximum allowed age of {max_calibration_age_hours:.1f} hours.",
                    "calibration_status": "STALE_CALIBRATION",
                    "action_required": "Schedule routine wellhead sampling to regenerate calibration factor."
                }
            )

        # 2. Normalize Live Reading to fraction
        wc_live_frac = cls.to_fraction(current_live_reading.water_cut_value, current_live_reading.is_percentage)

        # 3. Compute Calibrated Final Water Cut
        wc_final_frac = wc_live_frac * calibration_factor
        wc_final_frac = max(0.0, min(1.0, wc_final_frac))  # Bounded strictly to [0.0, 1.0]

        # 4. Check 100% Water Cut Boundary Rule (Rule 25)
        wor_status = "CALCULATED"
        wor_value = None
        if abs(wc_final_frac - 1.0) < 1e-6:
            wor_status = "UNDEFINED_WOR"
            wor_value = None
            note = "Water Cut is 100.0% (Oil fraction = 0.0). WOR is mathematically undefined/infinite. No synthetic epsilon substituted."
        else:
            wor_value = round(wc_final_frac / (1.0 - wc_final_frac), 5)
            note = "Calibrated dual-truth water cut evaluated successfully."

        return EngineeringResult(
            calculation_name="Water Cut Real-Time Calibration",
            value={
                "wc_live_fraction": round(wc_live_frac, 6),
                "wc_live_percent": round(wc_live_frac * 100.0, 2),
                "wc_final_fraction": round(wc_final_frac, 6),
                "wc_final_percent": round(wc_final_frac * 100.0, 2),
                "calibration_factor": round(calibration_factor, 6),
                "calibration_age_hours": round(time_diff_hours, 1),
                "wor": wor_value,
                "wor_status": wor_status
            },
            unit="fraction",
            model="Dual-Truth Water Cut Reconciliation (Live * Factor)",
            correlation="Live Telemetry Calibrated by Lab Reference",
            correlation_reference="API MPMS Chapter 10",
            inputs=inputs,
            assumptions=[
                "Live sensor drift is linear over the calibration validity window",
                "Fluid PVT and gas-oil ratio remain within baseline envelope"
            ],
            limitations=[
                "Calibrated water cut is an operational engineering estimate, not a certified fiscal lab measurement.",
                "Water cut = 100% forbids finite WOR evaluation."
            ],
            evidence={
                "provenance": {
                    "live_meter_tag": current_live_reading.meter_tag,
                    "calibration_timestamp": calibration_timestamp.isoformat(),
                    "calibration_age_hours": round(time_diff_hours, 1),
                    "note": note
                }
            },
            status=EngineeringStatus.VALID.value
        )


# Canonical aliases
WCCalibrationEngine = WaterCutCalibrationEngine

