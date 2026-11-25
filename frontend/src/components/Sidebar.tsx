"use client";

import React, { useState, useEffect } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import { fetchFieldControlMode } from "@/lib/api";
import {
  Shield,
  Activity,
  LayoutDashboard,
  Cpu,
  FileText,
  Database,
  Gauge,
  Sliders,
  Layers,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  ShieldAlert,
  Globe,
  Plus,
} from "lucide-react";

export type DashboardViewType = "surveillance" | "field_overview" | "engines" | "reports";

interface SidebarProps {
  activeView: DashboardViewType;
  setActiveView: (view: DashboardViewType) => void;
  onOpenManualModal: () => void;
  onOpenSeparatorModal: () => void;
  onOpenConfigModal: () => void;
  onOpenWellManagement: () => void;
  onOpenSupervisoryModal: () => void;
  isCollapsed: boolean;
  setIsCollapsed: (collapsed: boolean) => void;
}

export function Sidebar({
  activeView,
  setActiveView,
  onOpenManualModal,
  onOpenSeparatorModal,
  onOpenConfigModal,
  onOpenWellManagement,
  onOpenSupervisoryModal,
  isCollapsed,
  setIsCollapsed,
}: SidebarProps) {
  const { language, toggleLanguage, t, direction } = useLanguage();
  const { wells } = useWell();

  const [isSupervisoryActive, setIsSupervisoryActive] = useState(false);

  useEffect(() => {
    fetchFieldControlMode()
      .then((res) => setIsSupervisoryActive(res.enabled))
      .catch(() => {});
  }, []);

  const navItems = [
    {
      id: "surveillance" as DashboardViewType,
      label: t("sidebar.surveillance"),
      icon: <Activity className="w-4 h-4 shrink-0 text-cyan-400" />,
      badge: null,
    },
    {
      id: "field_overview" as DashboardViewType,
      label: t("sidebar.field_overview"),
      icon: <LayoutDashboard className="w-4 h-4 shrink-0 text-emerald-400" />,
      badge: null,
    },
    {
      id: "engines" as DashboardViewType,
      label: t("sidebar.engines_hub"),
      icon: <Cpu className="w-4 h-4 shrink-0 text-indigo-400" />,
      badge: "36",
    },
    {
      id: "reports" as DashboardViewType,
      label: t("sidebar.reports"),
      icon: <FileText className="w-4 h-4 shrink-0 text-amber-400" />,
      badge: null,
    },
  ];

  return (
    <aside
      className={`fixed top-0 bottom-0 z-50 flex flex-col justify-between bg-[#070c17] text-slate-200 transition-all duration-300 ease-in-out border-oilfield-700/80 ${
        direction === "rtl" ? "right-0 border-l" : "left-0 border-r"
      } ${isCollapsed ? "w-20" : "w-64"}`}
    >
      {/* Top Header: Brand & Collapse Toggle */}
      <div>
        <div className="h-16 px-4 flex items-center justify-between border-b border-oilfield-700/60">
          {!isCollapsed && (
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-700 flex items-center justify-center shadow-md shadow-cyan-900/30 shrink-0">
                <Shield className="w-5 h-5 text-white" />
              </div>
              <div className="truncate">
                <div className="flex items-center gap-1.5">
                  <h1 className="text-sm font-black tracking-tight text-white truncate">
                    {t("app_name")}
                  </h1>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-slate-800 text-cyan-300 border border-slate-700">
                    v2.0
                  </span>
                </div>
                <p className="text-[10px] text-slate-400 truncate font-medium">SPE-PRMS Standard</p>
              </div>
            </div>
          )}

          {isCollapsed && (
            <div className="mx-auto w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-700 flex items-center justify-center shadow-md shadow-cyan-900/30">
              <Shield className="w-5 h-5 text-white" />
            </div>
          )}

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition"
            title={isCollapsed ? t("sidebar.expand") : t("sidebar.collapse")}
          >
            {direction === "rtl" ? (
              isCollapsed ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
            ) : (
              isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation Section */}
        <div className="p-3 space-y-6 overflow-y-auto max-h-[calc(100vh-220px)]">
          {/* Main Views */}
          <div>
            {!isCollapsed && (
              <span className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                {t("sidebar.navigation")}
              </span>
            )}
            <nav className="space-y-1">
              {navItems.map((item) => {
                const isActive = activeView === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveView(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-semibold transition ${
                      isActive
                        ? "bg-cyan-600/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                        : "text-slate-300 hover:bg-slate-800/60 hover:text-white border border-transparent"
                    } ${isCollapsed ? "justify-center" : "justify-between"}`}
                    title={isCollapsed ? item.label : undefined}
                  >
                    <div className="flex items-center gap-3 truncate">
                      {item.icon}
                      {!isCollapsed && <span className="truncate">{item.label}</span>}
                    </div>
                    {!isCollapsed && item.badge && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-950 text-indigo-300 border border-indigo-700/60">
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Field Operations & Actions */}
          <div className="pt-2 border-t border-oilfield-700/40">
            {!isCollapsed && (
              <span className="px-3 text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-2">
                {t("sidebar.field_operations")}
              </span>
            )}
            <div className="space-y-1">
              <button
                onClick={onOpenManualModal}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-slate-300 hover:bg-slate-800/60 hover:text-white transition ${
                  isCollapsed ? "justify-center" : ""
                }`}
                title={isCollapsed ? t("dashboard.ingest_manual") : undefined}
              >
                <Database className="w-4 h-4 shrink-0 text-emerald-400" />
                {!isCollapsed && <span className="truncate">{t("dashboard.ingest_manual")}</span>}
              </button>

              <button
                onClick={onOpenSeparatorModal}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-slate-300 hover:bg-slate-800/60 hover:text-white transition ${
                  isCollapsed ? "justify-center" : ""
                }`}
                title={isCollapsed ? t("dashboard.ingest_separator") : undefined}
              >
                <Gauge className="w-4 h-4 shrink-0 text-cyan-400" />
                {!isCollapsed && <span className="truncate">{t("dashboard.ingest_separator")}</span>}
              </button>

              <button
                onClick={onOpenConfigModal}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-slate-300 hover:bg-slate-800/60 hover:text-white transition ${
                  isCollapsed ? "justify-center" : ""
                }`}
                title={isCollapsed ? t("dashboard.configure_well") : undefined}
              >
                <Sliders className="w-4 h-4 shrink-0 text-amber-400" />
                {!isCollapsed && <span className="truncate">{t("dashboard.configure_well")}</span>}
              </button>

              <button
                onClick={onOpenWellManagement}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-slate-300 hover:bg-slate-800/60 hover:text-white transition ${
                  isCollapsed ? "justify-center" : "justify-between"
                }`}
                title={isCollapsed ? t("header.manage_wells_btn", { count: wells.length }) : undefined}
              >
                <div className="flex items-center gap-3 truncate">
                  <Layers className="w-4 h-4 shrink-0 text-purple-400" />
                  {!isCollapsed && (
                    <span className="truncate">
                      {t("header.manage_wells_btn", { count: wells.length })}
                    </span>
                  )}
                </div>
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Footer: Supervisory Mode & Language Toggle */}
      <div className="p-3 border-t border-oilfield-700/60 space-y-2 bg-[#050912]">
        {/* Supervisory Mode Toggle */}
        <button
          onClick={onOpenSupervisoryModal}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[11px] font-bold border transition ${
            isSupervisoryActive
              ? "bg-amber-950/80 border-amber-500/60 text-amber-300 hover:bg-amber-900"
              : "bg-slate-900 border-slate-700/80 text-slate-300 hover:bg-slate-800"
          } ${isCollapsed ? "justify-center" : ""}`}
          title={
            isSupervisoryActive
              ? t("header.supervisory_write_mode")
              : t("header.read_only_boundary")
          }
        >
          {isSupervisoryActive ? (
            <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0" />
          ) : (
            <ShieldCheck className="w-4 h-4 text-cyan-400 shrink-0" />
          )}
          {!isCollapsed && (
            <span className="truncate">
              {isSupervisoryActive ? "SUPERVISORY WRITE" : "READ-ONLY BOUNDARY"}
            </span>
          )}
        </button>

        {/* Language Switcher */}
        <button
          onClick={toggleLanguage}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold bg-[#0a1120] hover:bg-slate-800 text-cyan-300 border border-oilfield-700 transition ${
            isCollapsed ? "justify-center" : "justify-between"
          }`}
          title="Switch Language"
        >
          <div className="flex items-center gap-2.5">
            <Globe className="w-4 h-4 shrink-0 text-cyan-400" />
            {!isCollapsed && <span>{t("header.lang_toggle")}</span>}
          </div>
          {!isCollapsed && (
            <span className="text-[10px] font-mono text-slate-400 uppercase">
              {language === "en" ? "EN" : "AR"}
            </span>
          )}
        </button>
      </div>
    </aside>
  );
}