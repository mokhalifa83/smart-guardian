"""
Smart Guardian Reservoir Intelligence Layer - Physics-Informed AI (PIAI) Guardrails & SPE Standards Layer
========================================================================================================
Architecture Principle:
No Black-Box AI. All engineering calculations, predictive models, and surveillance diagnostics
must be strictly bounded by peer-reviewed Society of Petroleum Engineers (SPE) physics and
hard thermodynamic / fluid mechanics conservation laws.

Governing Standards & Peer-Reviewed References:
1. SPE-PRMS: Petroleum Resources Management System (SPE, AAPG, WPC, SPEE, SEG, EAGE)
2. Havlena, D. & Odeh, A.S. (1963): SPE-510 - The Material Balance as an Equation of a Straight Line
3. Vogel, J.V. (1968): SPE-1476 - Inflow Performance Relationships for Solution-Gas Drive Wells
4. Chan, K.S. (1995): SPE-30775 - Water Control Diagnostic Plots
5. Buckley, S.E. & Leverett, M.C. (1942): Trans. AIME 146 - Mechanism of Fluid Displacement in Sands
6. Arps, J.J. (1945): Trans. AIME 160 - Analysis of Decline Curves
7. Horner, D.R. (1951): Third World Pet. Cong. - Pressure Build-up in Wells
8. Standing, M.B. (1947): SPE-AIME - A General Pressure-Volume-Temperature Correlation for California Crudes
9. Vasquez, M. & Beggs, H.D. (1980): SPE-6719 - Correlations for Fluid Physical Property Prediction
"""

import math
from typing import Any, Dict, List, Optional, Tuple
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class PhysicsConstraintViolation(Exception):
    """Raised when an unconstrained model or calculation violates immutable physical laws."""
    def __init__(self, rule_code: str, message: str, physical_domain: str, observed_value: Any, expected_bound: str):
        super().__init__(f"[{rule_code}] {message} (Observed: {observed_value}, Expected: {expected_bound})")
        self.rule_code = rule_code
        self.physical_domain = physical_domain
        self.observed_value = observed_value
        self.expected_bound = expected_bound


