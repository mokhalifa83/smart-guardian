"""
Smart Guardian Reservoir Intelligence Layer - STEP 2C
Integrated Analysis Service (analysis_future_stubs.py upgraded)

Provides concrete implementations of IReservoirEngineeringEngine connecting
surveillance analysis requests to canonical Step 2A, 2B, and 2C reservoir engineering engines.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from pydantic import BaseModel

from app.services.reservoir.contracts import EngineeringResult
from app.services.reservoir.pvt_engine import PVTEngine
from app.services.reservoir.chan_service import ChanSurveillanceService
from app.services.reservoir.material_balance import MaterialBalanceEngine
from app.services.reservoir.reservoir_engine import ReservoirEngineeringOrchestrator


class ReservoirEngineInput(BaseModel):
    well_code: str
    timestamp: datetime
    parameters: Dict[str, Any]


class ReservoirEngineOutput(BaseModel):
    engine_name: str
    well_code: str
    timestamp: datetime
    indicators: Dict[str, Any]
    evidence_bundle: Dict[str, Any]
    decision_support_recommendations: list[str]


class IReservoirEngineeringEngine(ABC):
    """
    Standard interface contract for reservoir engineering engines.
    Follows canonical engineering flow:
    Calculation -> Indicator -> Evidence -> Diagnostic Interpretation -> Potential Root Cause -> Decision Support.
    """

    @property
    @abstractmethod
    def engine_name(self) -> str:
        pass

    @abstractmethod
    async def compute(self, input_data: ReservoirEngineInput) -> ReservoirEngineOutput:
        pass


class ChanDiagnosticEngineService(IReservoirEngineeringEngine):
    """
    Connected Chan Diagnostic Analysis Engine.
    Evaluates WOR vs Np and WOR' derivative to diagnose water production mechanism.
    Delegates strictly to canonical ChanSurveillanceService / ChanDiagnosticEngine.
    """
    @property
    def engine_name(self) -> str:
        return "CHAN_DIAGNOSTICS_ENGINE"

    async def compute(self, input_data: ReservoirEngineInput) -> ReservoirEngineOutput:
        records = input_data.parameters.get("records", [])
        smoothing = input_data.parameters.get("smoothing_window", 3)
        result = ChanSurveillanceService.analyze_well_chan_history(
            records=records,
            well_code=input_data.well_code,
            smoothing_window=smoothing
        )

        indicators = {
            "status": result.status,
            "observed_pattern": result.observed_pattern,
            "diagnostic_interpretation": result.diagnostic_interpretation
        }

        recs = result.required_confirmation + [
            "Monitor WOR slope continuously.",
            "Verify mechanical integrity before planning chemical water shut-off."
        ]

        return ReservoirEngineOutput(
            engine_name=self.engine_name,
            well_code=input_data.well_code,
            timestamp=input_data.timestamp,
            indicators=indicators,
            evidence_bundle=result.evidence,
            decision_support_recommendations=recs
        )


class MaterialBalanceEngineService(IReservoirEngineeringEngine):
    """
    Connected Havlena-Odeh Material Balance Engine.
    Delegates to canonical MaterialBalanceEngine.
    """
    @property
    def engine_name(self) -> str:
        return "MATERIAL_BALANCE_HAVLENA_ODEH"

    async def compute(self, input_data: ReservoirEngineInput) -> ReservoirEngineOutput:
        history = input_data.parameters.get("history_points", [])
        pi = input_data.parameters.get("pi_psia", 4000.0)
        cw = input_data.parameters.get("cw_1_psi", 3.5e-6)
        cf = input_data.parameters.get("cf_1_psi", 4.0e-6)
        swi = input_data.parameters.get("swi", 0.25)

        result = MaterialBalanceEngine.calculate_havlena_odeh(
            history_points=history,
            pi_psia=pi,
            cw_1_psi=cw,
            cf_1_psi=cf,
            swi=swi
        )

        indicators = {
            "status": result.status,
            "ooip_n_stb": result.value,
            "r_squared": result.evidence.get("r_squared")
        }

        return ReservoirEngineOutput(
            engine_name=self.engine_name,
            well_code=input_data.well_code,
            timestamp=input_data.timestamp,
            indicators=indicators,
            evidence_bundle=result.evidence,
            decision_support_recommendations=[
                f"Dynamic OOIP estimated at {round(result.value / 1e6, 3) if result.value else 'N/A'} MMSTB.",
                "Verify aquifer drive index balance."
            ]
        )


class PVTCorrelationsEngineService(IReservoirEngineeringEngine):
    """
    Connected Black Oil PVT correlations engine.
    Delegates to canonical PVTEngine.
    """
    @property
    def engine_name(self) -> str:
        return "BLACK_OIL_PVT_CORRELATIONS"

    async def compute(self, input_data: ReservoirEngineInput) -> ReservoirEngineOutput:
        p = input_data.parameters.get("pressure_psia", 2500.0)
        t = input_data.parameters.get("temperature_f", 180.0)
        api = input_data.parameters.get("api_gravity", 35.0)
        gas_grav = input_data.parameters.get("gas_gravity", 0.75)

        bo_res = PVTEngine.calculate_oil_fvf_bo(p, t, api, gas_grav)
        bg_res = PVTEngine.calculate_gas_fvf_bg(p, t, gas_grav)
        bw_res = PVTEngine.calculate_water_fvf_bw(p, t)

        indicators = {
            "Bo_rb_stb": bo_res.value,
            "Bg_rb_scf": bg_res.value,
            "Bw_rb_stb": bw_res.value
        }

        return ReservoirEngineOutput(
            engine_name=self.engine_name,
            well_code=input_data.well_code,
            timestamp=input_data.timestamp,
            indicators=indicators,
            evidence_bundle={
                "bo_evidence": bo_res.evidence,
                "bg_evidence": bg_res.evidence,
                "bw_evidence": bw_res.evidence
            },
            decision_support_recommendations=[
                "Canonical PVT properties evaluated successfully for reservoir simulation and allocation."
            ]
        )


# Backward compatibility aliases for Phase 1 stub imports
ChanDiagnosticEngineStub = ChanDiagnosticEngineService
MaterialBalanceEngineStub = MaterialBalanceEngineService
PVTCorrelationsEngineStub = PVTCorrelationsEngineService
