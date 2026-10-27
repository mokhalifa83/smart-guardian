"""
Smart Guardian Reservoir Intelligence Layer - Buckley-Leverett Displacement Engine (Step 2B)
References:
- Buckley, S.E. and Leverett, M.C. (1942), "Mechanism of Fluid Displacement in Sands", Trans. AIME, 146, 107-116.
- Welge, H.J. (1952), "A Simplified Method for Computing Oil Recovery by Gas or Water Drive", Trans. AIME, 195, 91-98.

Implements 1D Analytical Frontal Advance Immiscible Displacement:
1. Welge Tangent Construction for Shock-Front Saturation (Swf)
2. Water-Front Advance Velocity (v_Swf)
3. Average Water Saturation Behind Front at Breakthrough (Sw_avg_bt)
4. Time to Water Breakthrough (t_bt)
5. Dimensionless Pore Volumes Injected (PVI) and Oil Recovery at Breakthrough

Strictly adheres to:
- Mandatory architectural disclaimer: "This is an analytical 1D displacement model; it is NOT a full-field reservoir simulator."
- Validation of injection rate, cross-sectional area, porosity, distance, and saturation limits
- Standard EngineeringResult contract with complete assumptions, limitations, and provenance
"""

import math
from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.fractional_flow_engine import FractionalFlowEngine, FractionalFlowPoint


