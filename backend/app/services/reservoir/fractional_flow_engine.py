"""
Smart Guardian Reservoir Intelligence Layer - Relative Permeability & Fractional Flow Engine (Step 2B)
References:
- Leverett, M.C. (1941), "Capillary Behavior in Porous Solids", Trans. AIME, 142, 152-169.
- Corey, A.T. (1954), "The Interrelation Between Gas and Oil Relative Permeabilities", Prod. Monthly, 19(1), 38-41.

Implements canonical Two-Phase (Oil-Water) Flow Physics:
1. Core / Laboratory Measured Relative Permeability Ingestion & Interpolation
2. Corey Theoretical Empirical Power-Law Model (explicitly labeled as Modeled, never Measured)
3. Phase Mobilities (lambda_w, lambda_o) and End-Point Mobility Ratio M
4. Fractional Flow Curve fw(Sw) and Derivative dfw/dSw

Strictly adheres to:
- No fabricated relative permeability curves: returns INSUFFICIENT_DATA if core curves are missing and no theoretical model is requested
- Physical saturation boundary checks: 0 <= Swc < 1, 0 <= Sor < 1, Swc + Sor < 1
- Standard EngineeringResult contract with complete assumptions, limitations, and provenance
"""

import math
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class CoreRelPermPoint(BaseModel):
    """Laboratory measured core relative permeability point."""
    sw_fraction: float = Field(..., ge=0.0, le=1.0, description="Water saturation fraction (0.0 to 1.0)")
    krw: float = Field(..., ge=0.0, le=1.0, description="Water relative permeability")
    kro: float = Field(..., ge=0.0, le=1.0, description="Oil relative permeability")

    model_config = ConfigDict(from_attributes=True)


class FractionalFlowPoint(BaseModel):
    """Calculated fractional flow coordinate."""
    sw: float
    krw: float
    kro: float
    fw: float
    fw_prime: Optional[float] = None


