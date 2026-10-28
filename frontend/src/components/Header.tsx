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
    <header className="border-b border-zinc-800 bg-[#09090b]/98 backdrop-blur-md sticky top-0 z-40 text-white font-cairo shadow-lg shadow-black/50">
      {/* Top Banner: Industrial Mode & Live Heartbeat */}
      <div className="bg-[#0e0e11] border-b border-zinc-800/80 px-6 py-2 flex items-center justify-between text-xs sm:text-sm">
        <div className="flex items-center gap-3">
          {/* Mode Indicator & Switcher Button */}
          <button
            onClick={onOpenSupervisoryModal}
            className={`flex items-center gap-2 px-3.5 py-1 rounded-full text-xs font-bold border transition ${
              isSupervisoryActive
                ? "bg-red-950/90 border-red-500/80 text-red-300 hover:bg-red-900 shadow-sm shadow-red-500/25 animate-pulse"
                : "bg-zinc-900 border-zinc-700 text-zinc-300 hover:bg-zinc-800"
            }`}
            title="Click to toggle between Read-Only and Supervisory Write Mode"
          >
            {isSupervisoryActive ? (
              <>
                <ShieldAlert className="w-4 h-4 text-red-400" />
                <span>SUPERVISORY WRITE MODE (ACTIVE)</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-4 h-4 text-red-500" />
                <span>READ-ONLY SURVEILLANCE BOUNDARY (CLICK TO UNLOCK)</span>
              </>
            )}
          </button>

          <span className="hidden lg:inline text-zinc-400 text-xs">
            • {t("phase_notice") || "Digital Oilfield & Reservoir Intelligence Layer (SPE-PRMS Standard)"}
          </span>
        </div>

        <div className="flex items-center gap-2.5 text-zinc-300 text-xs sm:text-sm font-semibold">
          <span className="inline-block w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse shadow-sm shadow-red-500/60"></span>
          <span className="font-mono text-red-400 tracking-wide">TELEMETRY LIVE</span>
        </div>
      </div>

      {/* Main Bar */}
      <div className="max-w-7xl mx-auto px-6 py-4 flex flex-wrap items-center justify-between gap-5">
        {/* Brand */}
        <div className="flex items-center gap-3.5">
          <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-red-500 via-red-600 to-zinc-900 flex items-center justify-center shadow-lg shadow-red-600/30 border border-red-400/40">
            <Shield className="w-6 h-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-2xl font-black tracking-tight text-white">
                {t("app_name")}
              </h1>
              <span className="px-2.5 py-0.5 rounded-md text-xs font-mono font-black bg-red-950 text-red-300 border border-red-800/80">
                PROD v2.0
              </span>
            </div>
            <p className="text-sm text-zinc-400 font-medium">{t("app_tagline")}</p>
          </div>
        </div>

        {/* Well Selector & Actions */}
        <div className="flex flex-wrap items-center gap-3">
          {/* Well Select Dropdown */}
          <div className="flex items-center gap-2.5 bg-zinc-900 border border-zinc-700 hover:border-red-500/80 transition rounded-xl px-4 py-2.5 shadow-sm">
            <Activity className="w-5 h-5 text-red-500" />
            <label className="text-xs text-zinc-400 font-bold uppercase tracking-wider">
              {t("dashboard.well_code")}:
            </label>
            <select
              value={selectedWellCode}
              onChange={(e) => setSelectedWellCode(e.target.value)}
              className="bg-transparent text-base font-black text-white focus:outline-none cursor-pointer font-mono"
            >
              {wells && wells.length > 0 ? (
                wells.map((w) => (
                  <option key={w.well_code} value={w.well_code} className="bg-zinc-950 text-white">
                    {w.well_code} ({w.field_name})
                  </option>
                ))
              ) : (
                <option value={selectedWellCode} className="bg-zinc-950 text-white">
                  {selectedWellCode}
                </option>
              )}
            </select>
          </div>

          {/* Manage Wells / Add Well Button */}
          <button
            onClick={onOpenWellManagement}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-bold rounded-xl bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white shadow-md shadow-red-700/25 transition border border-red-500/40"
            title="Manage all wells: Add new, rename, configure thresholds, or delete"
          >
            <Layers className="w-4 h-4" />
            <span>Manage Wells ({wells.length})</span>
          </button>

          {/* Action Modals */}
          <button
            onClick={onOpenManualModal}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-bold rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-100 border border-zinc-700 hover:border-zinc-500 transition shadow-sm"
          >
            <Database className="w-4 h-4 text-red-400" />
            <span>{t("dashboard.ingest_manual")}</span>
          </button>

          <button
            onClick={onOpenSeparatorModal}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-bold rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-100 border border-zinc-700 hover:border-zinc-500 transition shadow-sm"
          >
            <Activity className="w-4 h-4 text-red-400" />
            <span>{t("dashboard.ingest_separator")}</span>
          </button>

          <button
            onClick={onOpenConfigModal}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-bold rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-100 border border-zinc-700 hover:border-zinc-500 transition shadow-sm"
          >
            <Sliders className="w-4 h-4 text-zinc-300" />
            <span>{t("dashboard.configure_well")}</span>
          </button>

          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            className="flex items-center gap-2 px-4 py-2.5 text-sm font-bold rounded-xl bg-zinc-900 hover:bg-zinc-800 text-zinc-200 border border-zinc-700 transition shadow-sm"
            title="Toggle Arabic / English & RTL / LTR"
          >
            <Globe className="w-4 h-4 text-red-400" />
            <span>{language === "en" ? "العربية (Cairo)" : "English (Cairo)"}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
