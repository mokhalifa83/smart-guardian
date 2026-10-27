"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C
Reservoir Engineering Orchestrator (reservoir_engine.py)

ARCHITECTURAL PRINCIPLE:
- Orchestrator ONLY.
- STRICTLY ZERO duplicate equations or petroleum physics calculations.
- Dispatches all physics computations to canonical engines:
    * PVTEngine
    * ChanSurveillanceService / ChanDiagnosticsEngine
    * DarcyRadialFlowEngine
    * ProductivityIndexEngine
    * VogelIPREngine
    * MaterialBalanceEngine
    * VRREngine
    * DeclineCurveEngine
    * WellTestEngine
    * AquiferEngine
    * FractionalFlowEngine
    * BuckleyLeverettEngine
    * WaterfloodEngine
    * SweepEfficiencyEngine
    * ReservesEngine
    * GasReservoirEngine
    * VirtualSeparatorPVTFoundation / VirtualSeparatorService
    * WCCalibrationEngine
    * WellAllocationEngine

Provides integrated, multi-discipline reservoir diagnostic suites.
Standardizes outputs through UnifiedEngineeringEvidence and EngineeringResult.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.evidence_model import UnifiedEngineeringEvidence, EvidenceChainBuilder

# Canonical Step 2A, 2B, and 2C Engines
from app.services.reservoir.pvt_engine import PVTEngine
from app.services.reservoir.chan_service import ChanSurveillanceService
from app.services.reservoir.darcy_engine import DarcyRadialFlowEngine
from app.services.reservoir.productivity_index import ProductivityIndexEngine
from app.services.reservoir.vogel_engine import VogelIPREngine
from app.services.reservoir.material_balance import MaterialBalanceEngine, MaterialBalanceHistoryPoint
from app.services.reservoir.vrr_engine import VRREngine
from app.services.reservoir.decline_engine import DeclineCurveEngine
from app.services.reservoir.well_test_engine import WellTestEngine
from app.services.reservoir.aquifer_engine import AquiferEngine
from app.services.reservoir.fractional_flow_engine import FractionalFlowEngine
from app.services.reservoir.buckley_leverett_engine import BuckleyLeverettEngine
from app.services.reservoir.waterflood_engine import WaterfloodEngine, WaterfloodObservationPoint
from app.services.reservoir.sweep_engine import SweepEngine, SweepEfficiencyEngine
from app.services.reservoir.reserves_engine import ReservesEngine
from app.services.reservoir.gas_reservoir_engine import GasReservoirEngine
from app.services.reservoir.virtual_separator_pvt import VirtualSeparatorPVTFoundation
from app.services.reservoir.separator_service import VirtualSeparatorService
from app.services.reservoir.wc_calibration import WCCalibrationEngine, LabWaterCutSample, LiveWaterCutObservation
from app.services.reservoir.well_allocation import WellAllocationEngine, ChokeAllocationInputs