class BuckleyLeverettEngine:
    """
    Canonical Buckley-Leverett (1942) & Welge (1952) Frontal Advance Displacement Engine.
    Single Source of Truth for analytical shock-front saturation, breakthrough timing, and frontal velocity.
    """

    @classmethod
    def calculate_displacement(
        cls,
        injection_rate_bpd: float,
        cross_sectional_area_ft2: float,
        length_between_wells_ft: float,
        porosity_fraction: float,
        initial_water_saturation: float,
        so_residual: float,
        water_viscosity_cp: float,
        oil_viscosity_cp: float,
        krw_endpoint: float = 0.30,
        kro_endpoint: float = 0.85,
        nw_exponent: float = 2.0,
        no_exponent: float = 2.5
    ) -> EngineeringResult:
        """
        Calculates 1D Buckley-Leverett frontal advance displacement, shock-front saturation,
        and time to breakthrough using the Welge tangent method.
        """
        inputs = {
            "injection_rate_bpd": injection_rate_bpd,
            "cross_sectional_area_ft2": cross_sectional_area_ft2,
            "length_between_wells_ft": length_between_wells_ft,
            "porosity_fraction": porosity_fraction,
            "initial_water_saturation": initial_water_saturation,
            "so_residual": so_residual,
            "water_viscosity_cp": water_viscosity_cp,
            "oil_viscosity_cp": oil_viscosity_cp
        }

        # 1. Validation
        if any(v <= 0 for v in [injection_rate_bpd, cross_sectional_area_ft2, length_between_wells_ft, porosity_fraction, water_viscosity_cp, oil_viscosity_cp]):
            return EngineeringResult(
                calculation_name="Buckley-Leverett 1D Displacement",
                model="Buckley-Leverett (1942) & Welge (1952) Analytical Model",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={"error": "Geometric dimensions, rates, and fluid properties must be strictly positive."}
            )

        if initial_water_saturation < 0.0 or so_residual < 0.0 or (initial_water_saturation + so_residual) >= 1.0:
            return EngineeringResult(
                calculation_name="Buckley-Leverett 1D Displacement",
                model="Buckley-Leverett (1942) & Welge (1952) Analytical Model",
                status=EngineeringStatus.INVALID_INPUT.value,
                inputs=inputs,
                evidence={"error": "Invalid saturation limits: Swi + Sor must be < 1.0."}
            )

        # 2. Generate canonical fractional flow curve
        ff_res = FractionalFlowEngine.calculate_corey_model(
            sw_connate=initial_water_saturation,
            so_residual=so_residual,
            krw_endpoint=krw_endpoint,
            kro_endpoint=kro_endpoint,
            nw_exponent=nw_exponent,
            no_exponent=no_exponent,
            water_viscosity_cp=water_viscosity_cp,
            oil_viscosity_cp=oil_viscosity_cp,
            num_points=100
        )

        if ff_res.status != EngineeringStatus.VALID.value:
            return ff_res

        curve_points_raw = ff_res.evidence.get("curve_points", [])
        if not curve_points_raw:
            return EngineeringResult(
                calculation_name="Buckley-Leverett 1D Displacement",
                model="Buckley-Leverett (1942) & Welge (1952) Analytical Model",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "Unable to generate fractional flow discretization points."}
            )

        # 3. Welge Tangent Construction to find Shock-Front Saturation Swf
        # Tangent slope from initial point (Swi, fw(Swi) = 0):
        # Slope = (fw(Sw) - fw(Swi)) / (Sw - Swi)
        # Find Sw > Swi that maximizes the secant slope (the tangent point)
        best_tangent_slope = -1.0
        best_point = None

        swi = initial_water_saturation
        fwi = 0.0

        for pt_dict in curve_points_raw:
            sw = pt_dict["sw"]
            fw = pt_dict["fw"]
            fw_prime = pt_dict["fw_prime"]

            if sw > swi + 0.01:
                secant_slope = (fw - fwi) / (sw - swi)
                if secant_slope > best_tangent_slope:
                    best_tangent_slope = secant_slope
                    best_point = pt_dict

        if not best_point:
            return EngineeringResult(
                calculation_name="Buckley-Leverett 1D Displacement",
                model="Buckley-Leverett (1942) & Welge (1952) Analytical Model",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Could not determine tangent point for shock-front saturation."}
            )

        swf = best_point["sw"]
        fw_f = best_point["fw"]
        dfw_dsw_f = best_tangent_slope  # At the tangent point, secant slope equals derivative

        # 4. Average Water Saturation Behind the Front at Breakthrough (Welge equation):
        # Sw_avg_bt = Swf + (1 - fw(Swf)) / (dfw/dSw)|Swf
        sw_avg_bt = swf + (1.0 - fw_f) / dfw_dsw_f
        sw_avg_bt = min(1.0 - so_residual, max(swf, sw_avg_bt))

        # 5. Volumetric Reservoir and Breakthrough Calculations
        # Pore Volume: Vp (cu ft) = Area * Length * phi
        # In reservoir barrels: Vp_rb = Vp / 5.614583
        vp_ft3 = cross_sectional_area_ft2 * length_between_wells_ft * porosity_fraction
        vp_rb = vp_ft3 / 5.614583

        # Front velocity: v = (qt / (A * phi)) * (dfw/dSw) in ft/day
        # qt in cu ft/day: injection_rate_bpd * 5.614583
        qt_cuft_day = injection_rate_bpd * 5.614583
        interstitial_velocity_base = qt_cuft_day / (cross_sectional_area_ft2 * porosity_fraction)  # ft/day
        front_velocity_ft_day = interstitial_velocity_base * dfw_dsw_f

        # Time to breakthrough: t_bt = Length / v_front = Vp_rb / (injection_rate_bpd * dfw_dsw_f)
        if injection_rate_bpd * dfw_dsw_f > 0:
            time_to_breakthrough_days = vp_rb / (injection_rate_bpd * dfw_dsw_f)
        else:
            time_to_breakthrough_days = None

        # Dimensionless Pore Volumes Injected at breakthrough: PVI_bt = 1 / (dfw/dSw)|Swf
        pvi_at_breakthrough = 1.0 / dfw_dsw_f if dfw_dsw_f > 0 else None

        # Recovery factor at breakthrough (fraction of initial oil in place OOIP):
        # OOIP_fraction = 1 - Swi
        # Oil displaced at breakthrough = Sw_avg_bt - Swi
        oil_init_fraction = 1.0 - swi
        recovery_factor_bt = (sw_avg_bt - swi) / oil_init_fraction if oil_init_fraction > 0 else 0.0

        # Cumulative oil produced at breakthrough (STB, assuming Bo ~ 1.0 or reservoir barrels)
        np_at_breakthrough_rb = vp_rb * (sw_avg_bt - swi)

        return EngineeringResult(
            calculation_name="Buckley-Leverett 1D Displacement Analysis",
            value={
                "shock_front_saturation_swf": round(swf, 4),
                "fractional_flow_at_front_fw": round(fw_f, 4),
                "tangent_slope_dfw_dsw": round(dfw_dsw_f, 4),
                "average_saturation_at_breakthrough": round(sw_avg_bt, 4),
                "time_to_breakthrough_days": round(time_to_breakthrough_days, 1) if time_to_breakthrough_days is not None else None,
                "pore_volumes_injected_at_breakthrough": round(pvi_at_breakthrough, 4) if pvi_at_breakthrough is not None else None,
                "oil_recovery_factor_at_breakthrough": round(recovery_factor_bt, 4),
                "oil_produced_at_breakthrough_rb": round(np_at_breakthrough_rb, 1),
                "front_velocity_ft_per_day": round(front_velocity_ft_day, 2)
            },
            unit="dimensionless",
            model="Buckley-Leverett (1942) & Welge (1952) Frontal Advance",
            correlation="Buckley-Leverett (1942), Welge (1952)",
            correlation_reference="Buckley, S.E. and Leverett, M.C. (1942), Trans. AIME, 146, 107-116; Welge, H.J. (1952), Trans. AIME, 195, 91-98",
            inputs=inputs,
            assumptions=[
                "MANDATORY ARCHITECTURAL DISCLAIMER: This is an analytical 1D linear displacement model; it is NOT a full-field 3D reservoir simulator.",
                "Immiscible displacement of incompressible fluids in a homogeneous horizontal linear system",
                "Negligible capillary pressure gradient behind the shock front"
            ],
            limitations=[
                "Does not account for reservoir heterogeneity, gravity segregation, or areal/vertical sweep inefficiencies.",
                "Valid only for 1D linear geometry; pattern waterfloods require areal sweep factor corrections."
            ],
            evidence={
                "disclaimer": "Analytical 1D Buckley-Leverett model. Results represent maximum theoretical 1D sweep efficiency.",
                "tangent_point": {
                    "swf": round(swf, 4),
                    "fw": round(fw_f, 4),
                    "slope": round(dfw_dsw_f, 4)
                },
                "breakthrough_summary": f"Predicted breakthrough in {time_to_breakthrough_days:.1f} days after {pvi_at_breakthrough:.3f} PVI with {recovery_factor_bt*100:.1f}% displacement recovery." if time_to_breakthrough_days is not None else "Breakthrough not determinable."
            },
            status=EngineeringStatus.VALID.value
        )
