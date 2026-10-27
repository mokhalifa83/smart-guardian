"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C
Gas Reservoir Engineering Engine (gas_reservoir_engine.py)

Strict Petroleum Engineering Formulations:
1. Gas Material Balance (p/z Analysis):
   Volumetric gas reservoir:
       (p / z) = (pi / zi) * (1 - (Gp / G))
   Linear extrapolation to (p / z) = 0 yields Original Gas In Place (OGIP, G).
   At abandonment pressure pa:
       Gpa = EUR = G * [1 - (pa / za) / (pi / zi)]
   Detects water drive / aquifer support when p/z exhibits characteristic concave-upward curvature.

2. Gas Deliverability (Rawlins & Schellhardt):
       qg = C * (pr^2 - pwf^2)^n   (0.5 <= n <= 1.0)
   Absolute Open Flow Potential (AOF) at pwf = 0:
       AOF = C * (pr^2)^n

3. Real Gas Pseudo-Pressure Formulation m(p):
       m(p) = 2 * Integral_{p_base}^p [ p / (mu_g(p) * z(p)) ] dp

4. Non-Darcy Turbulence Factor (Forchheimer Formulation):
       pr^2 - pwf^2 = a_lam * qg + b_turb * qg^2

CANONICAL ARCHITECTURE:
- PVT properties (Z-factor, Bg, mu_g) MUST use canonical PVTEngine.
- Zero duplicate PVT correlations.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.pvt_engine import PVTEngine