class ReservoirEngineeringOrchestrator:
    """
    High-level orchestration coordinator for the Smart Guardian Reservoir Intelligence Platform.
    Enforces multi-evidence cross-validation across specialized canonical engines.
    """

    @classmethod
    def orchestrate_well_performance_diagnostic(
        cls,
        well_code: str,
        reservoir_pressure_psia: float,
        flowing_pressure_pwf_psia: float,
        test_liquid_rate_stbd: float,
        bubble_point_psia: float,
        chan_data: Optional[Dict[str, Any]] = None,
        wc_calibration_data: Optional[Dict[str, Any]] = None,
        allocation_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates integrated well diagnostic:
        1. Inflow performance (PI & Vogel)
        2. Chan water production diagnostic (if time-series provided)
        3. Water cut calibration reconciliation (if live/lab data provided)
        4. Well choke flow allocation (if choke parameters provided)
        5. Synthesizes multi-evidence diagnostic interpretation and advisory recommendations.
        """
        results: Dict[str, Any] = {
            "well_code": well_code,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analyses": {},
            "evidence_chain": [],
            "overall_status": EngineeringStatus.VALID.value,
            "integrated_decision_support": []
        }

        # 1. Inflow Performance (PI & Vogel)
        qmax_res = VogelIPREngine.estimate_qmax_from_test(
            test_rate_stbd=test_liquid_rate_stbd,
            test_flowing_bhp_psia=flowing_pressure_pwf_psia,
            reservoir_pressure_psia=reservoir_pressure_psia
        )
        qmax_val = float(qmax_res.value) if qmax_res.status == EngineeringStatus.VALID.value else test_liquid_rate_stbd * 1.5
        vogel_res = VogelIPREngine.generate_ipr_curve(
            qmax_stbd=qmax_val,
            reservoir_pressure_psia=reservoir_pressure_psia
        )
        results["analyses"]["inflow_ipr"] = vogel_res.model_dump()
        results["analyses"]["qmax_estimation"] = qmax_res.model_dump()

        pi_res = ProductivityIndexEngine.calculate_pi(
            flow_rate_stbd=test_liquid_rate_stbd,
            reservoir_pressure_psia=reservoir_pressure_psia,
            flowing_bhp_psia=flowing_pressure_pwf_psia
        )
        results["analyses"]["productivity_index"] = pi_res.model_dump()

        # Inflow evidence
        inflow_evidence = EvidenceChainBuilder.build_from_engineering_result(
            result=vogel_res,
            discipline="INFLOW_PERFORMANCE",
            well_or_entity_id=well_code,
            indicator="VOGEL_TWO_PHASE_IPR" if flowing_pressure_pwf_psia < bubble_point_psia else "LINEAR_DARCY_PI",
            decision_support=[
                f"Well operating at PI = {pi_res.value if pi_res.value else 'N/A'} STB/d/psi.",
                f"Maximum AOF capacity Qmax = {qmax_val:.1f} STB/d."
            ]
        )
        results["evidence_chain"].append(inflow_evidence.model_dump())

        # 2. Chan Diagnostics (if data provided)
        if chan_data and "records" in chan_data:
            chan_res = ChanSurveillanceService.analyze_well_chan_history(
                records=chan_data["records"],
                well_code=well_code,
                smoothing_window=chan_data.get("smoothing_window", 3)
            )
            results["analyses"]["chan_diagnostic"] = chan_res.model_dump()

            chan_evidence = EvidenceChainBuilder.build_from_engineering_result(
                result=chan_res,
                discipline="WATER_DIAGNOSTICS",
                well_or_entity_id=well_code,
                indicator=chan_res.observed_pattern or "CHAN_SLOPE_ANALYSIS",
                decision_support=chan_res.required_confirmation + [
                    "Correlate Chan diagnostic slope with pulsed-neutron RST logging before water shut-off."
                ]
            )
            results["evidence_chain"].append(chan_evidence.model_dump())

        # 3. Water Cut Calibration (if data provided)
        if wc_calibration_data:
            lab_wc = wc_calibration_data.get("lab_sample_wc", wc_calibration_data.get("lab_wc"))
            live_wc = wc_calibration_data.get("live_meter_wc", wc_calibration_data.get("live_wc"))
            if lab_wc is not None and live_wc is not None:
                lab = LabWaterCutSample(
                    sample_id=f"LAB-{well_code}",
                    timestamp=datetime.now(timezone.utc),
                    well_code=well_code,
                    water_cut_value=float(lab_wc)
                )
                live = LiveWaterCutObservation(
                    timestamp=datetime.now(timezone.utc),
                    well_code=well_code,
                    water_cut_value=float(live_wc)
                )
                wc_res = WCCalibrationEngine.calculate_calibration_factor(
                    lab_sample=lab,
                    live_observation_at_sample=live
                )
                results["analyses"]["wc_calibration"] = wc_res.model_dump()

        # 4. Well Allocation (if data provided)
        if allocation_data:
            if isinstance(allocation_data, ChokeAllocationInputs):
                choke_in = allocation_data
            else:
                choke_in = ChokeAllocationInputs(
                    wellhead_pressure_psia=allocation_data.get("whp_psia", allocation_data.get("wellhead_pressure_psia", 200.0)),
                    choke_size_64ths=allocation_data.get("choke_64ths", allocation_data.get("choke_size_64ths", 32.0)),
                    producing_gor_scf_stb=allocation_data.get("glr_scf_stb", allocation_data.get("producing_gor_scf_stb", 500.0)),
                    calibrated_wc_fraction=allocation_data.get("wc_fraction", 0.30),
                    well_code=well_code
                )
            alloc_res = WellAllocationEngine.calculate_choke_allocation(choke_in)
            results["analyses"]["choke_allocation"] = alloc_res.model_dump()

        # 5. Integrated Advisory Recommendations
        results["integrated_decision_support"] = [
            f"Surveillance summary for well {well_code} completed across active modules.",
            "Verify sensor calibrations and validate water cut measurement against lab samples prior to operational intervention.",
            "Maintain continuous pressure and rate monitoring within authorized operating envelop."
        ]

        return results

    @classmethod
    def orchestrate_reservoir_depletion_audit(
        cls,
        reservoir_name: str,
        volumetric_params: Dict[str, Any],
        mbe_history: Optional[List[Dict[str, Any]]] = None,
        aquifer_params: Optional[Dict[str, Any]] = None,
        vrr_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates reservoir-level depletion and material balance audit:
        1. Static Volumetric OOIP / Reserves (ReservesEngine)
        2. Dynamic Havlena-Odeh Material Balance (MaterialBalanceEngine)
        3. Aquifer water influx model (AquiferEngine)
        4. Voidage Replacement Ratio (VRREngine)
        5. Reconciles static volumetric OOIP vs dynamic MBE N:
           Triggers engineering audit alert if deviation > 15%.
        """
        results: Dict[str, Any] = {
            "reservoir_name": reservoir_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analyses": {},
            "evidence_chain": [],
            "reconciliation": {},
            "audit_alerts": []
        }

        # 1. Volumetric Reserves
        vol_res = ReservesEngine.calculate_oil_reserves_and_resources(
            area_acres=volumetric_params.get("area_acres", 1000.0),
            net_pay_ft=volumetric_params.get("net_pay_ft", 50.0),
            porosity=volumetric_params.get("porosity", 0.20),
            initial_water_sat=volumetric_params.get("initial_water_sat", 0.25),
            initial_oil_fvf_boi=volumetric_params.get("initial_oil_fvf_boi", 1.25),
            recovery_factor=volumetric_params.get("recovery_factor", 0.30),
            cumulative_oil_np_stb=volumetric_params.get("cumulative_oil_np_stb", 0.0),
            well_or_field_id=reservoir_name
        )
        results["analyses"]["volumetric_reserves"] = vol_res.model_dump()

        vol_evidence = EvidenceChainBuilder.build_from_engineering_result(
            result=vol_res,
            discipline="STATIC_RESERVES",
            well_or_entity_id=reservoir_name,
            indicator="SPE_PRMS_VOLUMETRIC_EVALUATION",
            decision_support=[
                f"Volumetric OOIP = {vol_res.evidence.get('ooip_mmstb', 'N/A')} MMSTB.",
                f"Remaining Commercial Reserves = {vol_res.evidence.get('remaining_reserves_mmstb', 'N/A')} MMSTB."
            ]
        )
        results["evidence_chain"].append(vol_evidence.model_dump())

        # 2. Material Balance (if history provided)
        mbe_n_stb = None
        if mbe_history and len(mbe_history) >= 2:
            mbe_pts = []
            for pt in mbe_history:
                if isinstance(pt, MaterialBalanceHistoryPoint):
                    mbe_pts.append(pt)
                else:
                    mbe_pts.append(MaterialBalanceHistoryPoint(
                        pressure_psia=pt.get("pressure_psia"),
                        np_stb=pt.get("cumulative_oil_np_stb", pt.get("np_stb", 0.0)),
                        wp_stb=pt.get("cumulative_water_wp_stb", pt.get("wp_stb", 0.0)),
                        gp_mscf=pt.get("cumulative_gas_gp_mscf", pt.get("gp_mscf", (pt.get("cumulative_gas_gp_scf", 0.0) / 1000.0) if pt.get("cumulative_gas_gp_scf") else 0.0)),
                        bo_rb_stb=pt.get("bo_rb_stb"),
                        bg_rb_scf=pt.get("bg_rb_scf"),
                        bw_rb_stb=pt.get("bw_rb_stb", 1.0),
                        rs_scf_stb=pt.get("rs_scf_stb"),
                        we_rb=pt.get("we_bbl", pt.get("we_rb", 0.0))
                    ))

            init_bg = volumetric_params.get("initial_bg", mbe_pts[0].bg_rb_scf if mbe_pts[0].bg_rb_scf else 0.0012)
            init_rs = volumetric_params.get("initial_rs", mbe_pts[0].rs_scf_stb if mbe_pts[0].rs_scf_stb else 500.0)
            init_bo = volumetric_params.get("initial_oil_fvf_boi", mbe_pts[0].bo_rb_stb if mbe_pts[0].bo_rb_stb else 1.25)
            init_p = volumetric_params.get("initial_pressure_psia", mbe_pts[0].pressure_psia if mbe_pts[0].pressure_psia else 4000.0)

            mbe_res = MaterialBalanceEngine.calculate_history_series(
                history=mbe_pts,
                initial_pressure_psia=init_p,
                initial_bo=init_bo,
                initial_bg=init_bg,
                initial_rs=init_rs,
                initial_swi=volumetric_params.get("initial_water_sat", 0.25),
                cf_pore_compressibility=volumetric_params.get("cf", 3.5e-6),
                cw_water_compressibility=volumetric_params.get("cw", 3.0e-6)
            )
            results["analyses"]["material_balance"] = mbe_res.model_dump()
            mbe_n_stb = mbe_res.value.get("estimated_ooip_N_stb") if isinstance(mbe_res.value, dict) else mbe_res.value

            mbe_evidence = EvidenceChainBuilder.build_from_engineering_result(
                result=mbe_res,
                discipline="DYNAMIC_MATERIAL_BALANCE",
                well_or_entity_id=reservoir_name,
                indicator="HAVLENA_ODEH_F_OVER_ET",
                decision_support=[
                    f"Dynamic Material Balance OOIP (N) = {round(mbe_n_stb / 1e6, 3) if mbe_n_stb else 'N/A'} MMSTB.",
                    "Verify drive mechanism balance indices (depletion vs gas cap vs water drive)."
                ]
            )
            results["evidence_chain"].append(mbe_evidence.model_dump())

        # 3. Static vs Dynamic Reconciliation
        static_n_stb = vol_res.evidence.get("ooip_stb")
        if static_n_stb and mbe_n_stb and static_n_stb > 0 and mbe_n_stb > 0:
            deviation_pct = ((mbe_n_stb - static_n_stb) / static_n_stb) * 100.0
            results["reconciliation"] = {
                "volumetric_ooip_stb": static_n_stb,
                "mbe_ooip_stb": mbe_n_stb,
                "absolute_difference_stb": abs(mbe_n_stb - static_n_stb),
                "deviation_percentage": round(deviation_pct, 2),
                "is_reconciled": abs(deviation_pct) <= 15.0
            }

            if abs(deviation_pct) > 15.0:
                alert_msg = (
                    f"RESERVOIR AUDIT ALERT: Dynamic Material Balance OOIP ({mbe_n_stb/1e6:.2f} MMSTB) "
                    f"deviates by {deviation_pct:+.1f}% from Static Volumetric OOIP ({static_n_stb/1e6:.2f} MMSTB). "
                    f"Significant deviation indicates potential unaccounted aquifer support, compartmentalization, or seismic volume revision."
                )
                results["audit_alerts"].append({
                    "alert_type": "RESERVOIR_N_DEVIATION",
                    "severity": "WARNING",
                    "message": alert_msg,
                    "deviation_pct": round(deviation_pct, 2)
                })

        return results

    @classmethod
    def orchestrate_waterflood_sweep_analysis(
        cls,
        pattern_name: str,
        hall_history: Optional[List[Dict[str, float]]] = None,
        sweep_params: Optional[Dict[str, Any]] = None,
        buckley_leverett_params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Orchestrates waterflood surveillance:
        1. Hall Diagnostic Plot (WaterfloodEngine)
        2. Displacement and Volumetric Sweep Efficiency (SweepEfficiencyEngine)
        3. Buckley-Leverett front advance & breakthrough (BuckleyLeverettEngine)
        """
        results: Dict[str, Any] = {
            "pattern_name": pattern_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analyses": {},
            "evidence_chain": [],
            "decision_support": []
        }

        # 1. Hall Plot Diagnostic
        if hall_history and len(hall_history) >= 2:
            wf_pts = []
            for h in hall_history:
                if isinstance(h, WaterfloodObservationPoint):
                    wf_pts.append(h)
                else:
                    wf_pts.append(WaterfloodObservationPoint(
                        timestamp=h.get("timestamp", datetime.now(timezone.utc)),
                        injection_rate_bpd=h.get("injection_rate_bpd", 500.0),
                        wellhead_injection_pressure_psia=h.get("wellhead_injection_pressure_psia", h.get("flowing_tubing_pressure_psi", 2000.0)),
                        offset_oil_rate_stbd=h.get("offset_oil_rate_stbd", 150.0),
                        offset_water_rate_bpd=h.get("offset_water_rate_bpd", 50.0)
                    ))
            hall_res = WaterfloodEngine.analyze_waterflood_surveillance(
                history=wf_pts,
                pattern_name=pattern_name
            )
            results["analyses"]["hall_plot"] = hall_res.model_dump()

            hall_evidence = EvidenceChainBuilder.build_from_engineering_result(
                result=hall_res,
                discipline="WATERFLOOD_SURVEILLANCE",
                well_or_entity_id=pattern_name,
                indicator=hall_res.observed_pattern or "HALL_INJECTIVITY_SLOPE",
                decision_support=[
                    f"Hall slope evaluation: {hall_res.diagnostic_interpretation}",
                    "Maintain continuous monitoring of wellhead injection pressure vs rate."
                ]
            )
            results["evidence_chain"].append(hall_evidence.model_dump())

        # 2. Sweep Efficiency
        if sweep_params:
            sweep_res = SweepEngine.calculate_total_volumetric_sweep(
                sw_connate=sweep_params.get("sw_connate", 0.20),
                so_residual=sweep_params.get("so_residual", 0.25),
                areal_sweep_ea=sweep_params.get("ea_areal", 0.75),
                vertical_sweep_ei=sweep_params.get("ev_vertical", 0.70)
            )
            results["analyses"]["sweep_efficiency"] = sweep_res.model_dump()

        # 3. Buckley-Leverett (if params provided)
        if buckley_leverett_params:
            bl_res = BuckleyLeverettEngine.calculate_displacement(
                injection_rate_bpd=buckley_leverett_params.get("injection_rate_bpd", 1000.0),
                cross_sectional_area_ft2=buckley_leverett_params.get("cross_sectional_area_ft2", 20000.0),
                length_between_wells_ft=buckley_leverett_params.get("length_between_wells_ft", 1000.0),
                porosity_fraction=buckley_leverett_params.get("porosity_fraction", 0.20),
                initial_water_saturation=buckley_leverett_params.get("sw_connate", 0.20),
                so_residual=buckley_leverett_params.get("sor", 0.25),
                water_viscosity_cp=buckley_leverett_params.get("water_viscosity_cp", 0.5),
                oil_viscosity_cp=buckley_leverett_params.get("oil_viscosity_cp", 2.0)
            )
            results["analyses"]["buckley_leverett"] = bl_res.model_dump()

        results["decision_support"] = [
            f"Waterflood surveillance synthesized for pattern {pattern_name}.",
            "Balance injection allocation to prevent early breakthrough in high-permeability thief zones."
        ]

        return results
