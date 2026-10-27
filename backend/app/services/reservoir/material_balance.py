"""
Smart Guardian Reservoir Intelligence Layer - Material Balance & Havlena-Odeh Engine (Step 2A)
Reference: Havlena, D. and Odeh, A.S. (1963), "The Material Balance as an Equation of a Straight Line",
Journal of Petroleum Technology, 15(8), 896-900.

Implements the general Schilthuis Material Balance Equation in Havlena-Odeh form:
    F = N * [Eo + m * Eg + Ef_w] + We

Components:
1. Underground Withdrawal F (res bbl):
       F = Np * [Bo + (Rp - Rs) * Bg] + Wp * Bw
2. Oil & Dissolved Gas Expansion Eo (res bbl / stb):
       Eo = (Bo - Boi) + (Rsi - Rs) * Bg
3. Gas Cap Expansion Eg (res bbl / stb):
       Eg = Boi * [(Bg / Bgi) - 1]
4. Formation & Connate Water Expansion Ef_w (res bbl / stb):
       Ef_w = (1 + m) * Boi * [(cw * Swi + cf) / (1 - Swi)] * Delta_P
5. Drive Mechanism Indices:
       DDI  (Depletion Drive Index)   = N * Eo / F
       SDI  (Segregation Drive Index) = N * m * Eg / F
       WDI  (Water Drive Index)       = (We - Wp * Bw) / F
       EDI  (Formation Expansion Ind) = N * Ef_w / F
       Sum(Drive Indices) = 1.0 (at balance)
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, ConfigDict
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus


class MaterialBalanceHistoryPoint(BaseModel):
    pressure_psia: float
    np_stb: float               # Cumulative oil produced
    wp_stb: float = 0.0         # Cumulative water produced
    gp_mscf: Optional[float] = None # Cumulative gas produced
    bo_rb_stb: Optional[float] = None
    bg_rb_scf: Optional[float] = None
    bw_rb_stb: float = 1.0
    rs_scf_stb: Optional[float] = None
    we_rb: float = 0.0          # Estimated or modeled water influx


class MaterialBalanceEngine:
    """
    Canonical Material Balance and Havlena-Odeh Straight Line Diagnostic Engine.
    """

    @classmethod
    def calculate_single_state(
        cls,
        # Initial Conditions
        initial_pressure_psia: float,
        initial_bo: float,
        initial_bg: float,
        initial_rs: float,
        initial_swi: float,
        # Current Conditions
        current_pressure_psia: float,
        current_bo: float,
        current_bg: float,
        current_rs: float,
        # Cumulative Production
        np_stb: float,
        wp_stb: float,
        gp_mscf: Optional[float] = None,
        rp_scf_stb: Optional[float] = None,
        bw_rb_stb: float = 1.0,
        # Reservoir & Rock Properties
        m_gas_cap_ratio: float = 0.0,
        cf_pore_compressibility: float = 3.5e-6,
        cw_water_compressibility: float = 3.0e-6,
        we_water_influx_rb: float = 0.0,
        n_stb_estimate: Optional[float] = None
    ) -> EngineeringResult:
        inputs = {
            "initial_pressure_psia": initial_pressure_psia,
            "current_pressure_psia": current_pressure_psia,
            "np_stb": np_stb,
            "wp_stb": wp_stb,
            "m_gas_cap_ratio": m_gas_cap_ratio,
            "initial_bo": initial_bo,
            "current_bo": current_bo,
            "initial_bg": initial_bg,
            "current_bg": current_bg
        }

        # 1. Input completeness check
        if any(v is None for v in [initial_pressure_psia, current_pressure_psia, initial_bo, current_bo, initial_bg, current_bg, np_stb]):
            return EngineeringResult(
                model="Havlena-Odeh Material Balance",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs=inputs,
                evidence={"error": "Missing essential PVT or production history inputs for Material Balance evaluation"}
            )

        delta_p = initial_pressure_psia - current_pressure_psia
        if delta_p < 0.0:
            return EngineeringResult(
                model="Havlena-Odeh Material Balance",
                status=EngineeringStatus.OUT_OF_RANGE.value,
                inputs=inputs,
                evidence={"error": f"Current pressure ({current_pressure_psia}) exceeds initial reservoir pressure ({initial_pressure_psia})"}
            )

        # 2. Cumulative GOR (Rp)
        if rp_scf_stb is None:
            if gp_mscf is not None and np_stb > 0.0:
                rp_scf_stb = (gp_mscf * 1000.0) / np_stb
            else:
                rp_scf_stb = initial_rs  # Fallback only when zero gas excess

        # 3. Underground Withdrawal F (res bbl)
        gas_term = (rp_scf_stb - current_rs) * current_bg
        f_withdrawal = np_stb * (current_bo + gas_term) + wp_stb * bw_rb_stb

        # 4. Oil & Dissolved Gas Expansion Eo (res bbl / stb)
        eo = (current_bo - initial_bo) + (initial_rs - current_rs) * current_bg

        # 5. Gas Cap Expansion Eg (res bbl / stb)
        if initial_bg > 0.0:
            eg = initial_bo * ((current_bg / initial_bg) - 1.0)
        else:
            eg = 0.0

        # 6. Formation & Connate Water Expansion Ef_w (res bbl / stb)
        if initial_swi < 1.0:
            ef_w = (1.0 + m_gas_cap_ratio) * initial_bo * ((cw_water_compressibility * initial_swi + cf_pore_compressibility) / (1.0 - initial_swi)) * delta_p
        else:
            ef_w = 0.0

        # Total expansion Et
        et = eo + m_gas_cap_ratio * eg + ef_w

        # 7. Estimated OOIP N if not provided
        n_calculated = None
        if et > 0:
            n_calculated = (f_withdrawal - we_water_influx_rb) / et

        n_used = n_stb_estimate if n_stb_estimate is not None else n_calculated

        # 8. Drive Mechanism Indices (where N is known and F > 0)
        ddi = None
        sdi = None
        wdi = None
        edi = None
        drive_evidence = {}

        if n_used is not None and f_withdrawal > 0.0:
            ddi = (n_used * eo) / f_withdrawal
            sdi = (n_used * m_gas_cap_ratio * eg) / f_withdrawal
            wdi = (we_water_influx_rb - wp_stb * bw_rb_stb) / f_withdrawal
            edi = (n_used * ef_w) / f_withdrawal

            primary_drive = "DEPLETION_EXPANSION"
            if wdi > 0.40:
                primary_drive = "ACTIVE_WATER_DRIVE"
            elif sdi > 0.40:
                primary_drive = "GAS_CAP_EXPANSION_DRIVE"

            drive_evidence = {
                "DDI_depletion_index": round(ddi, 4),
                "SDI_gas_cap_index": round(sdi, 4),
                "WDI_water_drive_index": round(wdi, 4),
                "EDI_formation_expansion_index": round(edi, 4),
                "primary_inferred_drive": primary_drive
            }

        return EngineeringResult(
            value={
                "F_underground_withdrawal_rb": round(f_withdrawal, 2),
                "Eo_oil_expansion_rb_stb": round(eo, 6),
                "Eg_gas_cap_expansion_rb_stb": round(eg, 6),
                "Ef_w_rock_water_expansion_rb_stb": round(ef_w, 6),
                "Et_total_expansion_rb_stb": round(et, 6),
                "estimated_N_stb": round(n_used, 2) if n_used is not None else None
            },
            unit="material_balance_quantities",
            model="Havlena-Odeh Straight Line Material Balance",
            correlation="Havlena & Odeh (1963)",
            correlation_reference="Havlena, D. and Odeh, A.S. (1963), JPT, 15(8), 896-900, Trans. AIME, 228",
            inputs=inputs,
            assumptions=[
                "Zero water influx assumed unless explicitly modeled in We parameter",
                "Equilibrium PVT properties across entire reservoir compartment",
                "Volumetric tank model (no spatial permeability gradient)"
            ],
            limitations=[
                "Havlena-Odeh linear analysis requires multiple pressure survey intervals to verify regression linearity.",
                "Gas cap expansion requires accurate m (ratio of gas cap volume to oil zone volume)."
            ],
            evidence={
                "delta_P_psi": round(delta_p, 2),
                "Rp_scf_stb": round(rp_scf_stb, 2),
                "drive_indices": drive_evidence
            },
            status=EngineeringStatus.VALID.value
        )

    @classmethod
    def calculate_history_series(
        cls,
        history: List[MaterialBalanceHistoryPoint],
        initial_pressure_psia: float,
        initial_bo: Optional[float] = None,
        initial_bg: Optional[float] = None,
        initial_rs: Optional[float] = None,
        initial_swi: float = 0.20,
        m_gas_cap_ratio: float = 0.0,
        cf_pore_compressibility: float = 3.5e-6,
        cw_water_compressibility: float = 3.0e-6,
        reservoir_temperature_f: Optional[float] = None,
        gas_gravity: Optional[float] = None,
        oil_api: Optional[float] = None,
        we_modeled_series: Optional[List[float]] = None
    ) -> EngineeringResult:
        """
        Executes multi-survey Havlena-Odeh straight-line material balance on historical time series.
        Integrates with canonical PVTEngine when PVT inputs (T, gas_gravity, oil_api) are provided.
        Computes F, Eo, Eg, Ef_w, Et and performs least-squares regression to find OOIP N.
        """
        from app.services.reservoir.pvt_engine import PVTEngine

        if not history or len(history) < 2:
            return EngineeringResult(
                model="Havlena-Odeh Linear Material Balance Series",
                status=EngineeringStatus.INSUFFICIENT_DATA.value,
                inputs={"history_points_count": len(history) if history else 0},
                evidence={"error": "At least 2 chronological reservoir pressure surveys are required for linear regression."}
            )

        # 1. Resolve initial PVT if not provided
        if any(v is None for v in [initial_bo, initial_bg, initial_rs]):
            if any(v is None for v in [reservoir_temperature_f, gas_gravity, oil_api]):
                return EngineeringResult(
                    model="Havlena-Odeh Linear Material Balance Series",
                    status=EngineeringStatus.INSUFFICIENT_DATA.value,
                    inputs={"initial_pressure_psia": initial_pressure_psia},
                    evidence={"error": "Either explicit initial PVT (initial_bo, initial_bg, initial_rs) or canonical PVT inputs (T, gas_gravity, oil_api) must be provided."}
                )
            # Use canonical PVTEngine
            rs_res = PVTEngine.calculate_solution_gor_rs(
                pressure_psia=initial_pressure_psia,
                temperature_f=reservoir_temperature_f,
                gas_gravity=gas_gravity,
                oil_api=oil_api
            )
            initial_rs = rs_res.value
            bo_res = PVTEngine.calculate_oil_fvf_bo(
                pressure_psia=initial_pressure_psia,
                temperature_f=reservoir_temperature_f,
                api_gravity=oil_api,
                gas_gravity=gas_gravity,
                rs=initial_rs
            )
            initial_bo = bo_res.value
            bg_res = PVTEngine.calculate_gas_fvf_bg(
                pressure_psia=initial_pressure_psia,
                temperature_f=reservoir_temperature_f,
                gas_gravity=gas_gravity
            )
            initial_bg = bg_res.value

        processed_points = []
        f_list: List[float] = []
        et_list: List[float] = []

        for idx, pt in enumerate(history):
            p_curr = pt.pressure_psia
            if p_curr > initial_pressure_psia:
                return EngineeringResult(
                    model="Havlena-Odeh Linear Material Balance Series",
                    status=EngineeringStatus.OUT_OF_RANGE.value,
                    inputs={"survey_index": idx, "pressure_psia": p_curr, "initial_pressure_psia": initial_pressure_psia},
                    evidence={"error": f"Survey point {idx} pressure ({p_curr} psia) exceeds initial pressure ({initial_pressure_psia} psia)"}
                )

            # Resolve current PVT if missing
            bo_curr = pt.bo_rb_stb
            bg_curr = pt.bg_rb_scf
            rs_curr = pt.rs_scf_stb

            if any(v is None for v in [bo_curr, bg_curr, rs_curr]):
                if any(v is None for v in [reservoir_temperature_f, gas_gravity, oil_api]):
                    return EngineeringResult(
                        model="Havlena-Odeh Linear Material Balance Series",
                        status=EngineeringStatus.INSUFFICIENT_DATA.value,
                        inputs={"survey_index": idx},
                        evidence={"error": f"Missing PVT properties at survey point {idx} and PVT stream inputs not configured."}
                    )
                rs_pt = PVTEngine.calculate_solution_gor_rs(
                    pressure_psia=p_curr,
                    temperature_f=reservoir_temperature_f,
                    gas_gravity=gas_gravity,
                    oil_api=oil_api
                )
                rs_curr = rs_pt.value
                bo_pt = PVTEngine.calculate_oil_fvf_bo(
                    pressure_psia=p_curr,
                    temperature_f=reservoir_temperature_f,
                    api_gravity=oil_api,
                    gas_gravity=gas_gravity,
                    rs=rs_curr
                )
                bo_curr = bo_pt.value
                bg_pt = PVTEngine.calculate_gas_fvf_bg(
                    pressure_psia=p_curr,
                    temperature_f=reservoir_temperature_f,
                    gas_gravity=gas_gravity
                )
                bg_curr = bg_pt.value

            we_val = pt.we_rb
            if we_modeled_series and idx < len(we_modeled_series):
                we_val = we_modeled_series[idx]

            single_res = cls.calculate_single_state(
                initial_pressure_psia=initial_pressure_psia,
                initial_bo=initial_bo,
                initial_bg=initial_bg,
                initial_rs=initial_rs,
                initial_swi=initial_swi,
                current_pressure_psia=p_curr,
                current_bo=bo_curr,
                current_bg=bg_curr,
                current_rs=rs_curr,
                np_stb=pt.np_stb,
                wp_stb=pt.wp_stb,
                gp_mscf=pt.gp_mscf,
                bw_rb_stb=pt.bw_rb_stb,
                m_gas_cap_ratio=m_gas_cap_ratio,
                cf_pore_compressibility=cf_pore_compressibility,
                cw_water_compressibility=cw_water_compressibility,
                we_water_influx_rb=we_val
            )

            if single_res.status != EngineeringStatus.VALID.value:
                return single_res

            val = single_res.value
            f_withdrawal = val["F_underground_withdrawal_rb"]
            et_total = val["Et_total_expansion_rb_stb"]
            f_net = f_withdrawal - we_val

            f_list.append(f_net)
            et_list.append(et_total)

            processed_points.append({
                "survey_index": idx,
                "pressure_psia": p_curr,
                "np_stb": pt.np_stb,
                "wp_stb": pt.wp_stb,
                "gp_mscf": pt.gp_mscf,
                "bo_rb_stb": bo_curr,
                "bg_rb_scf": bg_curr,
                "rs_scf_stb": rs_curr,
                "we_rb": we_val,
                "F_underground_withdrawal_rb": f_withdrawal,
                "F_net_rb": round(f_net, 2),
                "Eo_rb_stb": val["Eo_oil_expansion_rb_stb"],
                "Eg_rb_stb": val["Eg_gas_cap_expansion_rb_stb"],
                "Ef_w_rb_stb": val["Ef_w_rock_water_expansion_rb_stb"],
                "Et_total_expansion_rb_stb": et_total,
                "drive_indices": single_res.evidence.get("drive_indices", {})
            })

        # 2. Havlena-Odeh Straight Line Regression (F_net = N * Et)
        # Forced through origin: N = sum(Et * F_net) / sum(Et^2)
        sum_et2 = sum(et * et for et in et_list)
        sum_et_f = sum(et * f for et, f in zip(et_list, f_list))

        if sum_et2 > 1e-12:
            n_slope = sum_et_f / sum_et2
        else:
            n_slope = None

        # Calculate R^2
        r2 = None
        if n_slope is not None and len(f_list) >= 2:
            mean_f = sum(f_list) / len(f_list)
            ss_tot = sum((f - mean_f) ** 2 for f in f_list)
            ss_res = sum((f - n_slope * et) ** 2 for f, et in zip(f_list, et_list))
            if ss_tot > 1e-12:
                r2 = max(0.0, min(1.0, 1.0 - (ss_res / ss_tot)))
            else:
                r2 = 1.0

        # Unconstrained linear regression: F_net = slope * Et + intercept
        n_pts = len(f_list)
        mean_et = sum(et_list) / n_pts
        mean_f = sum(f_list) / n_pts
        s_xx = sum((et - mean_et) ** 2 for et in et_list)
        s_xy = sum((et - mean_et) * (f - mean_f) for et, f in zip(et_list, f_list))
        unconstrained_slope = (s_xy / s_xx) if s_xx > 1e-12 else None
        unconstrained_intercept = (mean_f - unconstrained_slope * mean_et) if unconstrained_slope is not None else None

        return EngineeringResult(
            value={
                "estimated_ooip_N_stb": round(n_slope, 2) if n_slope is not None else None,
                "regression_r2": round(r2, 4) if r2 is not None else None,
                "surveys_analyzed": len(processed_points),
                "unconstrained_slope_N": round(unconstrained_slope, 2) if unconstrained_slope is not None else None,
                "unconstrained_intercept_rb": round(unconstrained_intercept, 2) if unconstrained_intercept is not None else None
            },
            unit="stb",
            model="Havlena-Odeh Linear Material Balance Regression",
            correlation="Havlena & Odeh (1963)",
            correlation_reference="Havlena, D. and Odeh, A.S. (1963), 'The Material Balance as an Equation of a Straight Line', JPT, 15(8), 896-900",
            inputs={
                "initial_pressure_psia": initial_pressure_psia,
                "initial_bo": initial_bo,
                "initial_bg": initial_bg,
                "initial_rs": initial_rs,
                "surveys_count": len(history)
            },
            assumptions=[
                "Havlena-Odeh straight line formulation F = N * Et enforced through origin",
                "Volumetric tank model assumption",
                "Downhole Bo, Bg, Rs determined using canonical PVTEngine where applicable"
            ],
            limitations=[
                "Deviations from straight line indicate unaccounted water influx (We) or gas cap expansion (m).",
                "A minimum of 3-4 historical pressure surveys is recommended for high statistical confidence."
            ],
            evidence={
                "survey_points": processed_points,
                "regression_fit": {
                    "slope_N": round(n_slope, 2) if n_slope is not None else None,
                    "r_squared": round(r2, 4) if r2 is not None else None,
                    "origin_forced": True
                }
            },
            status=EngineeringStatus.VALID.value
        )
