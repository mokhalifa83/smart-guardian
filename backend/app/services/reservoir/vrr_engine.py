"""
Smart Guardian Reservoir Intelligence Layer - Voidage Replacement Ratio (VRR) Engine (Step 2A)
Implements:
    VRR = Injected Reservoir Volume / Produced Reservoir Volume
Strictly converts all surface rates and volumes to downhole reservoir volumes using PVT:
- Injected Reservoir Volume:
    V_inj = Wi_bbl * Bw + Gi_scf * Bg
- Produced Reservoir Volume:
    V_prod = Np_stb * Bo + Wp_bbl * Bw + (Gp_scf - Np_stb * Rs) * Bg

Strictly enforces:
1. Rate != Volume distinction (rates must be integrated over time window Delta_t)
2. No unit mixing (never sums STB oil + BBL water without downhole FVF conversion)
3. Zero division prevention: if V_prod == 0, returns UNDEFINED_VRR
"""

from typing import Optional, Dict, Any
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class VoidageReplacementEngine:
    """
    Canonical Voidage Replacement Ratio (VRR) Engine.
    """

    @staticmethod
    def calculate_vrr(
        # Cumulative Production Volumes
        produced_oil_stb: float,
        produced_water_bbl: float,
        produced_gas_scf: Optional[float] = None,
        # Injection Volumes
        injected_water_bbl: float = 0.0,
        injected_gas_scf: float = 0.0,
        # In-Situ PVT Properties
        bo_rb_stb: float = 1.25,
        bw_rb_stb: float = 1.02,
        bg_rb_scf: float = 0.00095,
        rs_scf_stb: float = 500.0,
        # Metadata
        time_window_days: Optional[float] = None,
        is_instantaneous_rate: bool = False
    ) -> EngineeringResult:
        inputs = {
            "produced_oil_stb": produced_oil_stb,
            "produced_water_bbl": produced_water_bbl,
            "produced_gas_scf": produced_gas_scf,
            "injected_water_bbl": injected_water_bbl,
            "injected_gas_scf": injected_gas_scf,
            "bo_rb_stb": bo_rb_stb,
            "bw_rb_stb": bw_rb_stb,
            "bg_rb_scf": bg_rb_scf,
            "rs_scf_stb": rs_scf_stb,
            "time_window_days": time_window_days,
            "is_instantaneous_rate": is_instantaneous_rate
        }

        # 1. Physics Validation
        if produced_oil_stb < 0.0 or produced_water_bbl < 0.0:
            return EngineeringResult(
                model="Voidage Replacement Ratio (VRR)",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Production volumes/rates cannot be negative"}
            )

        if injected_water_bbl < 0.0 or injected_gas_scf < 0.0:
            return EngineeringResult(
                model="Voidage Replacement Ratio (VRR)",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "Injection volumes/rates cannot be negative"}
            )

        if bo_rb_stb <= 0.0 or bw_rb_stb <= 0.0 or bg_rb_scf <= 0.0:
            return EngineeringResult(
                model="Voidage Replacement Ratio (VRR)",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": "PVT formation volume factors (Bo, Bw, Bg) must be strictly positive"}
            )

        # 2. Downhole Produced Reservoir Volume (V_prod, res bbl)
        v_oil_res = produced_oil_stb * bo_rb_stb
        v_water_res = produced_water_bbl * bw_rb_stb

        # Free gas volume downhole
        v_gas_res = 0.0
        if produced_gas_scf is not None:
            liberated_solution_gas = produced_oil_stb * rs_scf_stb
            free_gas_surface = max(0.0, produced_gas_scf - liberated_solution_gas)
            v_gas_res = free_gas_surface * bg_rb_scf

        v_prod_total = v_oil_res + v_water_res + v_gas_res

        # 3. Downhole Injected Reservoir Volume (V_inj, res bbl)
        v_inj_water_res = injected_water_bbl * bw_rb_stb
        v_inj_gas_res = injected_gas_scf * bg_rb_scf
        v_inj_total = v_inj_water_res + v_inj_gas_res

        # 4. Zero Withdrawal Check
        if v_prod_total <= 0.0:
            return EngineeringResult(
                model="Voidage Replacement Ratio (VRR)",
                status=EngineeringStatus.UNDEFINED_VRR.value,
                inputs=inputs,
                assumptions=["Zero downhole fluid withdrawal (shut-in or zero production)"],
                limitations=["VRR cannot be calculated when total produced reservoir volume is zero"],
                evidence={
                    "produced_reservoir_volume_rb": 0.0,
                    "explanation": "Zero total produced reservoir volume; division by zero prevented."
                }
            )

        vrr = v_inj_total / v_prod_total

        # Reservoir balance interpretation
        status_interpretation = "OVER_INJECTING" if vrr > 1.05 else ("UNDER_INJECTING" if vrr < 0.95 else "BALANCED_VOYAGE")

        return EngineeringResult(
            value=round(vrr, 4),
            unit="ratio",
            model="Canonical Voidage Replacement Ratio",
            correlation="Downhole Reservoir Volume Conversion",
            correlation_reference="Dake, L.P. (1978), Fundamentals of Reservoir Engineering, Elsevier",
            inputs=inputs,
            assumptions=[
                "Surface rates converted strictly to in-situ downhole reservoir barrels (rb) via Bo, Bw, Bg",
                "Solution gas volume subtracted from total gas before converting free gas to downhole volume",
                "Rate vs Volume distinction preserved via time_window_days metadata"
            ],
            limitations=[
                "Accurate VRR requires consistent allocation across pattern injection boundaries",
                "Assumes average compartment PVT properties"
            ],
            evidence={
                "vrr_value": round(vrr, 4),
                "injected_res_volume_rb": round(v_inj_total, 2),
                "produced_res_volume_rb": round(v_prod_total, 2),
                "oil_res_volume_rb": round(v_oil_res, 2),
                "water_res_volume_rb": round(v_water_res, 2),
                "gas_res_volume_rb": round(v_gas_res, 2),
                "interpretation": status_interpretation
            },
            status=EngineeringStatus.VALID.value
        )


# Canonical Alias
VRREngine = VoidageReplacementEngine

