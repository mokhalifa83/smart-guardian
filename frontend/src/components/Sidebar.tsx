"use client";

import React, { useState, useEffect } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import { useTheme } from "@/context/ThemeContext";
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
  Sun,
  Moon,
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
  const { theme, toggleTheme } = useTheme();
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
      icon: <Activity className="w-4 h-4 shrink-0 text-blue-600 dark:text-cyan-400" />,
      badge: null,
    },
    {
      id: "field_overview" as DashboardViewType,
      label: t("sidebar.field_overview"),
      icon: <LayoutDashboard className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />,
      badge: null,
    },
    {
      id: "engines" as DashboardViewType,
      label: t("sidebar.engines_hub"),
      icon: <Cpu className="w-4 h-4 shrink-0 text-indigo-600 dark:text-indigo-400" />,
      badge: "36",
    },
    {
      id: "reports" as DashboardViewType,
      label: t("sidebar.reports"),
      icon: <FileText className="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />,
      badge: null,
    },
  ];

  return (
    <aside
      className={`fixed top-0 bottom-0 z-50 flex flex-col justify-between bg-white dark:bg-[#0f172a] text-slate-800 dark:text-slate-200 transition-all duration-300 ease-in-out border-slate-200 dark:border-slate-800 shadow-sm ${
        direction === "rtl" ? "right-0 border-l" : "left-0 border-r"
      } ${isCollapsed ? "w-20" : "w-64"}`}
    >
      {/* Top Header: Brand & Collapse Toggle */}
      <div>
        <div className="h-14 px-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-800">
          {!isCollapsed && (
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-700 to-indigo-900 dark:from-cyan-500 dark:to-blue-700 flex items-center justify-center shadow-sm shrink-0">
                <Shield className="w-4 h-4 text-white" />
              </div>
              <div className="truncate">
                <div className="flex items-center gap-1.5">
                  <h1 className="text-xs font-black tracking-tight text-slate-900 dark:text-white truncate">
                    {t("app_name")}
                  </h1>
                  <span className="px-1.5 py-0.2 rounded text-[9px] font-mono font-bold bg-slate-100 dark:bg-slate-800 text-blue-700 dark:text-cyan-300 border border-slate-300 dark:border-slate-700">
                    v2.5
                  </span>
                </div>
                <p className="text-[10px] text-slate-500 dark:text-slate-400 truncate font-medium">SPE-PRMS Standard</p>
              </div>
            </div>
          )}

          {isCollapsed && (
            <div className="mx-auto w-8 h-8 rounded-lg bg-gradient-to-br from-blue-700 to-indigo-900 dark:from-cyan-500 dark:to-blue-700 flex items-center justify-center shadow-sm">
              <Shield className="w-4 h-4 text-white" />
            </div>
          )}

          <button
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition"
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
        <div className="p-3 space-y-5 overflow-y-auto max-h-[calc(100vh-250px)]">
          {/* Main Views */}
          <div>
            {!isCollapsed && (
              <span className="px-3 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-2">
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
                    className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs font-semibold transition ${
                      isActive
                        ? "bg-blue-50 text-blue-800 border border-blue-200 dark:bg-slate-800/90 dark:text-cyan-300 dark:border-slate-700 shadow-sm"
                        : "text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-white border border-transparent"
                    } ${isCollapsed ? "justify-center" : "justify-between"}`}
                    title={isCollapsed ? item.label : undefined}
                  >
                    <div className="flex items-center gap-3 truncate">
                      {item.icon}
                      {!isCollapsed && <span className="truncate">{item.label}</span>}
                    </div>
                    {!isCollapsed && item.badge && (
                      <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-indigo-100 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                        {item.badge}
                      </span>
                    )}
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Field Operations & Actions */}
          <div className="pt-2 border-t border-slate-200 dark:border-slate-800">
            {!isCollapsed && (
              <span className="px-3 text-[10px] font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider block mb-2">
                {t("sidebar.field_operations")}
              </span>
            )}
            <div className="space-y-1">
              <button
                onClick={onOpenManualModal}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-white transition ${
                  isCollapsed ? "justify-center" : ""
                }`}
                title={isCollapsed ? t("dashboard.ingest_manual") : undefined}
              >
                <Database className="w-4 h-4 shrink-0 text-emerald-600 dark:text-emerald-400" />
                {!isCollapsed && <span className="truncate">{t("dashboard.ingest_manual")}</span>}
              </button>

              <button
                onClick={onOpenSeparatorModal}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-white transition ${
                  isCollapsed ? "justify-center" : ""
                }`}
                title={isCollapsed ? t("dashboard.ingest_separator") : undefined}
              >
                <Gauge className="w-4 h-4 shrink-0 text-blue-600 dark:text-cyan-400" />
                {!isCollapsed && <span className="truncate">{t("dashboard.ingest_separator")}</span>}
              </button>

              <button
                onClick={onOpenConfigModal}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-white transition ${
                  isCollapsed ? "justify-center" : ""
                }`}
                title={isCollapsed ? t("dashboard.configure_well") : undefined}
              >
                <Sliders className="w-4 h-4 shrink-0 text-amber-600 dark:text-amber-400" />
                {!isCollapsed && <span className="truncate">{t("dashboard.configure_well")}</span>}
              </button>

              <button
                onClick={onOpenWellManagement}
                className={`w-full flex items-center gap-3 px-3 py-2 rounded-xl text-xs text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800/60 hover:text-slate-900 dark:hover:text-white transition ${
                  isCollapsed ? "justify-center" : "justify-between"
                }`}
                title={isCollapsed ? t("header.manage_wells_btn", { count: wells.length }) : undefined}
              >
                <div className="flex items-center gap-3 truncate">
                  <Layers className="w-4 h-4 shrink-0 text-purple-600 dark:text-purple-400" />
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

      {/* Bottom Footer: Theme Switcher, Supervisory Mode, & Language Toggle */}
      <div className="p-3 border-t border-slate-200 dark:border-slate-800 space-y-2 bg-slate-50 dark:bg-[#0b1322]">
        {/* Theme Switcher Button */}
        <button
          onClick={toggleTheme}
          className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs font-semibold bg-white dark:bg-slate-800/90 text-slate-700 dark:text-slate-200 border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 transition ${
            isCollapsed ? "justify-center" : "justify-between"
          }`}
          title={theme === "light" ? "Switch to Dark Executive Slate" : "Switch to Executive Light Theme"}
        >
          <div className="flex items-center gap-2.5">
            {theme === "light" ? (
              <Moon className="w-4 h-4 text-indigo-600 shrink-0" />
            ) : (
              <Sun className="w-4 h-4 text-amber-400 shrink-0" />
            )}
            {!isCollapsed && (
              <span>{theme === "light" ? "Dark Executive" : "Executive Light"}</span>
            )}
          </div>
          {!isCollapsed && (
            <span className="text-[10px] font-mono text-slate-400 uppercase">
              {theme}
            </span>
          )}
        </button>

        {/* Supervisory Mode Toggle */}
        <button
          onClick={onOpenSupervisoryModal}
          className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-[11px] font-bold border transition ${
            isSupervisoryActive
              ? "bg-amber-100 dark:bg-amber-950/80 border-amber-300 dark:border-amber-500/60 text-amber-900 dark:text-amber-300"
              : "bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-700/80 text-slate-700 dark:text-slate-300"
          } ${isCollapsed ? "justify-center" : ""}`}
          title={
            isSupervisoryActive
              ? t("header.supervisory_write_mode")
              : t("header.read_only_boundary")
          }
        >
          {isSupervisoryActive ? (
            <ShieldAlert className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" />
          ) : (
            <ShieldCheck className="w-4 h-4 text-blue-600 dark:text-cyan-400 shrink-0" />
          )}
          {!isCollapsed && (
            <span className="truncate">
              {isSupervisoryActive ? "SUPERVISORY MODE" : "READ-ONLY BOUNDARY"}
            </span>
          )}
        </button>

        {/* Language Switcher */}
        <button
          onClick={toggleLanguage}
          className={`w-full flex items-center gap-2.5 px-3 py-1.5 rounded-xl text-xs font-semibold bg-white dark:bg-slate-800 text-slate-700 dark:text-cyan-300 border border-slate-200 dark:border-slate-700 hover:bg-slate-100 dark:hover:bg-slate-700 transition ${
            isCollapsed ? "justify-center" : "justify-between"
          }`}
          title="Switch Language"
        >
          <div className="flex items-center gap-2.5">
            <Globe className="w-4 h-4 shrink-0 text-blue-600 dark:text-cyan-400" />
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