"use client";

import React from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import {
  Menu,
  Activity,
  RefreshCw,
  Clock,
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
  const { wells, selectedWellCode, setSelectedWellCode, selectedWell } = useWell();

  return (
    <header className="h-14 border-b border-oilfield-700/60 bg-[#070c17]/95 backdrop-blur-md sticky top-0 z-40 text-white font-cairo px-4 lg:px-6 flex items-center justify-between">
      {/* Left / Start: Mobile Menu Toggle & Active Well Selector */}
      <div className="flex items-center gap-3">
        {onToggleSidebar && (
          <button
            onClick={onToggleSidebar}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition md:hidden"
            title="Toggle Menu"
          >
            <Menu className="w-5 h-5" />
          </button>
        )}

        {/* Well Selector Pill */}
        <div className="flex items-center gap-2 bg-[#0c1527] border border-oilfield-600 hover:border-cyan-500/60 transition rounded-xl px-3 py-1.5 shadow-sm">
          <Activity className="w-4 h-4 text-cyan-400 shrink-0" />
          <span className="text-xs text-slate-400 font-semibold hidden sm:inline">
            {t("dashboard.well_code")}:
          </span>
          <select
            value={selectedWellCode}
            onChange={(e) => setSelectedWellCode(e.target.value)}
            className="bg-transparent text-xs font-bold text-white focus:outline-none cursor-pointer font-mono"
          >
            {wells && wells.length > 0 ? (
              wells.map((w) => (
                <option key={w.well_code} value={w.well_code} className="bg-[#0b1322] text-white">
                  {w.well_code} ({w.field_name})
                </option>
              ))
            ) : (
              <option value={selectedWellCode} className="bg-[#0b1322] text-white">
                {selectedWellCode}
              </option>
            )}
          </select>
        </div>

        {selectedWell && (
          <span className="hidden sm:inline-block px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-slate-800 text-cyan-300 border border-slate-700">
            {selectedWell.field_name}
          </span>
        )}
      </div>

      {/* Right / End: Live Telemetry Indicator & Refresh Action */}
      <div className="flex items-center gap-3">
        {/* Telemetry Live Badge */}
        <div className="flex items-center gap-2 px-2.5 py-1 rounded-full bg-[#0b1322] border border-oilfield-700/60 text-xs">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
          <span className="font-mono text-emerald-400 font-semibold text-[11px]">
            {t("header.telemetry_live")}
          </span>
        </div>

        {/* Quick Refresh */}
        {onRefresh && (
          <button
            onClick={onRefresh}
            disabled={isFetching}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-oilfield-700 hover:bg-oilfield-600 text-white border border-oilfield-600 text-xs font-semibold transition disabled:opacity-50"
            title="Poll API telemetry"
          >
            <RefreshCw className={`w-3.5 h-3.5 text-cyan-400 ${isFetching ? "animate-spin" : ""}`} />
            <span className="hidden sm:inline">{t("dashboard.refresh_now")}</span>
          </button>
        )}
      </div>
    </header>
  );
}