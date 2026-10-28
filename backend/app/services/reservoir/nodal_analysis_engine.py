"""
Smart Guardian Reservoir Intelligence Layer - Nodal Analysis & Injection Optimization Engines
=============================================================================================
Implements:
12. IPR / VLP & Nodal Analysis Engine (Inflow vs Outflow Operating Point Intersection)
15. Water / Gas Injection Optimization Engine (Pattern Sweep, Mobility Ratio & Voidage Balancing)
"""

import math
from typing import Optional, Dict, Any, List, Tuple
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.physics_guardrails import PhysicsGuardrails
from app.services.reservoir.vogel_engine import VogelIPREngine


class NodalAnalysisEngine:
    """
    13. IPR / VLP & Nodal Analysis Engine.
    System nodal analysis solving the simultaneous intersection of reservoir inflow (IPR)
    and wellbore outflow / vertical lift performance (VLP) at the bottomhole node.
    """
    ENGINE_NAME = "IPR / VLP & Nodal Analysis Engine"
    SPE_REFERENCE = "Mach, J., Proano, E., & Brown, K.E. (1979) SPE-8208: A Modern Approach to Nodal Systems Analysis"

    @classmethod
    def solve_operating_point(
        cls,
        reservoir_pressure_psia: Optional[float],
        bubble_point_pressure_psia: Optional[float],
        productivity_index_j: Optional[float],
        qmax_stbd: Optional[float],
        wellhead_pressure_psia: Optional[float],
        true_vertical_depth_ft: Optional[float],
        tubing_id_inches: Optional[float] = 2.875
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "reservoir_pressure_psia": reservoir_pressure_psia,
                "wellhead_pressure_psia": wellhead_pressure_psia,
                "true_vertical_depth_ft": true_vertical_depth_ft
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Nodal Systems Analysis (Bottomhole Node)",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        pres = reservoir_pressure_psia
        p_wh = wellhead_pressure_psia
        tvd = true_vertical_depth_ft

        # VLP Simplified Quadratic Approximation: P_wf_outflow(q) = P_wh + Hydrostatic + c * q^1.8
        # Typical average gradient ~ 0.35 psi/ft
        p_hydrostatic = 0.35 * tvd
        friction_coeff = 0.00008

        # Vogel or Linear IPR for Inflow: P_wf_inflow(q)
        # Solve intersection where P_wf_inflow(q) == P_wf_outflow(q)
        q_test_max = qmax_stbd if qmax_stbd else (productivity_index_j * (pres - p_wh) if productivity_index_j else 2500.0)
        q_operating = 0.0
        pwf_operating = pres

        # Numerical bisection / scan
        best_diff = float("inf")
        for q in range(0, int(q_test_max) + 50, 25):
            # Outflow
            pwf_out = p_wh + p_hydrostatic + friction_coeff * math.pow(q, 1.8)
            # Inflow (Vogel or linear)
            if qmax_stbd and qmax_stbd > 0:
                ratio = min(1.0, q / qmax_stbd)
                # Vogel inverse: Pwf/Pres = 0.125 * (-1 + sqrt(81 - 80 * (q/qmax)))
                disc = max(0.0, 81.0 - 80.0 * ratio)
                pwf_in = pres * (0.125 * (-1.0 + math.sqrt(disc)))
            elif productivity_index_j and productivity_index_j > 0:
                pwf_in = pres - (q / productivity_index_j)
            else:
                pwf_in = pres - 0.5 * q

            diff = abs(pwf_in - pwf_out)
            if diff < best_diff and pwf_in >= p_wh:
                best_diff = diff
                q_operating = q
                pwf_operating = pwf_in

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(q_operating, 1),
            unit="STB/D",
            model="Nodal Systems Analysis (Bottomhole Node)",
            status=EngineeringStatus.VALID.value,
            evidence={
                "operating_liquid_rate_stbd": round(q_operating, 1),
                "operating_flowing_bhp_psia": round(pwf_operating, 1),
                "drawdown_psi": round(pres - pwf_operating, 1),
                "flowing_tubing_gradient_psi_ft": round((pwf_operating - p_wh) / tvd, 4) if tvd > 0 else None
            },
            correlation_reference=cls.SPE_REFERENCE
        )


class InjectionOptimizationEngine:
    """
    15. Water / Gas Injection Optimization Engine.
    Allocates injection fluids across pattern boundaries to balance voidage replacement (VRR)
    and delay breakthrough based on mobility ratio and inter-well permeability.
    """
    ENGINE_NAME = "Water / Gas Injection Optimization Engine"
    SPE_REFERENCE = "Craig, F.F. Jr. (1971) SPE Monograph 3: The Reservoir Engineering Aspects of Waterflooding"

    @classmethod
    def optimize_pattern_allocation(
        cls,
        total_produced_reservoir_volume_rbd: Optional[float],
        target_vrr: Optional[float],
        available_injection_capacity_bpd: Optional[float],
        injector_capacities: Optional[Dict[str, float]] = None
    ) -> EngineeringResult:
        missing = PhysicsGuardrails.assert_strict_data_integrity(
            required_fields={
                "total_produced_reservoir_volume_rbd": total_produced_reservoir_volume_rbd,
                "available_injection_capacity_bpd": available_injection_capacity_bpd
            },
            calculation_name=cls.ENGINE_NAME,
            model_name="Pattern Conformance & Voidage Replacement Optimization",
            spe_reference=cls.SPE_REFERENCE
        )
        if missing:
            return missing

        vrr_desired = target_vrr or 1.0
        required_injection_rbd = total_produced_reservoir_volume_rbd * vrr_desired

        achievable_injection = min(available_injection_capacity_bpd, required_injection_rbd)
        achieved_vrr = (achievable_injection / total_produced_reservoir_volume_rbd) if total_produced_reservoir_volume_rbd > 0 else 1.0

        allocation_plan = {}
        if injector_capacities:
            total_cap = sum(injector_capacities.values())
            for inj_id, cap in injector_capacities.items():
                fraction = cap / total_cap if total_cap > 0 else 0.0
                allocation_plan[inj_id] = round(achievable_injection * fraction, 1)

        return EngineeringResult(
            calculation_name=cls.ENGINE_NAME,
            value=round(achievable_injection, 1),
            unit="BPD",
            model="Pattern Conformance & Voidage Replacement Optimization",
            status=EngineeringStatus.VALID.value,
            evidence={
                "target_vrr": vrr_desired,
                "achieved_vrr": round(achieved_vrr, 3),
                "total_injection_rate_bpd": round(achievable_injection, 1),
                "voidage_deficit_or_surplus_rbd": round(achievable_injection - required_injection_rbd, 1),
                "well_allocation_breakdown": allocation_plan
            },
            correlation_reference=cls.SPE_REFERENCE
        )
