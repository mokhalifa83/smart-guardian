"use client";

import React from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import { useTheme } from "@/context/ThemeContext";
import {
  Menu,
  Activity,
  RefreshCw,
  Sun,
  Moon,
} from "lucide-react";

interface HeaderProps {
  onToggleSidebar?: () => void;
  onRefresh?: () => void;
  isFetching?: boolean;
}

export function Header({
  onToggleSidebar,
  onRefresh,
  isFetching = false,
}: HeaderProps) {
  const { t } = useLanguage();
  const { theme, toggleTheme } = useTheme();
  const { wells, selectedWellCode, setSelectedWellCode, selectedWell } = useWell();

  return (
    <header className="h-14 border-b border-slate-200 dark:border-slate-800 bg-white/95 dark:bg-[#0f172a]/95 backdrop-blur-md sticky top-0 z-40 text-slate-800 dark:text-white font-cairo px-4 lg:px-6 flex items-center justify-between shadow-sm">
      {/* Left / Start: Mobile Menu Toggle & Active Well Selector */}
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition md:hidden"
            title="Toggle Menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Well Selector Pill */}
        <div className="flex items-center gap-2 bg-slate-50 dark:bg-[#0c1527] border border-slate-200 dark:border-slate-700 hover:border-blue-400 dark:hover:border-cyan-500/60 transition rounded-xl px-3 py-1.5 shadow-sm">
          <Activity className="w-4 h-4 text-blue-600 dark:text-cyan-400 shrink-0" />
          <span className="text-xs text-slate-500 dark:text-slate-400 font-semibold hidden sm:inline">
            {t("dashboard.well_code")}:
          </span>
          <select
            value={selectedWellCode}
            onChange={(e) => setSelectedWellCode(e.target.value)}
            className="bg-transparent text-xs font-bold text-slate-800 dark:text-white focus:outline-none cursor-pointer font-mono"
          >
            {wells && wells.length > 0 ? (
              wells.map((w) => (
                <option key={w.well_code} value={w.well_code} className="bg-white dark:bg-[#0b1322] text-slate-900 dark:text-white">
                  {w.well_code} ({w.field_name})
                </option>
              ))
            ) : (
              <option value={selectedWellCode} className="bg-white dark:bg-[#0b1322] text-slate-900 dark:text-white">
                {selectedWellCode}
              </option>
            )}
          </select>
        </div>

        {selectedWell && (
          <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-100 dark:bg-slate-800 text-blue-800 dark:text-cyan-300 border border-slate-200 dark:border-slate-700">
            {selectedWell.field_name}
          </span>
        )}
      </div>

      {/* Right / End: Live Telemetry, Theme Toggle, & Refresh */}
      <div className="flex items-center gap-2.5">
        {/* Telemetry Live Badge */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/60 text-xs">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400"></span>
          <span className="font-mono text-emerald-800 dark:text-emerald-400 font-semibold text-[11px]">
            {t("header.telemetry_live")}
          </span>
        </div>

        {/* Header Theme Switcher Icon */}
        <button
          onClick={toggleTheme}
          className="p-1.5 rounded-xl text-slate-600 dark:text-slate-300 bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 border border-slate-200 dark:border-slate-700 transition shadow-sm"
          title={theme === "light" ? "Switch to Dark Executive Slate" : "Switch to Executive Light Theme"}
        >
          {theme === "light" ? (
            <Moon className="w-4 h-4 text-indigo-700" />
          ) : (
            <Sun className="w-4 h-4 text-amber-400" />
          )}
        </button>

        {/* Quick Refresh */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-blue-700 hover:bg-blue-600 dark:bg-slate-800 dark:hover:bg-slate-700 text-white dark:text-slate-200 border border-blue-600 dark:border-slate-700 text-xs font-semibold transition disabled:opacity-50 shadow-sm"
            title="Poll API telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-blue-200 dark:text-cyan-400 ${isFetching ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">{t("dashboard.refresh_now")}</span>
          </button>
        )}
      </div>
    </header>
  );
}