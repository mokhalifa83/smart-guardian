"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C
Virtual Separator Operational Reconciliation Service (reconciliation_service.py)

Reconciles real-time Virtual Separator estimates against Certified Reference Measurements
(e.g., Test Separator physical test, Lab centrifuge cut, Multiphase Flow Meter calibration).
Follows Order 3 requirements:
- Computes relative difference and percentage error
- Categorizes calibration status (EXCELLENT, ACCEPTABLE, CALIBRATION_REQUIRED)
- Derives field calibration factor C_f = V_ref / V_est
- Triggers engineering audit alert when deviation exceeds configurable tolerance (default 10%)
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class VirtualSeparatorReconciliationService:
    """
    Reconciliation engine comparing Virtual Separator estimates to Certified Reference Measurements.
    """

    @classmethod
    def reconcile_virtual_vs_reference(
        cls,
        entity_code: str,
        virtual_oil_rate_stbd: float,
        virtual_water_cut_pct: float,
        reference_oil_rate_stbd: float,
        reference_water_cut_pct: float,
        tolerance_pct: float = 10.0,
        virtual_gas_rate_mscfd: Optional[float] = None,
        reference_gas_rate_mscfd: Optional[float] = None
    ) -> EngineeringResult:
        """
        Reconciles Virtual vs Reference measurements.
        Relative error: (Virtual - Reference) / Reference * 100%
        """
        inputs = {
            "entity_code": entity_code,
            "virtual_oil_rate_stbd": virtual_oil_rate_stbd,
            "virtual_water_cut_pct": virtual_water_cut_pct,
            "reference_oil_rate_stbd": reference_oil_rate_stbd,
            "reference_water_cut_pct": reference_water_cut_pct,
            "tolerance_pct": tolerance_pct,
            "virtual_gas_rate_mscfd": virtual_gas_rate_mscfd,
            "reference_gas_rate_mscfd": reference_gas_rate_mscfd
        }

        if reference_oil_rate_stbd <= 0:
            return EngineeringResult(
                calculation_name="VIRTUAL_SEPARATOR_RECONCILIATION",
                value=None,
                unit="dimensionless",
                inputs=inputs,
                model="Virtual Separator Operational Reconciliation",
                status=EngineeringStatus.INVALID_INPUT.value,
                warnings=["Reference oil rate must be strictly positive for reconciliation."]
            )

        # Rate error
        oil_diff = virtual_oil_rate_stbd - reference_oil_rate_stbd
        oil_error_pct = (oil_diff / reference_oil_rate_stbd) * 100.0
        calibration_factor = reference_oil_rate_stbd / virtual_oil_rate_stbd if virtual_oil_rate_stbd > 0 else 1.0

        # Water cut error
        wc_diff = virtual_water_cut_pct - reference_water_cut_pct

        # Determine status
        abs_err = abs(oil_error_pct)
        if abs_err <= 5.0:
            recon_status = "EXCELLENT_AGREEMENT"
            diag_interp = f"Virtual separator oil estimate is within {abs_err:.1f}% of reference physical measurement."
            rec_action = "No calibration change required. Continue operational surveillance."
            result_status = EngineeringStatus.VALID.value
        elif abs_err <= tolerance_pct:
            recon_status = "ACCEPTABLE_DEVIATION"
            diag_interp = f"Virtual separator oil estimate deviates by {oil_error_pct:+.1f}% from reference (within {tolerance_pct}% tolerance)."
            rec_action = f"Apply fine calibration factor Cf = {calibration_factor:.4f} during next scheduled update."
            result_status = EngineeringStatus.VALID.value
        else:
            recon_status = "CALIBRATION_REQUIRED"
            diag_interp = (
                f"Virtual separator oil estimate deviates by {oil_error_pct:+.1f}% from certified reference. "
                f"Exceeds acceptable tolerance of {tolerance_pct}%."
            )
            rec_action = f"Recalibrate Virtual Separator PVT and choke discharge coefficients. Recommended factor Cf = {calibration_factor:.4f}."
            result_status = EngineeringStatus.CALIBRATION_REQUIRED.value

        warnings = []
        if abs_err > tolerance_pct:
            warnings.append(
                f"RECONCILIATION ALERT: Virtual rate ({virtual_oil_rate_stbd:.1f} STBD) differs significantly "
                f"from reference measurement ({reference_oil_rate_stbd:.1f} STBD). Deviation: {oil_error_pct:+.1f}%."
            )

        return EngineeringResult(
            calculation_name="VIRTUAL_SEPARATOR_RECONCILIATION",
            value=round(oil_error_pct, 2),
            unit="percent",
            inputs=inputs,
            model="Virtual Separator vs Physical Reference Metrology Reconciliation",
            assumptions=[
                "Reference measurement acquired under stabilized test conditions with calibrated separator instrumentation",
                "Virtual estimate computed from simultaneous wellhead telemetry and PVT fluid properties"
            ],
            limitations=[
                "Uncertainty in reference meter fluid shrinkage or emulsion layer affects reference ground truth."
            ],
            evidence={
                "entity_code": entity_code,
                "reconciliation_status": recon_status,
                "oil_rate_error_pct": round(oil_error_pct, 2),
                "oil_rate_absolute_difference_stbd": round(oil_diff, 2),
                "water_cut_absolute_difference_pct": round(wc_diff, 2),
                "derived_calibration_factor": round(calibration_factor, 4),
                "tolerance_pct": tolerance_pct,
                "recommended_action": rec_action
            },
            status=result_status,
            provenance={
                "service": "VirtualSeparatorReconciliationService",
                "version": "Step2C-v1.2",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            observed_pattern=recon_status,
            diagnostic_interpretation=diag_interp,
            warnings=warnings
        )
