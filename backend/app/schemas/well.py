from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class WellConfigBase(BaseModel):
    wc_threshold: float = Field(default=80.0, ge=0.0, le=100.0, description="Configurable Water Cut warning threshold percentage")
    wc_trend_window_hours: int = Field(default=24, ge=1, le=720)
    alert_cooldown_minutes: int = Field(default=60, ge=1, le=1440)
    surveillance_interval_minutes: int = Field(default=5, ge=1, le=1440)
    is_active: bool = True


class WellConfigUpdate(BaseModel):
    wc_threshold: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    wc_trend_window_hours: Optional[int] = Field(default=None, ge=1, le=720)
    alert_cooldown_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    surveillance_interval_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    is_active: Optional[bool] = None


class WellConfigResponse(WellConfigBase):
    well_code: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class WellBase(BaseModel):
    well_code: str = Field(..., min_length=2, max_length=50)
    field_name: str = Field(..., min_length=2, max_length=100)
    status: str = Field(default="ACTIVE")


class WellCreate(WellBase):
    config: Optional[WellConfigBase] = None


class WellUpdate(BaseModel):
    field_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    status: Optional[str] = Field(default=None)
    wc_threshold: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    new_well_code: Optional[str] = Field(default=None, min_length=2, max_length=50)


class WellResponse(WellBase):
    created_at: datetime
    updated_at: datetime
    config: Optional[WellConfigResponse] = None

    model_config = ConfigDict(from_attributes=True)