class FractionalFlowEngine:
    """
    Canonical Relative Permeability and Fractional Flow Physics Engine.
    Single Source of Truth for mobility ratios, fractional flow, and saturation relationships.
    """

    @classmethod
    def calculate_corey_model(
        cls,
        sw_connate: float,
        so_residual: float,
        krw_endpoint: float,
        kro_endpoint: float,
        nw_exponent: float,
        no_exponent: float,
        water_viscosity_cp: float,
        oil_viscosity_cp: float,
        num_points: int = 50
    ) -> EngineeringResult:
        """
        Generates Corey (1954) empirical power-law relative permeability and fractional flow curve.
        Explicitly flagged as THEORETICAL_MODEL, NOT measured laboratory data.
        """
        inputs = {
            "model_type": "COREY_THEORETICAL",
            "sw_connate": sw_connate,
            "so_residual": so_residual,
            "krw_endpoint": krw_endpoint,
            "kro_endpoint": kro_endpoint,
            "nw_exponent": nw_exponent,
            "no_exponent": no_exponent,
            "water_viscosity_cp": water_viscosity_cp,
            "oil_viscosity_cp": oil_viscosity_cp
        }

        # 1. Validation
        if sw_connate < 0.0 or so_residual < 0.0 or (sw_connate + so_residual) >= 1.0:
            return EngineeringResult(
                calculation_name="Corey Relative Permeability & Fractional Flow",
                model="Corey (1954) Power-Law Model",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={"error": f"Invalid saturation boundaries: Swc ({sw_connate}) + Sor ({so_residual}) must be < 1.0."}
            )

        if water_viscosity_cp <= 0 or oil_viscosity_cp <= 0 or krw_endpoint <= 0 or kro_endpoint <= 0:
            return EngineeringResult(
                calculation_name="Corey Relative Permeability & Fractional Flow",
                model="Corey (1954) Power-Law Model",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={"error": "Viscosities and relative permeability endpoints must be strictly positive."}
            )

        # End-point mobility ratio: M = (krw_endpoint / mu_w) / (kro_endpoint / mu_o)
        end_point_mobility_ratio = (krw_endpoint / water_viscosity_cp) / (kro_endpoint / oil_viscosity_cp)

        # Discretize saturation range [Swc, 1 - Sor]
        sw_min = sw_connate
        sw_max = 1.0 - so_residual
        delta_sw = (sw_max - sw_min) / max(10, num_points - 1)

        curve_points: List[FractionalFlowPoint] = []
        viscosity_ratio = water_viscosity_cp / oil_viscosity_cp

        for i in range(num_points):
            sw = sw_min + i * delta_sw
            sw = min(sw_max, max(sw_min, sw))

            # Normalized water saturation: Swn = (Sw - Swc) / (1 - Swc - Sor)
            denom = 1.0 - sw_connate - so_residual
            s_wn = max(0.0, min(1.0, (sw - sw_connate) / denom))

            # Corey power laws
            krw = krw_endpoint * (s_wn ** nw_exponent)
            kro = kro_endpoint * ((1.0 - s_wn) ** no_exponent)

            # Fractional flow: fw = 1 / [1 + (kro/krw) * (mu_w/mu_o)]
            if krw <= 1e-12:
                fw = 0.0
            elif kro <= 1e-12:
                fw = 1.0
            else:
                perm_ratio = kro / krw
                fw = 1.0 / (1.0 + perm_ratio * viscosity_ratio)

            curve_points.append(
                FractionalFlowPoint(
                    sw=round(sw, 4),
                    krw=round(krw, 6),
                    kro=round(kro, 6),
                    fw=round(fw, 6),
                    fw_prime=None
                )
            )

        # Calculate numerical derivatives: dfw / dSw
        for k in range(len(curve_points)):
            if k == 0:
                dsw = curve_points[1].sw - curve_points[0].sw
                dfw = curve_points[1].fw - curve_points[0].fw
                prime = dfw / dsw if dsw > 1e-6 else 0.0
            elif k == len(curve_points) - 1:
                dsw = curve_points[-1].sw - curve_points[-2].sw
                dfw = curve_points[-1].fw - curve_points[-2].fw
                prime = dfw / dsw if dsw > 1e-6 else 0.0
            else:
                dsw = curve_points[k+1].sw - curve_points[k-1].sw
                dfw = curve_points[k+1].fw - curve_points[k-1].fw
                prime = dfw / dsw if dsw > 1e-6 else 0.0

            curve_points[k].fw_prime = round(max(0.0, prime), 4)

        return EngineeringResult(
            calculation_name="Fractional Flow Curve",
            value={
                "end_point_mobility_ratio_M": round(end_point_mobility_ratio, 4),
                "sw_connate": sw_connate,
                "so_residual": so_residual,
                "favorable_displacement": bool(end_point_mobility_ratio <= 1.0),
                "points_count": len(curve_points)
            },
            unit="dimensionless",
            model="Corey (1954) Relative Permeability & Leverett (1941) Fractional Flow",
            correlation="Corey (1954), Leverett (1941)",
            correlation_reference="Corey, A.T. (1954), Prod. Monthly, 19(1), 38-41; Leverett, M.C. (1941), Trans. AIME, 142, 152-169",
            inputs=inputs,
            assumptions=[
                "Explicitly modeled empirical Corey curves (NOT direct core laboratory measurements)",
                "Two-phase immiscible flow without capillary pressure gradient (horizontal or gravity-negligible)",
                "Isothermal constant fluid viscosities"
            ],
            limitations=[
                "Corey power law is an idealized approximation; core-flood measurements should supersede theoretical curves when available.",
                "Capillary pressure effects near the shock front are neglected in the Leverett horizontal formulation."
            ],
            evidence={
                "mobility_classification": "Favorable waterflood displacement (M <= 1.0)" if end_point_mobility_ratio <= 1.0 else "Unfavorable waterflood displacement (M > 1.0, potential viscous fingering)",
                "curve_points": [p.model_dump() for p in curve_points]
            },
            status=EngineeringStatus.VALID.value
        )

    @classmethod
    def calculate_from_core_data(
        cls,
        core_points: List[CoreRelPermPoint],
        water_viscosity_cp: float,
        oil_viscosity_cp: float
    ) -> EngineeringResult:
        """
        Evaluates fractional flow fw(Sw) and phase mobilities directly from laboratory measured core flood points.
        """
        inputs = {
            "source_type": "LABORATORY_CORE_DATA",
            "points_count": len(core_points) if core_points else 0,
            "water_viscosity_cp": water_viscosity_cp,
            "oil_viscosity_cp": oil_viscosity_cp
        }

        if not core_points or len(core_points) < 3:
            return EngineeringResult(
                calculation_name="Core Fractional Flow Analysis",
                model="Leverett (1941) Fractional Flow from Laboratory Core",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "At least 3 core relative permeability measurements are required."}
            )

        if water_viscosity_cp <= 0 or oil_viscosity_cp <= 0:
            return EngineeringResult(
                calculation_name="Core Fractional Flow Analysis",
                model="Leverett (1941) Fractional Flow from Laboratory Core",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={"error": "Water and oil viscosities must be strictly positive."}
            )

        sorted_core = sorted(core_points, key=lambda x: x.sw_fraction)
        viscosity_ratio = water_viscosity_cp / oil_viscosity_cp

        results: List[FractionalFlowPoint] = []
        for pt in sorted_core:
            sw = pt.sw_fraction
            krw = pt.krw
            kro = pt.kro

            if krw <= 1e-12:
                fw = 0.0
            elif kro <= 1e-12:
                fw = 1.0
            else:
                perm_ratio = kro / krw
                fw = 1.0 / (1.0 + perm_ratio * viscosity_ratio)

            results.append(FractionalFlowPoint(sw=sw, krw=krw, kro=kro, fw=round(fw, 6)))

        # Numerical derivative
        for k in range(len(results)):
            if k == 0:
                dsw = results[1].sw - results[0].sw
                dfw = results[1].fw - results[0].fw
                prime = dfw / dsw if dsw > 1e-6 else 0.0
            elif k == len(results) - 1:
                dsw = results[-1].sw - results[-2].sw
                dfw = results[-1].fw - results[-2].fw
                prime = dfw / dsw if dsw > 1e-6 else 0.0
            else:
                dsw = results[k+1].sw - results[k-1].sw
                dfw = results[k+1].fw - results[k-1].fw
                prime = dfw / dsw if dsw > 1e-6 else 0.0
            results[k].fw_prime = round(max(0.0, prime), 4)

        # End-point mobility ratio
        krw_max = sorted_core[-1].krw
        kro_max = sorted_core[0].kro
        m_endpoint = (krw_max / water_viscosity_cp) / (kro_max / oil_viscosity_cp) if kro_max > 0 else None

        return EngineeringResult(
            calculation_name="Core Fractional Flow Analysis",
            value={
                "end_point_mobility_ratio_M": round(m_endpoint, 4) if m_endpoint is not None else None,
                "sw_min": sorted_core[0].sw_fraction,
                "sw_max": sorted_core[-1].sw_fraction,
                "points_count": len(results)
            },
            unit="dimensionless",
            model="Leverett (1941) Fractional Flow from Laboratory Core flood",
            correlation="Leverett (1941)",
            correlation_reference="Leverett, M.C. (1941), Trans. AIME, 142, 152-169",
            inputs=inputs,
            assumptions=[
                "Laboratory core measurement represents reservoir wettability and pore structure",
                "Negligible capillary pressure gradient at field-scale flow velocities"
            ],
            limitations=[
                "Core scale measurements must be upscaled properly for reservoir heterogeneities.",
                "End effects during core-flood laboratory tests must be filtered."
            ],
            evidence={"curve_points": [p.model_dump() for p in results]},
            status=EngineeringStatus.VALID.value
        )
