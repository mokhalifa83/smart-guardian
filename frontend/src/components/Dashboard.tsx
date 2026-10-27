"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboard } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import { Header } from "@/components/Header";
import { KpiCard } from "@/components/KpiCard";
import { AlertList } from "@/components/AlertList";
import { WellConfigModal } from "@/components/WellConfigModal";
import { ManualReadingModal } from "@/components/ManualReadingModal";
import { SeparatorReadingModal } from "@/components/SeparatorReadingModal";
import { WellManagementModal } from "@/components/WellManagementModal";
import { SupervisoryModeModal } from "@/components/SupervisoryModeModal";
import { formatDateTime } from "@/lib/utils";
import {
  RefreshCw,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ShieldCheck,
  Server,
  Layers,
  Activity,
} from "lucide-react";

export function Dashboard() {
  const { t } = useLanguage();
  const { selectedWellCode, selectedWell } = useWell();

  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [isSeparatorModalOpen, setIsSeparatorModalOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [isWellManagementOpen, setIsWellManagementOpen] = useState(false);
  const [isSupervisoryModalOpen, setIsSupervisoryModalOpen] = useState(false);

  // TanStack Query with 30-second polling as specified in prompt section 23
  const {
    data: dashboard,
    isLoading,
    isError,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["dashboard", selectedWellCode],
    queryFn: () => fetchDashboard(selectedWellCode),
    refetchInterval: 30000,
  });

  return (
    <div className="min-h-screen bg-[#070c16] text-slate-100 flex flex-col font-cairo">
      <Header
        onOpenManualModal={() => setIsManualModalOpen(true)}
        onOpenSeparatorModal={() => setIsSeparatorModalOpen(true)}
        onOpenConfigModal={() => setIsConfigModalOpen(true)}
        onOpenWellManagement={() => setIsWellManagementOpen(true)}
        onOpenSupervisoryModal={() => setIsSupervisoryModalOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 py-6 space-y-6">
        {/* Well Surveillance Summary Banner */}
        <div className="rounded-2xl border border-cyan-500/20 bg-[#0c1527] p-6 shadow-2xl shadow-cyan-950/20 flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h2 className="text-2xl font-black tracking-tight text-white font-mono">
                {dashboard?.well_code || selectedWellCode}
              </h2>
              <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-cyan-950 text-cyan-300 border border-cyan-800">
                {selectedWell?.field_name || dashboard?.field_name || "Field Reservoir"}
              </span>
              <span
                className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                  (selectedWell?.status || dashboard?.well_status) === "ACTIVE"
                    ? "bg-emerald-950 text-emerald-400 border border-emerald-800 animate-pulse"
                    : "bg-amber-950 text-amber-400 border border-amber-800"
                }`}
              >
                {selectedWell?.status || dashboard?.well_status || "ACTIVE"}
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1.5 font-medium">
              {t("dashboard.subtitle")}
            </p>
          </div>

          {/* Quick Metrics & Actions */}
          <div className="flex flex-wrap items-center gap-3 text-xs">
            <div className="bg-[#080e1b] border border-oilfield-700/80 px-3.5 py-2 rounded-xl">
              <span className="text-slate-400 block text-[11px] font-semibold">{t("dashboard.configured_threshold")}:</span>
              <span className="text-sm font-bold font-mono text-amber-400">
                {dashboard ? `${dashboard.configured_wc_threshold}%` : "80.0%"}
              </span>
            </div>

            <div className="bg-[#080e1b] border border-oilfield-700/80 px-3.5 py-2 rounded-xl">
              <span className="text-slate-400 block text-[11px] font-semibold">{t("dashboard.latest_ts")}:</span>
              <span className="text-xs font-bold font-mono text-cyan-300">
                {formatDateTime(dashboard?.latest_timestamp)}
              </span>
            </div>

            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-oilfield-700 hover:bg-oilfield-600 text-white border border-oilfield-600 transition shadow-sm"
              title="Poll API immediately"
            >
              <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${isFetching ? "animate-spin" : ""}`} />
              <span className="font-semibold">{t("dashboard.refresh_now")}</span>
            </button>
          </div>
        </div>

        {/* Global Surveillance State Banner */}
        {dashboard && (
          <div
            className={`rounded-xl border p-4 flex items-center justify-between transition-all ${
              dashboard.surveillance_state === "WARNING"
                ? "bg-amber-950/40 border-amber-500/40 text-amber-200"
                : dashboard.surveillance_state === "NORMAL"
                ? "bg-emerald-950/40 border-emerald-500/40 text-emerald-200"
                : "bg-slate-900/80 border-slate-700 text-slate-300"
            }`}
          >
            <div className="flex items-center gap-3">
              {dashboard.surveillance_state === "WARNING" ? (
                <AlertTriangle className="w-5 h-5 text-amber-400 shrink-0" />
              ) : dashboard.surveillance_state === "NORMAL" ? (
                <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
              ) : (
                <HelpCircle className="w-5 h-5 text-slate-400 shrink-0" />
              )}
              <div>
                <span className="text-xs font-bold uppercase tracking-wider">
                  Surveillance Condition: {dashboard.surveillance_state}
                </span>
                <p className="text-xs text-slate-300 mt-0.5">
                  {dashboard.surveillance_state === "WARNING"
                    ? "Production threshold exceedance detected on monitored asset. Operational review required."
                    : dashboard.surveillance_state === "NORMAL"
                    ? "Wellhead telemetry operating within validated engineering envelope."
                    : "Telemetry data is currently unavailable. Waiting for sensor stream."}
                </p>
              </div>
            </div>

            <span className="text-[11px] font-mono font-bold px-2.5 py-1 rounded-lg bg-black/40 border border-white/10">
              {dashboard.surveillance_state}
            </span>
          </div>
        )}

        {/* Loading & Error States */}
        {isLoading && (
          <div className="flex flex-col items-center justify-center p-12 text-slate-400 space-y-3">
            <RefreshCw className="w-8 h-8 animate-spin text-cyan-400" />
            <p className="text-sm font-semibold">Streaming surveillance telemetry...</p>
          </div>
        )}

        {isError && (
          <div className="p-6 rounded-2xl bg-rose-950/40 border border-rose-800 text-rose-200 flex items-center gap-3">
            <AlertTriangle className="w-6 h-6 shrink-0" />
            <div>
              <h3 className="font-bold text-sm">Failed to connect to backend surveillance engine</h3>
              <p className="text-xs text-rose-300 mt-1">{(error as any)?.message || "Network unreachable"}</p>
            </div>
          </div>
        )}

        {/* Core KPI Cards Grid */}
        {dashboard && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                Real-Time Surveillance Metrics
              </h3>
              <span className="text-[11px] text-slate-500 font-medium">
                Distinguishes Measured vs Calculated vs Derived
              </span>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {dashboard.kpis.map((kpi) => (
                <KpiCard key={kpi.metric_key} data={kpi} />
              ))}
            </div>
          </div>
        )}

        {/* Operational Alerts Section */}
        {dashboard && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                  {t("dashboard.active_alerts")}
                </h3>
                {dashboard.active_alerts.length > 0 && (
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500 text-black">
                    {dashboard.active_alerts.length}
                  </span>
                )}
              </div>
              <span className="text-[11px] text-slate-500 font-medium">
                Structured Lifecycle (ACTIVE → ACKNOWLEDGED → RESOLVED)
              </span>
            </div>
            <AlertList alerts={dashboard.active_alerts} wellCode={selectedWellCode} />
          </div>
        )}

        {/* Architectural Footer Note */}
        <div className="rounded-xl border border-oilfield-700/60 bg-[#080e1b] p-4 text-xs text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <Server className="w-4 h-4 text-slate-500 shrink-0" />
            <div>
              <span className="font-semibold text-slate-300">Data Integrity Principle: </span>
              <span>{t("footer.provenance_notice")}</span>
            </div>
          </div>
          <span className="text-[11px] text-cyan-400 font-mono font-semibold">
            SMART GUARDIAN ENGINE v2.0
          </span>
        </div>
      </main>

      {/* Modals */}
      <ManualReadingModal
        isOpen={isManualModalOpen}
        onClose={() => setIsManualModalOpen(false)}
        wellCode={selectedWellCode}
      />

      <SeparatorReadingModal
        isOpen={isSeparatorModalOpen}
        onClose={() => setIsSeparatorModalOpen(false)}
        wellCode={selectedWellCode}
      />

      <WellConfigModal
        isOpen={isConfigModalOpen}
        onClose={() => setIsConfigModalOpen(false)}
        wellCode={selectedWellCode}
      />

      <WellManagementModal
        isOpen={isWellManagementOpen}
        onClose={() => setIsWellManagementOpen(false)}
      />

      <SupervisoryModeModal
        isOpen={isSupervisoryModalOpen}
        onClose={() => setIsSupervisoryModalOpen(false)}
      />
    </div>
  );
}
