import {
  DashboardResponse,
  Well,
  WellConfig,
  ManualReadingCreatePayload,
  SeparatorReadingCreatePayload,
  Alert
} from "@/types/api";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export async function fetchWells(): Promise<Well[]> {
  const res = await fetch(`${API_BASE}/wells`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch wells list");
  return res.json();
}

export async function fetchDashboard(wellCode?: string): Promise<DashboardResponse> {
  const url = wellCode ? `${API_BASE}/dashboard?well_code=${encodeURIComponent(wellCode)}` : `${API_BASE}/dashboard`;
  const res = await fetch(url, { cache: "no-store" });
  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({}));
    throw new Error(errorBody.detail || "Failed to fetch dashboard data");
  }
  return res.json();
}

export async function fetchWellConfig(wellCode: string): Promise<WellConfig> {
  const res = await fetch(`${API_BASE}/wells/${encodeURIComponent(wellCode)}/config`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch well configuration");
  return res.json();
}

export async function updateWellConfig(wellCode: string, payload: Partial<WellConfig>): Promise<WellConfig> {
  const res = await fetch(`${API_BASE}/wells/${encodeURIComponent(wellCode)}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to update well config");
  return res.json();
}

export async function ingestManualReading(payload: ManualReadingCreatePayload): Promise<any> {
  const res = await fetch(`${API_BASE}/readings/manual`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Manual reading ingestion failed");
  }
  return res.json();
}

export async function ingestSeparatorReading(payload: SeparatorReadingCreatePayload): Promise<any> {
  const res = await fetch(`${API_BASE}/separator-data`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Separator telemetry ingestion failed");
  }
  return res.json();
}

export async function acknowledgeAlert(alertId: string, acknowledgedBy = "operator"): Promise<Alert> {
  const res = await fetch(`${API_BASE}/alerts/${encodeURIComponent(alertId)}/acknowledge`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ acknowledged_by: acknowledgedBy }),
  });
  if (!res.ok) throw new Error("Failed to acknowledge alert");
  return res.json();
}

export async function resolveAlert(alertId: string, resolvedBy = "operator", notes = ""): Promise<Alert> {
  const res = await fetch(`${API_BASE}/alerts/${encodeURIComponent(alertId)}/resolve`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ resolved_by: resolvedBy, resolution_notes: notes }),
  });
  if (!res.ok) throw new Error("Failed to resolve alert");
  return res.json();
}

export async function createWell(payload: {
  well_code: string;
  field_name: string;
  status?: string;
  config?: { wc_threshold?: number };
}): Promise<Well> {
  const res = await fetch(`${API_BASE}/wells`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to create new well");
  }
  return res.json();
}

export async function updateWell(
  wellCode: string,
  payload: { field_name?: string; status?: string; wc_threshold?: number }
): Promise<Well> {
  const res = await fetch(`${API_BASE}/wells/${encodeURIComponent(wellCode)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to update well");
  }
  return res.json();
}

export async function deleteWell(wellCode: string): Promise<{ status: string; message: string }> {
  const res = await fetch(`${API_BASE}/wells/${encodeURIComponent(wellCode)}`, {
    method: "DELETE",
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Failed to delete well");
  }
  return res.json();
}

export async function fetchFieldControlMode(): Promise<{
  enabled: boolean;
  authorized_by?: string;
  authorized_at?: string;
  reason?: string;
}> {
  const res = await fetch(`${API_BASE}/reservoir/field/mode`, { cache: "no-store" });
  if (!res.ok) throw new Error("Failed to fetch control mode");
  return res.json();
}

export async function toggleFieldControlMode(
  enabled: boolean,
  operator = "Chief Petroleum Engineer",
  reason = "Operational parameter adjustment"
): Promise<any> {
  const url = `${API_BASE}/reservoir/field/mode/toggle?enabled=${enabled}&operator=${encodeURIComponent(operator)}&reason=${encodeURIComponent(reason)}`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) throw new Error("Failed to toggle supervisory mode");
  return res.json();
}

export async function writeOpcuaTag(
  tagNodeId: string,
  value: number,
  operatorSignature = "Chief Engineer"
): Promise<any> {
  const url = `${API_BASE}/reservoir/field/opcua/write?tag_node_id=${encodeURIComponent(tagNodeId)}&value=${value}&operator_signature=${encodeURIComponent(operatorSignature)}`;
  const res = await fetch(url, { method: "POST" });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || "Write command rejected by safety boundary");
  }
  return res.json();
}