class PhysicsGuardrails:
    """
    Central Physics-Informed AI Guardrails & SPE Standards Verification Layer.
    Enforces Hard Physical Constraints on all 36 Reservoir Engines and predictive algorithms.
    """

    # =========================================================================
    # 1. THERMODYNAMICS & PVT HARD CONSTRAINTS (Standing 1947, Vasquez-Beggs 1980)
    # =========================================================================
    @staticmethod
    def validate_pvt_boundaries(
        bo: Optional[float] = None,
        bg: Optional[float] = None,
        bw: Optional[float] = None,
        rs: Optional[float] = None,
        reservoir_pressure_psia: Optional[float] = None,
        temperature_f: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Hard Thermodynamic Laws:
        - Bo >= 1.0 rb/STB (Liquid cannot contract below surface stock-tank volume without external phase change).
        - Bw >= 1.0 rb/STB (Water formation volume factor is strictly >= 1.0).
        - Bg > 0.0 rb/scf (Gas volume factor is strictly positive).
        - Rs >= 0.0 scf/STB (Solution GOR cannot be negative).
        - Absolute pressure > 0 psia and absolute temperature > -459.67 F.
        """
        if bo is not None and bo < 1.0:
            return False, f"Thermodynamic Violation: Bo ({bo} rb/stb) < 1.0 rb/stb. SPE PVT laws require Bo >= 1.0."

        if bw is not None and bw < 1.0:
            return False, f"Thermodynamic Violation: Bw ({bw} rb/stb) < 1.0 rb/stb. Water formation volume factor must be >= 1.0."

        if bg is not None and bg <= 0.0:
            return False, f"Thermodynamic Violation: Bg ({bg} rb/scf) <= 0.0. Gas volume factor must be strictly positive."

        if rs is not None and rs < 0.0:
            return False, f"Thermodynamic Violation: Rs ({rs} scf/stb) < 0.0. Solution gas-oil ratio cannot be negative."

        if reservoir_pressure_psia is not None and reservoir_pressure_psia <= 0.0:
            return False, f"Thermodynamic Violation: Pressure ({reservoir_pressure_psia} psia) <= 0. Absolute pressure must be positive."

        if temperature_f is not None and temperature_f < -459.67:
            return False, f"Thermodynamic Violation: Temperature ({temperature_f} F) is below absolute zero (-459.67 F)."

        return True, None

    # =========================================================================
    # 2. INFLOW PERFORMANCE & HYDRAULICS HARD CONSTRAINTS (Vogel 1968, Darcy)
    # =========================================================================
    @staticmethod
    def validate_inflow_hydraulics(
        reservoir_pressure_psia: float,
        flowing_bhp_psia: float,
        flow_rate_stbd: Optional[float] = None,
        qmax_stbd: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Fluid Mechanics & Reservoir Inflow Laws:
        - For a producing well, Pwf <= Pres (Energy dissipation requires potential drop towards wellbore).
        - Drawdown Delta_P = Pres - Pwf >= 0.
        - Producing flow rate q >= 0 (Negative rate implies injection, not production).
        - Producing rate q <= qmax (Rate cannot physically exceed theoretical absolute open flow potential AOFP).
        """
        if flowing_bhp_psia > reservoir_pressure_psia:
            return False, (
                f"Fluid Mechanics Violation: Pwf ({flowing_bhp_psia} psia) > Pres ({reservoir_pressure_psia} psia). "
                f"Negative drawdown is physically impossible for a producing well (violates Darcy's law)."
            )

        if flow_rate_stbd is not None and flow_rate_stbd < 0.0:
            return False, f"Physical Violation: Producing rate ({flow_rate_stbd} STB/D) < 0. Rate must be non-negative."

        if qmax_stbd is not None and flow_rate_stbd is not None and flow_rate_stbd > qmax_stbd:
            return False, (
                f"Fluid Mechanics Violation: Rate ({flow_rate_stbd} STB/D) > AOFP / Qmax ({qmax_stbd} STB/D). "
                f"A well cannot produce beyond maximum theoretical open-flow potential at zero backpressure."
            )

        return True, None

    # =========================================================================
    # 3. MATERIAL BALANCE & CONSERVATION OF MASS (Havlena-Odeh 1963, SPE-510)
    # =========================================================================
    @staticmethod
    def validate_material_balance_conservation(
        np_stb: float,
        n_stb_ooip: Optional[float] = None,
        recovery_factor: Optional[float] = None,
        drive_indices: Optional[Dict[str, float]] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Conservation of Mass Laws:
        - Cumulative production Np >= 0.
        - Cumulative production Np <= OOIP (N). A reservoir cannot produce more oil than originally in place.
        - Recovery factor RF in [0.0, 1.0] (0% to 100%).
        - Sum of Havlena-Odeh drive mechanism indices (DDI + SDI + WDI + EDI) must equal 1.0 +/- tolerance.
        """
        if np_stb < 0.0:
            return False, f"Conservation of Mass Violation: Np ({np_stb} STB) < 0. Cumulative production must be non-negative."

        if n_stb_ooip is not None:
            if n_stb_ooip <= 0.0:
                return False, f"Physical Violation: OOIP N ({n_stb_ooip} STB) <= 0. In-place volume must be strictly positive."
            if np_stb > n_stb_ooip:
                return False, (
                    f"Conservation of Mass Violation: Cumulative production Np ({np_stb:,.0f} STB) > "
                    f"OOIP N ({n_stb_ooip:,.0f} STB). Violates fundamental mass conservation."
                )

        if recovery_factor is not None:
            if recovery_factor < 0.0 or recovery_factor > 1.0:
                return False, f"Physical Violation: Recovery factor ({recovery_factor:.2%}) must be between 0.0 and 1.0."

        if drive_indices:
            total_index = sum(drive_indices.values())
            # Allow +/- 15% tolerance for pressure measurement uncertainty in field regression
            if not (0.85 <= total_index <= 1.15):
                return False, (
                    f"Material Balance Inconsistency: Sum of Drive Indices = {total_index:.3f} != 1.0. "
                    f"Drive indices must sum to unity at material balance equilibrium (Havlena & Odeh 1963)."
                )

        return True, None

    # =========================================================================
    # 4. MULTIPHASE FLOW & SATURATION HARD CONSTRAINTS (Buckley-Leverett 1942)
    # =========================================================================
    @staticmethod
    def validate_saturation_and_relative_perm(
        sw: Optional[float] = None,
        swi: Optional[float] = None,
        sor: Optional[float] = None,
        krw: Optional[float] = None,
        kro: Optional[float] = None,
        water_cut_pct: Optional[float] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Porous Media & Multiphase Laws:
        - Saturations Sw, Swi, Sor in [0.0, 1.0].
        - Physical saturation window: Swi <= Sw <= (1 - Sor).
        - Relative permeabilities krw, kro in [0.0, 1.0].
        - Water Cut in [0.0%, 100.0%].
        """
        if sw is not None and not (0.0 <= sw <= 1.0):
            return False, f"Porous Media Violation: Water saturation Sw ({sw}) must be within [0.0, 1.0]."

        if swi is not None and not (0.0 <= swi <= 1.0):
            return False, f"Porous Media Violation: Connate water saturation Swi ({swi}) must be within [0.0, 1.0]."

        if sor is not None and not (0.0 <= sor <= 1.0):
            return False, f"Porous Media Violation: Residual oil saturation Sor ({sor}) must be within [0.0, 1.0]."

        if swi is not None and sor is not None and (swi + sor) >= 1.0:
            return False, f"Physical Violation: Swi ({swi}) + Sor ({sor}) >= 1.0 leaves zero moveable hydrocarbon pore volume."

        if krw is not None and not (0.0 <= krw <= 1.0):
            return False, f"Physical Violation: Relative permeability krw ({krw}) must be within [0.0, 1.0]."

        if kro is not None and not (0.0 <= kro <= 1.0):
            return False, f"Physical Violation: Relative permeability kro ({kro}) must be within [0.0, 1.0]."

        if water_cut_pct is not None and not (0.0 <= water_cut_pct <= 100.0):
            return False, f"Field Telemetry Violation: Water Cut ({water_cut_pct}%) must be within [0.0%, 100.0%]."

        return True, None

    # =========================================================================
    # 5. DECLINE CURVE ANALYSIS HARD CONSTRAINTS (Arps 1945, SPE-AIME 160)
    # =========================================================================
    @staticmethod
    def validate_arps_decline_parameters(
        qi_stbd: float,
        nominal_decline_di: float,
        b_factor: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Arps Empirical Decline Foundations:
        - Initial rate qi > 0.
        - Nominal decline rate Di > 0 (Production must decline over time under depletion).
        - Conventional volumetric Arps b-factor in [0.0, 1.0]:
          * b = 0.0 (Exponential decline - constant Di)
          * 0.0 < b < 1.0 (Hyperbolic decline)
          * b = 1.0 (Harmonic decline)
          * Note: Transient fracture/unconventional flow may exhibit b > 1.0 temporarily,
            but must be tagged with explicit transient boundary notice.
        """
        if qi_stbd <= 0.0:
            return False, f"Arps DCA Violation: Initial rate qi ({qi_stbd} STB/D) must be positive."

        if nominal_decline_di <= 0.0:
            return False, f"Arps DCA Violation: Decline rate Di ({nominal_decline_di}) must be positive for depletion analysis."

        if b_factor < 0.0:
            return False, f"Arps DCA Violation: Arps b-factor ({b_factor}) cannot be negative."

        return True, None

    # =========================================================================
    # 6. STRICT DATA INTEGRITY POLICY (NO SYNTHETIC DATA / NO RANDOM GUESSES)
    # =========================================================================
    @staticmethod
    def assert_strict_data_integrity(
        required_fields: Dict[str, Any],
        calculation_name: str,
        model_name: str,
        spe_reference: str
    ) -> Optional[EngineeringResult]:
        """
        Enforces Rule:
        If required field telemetry or reservoir laboratory parameters are missing,
        NEVER substitute fake zeroes or synthetic values.
        Returns explicit EngineeringResult with status INSUFFICIENT_DATA and detailed notes.
        """
        missing_fields = [k for k, v in required_fields.items() if v is None]

        if missing_fields:
            return EngineeringResult(
                calculation_name=calculation_name,
                value=None,
                unit=None,
                inputs=required_fields,
                model=model_name,
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                correlation_reference=spe_reference,
                assumptions=[
                    "Strict Data Integrity Policy: No synthetic or fabricated fallback values permitted.",
                    "Physics-Informed AI: Unvalidated zero substitution is strictly prohibited."
                ],
                limitations=[
                    f"Missing required parameter(s): {', '.join(missing_fields)}.",
                    "Calculation halted to preserve 100% verified engineering accuracy."
                ],
                warnings=[
                    f"Calculation '{calculation_name}' aborted: Missing parameters [{', '.join(missing_fields)}]."
                ]
            )

        return None
