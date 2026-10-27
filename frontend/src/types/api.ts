export type DataQualityStatus = "VALID" | "INVALID" | "STALE" | "MISSING" | "DATA_UNAVAILABLE";
export type SourceCategory = "MANUAL" | "SOFTWARE_API" | "MQTT" | "CALCULATED" | "DERIVED";
export type ValueType = "MEASURED" | "CALCULATED" | "DERIVED";
export type AlertSeverity = "INFO" | "WARNING" | "CRITICAL";
export type AlertStatus = "ACTIVE" | "ACKNOWLEDGED" | "RESOLVED";
export type SurveillanceState = "NORMAL" | "WARNING" | "DATA_UNAVAILABLE";

export interface WellConfig {
  well_code: string;
  wc_threshold: number;
  wc_trend_window_hours: number;
  alert_cooldown_minutes: number;
  surveillance_interval_minutes: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Well {
  well_code: string;
  field_name: string;
  status: string;
  created_at: string;
  updated_at: string;
  config?: WellConfig;
}

export interface KpiCardData {
  title: string;
  metric_key: string;
  value: number | null;
  display_value: string;
  unit: string;
  status: SurveillanceState;
  timestamp: string | null;
  received_at: string | null;
  source: SourceCategory | null;
  quality_status: DataQualityStatus;
  value_type: ValueType;
  threshold: number | null;
  is_threshold_exceeded: boolean;
}

export interface Alert {
  alert_id: string;
  well_code: string;
  alert_type: string;
  severity: AlertSeverity;
  message: string;
  value: number | null;
  threshold: number | null;
  timestamp: string;
  status: AlertStatus;
  source: string;
  created_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface DashboardResponse {
  well_code: string;
  field_name: string;
  well_status: string;
  latest_timestamp: string | null;
  surveillance_state: SurveillanceState;
  kpis: KpiCardData[];
  active_alerts: Alert[];
  configured_wc_threshold: number;
  rate_limit_info: {
    rate_limit_per_source: number;
    rate_limit_per_well: number;
  };
}

export interface ManualReadingCreatePayload {
  well_code: string;
  measurement_type: "WATER_CUT" | "OIL_API_GRAVITY" | "SEPARATOR_PRESSURE";
  value: number | null;
  unit: string;
  timestamp: string;
  entered_by: string;
  is_data_unavailable?: boolean;
}

export interface SeparatorReadingCreatePayload {
  well_code: string;
  timestamp: string;
  pressure?: number | null;
  flow_rate?: number | null;
  water_cut?: number | null;
  wc_unit: "%" | "fraction";
  oil_rate?: number | null;
  water_rate?: number | null;
  gas_rate?: number | null;
  source?: SourceCategory;
  is_data_unavailable?: boolean;
}
