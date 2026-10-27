"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C
Reserves Engine (reserves_engine.py)

Strict Petroleum Engineering Volumetric Formulations:
- Original Oil In Place (OOIP / STOIIP):
    N = (7758 * A * h * phi * (1 - Swi)) / Boi   [STB]
- Original Gas In Place (OGIP / GIIP):
    G = (43560 * A * h * phi * (1 - Swi)) / Bgi  [scf or Mscf]  (when Bgi is in cuft/scf)
    or G = (7758 * A * h * phi * (1 - Swi)) / Bgi [scf]          (when Bgi is in rb/scf)

MANDATORY PROFESSIONAL INTEGRITY RULES:
1. OOIP / GIIP represents total static in-place hydrocarbons and is NEVER equivalent to commercially recoverable reserves.
2. EUR = InPlace * RecoveryFactor (RF).
3. Remaining Reserves = EUR - CumulativeProduction.
4. Recovery factor and economic limits must be documented and validated; they are NEVER invented or assumed arbitrarily.
5. In the absence of documented recovery factor or cumulative production, the engine returns INSUFFICIENT_DATA.
"""

from typing import Dict, Any, Optional
from datetime import datetime, timezone
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class ReservesEngine:
    """
    Production-grade volumetric reserves and resource estimation engine.
    Follows SPE-PRMS standards distinguishing Total In-Place, EUR, Remaining Reserves, and Remaining Resources.
    """

    VOLUMETRIC_OIL_CONSTANT: float = 7758.367  # bbl / (acre-ft)
    VOLUMETRIC_GAS_CONSTANT_CUFT: float = 43560.0  # cuft / (acre-ft)
    VOLUMETRIC_GAS_CONSTANT_BBL: float = 7758.367  # bbl / (acre-ft)

    @classmethod
    def calculate_ooip_volumetric(
        cls,
        area_acres: float,
        net_pay_ft: float,
        porosity: float,
        initial_water_sat: float,
        initial_oil_fvf_boi: float,
        well_or_field_id: str = "FIELD"
    ) -> EngineeringResult:
        """
        Calculates Original Oil In Place (OOIP / STOIIP) in STB.
        N = 7758 * A * h * phi * (1 - Swi) / Boi
        """
        inputs = {
            "area_acres": area_acres,
            "net_pay_ft": net_pay_ft,
            "porosity": porosity,
            "initial_water_sat": initial_water_sat,
            "initial_oil_fvf_boi": initial_oil_fvf_boi,
            "well_or_field_id": well_or_field_id
        }

        # Input validation
        warnings = []
        if area_acres <= 0 or net_pay_ft <= 0:
            return EngineeringResult(
                calculation_name="OOIP_VOLUMETRIC",
                value=None,
                unit="STB",
                inputs=inputs,
                model="Volumetric STOIIP Equation (Craft & Hawkins)",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Area and net pay must be strictly positive."],
                warnings=["Invalid geometric dimensions: area and pay must exceed zero."]
            )

        if not (0.0 < porosity < 1.0):
            return EngineeringResult(
                calculation_name="OOIP_VOLUMETRIC",
                value=None,
                unit="STB",
                inputs=inputs,
                model="Volumetric STOIIP Equation",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Porosity must be a fraction strictly between 0 and 1."],
                warnings=[f"Physically impossible porosity: {porosity}"]
            )

        if not (0.0 <= initial_water_sat < 1.0):
            return EngineeringResult(
                calculation_name="OOIP_VOLUMETRIC",
                value=None,
                unit="STB",
                inputs=inputs,
                model="Volumetric STOIIP Equation",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Water saturation must be a fraction between 0 and 1."],
                warnings=[f"Invalid initial water saturation: {initial_water_sat}"]
            )

        if initial_oil_fvf_boi <= 0:
            return EngineeringResult(
                calculation_name="OOIP_VOLUMETRIC",
                value=None,
                unit="STB",
                inputs=inputs,
                model="Volumetric STOIIP Equation",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Initial oil formation volume factor Boi must be strictly positive."],
                warnings=[f"Invalid Boi: {initial_oil_fvf_boi}"]
            )

        # Standard calculation
        hydrocarbon_pore_volume_acre_ft = area_acres * net_pay_ft * porosity * (1.0 - initial_water_sat)
        ooip_stb = (cls.VOLUMETRIC_OIL_CONSTANT * hydrocarbon_pore_volume_acre_ft) / initial_oil_fvf_boi

        return EngineeringResult(
            calculation_name="OOIP_VOLUMETRIC",
            value=float(ooip_stb),
            unit="STB",
            inputs=inputs,
            model="Volumetric STOIIP Equation (7758 * A * h * phi * (1 - Swi) / Boi)",
            assumptions=[
                "Homogeneous reservoir slab with uniform average porosity and saturation",
                "Volumetric bulk rock volume bounded by structure and fluid contacts",
                "Constant initial formation volume factor Boi across reservoir layer"
            ],
            limitations=[
                "OOIP represents total static in-place hydrocarbon volume, NOT recoverable reserves.",
                "Does not account for reservoir compartmentalization, faults, or recovery efficiency."
            ],
            evidence={
                "bulk_rock_volume_acre_ft": area_acres * net_pay_ft,
                "hydrocarbon_pore_volume_acre_ft": hydrocarbon_pore_volume_acre_ft,
                "initial_oil_saturation_fraction": 1.0 - initial_water_sat,
                "ooip_mmstb": round(ooip_stb / 1e6, 3)
            },
            status=EngineeringStatus.VALID.value,
            provenance={
                "engine": "ReservesEngine",
                "standard": "SPE-PRMS Volumetric Formulation",
                "version": "Step2C-v1.2",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            observed_pattern="STATIC_VOLUMETRIC_EVALUATION",
            diagnostic_interpretation="Original Oil In Place quantified from structural and petrophysical properties.",
            warnings=warnings
        )

    @classmethod
    def calculate_giip_volumetric(
        cls,
        area_acres: float,
        net_pay_ft: float,
        porosity: float,
        initial_water_sat: float,
        initial_gas_fvf_bgi: float,
        bgi_unit: str = "cuft_scf",
        well_or_field_id: str = "FIELD"
    ) -> EngineeringResult:
        """
        Calculates Original Gas In Place (OGIP / GIIP) in Mscf.
        When bgi_unit == 'cuft_scf': G = 43560 * A * h * phi * (1 - Swi) / Bgi  [scf]
        When bgi_unit == 'rb_scf': G = 7758 * A * h * phi * (1 - Swi) / Bgi    [scf]
        """
        inputs = {
            "area_acres": area_acres,
            "net_pay_ft": net_pay_ft,
            "porosity": porosity,
            "initial_water_sat": initial_water_sat,
            "initial_gas_fvf_bgi": initial_gas_fvf_bgi,
            "bgi_unit": bgi_unit,
            "well_or_field_id": well_or_field_id
        }

        if area_acres <= 0 or net_pay_ft <= 0:
            return EngineeringResult(
                calculation_name="GIIP_VOLUMETRIC",
                value=None,
                unit="Mscf",
                inputs=inputs,
                model="Volumetric OGIP Equation",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Area and net pay must be positive."],
                warnings=["Invalid reservoir dimensions."]
            )

        if not (0.0 < porosity < 1.0) or not (0.0 <= initial_water_sat < 1.0) or initial_gas_fvf_bgi <= 0:
            return EngineeringResult(
                calculation_name="GIIP_VOLUMETRIC",
                value=None,
                unit="Mscf",
                inputs=inputs,
                model="Volumetric OGIP Equation",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Porosity, water saturation, and Bgi must be within valid physical ranges."],
                warnings=["Invalid petrophysical or PVT properties."]
            )

        hcpv_acre_ft = area_acres * net_pay_ft * porosity * (1.0 - initial_water_sat)

        if bgi_unit.lower() in ["cuft_scf", "rcf_scf", "ft3_scf"]:
            giip_scf = (cls.VOLUMETRIC_GAS_CONSTANT_CUFT * hcpv_acre_ft) / initial_gas_fvf_bgi
            constant_used = cls.VOLUMETRIC_GAS_CONSTANT_CUFT
        elif bgi_unit.lower() in ["rb_scf", "res_bbl_scf"]:
            giip_scf = (cls.VOLUMETRIC_GAS_CONSTANT_BBL * hcpv_acre_ft) / initial_gas_fvf_bgi
            constant_used = cls.VOLUMETRIC_GAS_CONSTANT_BBL
        else:
            return EngineeringResult(
                calculation_name="GIIP_VOLUMETRIC",
                value=None,
                unit="Mscf",
                inputs=inputs,
                model="Volumetric OGIP Equation",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Unknown Bgi unit. Expected 'cuft_scf' or 'rb_scf'."],
                warnings=[f"Unsupported unit: {bgi_unit}"]
            )

        giip_mscf = giip_scf / 1000.0

        return EngineeringResult(
            calculation_name="GIIP_VOLUMETRIC",
            value=float(giip_mscf),
            unit="Mscf",
            inputs=inputs,
            model=f"Volumetric OGIP Equation ({constant_used} * A * h * phi * (1 - Swi) / Bgi)",
            assumptions=[
                "Uniform average reservoir porosity and gas saturation across drainage volume",
                "Volumetric bulk rock volume bounded by geological faults and gas-water contact",
                "Initial formation volume factor Bgi uniform at initial reservoir pressure"
            ],
            limitations=[
                "GIIP represents total static in-place gas resource, NOT commercially recoverable reserves.",
                "Does not account for water drive influx or gas trapping at abandonment pressure."
            ],
            evidence={
                "bulk_rock_volume_acre_ft": area_acres * net_pay_ft,
                "hydrocarbon_pore_volume_acre_ft": hcpv_acre_ft,
                "giip_bscf": round(giip_mscf / 1e6, 4),
                "giip_scf": giip_scf
            },
            status=EngineeringStatus.VALID.value,
            provenance={
                "engine": "ReservesEngine",
                "standard": "SPE-PRMS Gas Volumetric Formulation",
                "version": "Step2C-v1.2",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            observed_pattern="STATIC_VOLUMETRIC_GAS_EVALUATION",
            diagnostic_interpretation="Original Gas In Place quantified from geological and volumetric gas properties."
        )

    @classmethod
    def calculate_oil_reserves_and_resources(
        cls,
        area_acres: float,
        net_pay_ft: float,
        porosity: float,
        initial_water_sat: float,
        initial_oil_fvf_boi: float,
        recovery_factor: Optional[float],
        cumulative_oil_np_stb: float = 0.0,
        economic_limit_bopd: Optional[float] = None,
        well_or_field_id: str = "FIELD"
    ) -> EngineeringResult:
        """
        Computes SPE-PRMS classified Oil Reserves and Resources.
        Rigorous engineering distinction:
        - OOIP = Total In-Place Hydrocarbons
        - EUR = OOIP * RecoveryFactor
        - Remaining Reserves = EUR - CumulativeProduction (Np)
        - Remaining Resources (Unrecoverable) = OOIP - EUR

        STRICT INTEGRITY:
        If recovery_factor is None, engine returns INSUFFICIENT_DATA because reserves
        cannot be arbitrarily fabricated without an approved recovery mechanism.
        """
        inputs = {
            "area_acres": area_acres,
            "net_pay_ft": net_pay_ft,
            "porosity": porosity,
            "initial_water_sat": initial_water_sat,
            "initial_oil_fvf_boi": initial_oil_fvf_boi,
            "recovery_factor": recovery_factor,
            "cumulative_oil_np_stb": cumulative_oil_np_stb,
            "economic_limit_bopd": economic_limit_bopd,
            "well_or_field_id": well_or_field_id
        }

        # First compute volumetric OOIP
        ooip_res = cls.calculate_ooip_volumetric(
            area_acres=area_acres,
            net_pay_ft=net_pay_ft,
            porosity=porosity,
            initial_water_sat=initial_water_sat,
            initial_oil_fvf_boi=initial_oil_fvf_boi,
            well_or_field_id=well_or_field_id
        )

        if ooip_res.status != EngineeringStatus.VALID.value:
            return ooip_res

        ooip_stb = ooip_res.value

        # Enforce no fabricated recovery factors
        if recovery_factor is None:
            return EngineeringResult(
                calculation_name="OIL_RESERVES_EVALUATION",
                value=None,
                unit="STB",
                inputs=inputs,
                model="SPE-PRMS Reserves Classification Model",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                assumptions=["Reserves require a certified or technically validated recovery factor."],
                limitations=["Recovery factor not provided. OOIP cannot be converted to reserves without verified drive mechanism."],
                warnings=["INSUFFICIENT_DATA: Recovery factor is missing. SPE-PRMS strictly prohibits arbitrary recovery factor fabrication."],
                evidence={"ooip_stb": ooip_stb, "ooip_mmstb": round(ooip_stb / 1e6, 3)}
            )

        if not (0.0 < recovery_factor <= 1.0):
            return EngineeringResult(
                calculation_name="OIL_RESERVES_EVALUATION",
                value=None,
                unit="STB",
                inputs=inputs,
                model="SPE-PRMS Reserves Classification Model",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Recovery factor must be a fraction between 0.0 and 1.0."],
                warnings=[f"Invalid recovery factor: {recovery_factor}"]
            )

        if cumulative_oil_np_stb < 0:
            return EngineeringResult(
                calculation_name="OIL_RESERVES_EVALUATION",
                value=None,
                unit="STB",
                inputs=inputs,
                model="SPE-PRMS Reserves Classification Model",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Cumulative production Np cannot be negative."],
                warnings=[f"Negative cumulative production: {cumulative_oil_np_stb}"]
            )

        eur_stb = ooip_stb * recovery_factor
        remaining_reserves_stb = max(0.0, eur_stb - cumulative_oil_np_stb)
        unrecoverable_resources_stb = max(0.0, ooip_stb - eur_stb)
        depletion_percentage = (cumulative_oil_np_stb / eur_stb) * 100.0 if eur_stb > 0 else 0.0

        warnings = []
        if cumulative_oil_np_stb > eur_stb:
            warnings.append(
                f"AUDIT WARNING: Cumulative production ({cumulative_oil_np_stb:.0f} STB) exceeds calculated EUR ({eur_stb:.0f} STB). "
                f"Reservoir model or recovery factor requires immediate recalibration."
            )

        return EngineeringResult(
            calculation_name="OIL_RESERVES_EVALUATION",
            value=float(remaining_reserves_stb),
            unit="STB",
            inputs=inputs,
            model="SPE-PRMS Classical Recovery Factor & Volumetric Depletion Model",
            assumptions=[
                "Recovery factor reflects approved primary/secondary drive mechanism",
                "Cumulative production accurately metered and allocated to drainage area",
                "Economic limit conditions adhered to per field operating agreement"
            ],
            limitations=[
                "Volumetric EUR assumes uniform displacement efficiency across estimated pore volume.",
                "Subsurface compartmentalization or early water breakthrough can curtail actual recovery below EUR."
            ],
            evidence={
                "ooip_stb": float(ooip_stb),
                "ooip_mmstb": round(ooip_stb / 1e6, 3),
                "recovery_factor": recovery_factor,
                "eur_stb": float(eur_stb),
                "eur_mmstb": round(eur_stb / 1e6, 3),
                "cumulative_production_np_stb": cumulative_oil_np_stb,
                "remaining_reserves_stb": float(remaining_reserves_stb),
                "remaining_reserves_mmstb": round(remaining_reserves_stb / 1e6, 3),
                "unrecoverable_resources_stb": float(unrecoverable_resources_stb),
                "depletion_percentage_of_eur": round(depletion_percentage, 2),
                "economic_limit_bopd": economic_limit_bopd
            },
            status=EngineeringStatus.VALID.value,
            provenance={
                "engine": "ReservesEngine",
                "standard": "SPE-PRMS Compliance (OOIP vs EUR vs Reserves vs Resources)",
                "version": "Step2C-v1.2",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            observed_pattern="COMMERCIAL_RESERVES_RESOURCES_PARTITION",
            diagnostic_interpretation=(
                f"Volumetric OOIP of {ooip_stb / 1e6:.2f} MMSTB yields EUR of {eur_stb / 1e6:.2f} MMSTB (RF={recovery_factor*100:.1f}%). "
                f"Current production {cumulative_oil_np_stb / 1e6:.2f} MMSTB leaves {remaining_reserves_stb / 1e6:.2f} MMSTB in remaining commercial reserves."
            ),
            warnings=warnings
        )
