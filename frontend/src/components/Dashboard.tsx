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
import { ReservoirEnginesHub } from "@/components/ReservoirEnginesHub";
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
  Cpu,
} from "lucide-react";

export function Dashboard() {
  const { t } = useLanguage();
  const { selectedWellCode, selectedWell } = useWell();

  const [dashboardView, setDashboardView] = useState<"surveillance" | "engines">("surveillance");
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

      <main className="flex-1 max-w-7xl w-full mx-auto px-6 py-8 space-y-8">
        {/* Well Surveillance Summary Banner */}
        <div className="rounded-3xl border border-red-600/30 bg-gradient-to-r from-[#120707] via-[#0d0d10] to-[#120707] p-8 shadow-2xl shadow-black/80 flex flex-col md:flex-row md:items-center justify-between gap-6">
          <div>
            <div className="flex items-center gap-3.5 flex-wrap">
              <h2 className="text-3xl sm:text-4xl font-black tracking-tight text-white font-mono">
                {dashboard?.well_code || selectedWellCode}
              </h2>
              <span className="px-3.5 py-1 rounded-full text-xs sm:text-sm font-bold bg-zinc-900 text-zinc-200 border border-zinc-700">
                {selectedWell?.field_name || dashboard?.field_name || "Field Reservoir"}
              </span>
              <span
                className={`px-3.5 py-1 rounded-full text-xs sm:text-sm font-black ${
                  (selectedWell?.status || dashboard?.well_status) === "ACTIVE"
                    ? "bg-red-950 text-red-300 border border-red-600 animate-pulse shadow-sm shadow-red-600/30"
                    : "bg-zinc-800 text-zinc-300 border border-zinc-700"
                }`}
              >
                {selectedWell?.status || dashboard?.well_status || "ACTIVE"}
              </span>
            </div>
            <p className="text-sm text-zinc-400 mt-2 font-medium">
              {t("dashboard.subtitle")}
            </p>
          </div>

          {/* Quick Metrics & Actions */}
          <div className="flex flex-wrap items-center gap-3.5 text-xs sm:text-sm">
            <div className="bg-zinc-900 border border-zinc-700 px-5 py-3 rounded-2xl shadow-sm">
              <span className="text-zinc-400 block text-xs font-bold uppercase tracking-wider">{t("dashboard.configured_threshold")}:</span>
              <span className="text-lg font-black font-mono text-red-400 mt-0.5 block">
                {dashboard ? `${dashboard.configured_wc_threshold}%` : "80.0%"}
              </span>
            </div>

            <div className="bg-zinc-900 border border-zinc-700 px-5 py-3 rounded-2xl shadow-sm">
              <span className="text-zinc-400 block text-xs font-bold uppercase tracking-wider">{t("dashboard.latest_ts")}:</span>
              <span className="text-sm font-black font-mono text-zinc-200 mt-0.5 block">
                {formatDateTime(dashboard?.latest_timestamp)}
              </span>
            </div>

            <button
              onClick={() => refetch()}
              disabled={isFetching}
              className="flex items-center gap-2 px-5 py-3 rounded-2xl bg-zinc-900 hover:bg-zinc-800 text-white border border-zinc-700 hover:border-red-500 transition shadow-sm font-bold"
              title="Poll API immediately"
            >
              <RefreshCw className={`w-4 h-4 text-red-400 ${isFetching ? "animate-spin" : ""}`} />
              <span>{t("dashboard.refresh_now")}</span>
            </button>
          </div>
        </div>

        {/* View Mode Switcher: Real-Time Surveillance vs 36 Reservoir Engines */}
        <div className="flex flex-wrap items-center justify-between gap-4 bg-[#0e0e11] border border-zinc-800 p-2.5 rounded-2xl shadow-xl">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setDashboardView("surveillance")}
              className={`flex items-center gap-2.5 px-6 py-3 rounded-xl text-sm font-black transition ${
                dashboardView === "surveillance"
                  ? "bg-red-600 text-white shadow-lg shadow-red-600/40 border border-red-400/30"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900"
              }`}
            >
              <Activity className="w-5 h-5" />
              <span>المراقبة الحقلية المباشرة والإنذار المبكر (Field Surveillance & Alerts)</span>
            </button>

            <button
              onClick={() => setDashboardView("engines")}
              className={`flex items-center gap-2.5 px-6 py-3 rounded-xl text-sm font-black transition ${
                dashboardView === "engines"
                  ? "bg-gradient-to-r from-red-600 to-zinc-900 text-white shadow-lg shadow-red-600/40 border border-red-500/50"
                  : "text-zinc-400 hover:text-white hover:bg-zinc-900"
              }`}
            >
              <Cpu className="w-5 h-5 text-red-400" />
              <span>محركات المكمن والذكاء الهندسي (36 Physics Engines Hub)</span>
              <span className="px-2 py-0.5 rounded-md text-xs font-mono font-black bg-red-950 text-red-300 border border-red-800">
                36
              </span>
            </button>
          </div>

          <div className="text-xs text-zinc-400 font-mono hidden md:block px-4">
            Active Well: <strong className="text-red-400 text-sm font-black">{selectedWellCode}</strong>
          </div>
        </div>

        {/* ========================================================= */}
        {/* VIEW 1: FIELD SURVEILLANCE & REAL-TIME ALERTS VIEW       */}
        {/* ========================================================= */}
        {dashboardView === "surveillance" && (
          <div className="space-y-8">
            {/* Global Surveillance State Banner */}
            {dashboard && (
              <div
                className={`rounded-2xl border p-5 flex items-center justify-between transition-all shadow-xl ${
                  dashboard.surveillance_state === "WARNING"
                    ? "bg-gradient-to-r from-red-950/60 via-[#180808] to-[#0e0e11] border-red-600 text-red-200"
                    : dashboard.surveillance_state === "NORMAL"
                    ? "bg-zinc-900 border-zinc-700 text-zinc-200"
                    : "bg-zinc-900 border-zinc-800 text-zinc-400"
                }`}
              >
                <div className="flex items-center gap-4">
                  {dashboard.surveillance_state === "WARNING" ? (
                    <AlertTriangle className="w-7 h-7 text-red-500 shrink-0 animate-pulse" />
                  ) : dashboard.surveillance_state === "NORMAL" ? (
                    <CheckCircle2 className="w-7 h-7 text-emerald-400 shrink-0" />
                  ) : (
                    <HelpCircle className="w-7 h-7 text-zinc-500 shrink-0" />
                  )}
                  <div>
                    <span className="text-sm font-black uppercase tracking-wider block">
                      Surveillance Condition: {dashboard.surveillance_state}
                    </span>
                    <p className="text-sm text-zinc-300 mt-1 font-medium">
                      {dashboard.surveillance_state === "WARNING"
                        ? "Production threshold exceedance detected on monitored asset. Operational review required."
                        : dashboard.surveillance_state === "NORMAL"
                        ? "Wellhead telemetry operating within validated engineering envelope."
                        : "Telemetry data is currently unavailable. Waiting for sensor stream."}
                    </p>
                  </div>
                </div>

                <span className="text-xs font-mono font-black px-3.5 py-1.5 rounded-xl bg-black/60 border border-zinc-700">
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
          </div>
        )}

        {/* ========================================================= */}
        {/* VIEW 2: 36 PETROLEUM & RESERVOIR PHYSICS ENGINES HUB      */}
        {/* ========================================================= */}
        {dashboardView === "engines" && (
          <ReservoirEnginesHub />
        )}

        {/* Architectural Footer Note */}
        <div className="rounded-2xl border border-zinc-800 bg-[#0e0e11] p-5 text-sm text-zinc-400 flex flex-col sm:flex-row items-center justify-between gap-4 shadow-lg">
          <div className="flex items-center gap-3">
            <Server className="w-5 h-5 text-red-500 shrink-0" />
            <div>
              <span className="font-bold text-white">Data Integrity Principle: </span>
              <span className="text-zinc-300">{t("footer.provenance_notice")}</span>
            </div>
          </div>
          <span className="text-xs text-red-400 font-mono font-black tracking-wider bg-zinc-900 border border-zinc-800 px-3 py-1 rounded-lg">
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