class GasReservoirEngine:
    """
    Production-grade Gas Reservoir Engineering Engine.
    Covers gas material balance, OGIP p/z extrapolation, Rawlins-Schellhardt deliverability,
    AOF potential, real gas pseudo-pressure m(p), and non-Darcy turbulence.
    """

    @classmethod
    def calculate_pz_material_balance(
        cls,
        history: List[Dict[str, float]],
        temperature_f: float,
        gas_gravity: float,
        abandonment_pressure_psia: float = 500.0,
        reservoir_name: str = "GAS_RESERVOIR"
    ) -> EngineeringResult:
        """
        Executes p/z gas material balance linear regression.
        History must contain at least 2 points with:
            - 'pressure_psia' (psia)
            - 'cumulative_gas_gp_mscf' (Mscf)
        """
        inputs = {
            "num_history_points": len(history) if history else 0,
            "temperature_f": temperature_f,
            "gas_gravity": gas_gravity,
            "abandonment_pressure_psia": abandonment_pressure_psia,
            "reservoir_name": reservoir_name
        }

        if not history or len(history) < 2:
            return EngineeringResult(
                calculation_name="GAS_PZ_MATERIAL_BALANCE",
                value=None,
                unit="Mscf",
                inputs=inputs,
                model="Volumetric Gas Material Balance (p/z vs Gp)",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                assumptions=["Requires at least 2 static shut-in pressure surveys with accurate cumulative production Gp"],
                limitations=["Cannot compute slope or extrapolate OGIP with fewer than 2 valid history points."],
                warnings=["At least 2 historical (Gp, P) points are strictly required for p/z regression."]
            )

        if temperature_f is None or gas_gravity <= 0:
            return EngineeringResult(
                calculation_name="GAS_PZ_MATERIAL_BALANCE",
                value=None,
                unit="Mscf",
                inputs=inputs,
                model="Volumetric Gas Material Balance",
                status=EngineeringStatus.INVALID_INPUT.value,
                warnings=["Invalid temperature or gas gravity."]
            )

        # Process each point with canonical Hall-Yarborough Z-factor
        points_data = []
        gp_list = []
        pz_list = []

        for idx, pt in enumerate(history):
            p = pt.get("pressure_psia")
            gp = pt.get("cumulative_gas_gp_mscf", pt.get("cumulative_gas_mscf", pt.get("gp_mscf")))

            if p is None or p <= 0 or gp is None or gp < 0:
                return EngineeringResult(
                    calculation_name="GAS_PZ_MATERIAL_BALANCE",
                    value=None,
                    unit="Mscf",
                    inputs=inputs,
                    model="Volumetric Gas Material Balance",
                    status=EngineeringStatus.INVALID_INPUT.value,
                    warnings=[f"Point index {idx} contains invalid pressure ({p}) or Gp ({gp})."]
                )

            z_res = PVTEngine.calculate_z_factor_hall_yarborough(p, temperature_f, gas_gravity)
            if z_res.status != EngineeringStatus.VALID.value:
                return EngineeringResult(
                    calculation_name="GAS_PZ_MATERIAL_BALANCE",
                    value=None,
                    unit="Mscf",
                    inputs=inputs,
                    model="Volumetric Gas Material Balance",
                    status=z_res.status,
                    warnings=[f"Z-factor evaluation failed at P={p} psia: {z_res.warnings}"]
                )

            z_val = float(z_res.value)
            pz_val = p / z_val

            points_data.append({
                "pressure_psia": p,
                "z_factor": round(z_val, 4),
                "pz_psia": round(pz_val, 2),
                "cumulative_gas_gp_mscf": float(gp)
            })
            gp_list.append(float(gp))
            pz_list.append(float(pz_val))

        # Check for non-constant Gp
        if max(gp_list) == min(gp_list):
            return EngineeringResult(
                calculation_name="GAS_PZ_MATERIAL_BALANCE",
                value=None,
                unit="Mscf",
                inputs=inputs,
                model="Volumetric Gas Material Balance",
                status=EngineeringStatus.INVALID_INPUT.value,
                warnings=["Cumulative production Gp is constant across all points; cannot establish depletion trend."]
            )

        # Linear regression: p/z = a - b * Gp
        n_pts = len(gp_list)
        sum_x = sum(gp_list)
        sum_y = sum(pz_list)
        sum_xx = sum(x * x for x in gp_list)
        sum_xy = sum(x * y for x, y in zip(gp_list, pz_list))
        sum_yy = sum(y * y for y in pz_list)

        denominator = (n_pts * sum_xx - sum_x * sum_x)
        if abs(denominator) < 1e-12:
            return EngineeringResult(
                calculation_name="GAS_PZ_MATERIAL_BALANCE",
                value=None,
                unit="Mscf",
                inputs=inputs,
                model="Volumetric Gas Material Balance",
                status=EngineeringStatus.INVALID_INPUT.value,
                warnings=["Degenerate dataset: singular regression denominator."]
            )

        slope = (n_pts * sum_xy - sum_x * sum_y) / denominator  # expected negative for depletion
        intercept = (sum_y - slope * sum_x) / n_pts

        # Pearson R^2
        ss_tot = sum((y - (sum_y / n_pts)) ** 2 for y in pz_list)
        ss_res = sum((y - (intercept + slope * x)) ** 2 for x, y in zip(gp_list, pz_list))
        r_squared = 1.0 - (ss_res / ss_tot) if ss_tot > 0 else 1.0

        warnings = []
        observed_pattern = "DEPLETION_DRIVE_LINEAR"
        diagnostic_interp = "Classic volumetric gas depletion behavior observed."

        # Physical expectation: slope must be negative for depletion
        if slope >= 0:
            warnings.append("PHYSICAL ANOMALY: p/z slope is positive (increasing p/z with production). Possible gas injection or extreme measurement error.")
            observed_pattern = "ANOMALOUS_PRESSURE_INCREASE"
            diagnostic_interp = "Reservoir pressure increasing with cumulative production. Investigate gas injection or pressure gauge drift."
            ogip_mscf = None
            eur_mscf = None
            remaining_reserves_mscf = None
            rf = None
        else:
            # Extrapolation to p/z = 0 -> G = intercept / abs(slope)
            ogip_mscf = intercept / abs(slope)

            # Abandonment p/z
            z_ab_res = PVTEngine.calculate_z_factor_hall_yarborough(abandonment_pressure_psia, temperature_f, gas_gravity)
            z_ab = float(z_ab_res.value) if z_ab_res.status == EngineeringStatus.VALID.value else 0.95
            pz_ab = abandonment_pressure_psia / z_ab

            eur_mscf = (intercept - pz_ab) / abs(slope) if intercept > pz_ab else 0.0
            latest_gp = max(gp_list)
            remaining_reserves_mscf = max(0.0, eur_mscf - latest_gp)
            rf = (eur_mscf / ogip_mscf) if ogip_mscf > 0 else 0.0

            # Aquifer / water influx curvature check
            # In water drive, late p/z points stay above linear trend (concave upward)
            if n_pts >= 3:
                mid_idx = n_pts // 2
                expected_mid = intercept + slope * gp_list[mid_idx]
                actual_mid = pz_list[mid_idx]
                if pz_list[-1] > (intercept + slope * gp_list[-1]) and actual_mid < expected_mid:
                    warnings.append("DIAGNOSTIC EVIDENCE: p/z points deviate upwards from linear trend. Potential active water drive / aquifer encroachment.")
                    observed_pattern = "WATER_DRIVE_SUSPECTED_NON_LINEAR_PZ"
                    diagnostic_interp = "Concave-upward p/z trend indicates reservoir pressure maintenance from water drive or pore volume compaction."

        return EngineeringResult(
            calculation_name="GAS_PZ_MATERIAL_BALANCE",
            value=float(ogip_mscf) if ogip_mscf is not None else None,
            unit="Mscf",
            inputs=inputs,
            model="Volumetric Gas Material Balance (p/z vs Gp linear regression)",
            assumptions=[
                "Volumetric gas reservoir with closed boundaries (no initial water drive assumed)",
                "Equilibrium average static reservoir pressure across drainage volume",
                "Constant reservoir temperature"
            ],
            limitations=[
                "Water drive leads to optimistic overestimation of OGIP if linear regression is forced.",
                "Requires stabilized static shut-in pressures (build-up p*)."
            ],
            evidence={
                "points": points_data,
                "initial_pz_intercept_psia": round(intercept, 2),
                "slope_psia_per_mscf": slope,
                "r_squared": round(r_squared, 4),
                "ogip_mscf": round(ogip_mscf, 2) if ogip_mscf else None,
                "ogip_bscf": round(ogip_mscf / 1e6, 4) if ogip_mscf else None,
                "eur_mscf": round(eur_mscf, 2) if eur_mscf else None,
                "eur_bscf": round(eur_mscf / 1e6, 4) if eur_mscf else None,
                "remaining_reserves_mscf": round(remaining_reserves_mscf, 2) if remaining_reserves_mscf else None,
                "recovery_factor_at_abandonment": round(rf, 4) if rf else None,
                "abandonment_pressure_psia": abandonment_pressure_psia
            },
            status=EngineeringStatus.VALID.value,
            provenance={
                "engine": "GasReservoirEngine",
                "method": "Linear p/z Depletion Extrapolation",
                "pvt_engine": "PVTEngine.calculate_z_factor_hall_yarborough",
                "version": "Step2C-v1.2",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            observed_pattern=observed_pattern,
            diagnostic_interpretation=diagnostic_interp,
            warnings=warnings
        )

    @classmethod
    def calculate_gas_deliverability_ipr(
        cls,
        reservoir_pressure_pr_psia: float,
        flowing_pressure_pwf_psia: float,
        c_coefficient: float,
        n_exponent: float,
        well_code: str = "GAS_WELL"
    ) -> EngineeringResult:
        """
        Computes gas well deliverability using the Rawlins & Schellhardt Backpressure Equation:
            qg = C * (pr^2 - pwf^2)^n   [Mscf/d]
        Validates:
            pr > pwf >= 0
            0.5 <= n <= 1.0
            C > 0
        Also computes Absolute Open Flow (AOF) at pwf = 0:
            AOF = C * (pr^2)^n
        """
        inputs = {
            "reservoir_pressure_pr_psia": reservoir_pressure_pr_psia,
            "flowing_pressure_pwf_psia": flowing_pressure_pwf_psia,
            "c_coefficient": c_coefficient,
            "n_exponent": n_exponent,
            "well_code": well_code
        }

        # Validations
        if reservoir_pressure_pr_psia <= 0 or flowing_pressure_pwf_psia < 0:
            return EngineeringResult(
                calculation_name="GAS_DELIVERABILITY_RAWLINS_SCHELLHARDT",
                value=None,
                unit="Mscf/d",
                inputs=inputs,
                model="Rawlins & Schellhardt (1936) Backpressure Equation",
                status=EngineeringStatus.INVALID_INPUT.value,
                limitations=["Pressures must be non-negative."],
                warnings=["Invalid pressure inputs: pr must be positive, pwf >= 0."]
            )

        if flowing_pressure_pwf_psia >= reservoir_pressure_pr_psia:
            return EngineeringResult(
                calculation_name="GAS_DELIVERABILITY_RAWLINS_SCHELLHARDT",
                value=0.0,
                unit="Mscf/d",
                inputs=inputs,
                model="Rawlins & Schellhardt (1936)",
                status=EngineeringStatus.ZERO_DRAWDOWN.value,
                limitations=["Pwf >= Pr results in zero or negative drawdown."],
                warnings=["Zero or reverse drawdown: flowing pressure equals or exceeds reservoir pressure."]
            )

        if not (0.5 <= n_exponent <= 1.0):
            return EngineeringResult(
                calculation_name="GAS_DELIVERABILITY_RAWLINS_SCHELLHARDT",
                value=None,
                unit="Mscf/d",
                inputs=inputs,
                model="Rawlins & Schellhardt (1936)",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                limitations=["Backpressure exponent n must be between 0.5 (completely turbulent) and 1.0 (completely laminar)."],
                warnings=[f"Exponent n={n_exponent} outside standard petroleum engineering range [0.5, 1.0]."]
            )

        if c_coefficient <= 0:
            return EngineeringResult(
                calculation_name="GAS_DELIVERABILITY_RAWLINS_SCHELLHARDT",
                value=None,
                unit="Mscf/d",
                inputs=inputs,
                model="Rawlins & Schellhardt (1936)",
                status=EngineeringStatus.INVALID_INPUT.value,
                warnings=["Flow coefficient C must be strictly positive."]
            )

        # Computation
        delta_p2 = (reservoir_pressure_pr_psia ** 2) - (flowing_pressure_pwf_psia ** 2)
        qg_mscfd = c_coefficient * (delta_p2 ** n_exponent)

        # AOF at pwf = 0
        aof_mscfd = c_coefficient * ((reservoir_pressure_pr_psia ** 2) ** n_exponent)

        # Generate standard 5-point IPR curve
        ipr_curve = []
        pwf_steps = [0.0, 0.25 * reservoir_pressure_pr_psia, 0.5 * reservoir_pressure_pr_psia, 0.75 * reservoir_pressure_pr_psia, reservoir_pressure_pr_psia]
        for p_step in pwf_steps:
            dp2_step = max(0.0, (reservoir_pressure_pr_psia ** 2) - (p_step ** 2))
            q_step = c_coefficient * (dp2_step ** n_exponent)
            ipr_curve.append({"pwf_psia": round(p_step, 1), "qg_mscfd": round(q_step, 2)})

        return EngineeringResult(
            calculation_name="GAS_DELIVERABILITY_RAWLINS_SCHELLHARDT",
            value=round(qg_mscfd, 2),
            unit="Mscf/d",
            inputs=inputs,
            model="Rawlins & Schellhardt (1936) Backpressure Equation (qg = C * (Pr^2 - Pwf^2)^n)",
            assumptions=[
                "Radial pseudo-steady state gas flow",
                "Drawdown squared approximation valid for moderate pressure differentials",
                f"Turbulence flow regime governed by exponent n={n_exponent}"
            ],
            limitations=[
                "Backpressure equation assumes constant reservoir pressure Pr during test.",
                "At very high reservoir pressures (> 3000 psia), pseudo-pressure m(p) formulation is recommended."
            ],
            evidence={
                "drawdown_delta_p2_psia2": round(delta_p2, 2),
                "operating_flow_rate_mscfd": round(qg_mscfd, 2),
                "aof_potential_mscfd": round(aof_mscfd, 2),
                "aof_mmscfd": round(aof_mscfd / 1000.0, 3),
                "ipr_curve_points": ipr_curve
            },
            status=EngineeringStatus.VALID.value,
            provenance={
                "engine": "GasReservoirEngine",
                "standard": "Rawlins, E.L. and Schellhardt, M.A. (1936), USBM Monograph 7",
                "version": "Step2C-v1.2",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            observed_pattern="GAS_WELL_BACKPRESSURE_PERFORMANCE",
            diagnostic_interpretation=f"Gas deliverability evaluated: AOF potential is {aof_mscfd/1000:.2f} MMscf/d at reservoir pressure {reservoir_pressure_pr_psia:.0f} psia."
        )

    @classmethod
    def calculate_real_gas_pseudopressure(
        cls,
        pressure_psia: float,
        temperature_f: float,
        gas_gravity: float,
        p_base_psia: float = 14.7,
        num_intervals: int = 50
    ) -> EngineeringResult:
        """
        Computes the Real Gas Pseudo-Pressure function m(p) via numerical integration:
            m(p) = 2 * Integral_{p_base}^p [ p / (mu_g(p) * z(p)) ] dp   [psia^2 / cP]
        Uses canonical PVTEngine for both Hall-Yarborough Z-factor and Lee et al. gas viscosity.
        Integrates using the composite trapezoidal rule.
        """
        inputs = {
            "pressure_psia": pressure_psia,
            "temperature_f": temperature_f,
            "gas_gravity": gas_gravity,
            "p_base_psia": p_base_psia,
            "num_intervals": num_intervals
        }

        if pressure_psia <= p_base_psia:
            return EngineeringResult(
                calculation_name="GAS_PSEUDOPRESSURE_MP",
                value=0.0,
                unit="psia^2/cP",
                inputs=inputs,
                model="Real Gas Pseudo-Pressure Integral (Al-Hussainy, Ramey & Crawford, 1966)",
                status=EngineeringStatus.VALID.value,
                evidence={"integral_value": 0.0, "note": "Pressure <= base pressure"}
            )

        if gas_gravity <= 0 or num_intervals < 10:
            return EngineeringResult(
                calculation_name="GAS_PSEUDOPRESSURE_MP",
                value=None,
                unit="psia^2/cP",
                inputs=inputs,
                model="Real Gas Pseudo-Pressure Integral",
                status=EngineeringStatus.INVALID_INPUT.value,
                warnings=["Invalid gas gravity or insufficient integration intervals."]
            )

        dp = (pressure_psia - p_base_psia) / num_intervals
        pressures = [p_base_psia + i * dp for i in range(num_intervals + 1)]

        integrand_values = []
        for p in pressures:
            z_res = PVTEngine.calculate_z_factor_hall_yarborough(p, temperature_f, gas_gravity)
            if z_res.status != EngineeringStatus.VALID.value:
                return EngineeringResult(
                    calculation_name="GAS_PSEUDOPRESSURE_MP",
                    value=None,
                    unit="psia^2/cP",
                    inputs=inputs,
                    model="Real Gas Pseudo-Pressure Integral",
                    status=z_res.status,
                    warnings=[f"Failed evaluating Z-factor at P={p} psia: {z_res.warnings}"]
                )
            z_val = float(z_res.value)

            mu_res = PVTEngine.calculate_gas_viscosity_lee(p, temperature_f, gas_gravity, z_factor=z_val)
            if mu_res.status != EngineeringStatus.VALID.value:
                return EngineeringResult(
                    calculation_name="GAS_PSEUDOPRESSURE_MP",
                    value=None,
                    unit="psia^2/cP",
                    inputs=inputs,
                    model="Real Gas Pseudo-Pressure Integral",
                    status=mu_res.status,
                    warnings=[f"Failed evaluating gas viscosity at P={p} psia: {mu_res.warnings}"]
                )
            mu_val = float(mu_res.value)

            # Integrand: 2 * p / (mu_g * z)
            val = (2.0 * p) / (mu_val * z_val)
            integrand_values.append(val)

        # Composite trapezoidal rule: dp/2 * [y0 + 2*y1 + ... + yn]
        integral = (dp / 2.0) * (integrand_values[0] + 2.0 * sum(integrand_values[1:-1]) + integrand_values[-1])

        return EngineeringResult(
            calculation_name="GAS_PSEUDOPRESSURE_MP",
            value=round(integral, 2),
            unit="psia^2/cP",
            inputs=inputs,
            model="Al-Hussainy, Ramey & Crawford (1966) Real Gas Pseudo-Pressure Integral",
            correlation_reference="Al-Hussainy, R., Ramey, H.J. Jr., and Crawford, P.B. (1966), JPT, 18(5), 624-636",
            assumptions=[
                "Linearizes non-linear real gas pressure diffusivity equation",
                "Integrates continuously from base pressure using canonical Hall-Yarborough Z and Lee et al. viscosity"
            ],
            limitations=[
                "Composition assumed constant across integration path (dry natural gas).",
                "Requires condensate gas PVT adjustments if operating below dew point."
            ],
            evidence={
                "m_p_psia2_per_cp": round(integral, 2),
                "upper_pressure_psia": pressure_psia,
                "base_pressure_psia": p_base_psia,
                "num_intervals": num_intervals,
                "final_integrand_value": round(integrand_values[-1], 2)
            },
            status=EngineeringStatus.VALID.value,
            provenance={
                "engine": "GasReservoirEngine",
                "pvt_source": "Canonical PVTEngine (Hall-Yarborough Z + Lee et al. mu_g)",
                "version": "Step2C-v1.2",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            observed_pattern="RIGOROUS_PSEUDOPRESSURE_EVALUATION",
            diagnostic_interpretation=f"Real gas pseudo-pressure evaluated at {pressure_psia:.1f} psia: m(p) = {integral:.1f} psia^2/cP."
        )

    @classmethod
    def calculate_nondarcy_turbulence_factor(
        cls,
        reservoir_pressure_pr_psia: float,
        flowing_pressure_pwf_psia: float,
        gas_rate_qg_mscfd: float,
        laminar_coefficient_a: float,
        turbulent_coefficient_b: float,
        well_code: str = "GAS_WELL"
    ) -> EngineeringResult:
        """
        Calculates non-Darcy turbulence drawdown partition using Forchheimer formulation:
            Pr^2 - Pwf^2 = A * qg + B * qg^2
        Computes:
            - Laminar pressure drop component: A * qg
            - Turbulent non-Darcy pressure drop component: B * qg^2
            - Turbulence fraction: (B * qg^2) / (A * qg + B * qg^2)
        """
        inputs = {
            "reservoir_pressure_pr_psia": reservoir_pressure_pr_psia,
            "flowing_pressure_pwf_psia": flowing_pressure_pwf_psia,
            "gas_rate_qg_mscfd": gas_rate_qg_mscfd,
            "laminar_coefficient_a": laminar_coefficient_a,
            "turbulent_coefficient_b": turbulent_coefficient_b,
            "well_code": well_code
        }

        if gas_rate_qg_mscfd <= 0 or laminar_coefficient_a <= 0 or turbulent_coefficient_b < 0:
            return EngineeringResult(
                calculation_name="GAS_NONDARCY_TURBULENCE",
                value=None,
                unit="dimensionless",
                inputs=inputs,
                model="Forchheimer Quadratic Gas Drawdown Model",
                status=EngineeringStatus.INVALID_INPUT.value,
                warnings=["Rate and laminar coefficient A must be positive; B >= 0."]
            )

        dp2_laminar = laminar_coefficient_a * gas_rate_qg_mscfd
        dp2_turbulent = turbulent_coefficient_b * (gas_rate_qg_mscfd ** 2)
        dp2_total = dp2_laminar + dp2_turbulent

        turb_fraction = dp2_turbulent / dp2_total if dp2_total > 0 else 0.0

        return EngineeringResult(
            calculation_name="GAS_NONDARCY_TURBULENCE",
            value=round(turb_fraction, 4),
            unit="dimensionless",
            inputs=inputs,
            model="Forchheimer Quadratic Gas Drawdown Partition (Pr^2 - Pwf^2 = A*q + B*q^2)",
            assumptions=[
                "High-velocity gas flow near wellbore exhibits non-Darcy inertial pressure loss",
                "Turbulent coefficient B accounts for geometric choke and perforation flow convergence"
            ],
            limitations=[
                "Requires multi-rate flow-after-flow or isochronal test to decouple A and B coefficients accurately."
            ],
            evidence={
                "laminar_dp2_psia2": round(dp2_laminar, 2),
                "turbulent_dp2_psia2": round(dp2_turbulent, 2),
                "total_drawdown_dp2_psia2": round(dp2_total, 2),
                "turbulence_drawdown_fraction": round(turb_fraction, 4),
                "turbulence_percentage": round(turb_fraction * 100.0, 2)
            },
            status=EngineeringStatus.VALID.value,
            provenance={
                "engine": "GasReservoirEngine",
                "standard": "Forchheimer (1901) / Swift & Kiel (1962)",
                "version": "Step2C-v1.2",
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            observed_pattern="TURBULENT_HIGH_VELOCITY_GAS_FLOW" if turb_fraction > 0.25 else "PREDOMINANTLY_LAMINAR_FLOW",
            diagnostic_interpretation=(
                f"Non-Darcy turbulence accounts for {turb_fraction * 100.0:.1f}% of total squared drawdown at rate {gas_rate_qg_mscfd:.0f} Mscf/d."
            )
        )
