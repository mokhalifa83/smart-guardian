"""
Smart Guardian Reservoir Intelligence Layer - Virtual Separator Domain Models (Step 2B)
Defines data structures, configuration contracts, and stage states for virtual separation.
Prepares the engineering foundation for future STEP 2C field telemetry integration.
"""

from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class SeparatorStageCondition(BaseModel):
    """Pressure and temperature conditions for a single separation stage."""
    stage_index: int = Field(..., ge=1, le=5, description="Separation stage index (1 = HP, 2 = IP/LP, etc.)")
    stage_name: str = Field(default="HP_SEPARATOR", description="Stage designation")
    pressure_psia: float = Field(..., gt=0, description="Operating pressure in psia")
    temperature_f: float = Field(..., description="Operating temperature in degrees Fahrenheit")
    is_configuration_default: bool = Field(default=False, description="True if using fallback configuration value rather than measured telemetry")
    provenance_source: str = Field(default="CONFIGURED_PARAMETER")

    model_config = ConfigDict(from_attributes=True)


class VirtualSeparatorConfig(BaseModel):
    """Complete multi-stage separation configuration for a field or production train."""
    train_id: str = Field(default="TRAIN-01")
    stages: List[SeparatorStageCondition] = Field(default_factory=list)
    stock_tank_pressure_psia: float = Field(default=14.696, gt=0)
    stock_tank_temperature_f: float = Field(default=60.0)
    surveillance_target_interval_minutes: int = Field(default=5, gt=0, description="Target execution interval")
    test_separator_daily_rental_cost: float = Field(default=20000.0, ge=0, description="Configurable benchmark for avoided cost evaluation")
    currency: str = Field(default="USD")

    model_config = ConfigDict(from_attributes=True)


class PhaseSplitResult(BaseModel):
    """Phase-separated stream mass and volume properties."""
    phase_name: str  # GAS, OIL, WATER
    rate_volume_bpd: Optional[float] = None
    rate_gas_mscfd: Optional[float] = None
    fraction_of_total_stream: float
    density_lb_cuft: Optional[float] = None
    formation_volume_factor: Optional[float] = None
    unit: str

    model_config = ConfigDict(from_attributes=True)
