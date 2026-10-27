"""
Smart Guardian Reservoir Intelligence Layer - Chan Service Orchestrator (Step 2A)
Orchestrates data retrieval from production readings, validates input history,
calls the canonical ChanDiagnosticEngine (Single Source of Truth),
and formats structured results for API delivery and persistence.
"""

from typing import Optional, List, Any, Dict
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.readings import ProductionReading
from app.models.separator import SeparatorReading
from app.services.reservoir.contracts import EngineeringResult, EngineeringStatus
from app.services.reservoir.chan_engine import ChanDiagnosticEngine, ProductionTimePoint


class ChanService:
    """
    Service wrapper for Chan diagnostic execution.
    Does NOT reimplement Chan physics; delegates strictly to ChanDiagnosticEngine.
    """

    @classmethod
    async def get_well_chan_diagnostics(
        cls,
        db: AsyncSession,
        well_code: str,
        limit: int = 100
    ) -> EngineeringResult:
        """
        Retrieves real historical production readings for a well from the database,
        constructs the chronological series, and invokes the canonical Chan engine.
        Never fabricates synthetic points.
        """
        # 1. Fetch real production readings
        stmt = (
            select(ProductionReading)
            .where(ProductionReading.well_code == well_code)
            .order_by(ProductionReading.timestamp.asc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        readings = list(res.scalars().all())

        if not readings:
            # Check separator readings
            sep_stmt = (
                select(SeparatorReading)
                .where(SeparatorReading.well_code == well_code)
                .order_by(SeparatorReading.timestamp.asc())
                .limit(limit)
            )
            sep_res = await db.execute(sep_stmt)
            sep_readings = list(sep_res.scalars().all())

            if not sep_readings:
                return EngineeringResult(
                    model="Chan Service Wrapper",
                    status=EngineeringStatus.INSUFFICIENT_DATA.value,
                    inputs={"well_code": well_code, "points_retrieved": 0},
                    evidence={"error": f"No historical production or separator telemetry found for well {well_code}"}
                )

            # Map separator readings
            points = [
                ProductionTimePoint(
                    timestamp=r.timestamp,
                    oil_rate=r.oil_rate,
                    water_rate=r.water_rate,
                    water_cut_pct=r.water_cut
                )
                for r in sep_readings
            ]
        else:
            # Map production readings
            points = [
                ProductionTimePoint(
                    timestamp=r.timestamp,
                    oil_rate=r.oil_rate,
                    water_rate=r.water_rate,
                    water_cut_pct=r.wc_percent
                )
                for r in readings
            ]

        # 2. Invoke Canonical Physics Engine
        return ChanDiagnosticEngine.compute_chan_diagnostic_series(points, well_code=well_code)

    @classmethod
    def evaluate_custom_series(
        cls,
        points: List[ProductionTimePoint],
        well_code: str = "CUSTOM_EVALUATION"
    ) -> EngineeringResult:
        """
        Evaluates a client-submitted or test-provided chronological series
        via the canonical Chan engine.
        """
        return ChanDiagnosticEngine.compute_chan_diagnostic_series(points, well_code=well_code)

    @classmethod
    def analyze_well_chan_history(
        cls,
        records: List[Any],
        well_code: str = "CUSTOM_EVALUATION",
        smoothing_window: int = 3
    ) -> EngineeringResult:
        """
        Convenience orchestrator converting raw dictionary records to ProductionTimePoint
        and delegating to canonical ChanDiagnosticEngine.
        """
        pts = []
        for r in records:
            if isinstance(r, ProductionTimePoint):
                pts.append(r)
            elif isinstance(r, dict):
                pts.append(ProductionTimePoint(**r))
        return ChanDiagnosticEngine.compute_chan_diagnostic_series(pts, well_code=well_code, smoothing_window=smoothing_window)


# Canonical aliases
ChanSurveillanceService = ChanService

