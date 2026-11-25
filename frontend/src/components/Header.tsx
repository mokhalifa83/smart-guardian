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
  ChevronDown,
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
  const [isOperationsOpen, setIsOperationsOpen] = useState(false);

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
                ? "bg-amber-950/80 border-amber-500/60 text-amber-300 hover:bg-amber-900 shadow-sm"
                : "bg-slate-900/90 border-slate-700 text-slate-300 hover:bg-slate-800"
            }`}
            title="Toggle between Read-Only and Supervisory Write Mode"
          >
            {isSupervisoryActive ? (
              <>
                <ShieldAlert className="w-3.5 h-3.5 text-amber-400" />
                <span>{t("header.supervisory_write_mode")}</span>
              </>
            ) : (
              <>
                <ShieldCheck className="w-3.5 h-3.5 text-cyan-400" />
                <span>{t("header.read_only_boundary")}</span>
              </>
            )}
          </button>

          <span className="hidden lg:inline text-slate-400 text-[11px]">
            • {t("phase_notice")}
          </span>
        </div>

        <div className="flex items-center gap-2 text-slate-300 text-[11px]">
          <span className="inline-block w-2 h-2 rounded-full bg-emerald-400"></span>
          <span className="font-mono text-emerald-400 font-semibold">{t("header.telemetry_live")}</span>
        </div>
      </div>

      {/* Main Bar */}
      <div className="max-w-7xl mx-auto px-4 py-3 flex flex-wrap items-center justify-between gap-4">
        {/* Brand */}
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-700 flex items-center justify-center shadow-md shadow-cyan-900/40">
            <Shield className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-black tracking-tight text-white">
                {t("app_name")}
              </h1>
              <span className="px-1.5 py-0.5 rounded text-[10px] font-mono font-bold bg-slate-800 text-cyan-300 border border-slate-700">
                PROD v2.0
              </span>
            </div>
            <p className="text-[11px] text-slate-400 font-medium">{t("app_tagline")}</p>
          </div>
        </div>

        {/* Well Selector & Actions */}
        <div className="flex flex-wrap items-center gap-2">
          {/* Well Select Dropdown */}
          <div className="flex items-center gap-2 bg-[#0d1627] border border-oilfield-600 hover:border-cyan-500/60 transition rounded-xl px-3 py-1.5 shadow-sm">
            <Activity className="w-4 h-4 text-cyan-400" />
            <label className="text-xs text-slate-400 font-semibold">
              {t("dashboard.well_code")}:
            </label>
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

          {/* Manage Wells / Add Well Button */}
          <button
            onClick={onOpenWellManagement}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white shadow-sm transition"
            title="Manage all wells: Add new, rename, configure thresholds, or delete"
          >
            <Layers className="w-3.5 h-3.5" />
            <span>{t("header.manage_wells_btn", { count: wells.length })}</span>
          </button>

          {/* Field Operations Dropdown */}
          <div className="relative">
            <button
              onClick={() => setIsOperationsOpen(!isOperationsOpen)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-xl bg-[#0f1b2f] hover:bg-[#15243f] text-slate-200 border border-oilfield-600 transition"
              aria-expanded={isOperationsOpen}
            >
              <Database className="w-3.5 h-3.5 text-emerald-400" />
              <span>{t("header.operations_menu")}</span>
              <ChevronDown className={`w-3.5 h-3.5 text-slate-400 transition-transform ${isOperationsOpen ? "rotate-180" : ""}`} />
            </button>

            {isOperationsOpen && (
              <>
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setIsOperationsOpen(false)}
                />
                <div className="absolute right-0 rtl:right-auto rtl:left-0 mt-2 w-64 bg-[#0c1527] border border-oilfield-600 rounded-xl shadow-2xl z-50 py-1 divide-y divide-oilfield-700/60 animate-in fade-in zoom-in-95 duration-100">
                  <div className="px-3 py-1.5 text-[11px] font-bold text-slate-400 uppercase tracking-wider">
                    {t("header.operations_menu")}
                  </div>
                  <div className="py-1">
                    <button
                      onClick={() => {
                        setIsOperationsOpen(false);
                        onOpenManualModal();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-slate-200 hover:bg-[#16243d] hover:text-white transition text-start"
                    >
                      <Database className="w-4 h-4 text-emerald-400 shrink-0" />
                      <div>
                        <div className="font-semibold">{t("dashboard.ingest_manual")}</div>
                        <div className="text-[10px] text-slate-400">Shake-out water cut & wellhead gauge</div>
                      </div>
                    </button>

                    <button
                      onClick={() => {
                        setIsOperationsOpen(false);
                        onOpenSeparatorModal();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-slate-200 hover:bg-[#16243d] hover:text-white transition text-start"
                    >
                      <Activity className="w-4 h-4 text-cyan-400 shrink-0" />
                      <div>
                        <div className="font-semibold">{t("dashboard.ingest_separator")}</div>
                        <div className="text-[10px] text-slate-400">Multi-phase separator test telemetry</div>
                      </div>
                    </button>

                    <button
                      onClick={() => {
                        setIsOperationsOpen(false);
                        onOpenConfigModal();
                      }}
                      className="w-full flex items-center gap-2.5 px-3 py-2 text-xs text-slate-200 hover:bg-[#16243d] hover:text-white transition text-start"
                    >
                      <Sliders className="w-4 h-4 text-amber-400 shrink-0" />
                      <div>
                        <div className="font-semibold">{t("dashboard.configure_well")}</div>
                        <div className="text-[10px] text-slate-400">Alarm thresholds & cooldown limits</div>
                      </div>
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>

          {/* Language Toggle */}
          <button
            onClick={toggleLanguage}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl bg-[#0e1728] hover:bg-oilfield-700 text-cyan-300 border border-cyan-800/80 transition"
            title="Switch Language"
          >
            <Globe className="w-3.5 h-3.5" />
            <span>{t("header.lang_toggle")}</span>
          </button>
        </div>
      </div>
    </header>
  );
}
