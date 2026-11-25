"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchDashboard } from "@/lib/api";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import { Header } from "@/components/Header";
import { Sidebar, DashboardViewType } from "@/components/Sidebar";
import { KpiCard } from "@/components/KpiCard";
import { AlertList } from "@/components/AlertList";
import { ProductionChart } from "@/components/ProductionChart";
import { FieldOverview } from "@/components/FieldOverview";
import { ReportsView } from "@/components/ReportsView";
import { ReservoirEnginesHub } from "@/components/ReservoirEnginesHub";
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
  Server,
  Layers,
  Activity,
  Cpu,
} from "lucide-react";

export function Dashboard() {
  const { t, direction } = useLanguage();
  const { selectedWellCode, selectedWell, setSelectedWellCode } = useWell();

  const [activeView, setActiveView] = useState<DashboardViewType>("surveillance");
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);

  const [isManualModalOpen, setIsManualModalOpen] = useState(false);
  const [isSeparatorModalOpen, setIsSeparatorModalOpen] = useState(false);
  const [isConfigModalOpen, setIsConfigModalOpen] = useState(false);
  const [isWellManagementOpen, setIsWellManagementOpen] = useState(false);
  const [isSupervisoryModalOpen, setIsSupervisoryModalOpen] = useState(false);

  // TanStack Query with 30-second polling
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

  // Calculate margin based on sidebar state & direction
  const sidebarMargin = direction === "rtl"
    ? isSidebarCollapsed ? "mr-20" : "mr-64"
    : isSidebarCollapsed ? "ml-20" : "ml-64";

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-[#0f172a] text-slate-900 dark:text-slate-100 flex font-cairo">
      {/* Collapsible Sidebar */}
      <Sidebar
        activeView={activeView}
        setActiveView={setActiveView}
        onOpenManualModal={() => setIsManualModalOpen(true)}
        onOpenSeparatorModal={() => setIsSeparatorModalOpen(true)}
        onOpenConfigModal={() => setIsConfigModalOpen(true)}
        onOpenWellManagement={() => setIsWellManagementOpen(true)}
        onOpenSupervisoryModal={() => setIsSupervisoryModalOpen(true)}
        isCollapsed={isSidebarCollapsed}
        setIsCollapsed={setIsSidebarCollapsed}
      />

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col transition-all duration-300 min-w-0 ${sidebarMargin}`}>
        {/* Minimal Clean Top Bar */}
        <Header
          onToggleSidebar={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
          onRefresh={() => refetch()}
          isFetching={isFetching}
        />

        {/* Content Body */}
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 lg:px-6 py-6 space-y-6">
          {/* ========================================================= */}
          {/* VIEW 1: REAL-TIME SURVEILLANCE & TREND CHARTS VIEW        */}
          {/* ========================================================= */}
          {activeView === "surveillance" && (
            <div className="space-y-6">
              {/* Well Surveillance Summary Banner with Integrated Condition */}
              <div className="rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#1e293b] p-5 shadow-sm dark:shadow-xl flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                  <div className="flex flex-wrap items-center gap-2.5">
                    <h2 className="text-2xl font-black tracking-tight text-slate-900 dark:text-white font-mono">
                      {dashboard?.well_code || selectedWellCode}
                    </h2>
                    <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-100 dark:bg-slate-800 text-blue-800 dark:text-cyan-300 border border-slate-200 dark:border-slate-700">
                      {selectedWell?.field_name || dashboard?.field_name || "Field Reservoir"}
                    </span>
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${
                        (selectedWell?.status || dashboard?.well_status) === "ACTIVE"
                          ? "bg-emerald-100 dark:bg-emerald-950/80 text-emerald-800 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800"
                          : "bg-amber-100 dark:bg-amber-950/80 text-amber-800 dark:text-amber-400 border border-amber-200 dark:border-amber-800"
                      }`}
                    >
                      {selectedWell?.status || dashboard?.well_status || "ACTIVE"}
                    </span>

                    {/* Integrated Compact Surveillance Condition Badge */}
                    {dashboard && (
                      <div
                        className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-bold border transition ${
                          dashboard.surveillance_state === "WARNING"
                            ? "bg-amber-100 dark:bg-amber-950/60 border-amber-300 dark:border-amber-500/60 text-amber-900 dark:text-amber-300"
                            : dashboard.surveillance_state === "NORMAL"
                            ? "bg-emerald-100 dark:bg-emerald-950/60 border-emerald-300 dark:border-emerald-500/60 text-emerald-900 dark:text-emerald-300"
                            : "bg-slate-100 dark:bg-slate-900 border-slate-300 dark:border-slate-700 text-slate-700 dark:text-slate-300"
                        }`}
                        title={
                          dashboard.surveillance_state === "WARNING"
                            ? t("dashboard.surveillance_warning_desc")
                            : dashboard.surveillance_state === "NORMAL"
                            ? t("dashboard.surveillance_normal_desc")
                            : t("dashboard.surveillance_unavailable_desc")
                        }
                      >
                        {dashboard.surveillance_state === "WARNING" ? (
                          <AlertTriangle className="w-3.5 h-3.5 text-amber-600 dark:text-amber-400 shrink-0" />
                        ) : dashboard.surveillance_state === "NORMAL" ? (
                          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0" />
                        ) : (
                          <HelpCircle className="w-3.5 h-3.5 text-slate-500 dark:text-slate-400 shrink-0" />
                        )}
                        <span>
                          {t("dashboard.surveillance_condition")}: {t(`status.${dashboard.surveillance_state}`) || dashboard.surveillance_state}
                        </span>
                      </div>
                    )}
                  </div>
                  <p className="text-xs text-slate-500 dark:text-slate-400 mt-1.5 font-medium">
                    {t("dashboard.subtitle")}
                  </p>
                </div>

                {/* Quick Metrics & Actions */}
                <div className="flex flex-wrap items-center gap-2.5 text-xs">
                  <div className="bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 px-3.5 py-2 rounded-xl">
                    <span className="text-slate-500 dark:text-slate-400 block text-[11px] font-semibold">{t("dashboard.configured_threshold")}:</span>
                    <span className="text-sm font-bold font-mono text-amber-600 dark:text-amber-400">
                      {dashboard ? `${dashboard.configured_wc_threshold}%` : "80.0%"}
                    </span>
                  </div>

                  <div className="bg-slate-50 dark:bg-[#0f172a] border border-slate-200 dark:border-slate-700 px-3.5 py-2 rounded-xl">
                    <span className="text-slate-500 dark:text-slate-400 block text-[11px] font-semibold">{t("dashboard.latest_ts")}:</span>
                    <span className="text-xs font-bold font-mono text-blue-700 dark:text-cyan-300">
                      {formatDateTime(dashboard?.latest_timestamp)}
                    </span>
                  </div>

                  <button
                    onClick={() => refetch()}
                    disabled={isFetching}
                    className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-blue-700 hover:bg-blue-600 dark:bg-slate-800 dark:hover:bg-slate-700 text-white dark:text-slate-200 border border-blue-600 dark:border-slate-700 transition shadow-sm"
                    title="Poll API immediately"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 text-blue-200 dark:text-cyan-400 ${isFetching ? "animate-spin" : ""}`} />
                    <span className="font-semibold">{t("dashboard.refresh_now")}</span>
                  </button>
                </div>
              </div>

              {/* Operational Warning Notification Strip (Only shown when WARNING) */}
              {dashboard && dashboard.surveillance_state === "WARNING" && (
                <div className="rounded-xl border border-amber-300 dark:border-amber-500/40 bg-amber-50 dark:bg-amber-950/30 p-3.5 flex items-center justify-between text-amber-900 dark:text-amber-200">
                  <div className="flex items-center gap-2.5">
                    <AlertTriangle className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
                    <span className="text-xs font-medium">
                      {t("dashboard.surveillance_warning_desc")}
                    </span>
                  </div>
                  <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-amber-200 dark:bg-amber-900/60 text-amber-900 dark:text-amber-300 border border-amber-300 dark:border-amber-600/60">
                    {dashboard.surveillance_state}
                  </span>
                </div>
              )}

              {/* Interactive Multi-Parameter Production Trend Chart */}
              <ProductionChart
                wellCode={selectedWellCode}
                threshold={dashboard?.configured_wc_threshold}
              />

              {/* Core KPI Cards Grid */}
              {dashboard && (
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
                      {t("dashboard.realtime_metrics_title")}
                    </h3>
                    <span className="text-[11px] text-slate-500 font-medium">
                      {t("dashboard.realtime_metrics_subtitle")}
                    </span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                    {dashboard.kpis.map((kpi) => (
                      <KpiCard key={kpi.metric_key} data={kpi} />
                    ))}
                  </div>
                </div>
              )}

              {/* Operational Alerts Section with Smart Diagnostic Bridge */}
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
                      {t("dashboard.active_alerts_subtitle")}
                    </span>
                  </div>
                  <AlertList
                    alerts={dashboard.active_alerts}
                    wellCode={selectedWellCode}
                    onLaunchDiagnostic={(well) => {
                      setSelectedWellCode(well);
                      setActiveView("engines");
                    }}
                  />
                </div>
              )}
            </div>
          )}

          {/* ========================================================= */}
          {/* VIEW 2: FIELD-WIDE OVERVIEW & MULTI-WELL MATRIX           */}
          {/* ========================================================= */}
          {activeView === "field_overview" && (
            <FieldOverview
              onSelectWellToMonitor={(well) => {
                setSelectedWellCode(well);
                setActiveView("surveillance");
              }}
              onLaunchDiagnostics={(well) => {
                setSelectedWellCode(well);
                setActiveView("engines");
              }}
            />
          )}

          {/* ========================================================= */}
          {/* VIEW 3: 36 PETROLEUM & RESERVOIR PHYSICS ENGINES HUB      */}
          {/* ========================================================= */}
          {activeView === "engines" && (
            <ReservoirEnginesHub />
          )}

          {/* ========================================================= */}
          {/* VIEW 4: OFFICIAL ENGINEERING REPORTS & EXPORTS            */}
          {/* ========================================================= */}
          {activeView === "reports" && (
            <ReportsView />
          )}

          {/* Architectural Footer Note */}
          <div className="rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-[#1e293b] p-4 text-xs text-slate-500 dark:text-slate-400 flex flex-col sm:flex-row items-center justify-between gap-3 shadow-sm">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-slate-400 shrink-0" />
              <div>
                <span className="font-semibold text-slate-700 dark:text-slate-300">{t("dashboard.data_integrity_title")}: </span>
                <span>{t("footer.provenance_notice")}</span>
              </div>
            </div>
            <span className="text-[11px] text-blue-700 dark:text-cyan-400 font-mono font-semibold">
              {t("dashboard.engine_version")}
            </span>
          </div>
        </main>
      </div>

      {/* Modals with lazy conditional mount */}
      {isManualModalOpen && (
        <ManualReadingModal
          isOpen={isManualModalOpen}
          onClose={() => setIsManualModalOpen(false)}
          wellCode={selectedWellCode}
        />
      )}

      {isSeparatorModalOpen && (
        <SeparatorReadingModal
          isOpen={isSeparatorModalOpen}
          onClose={() => setIsSeparatorModalOpen(false)}
          wellCode={selectedWellCode}
        />
      )}

      {isConfigModalOpen && (
        <WellConfigModal
          isOpen={isConfigModalOpen}
          onClose={() => setIsConfigModalOpen(false)}
          wellCode={selectedWellCode}
        />
      )}

      {isWellManagementOpen && (
        <WellManagementModal
          isOpen={isWellManagementOpen}
          onClose={() => setIsWellManagementOpen(false)}
        />
      )}

      {isSupervisoryModalOpen && (
        <SupervisoryModeModal
          isOpen={isSupervisoryModalOpen}
          onClose={() => setIsSupervisoryModalOpen(false)}
        />
      )}
    </div>
  );
}