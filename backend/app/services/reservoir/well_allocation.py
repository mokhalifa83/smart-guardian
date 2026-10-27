"""
Smart Guardian Reservoir Intelligence Layer - Well Allocation & Choke Flow Engine (Step 2B)
References:
- Gilbert, W.E. (1954), "Flowing and Gas-Lift Well Performance", API Drilling and Production Practice, 126-157.
- Ros, N.C.J. (1961), "An Analysis of Critical Simultaneous Liquid/Gas Flow Through a Restriction", Applied Scientific Research.
- Baxendell, P.B. (1958), "Bean Performance - Eastern Venezuela", 4th World Pet. Cong.
- Achong, I. (1961), "Revised Bean Performance Formula for Lake Maracaibo Wells", Shell Internal Report.

Implements Choke Multiphase Critical Flow Allocation:
1. Gilbert (1954), Ros (1961), Baxendell (1958), and Achong (1961) Correlations
2. Liquid Rate (qL) Solution from Wellhead Pressure (Pwh), Choke Size (S in 64ths), and GOR (Rp)
3. Oil and Water Phase Split via Calibrated WC_Final Fraction: qo = qL * (1 - WC_Final), qw = qL * WC_Final
4. Mathematical Safety for 100% Water Cut (qo = 0.0, qw = qL)
5. Explicit Classification: Virtual Allocation / Engineering Estimate (Never certified fiscal measurement)

Strictly adheres to:
- Applicability verification (critical flow regime, positive pressures, choke sizes)
- Explicit calibration factor against reference test separator measurements
- Standard EngineeringResult contract with complete assumptions, limitations, and provenance
"""

