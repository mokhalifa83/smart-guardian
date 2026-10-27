"""
Smart Guardian Reservoir Intelligence Layer - Darcy Radial Flow Engine (Step 2A)
Implements semi-steady state (pseudo-steady state) radial Darcy flow:
    q = (k * h * (pr - pwf)) / (141.2 * mu * Bo * [ln(re/rw) - 0.75 + s])
Field-unit definitions:
- q: flow rate (stb/d)
- k: effective permeability (md)
- h: net pay thickness (ft)
- pr: average reservoir pressure (psia)
- pwf: flowing bottomhole pressure (psia)
- mu: oil viscosity (cp)
- Bo: oil formation volume factor (rb/stb)
- re: external drainage radius (ft)
- rw: wellbore radius (ft)
- s: skin factor (dimensionless)
"""

import math
from typing import Optional, Dict, Any
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class DarcyRadialFlowEngine:
    """
    Canonical Darcy Radial Flow Physics Engine.
    """

    @staticmethod
    def calculate_flow_rate(
        permeability_md: float,
        thickness_ft: float,
        reservoir_pressure_psia: float,
        flowing_bhp_psia: float,
        viscosity_cp: float,
        bo_rb_stb: float,
        drainage_radius_ft: float,
        wellbore_radius_ft: float,
        skin: float = 0.0
    ) -> EngineeringResult:
        inputs = {
            "permeability_md": permeability_md,
            "thickness_ft": thickness_ft,
            "reservoir_pressure_psia": reservoir_pressure_psia,
            "flowing_bhp_psia": flowing_bhp_psia,
            "viscosity_cp": viscosity_cp,
            "bo_rb_stb": bo_rb_stb,
            "drainage_radius_ft": drainage_radius_ft,
            "wellbore_radius_ft": wellbore_radius_ft,
            "skin": skin
        }

        # 1. Physics Validation
        if permeability_md <= 0.0:
            return EngineeringResult(
                model="Darcy Semi-Steady State Radial Flow",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Permeability must be strictly positive (got {permeability_md} md)"}
            )

        if thickness_ft <= 0.0:
            return EngineeringResult(
                model="Darcy Semi-Steady State Radial Flow",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Net pay thickness must be strictly positive (got {thickness_ft} ft)"}
            )

        if reservoir_pressure_psia <= flowing_bhp_psia:
            return EngineeringResult(
                model="Darcy Semi-Steady State Radial Flow",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Reservoir pressure ({reservoir_pressure_psia} psia) must exceed flowing BHP ({flowing_bhp_psia} psia)"}
            )

        if viscosity_cp <= 0.0 or bo_rb_stb <= 0.0:
            return EngineeringResult(
                model="Darcy Semi-Steady State Radial Flow",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Fluid viscosity (mu) and formation volume factor (Bo) must be strictly positive"}
            )

        if drainage_radius_ft <= wellbore_radius_ft or wellbore_radius_ft <= 0.0:
            return EngineeringResult(
                model="Darcy Semi-Steady State Radial Flow",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Geometry violation: drainage radius ({drainage_radius_ft} ft) must exceed wellbore radius ({wellbore_radius_ft} ft) > 0"}
            )

        # 2. Geometric & Skin Logarithmic Denominator
        geo_term = math.log(drainage_radius_ft / wellbore_radius_ft) - 0.75 + skin
        if geo_term <= 0.0:
            return EngineeringResult(
                model="Darcy Semi-Steady State Radial Flow",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Effective radial flow resistance term [ln(re/rw) - 0.75 + s] is non-positive ({geo_term:.3f})"}
            )

        # 3. Flow rate computation
        drawdown = reservoir_pressure_psia - flowing_bhp_psia
        numerator = permeability_md * thickness_ft * drawdown
        denominator = 141.2 * viscosity_cp * bo_rb_stb * geo_term
        q = numerator / denominator

        return EngineeringResult(
            value=round(q, 2),
            unit="stb/d",
            model="Darcy Semi-Steady State Radial Flow",
            correlation="Darcy's Law for Radial Flow in Porous Media",
            correlation_reference="Craft & Hawkins, Applied Petroleum Reservoir Engineering, 3rd Ed.",
            inputs=inputs,
            assumptions=[
                "Semi-steady state (pseudo-steady state) flow with closed circular boundary",
                "Single-phase, slightly compressible liquid flow",
                "Homogeneous, isotropic formation properties",
                "Fully penetrating vertical wellbore"
            ],
            limitations=[
                "Applicable above bubble point or for undersaturated single-phase oil reservoirs",
                "Not applicable for high gas saturation (use Vogel IPR for two-phase flow)"
            ],
            evidence={
                "drawdown_psi": round(drawdown, 2),
                "geometric_term": round(geo_term, 4),
                "productivity_ratio": round(q / drawdown, 4)
            },
            status=EngineeringStatus.VALID.value
        )

    calculate_semi_steady_state = calculate_flow_rate

