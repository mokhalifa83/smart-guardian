"use client";

import React, { useState, useEffect } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import { fetchFieldControlMode } from "@/lib/api";
import {
  Shield,
  ShieldAlert,
  ShieldCheck,
  Globe,
  Activity,
  Database,
  Sliders,
  Layers,
  Plus,
} from "lucide-react";

interface HeaderProps {
  onOpenManualModal: () => void;
  onOpenSeparatorModal: () => void;
  onOpenConfigModal: () => void;
  onOpenWellManagement: () => void;
  onOpenSupervisoryModal: () => void;
}

export function Header({
  onOpenManualModal,
  onOpenSeparatorModal,
  onOpenConfigModal,
  onOpenWellManagement,
  onOpenSupervisoryModal,
}: HeaderProps) {
  const { language, toggleLanguage, t } = useLanguage();
  const { wells, selectedWellCode, setSelectedWellCode } = useWell();

  const [isSupervisoryActive, setIsSupervisoryActive] = useState(false);

  useEffect(() => {
    fetchFieldControlMode()
      .then((res) => setIsSupervisoryActive(res.enabled))
      .catch(() => {});
  }, []);

  return (
    <header className="border-b border-oilfield-700/80 bg-[#070c16]/95 backdrop-blur-md sticky top-0 z-40 text-white font-cairo">
      {/* Top Banner: Industrial Mode & Live Heartbeat */}
      <div className="bg-[#0b1322] border-b border-oilfield-700/60 px-4 py-1.5 flex items-center justify-between text-xs">
        <div className="flex items-center gap-3">
          {/* Mode Indicator & Switcher Button */}
          <button
            onClick={onOpenSupervisoryModal}
            className={`flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold border transition ${
              isSupervisoryActive
                ? "bg-amber-950/80 border-amber-500/60 text-amber-300 hover:bg-amber-900 shadow-sm shadow-amber-500/20 animate-pulse"
                : "bg-cyan-950/80 border-cyan-500/50 text-cyan-300 hover:bg-cyan-900 shadow-sm shadow-cyan-500/20"
            }`}
            title="Click to toggle between Read-Only and Supervisory Write Mode"
          >
            {isSupervisoryActive ? (
              <>
                <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                <span>SUPERVISORY WRITE MODE (FULL FUNCTION)</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                <span>READ-ONLY SURVEILLANCE BOUNDARY (CLICK TO UNLOCK)</span>
              </>
            )}
          </button>

          <span className="hidden lg:inline text-slate-400 text-[11px]">
            • {t("phase_notice") || "Digital Oilfield & Reservoir Intelligence Layer (SPE-PRMS Standard)"}
          </span>
        </div>

        <div className="flex items-center gap-2.5 text-slate-300 text-[11px]">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400 animate-pulse shadow-sm shadow-emerald-400/50"></span>
          <span className="font-mono text-emerald-400">TELEMETRY LIVE</span>
        </div>
      </div>

      {/* Main Bar */}
      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-400 via-blue-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-cyan-500/25">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-xl font-black tracking-tight text-white">
                {t("app_name")}
              </h1>
              <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-800">
                PROD v2.0
              </span>
            </div>
            <p className="text-xs text-slate-400 font-medium">{t("app_tagline")}</p>
          </div>
        </div>

        {/* Well Selector & Actions */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Well Select Dropdown */}
          <div className="flex items-center gap-2 bg-[#0e1728] border border-oilfield-600 hover:border-cyan-500/60 transition rounded-xl px-3 py-1.5 shadow-sm">
            <Activity className="w-4 h-4 text-cyan-400" />
            <label className="text-xs text-slate-400 font-semibold">
              {t("dashboard.well_code")}:
            </label>
            <select
              value={selectedWellCode}
              onChange={(e) => setSelectedWellCode(e.target.value)}
              className="bg-transparent text-sm font-bold text-white focus:outline-none cursor-pointer font-mono"
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

          {/* Manage Wells / Add Well Button */}
          <button
            onClick={onOpenWellManagement}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-md shadow-cyan-600/20 transition"
            title="Manage all wells: Add new, rename, configure thresholds, or delete"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Manage Wells ({wells.length})</span>
          </button>

          {/* Action Modals */}
          <button
            onClick={onOpenManualModal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-[#0f1b2f] hover:bg-[#14243e] text-slate-200 border border-oilfield-600 transition"
          >
            <Database className="w-3.5 h-3.5 text-emerald-400" />
            <span>{t("dashboard.ingest_manual")}</span>
          </button>

          <button
            onClick={onOpenSeparatorModal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-[#0f1b2f] hover:bg-[#14243e] text-slate-200 border border-oilfield-600 transition"
          >
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span>{t("dashboard.ingest_separator")}</span>
          </button>

          <button
            onClick={onOpenConfigModal}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-[#0f1b2f] hover:bg-[#14243e] text-slate-200 border border-oilfield-600 transition"
          >
            <Sliders className="w-3.5 h-3.5 text-amber-400" />
            <span>{t("dashboard.configure_well")}</span>
          </button>

          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-[#0e1728] hover:bg-oilfield-700 text-cyan-300 border border-cyan-800/80 transition shadow-sm"
            title="Toggle Arabic / English & RTL / LTR"
          >
            <Globe className="w-3.5 h-3.5" />
            <span>{language === "en" ? "العربية (Cairo)" : "English (Cairo)"}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