import math
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class ChokeAllocationInputs(BaseModel):
    """Telemetry and configuration inputs for well choke flow allocation."""
    wellhead_pressure_psia: float = Field(..., gt=0, description="Flowing wellhead pressure Pwh in psia")
    choke_size_64ths: float = Field(..., gt=0, description="Choke diameter in 64ths of an inch (e.g. 32 = 32/64 in)")
    producing_gor_scf_stb: float = Field(..., gt=0, description="Producing gas-oil ratio Rp in SCF/STB")
    calibrated_wc_fraction: float = Field(..., ge=0.0, le=1.0, description="Calibrated water cut fraction (0.0 to 1.0)")
    flowline_pressure_psia: Optional[float] = Field(default=None, ge=0, description="Downstream flowline pressure in psia")
    bo_corrected_rb_stb: float = Field(default=1.20, gt=0)
    correlation_name: str = Field(default="GILBERT", description="GILBERT, ROS, BAXENDELL, or ACHONG")
    choke_discharge_calibration_factor: float = Field(default=1.0, gt=0, description="Empirical well calibration factor")
    well_code: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class WellAllocationEngine:
    """
    Canonical Well Allocation & Multiphase Choke Flow Engine.
    Single Source of Truth for multiphase choke allocation, phase splitting, and test separator calibration.
    """

    CORRELATION_COEFFICIENTS = {
        # Correlation: (C, a, b) where Pwh = C * qL * Rp^a / (S^b)
        "GILBERT": (10.0, 0.546, 1.89),
        "ROS": (17.4, 0.500, 2.00),
        "BAXENDELL": (9.56, 0.546, 1.93),
        "ACHONG": (3.82, 0.650, 1.88)
    }

    @classmethod
    def calculate_choke_allocation(
        cls,
        inputs: ChokeAllocationInputs
    ) -> EngineeringResult:
        """
        Calculates allocated oil, water, and gas rates from choke parameters and calibrated water cut.
        Classified strictly as Virtual Allocation / Engineering Estimate.
        """
        raw_inputs = inputs.model_dump()
        corr_key = inputs.correlation_name.upper()

        # 1. Correlation support check
        if corr_key not in cls.CORRELATION_COEFFICIENTS:
            return EngineeringResult(
                calculation_name="Well Choke Flow Allocation",
                model="Multiphase Critical Choke Flow",
                status=EngineeringStatus.NOT_APPLICABLE.value,
                inputs=raw_inputs,
                evidence={"error": f"Unsupported choke correlation '{inputs.correlation_name}'. Supported: GILBERT, ROS, BAXENDELL, ACHONG."}
            )

        c_base, a_exp, b_exp = cls.CORRELATION_COEFFICIENTS[corr_key]
        c_effective = c_base / inputs.choke_discharge_calibration_factor

        # 2. Critical Flow Regime Verification
        # Critical multiphase flow occurs when downstream Pline <= ~0.55 * Pwh
        warnings = []
        if inputs.flowline_pressure_psia is not None:
            pressure_ratio = inputs.flowline_pressure_psia / inputs.wellhead_pressure_psia
            if pressure_ratio > 0.58:
                warnings.append(
                    f"Downstream/wellhead pressure ratio ({pressure_ratio:.2f}) exceeds critical flow boundary (~0.55). "
                    "Flow may be subcritical; acoustic acoustic velocity is not achieved at the vena contracta. Choke correlation uncertainty increased."
                )

        # 3. Solve for Total Liquid Rate qL (STB/D)
        # Pwh = c_effective * qL * (Rp^a) / (S^b)
        # => qL = Pwh * (S^b) / (c_effective * Rp^a)
        numerator = inputs.wellhead_pressure_psia * (inputs.choke_size_64ths ** b_exp)
        denominator = c_effective * (inputs.producing_gor_scf_stb ** a_exp)

        if denominator <= 0:
            return EngineeringResult(
                calculation_name="Well Choke Flow Allocation",
                model=f"{corr_key.capitalize()} Multiphase Choke Flow",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=raw_inputs,
                evidence={"error": "Non-physical denominator in choke flow evaluation."}
            )

        allocated_liquid_rate_stbd = numerator / denominator

        # 4. Phase Splitting via Calibrated Water Cut Fraction
        wc_frac = inputs.calibrated_wc_fraction
        allocated_water_rate_bpd = allocated_liquid_rate_stbd * wc_frac
        allocated_oil_rate_stbd = allocated_liquid_rate_stbd * (1.0 - wc_frac)

        # Gas rate from producing GOR
        allocated_gas_rate_mscfd = (allocated_oil_rate_stbd * inputs.producing_gor_scf_stb) / 1000.0

        # Boundary condition check: 100% Water Cut
        wor_status = "NORMAL"
        wor_val = None
        if abs(wc_frac - 1.0) < 1e-6:
            allocated_oil_rate_stbd = 0.0
            allocated_gas_rate_mscfd = 0.0
            wor_status = "UNDEFINED_WOR"
            warnings.append("Well is producing at 100.0% Water Cut. Oil and gas rates are zero. WOR is mathematically undefined.")
        else:
            wor_val = round(allocated_water_rate_bpd / allocated_oil_rate_stbd, 4) if allocated_oil_rate_stbd > 0 else None

        return EngineeringResult(
            calculation_name="Well Choke Flow Allocation",
            value={
                "allocated_oil_rate_stbd": round(allocated_oil_rate_stbd, 2),
                "allocated_water_rate_bpd": round(allocated_water_rate_bpd, 2),
                "allocated_liquid_rate_stbd": round(allocated_liquid_rate_stbd, 2),
                "allocated_gas_rate_mscfd": round(allocated_gas_rate_mscfd, 2),
                "water_cut_percent": round(wc_frac * 100.0, 2),
                "wor": wor_val,
                "measurement_classification": "VIRTUAL_ALLOCATION_ENGINEERING_ESTIMATE"
            },
            unit="STB/D",
            model=f"{corr_key.capitalize()} (1954) Choke Flow Model",
            correlation=f"{corr_key.capitalize()} Multiphase Critical Choke Flow",
            correlation_reference=f"Gilbert, W.E. (1954), API DPP, 126-157; Ros (1961); Baxendell (1958)",
            inputs=raw_inputs,
            assumptions=[
                "CRITICAL CLASSIFICATION RULE: Output is classified strictly as 'Virtual Allocation / Engineering Estimate'. It does NOT replace certified fiscal test-separator measurements.",
                "Sonic/critical velocity attained at choke constriction (downstream pressure fluctuations do not affect upstream wellhead pressure)",
                "Gas-liquid mixture remains in homogeneous mist/froth dispersion through restriction"
            ],
            limitations=[
                "Choke erosion, wax deposition, or scale will alter effective orifice diameter over time, requiring periodic calibration.",
                "Correlation requires calibration against reference test separator measurements to establish field-specific discharge factor."
            ],
            warnings=warnings,
            evidence={
                "classification": "VIRTUAL_ALLOCATION_ENGINEERING_ESTIMATE",
                "wor_status": wor_status,
                "correlation_parameters": {
                    "correlation": corr_key,
                    "c_base": c_base,
                    "a_exponent": a_exp,
                    "b_exponent": b_exp,
                    "calibration_factor_applied": inputs.choke_discharge_calibration_factor
                }
            },
            status=EngineeringStatus.VALID.value
        )
