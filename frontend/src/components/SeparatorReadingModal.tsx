"use client";

import React, { useState } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import { ingestSeparatorReading } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Activity, Send, PlusCircle } from "lucide-react";

interface SeparatorReadingModalProps {
  isOpen: boolean;
  onClose: () => void;
  wellCode: string;
}

export function SeparatorReadingModal({ isOpen, onClose, wellCode: initialWellCode }: SeparatorReadingModalProps) {
  const { t } = useLanguage();
  const { wells, addWell, setSelectedWellCode } = useWell();
  const queryClient = useQueryClient();

  const [activeWell, setActiveWell] = useState<string>(initialWellCode || (wells[0]?.well_code ?? "WELL-001"));
  const [isCustomWell, setIsCustomWell] = useState<boolean>(false);
  const [customWellCode, setCustomWellCode] = useState<string>("");
  const [customFieldName, setCustomFieldName] = useState<string>("North Field");

  const [pressure, setPressure] = useState<string>("385.0");
  const [flowRate, setFlowRate] = useState<string>("2400.0");
  const [waterCut, setWaterCut] = useState<string>("82.5");
  const [wcUnit, setWcUnit] = useState<"%" | "fraction">("%");
  const [oilRate, setOilRate] = useState<string>("420.0");
  const [waterRate, setWaterRate] = useState<string>("1980.0");
  const [gasRate, setGasRate] = useState<string>("650.0");
  const [isUnavailable, setIsUnavailable] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: async () => {
      setErrorMessage(null);
      let targetCode = activeWell;

      if (isCustomWell) {
        if (!customWellCode.trim()) {
          throw new Error("Please enter a valid well code.");
        }
        targetCode = customWellCode.trim().toUpperCase();
        const exists = wells.some((w) => w.well_code === targetCode);
        if (!exists) {
          await addWell({
            well_code: targetCode,
            field_name: customFieldName.trim() || "Field Production",
            status: "ACTIVE",
          });
        }
      }

      await ingestSeparatorReading({
        well_code: targetCode,
        timestamp: new Date().toISOString(),
        pressure: isUnavailable ? null : parseFloat(pressure),
        flow_rate: isUnavailable ? null : parseFloat(flowRate),
        water_cut: isUnavailable ? null : parseFloat(waterCut),
        wc_unit: wcUnit,
        oil_rate: isUnavailable ? null : parseFloat(oilRate),
        water_rate: isUnavailable ? null : parseFloat(waterRate),
        gas_rate: isUnavailable ? null : parseFloat(gasRate),
        source: "SOFTWARE_API",
        is_data_unavailable: isUnavailable,
      });

      setSelectedWellCode(targetCode);
      return targetCode;
    },
    onSuccess: (targetCode) => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", targetCode] });
      queryClient.invalidateQueries({ queryKey: ["readings", targetCode] });
      queryClient.invalidateQueries({ queryKey: ["wells"] });
      onClose();
    },
    onError: (err: any) => {
      setErrorMessage(err.message || "Separator telemetry ingestion failed");
    },
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-xl rounded-2xl border border-cyan-500/30 bg-[#0b1322] shadow-2xl p-6 text-white max-h-[90vh] overflow-y-auto font-cairo">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-oilfield-700">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-cyan-500/20 border border-cyan-500/40 flex items-center justify-center">
              <Activity className="w-4 h-4 text-cyan-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">
                {t("modal.separator_title")}
              </h2>
              <p className="text-xs text-slate-400">
                Multi-phase test separator telemetry stream
              </p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        {errorMessage && (
          <div className="p-3 my-3 text-xs bg-rose-950/80 border border-rose-700 rounded-lg text-rose-200">
            {errorMessage}
          </div>
        )}

        {/* Well Asset Selector */}
        <div className="p-3 bg-[#0e192e] border border-oilfield-600 rounded-xl space-y-2 my-4">
          <div className="flex items-center justify-between text-xs">
            <label className="font-semibold text-cyan-300">Target Well Asset</label>
            <button
              type="button"
              onClick={() => setIsCustomWell(!isCustomWell)}
              className="text-[11px] text-cyan-400 hover:underline flex items-center gap-1"
            >
              <PlusCircle className="w-3 h-3" />
              <span>{isCustomWell ? "Pick Existing Well" : "+ Enter New Well Code"}</span>
            </button>
          </div>

          {isCustomWell ? (
            <div className="grid grid-cols-2 gap-2 pt-1">
              <div>
                <input
                  type="text"
                  value={customWellCode}
                  onChange={(e) => setCustomWellCode(e.target.value)}
                  placeholder="New Well Code (e.g. WELL-004)"
                  className="w-full bg-[#070c16] border border-cyan-500/50 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none font-mono"
                  required
                />
              </div>
              <div>
                <input
                  type="text"
                  value={customFieldName}
                  onChange={(e) => setCustomFieldName(e.target.value)}
                  placeholder="Field Name"
                  className="w-full bg-[#070c16] border border-oilfield-600 rounded-lg px-2.5 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none"
                />
              </div>
            </div>
          ) : (
            <select
              value={activeWell}
              onChange={(e) => setActiveWell(e.target.value)}
              className="w-full bg-[#070c16] border border-oilfield-600 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-400 cursor-pointer font-mono"
            >
              {wells.map((w) => (
                <option key={w.well_code} value={w.well_code}>
                  {w.well_code} ({w.field_name})
                </option>
              ))}
            </select>
          )}
        </div>

        {/* Explicit DATA_UNAVAILABLE checkbox */}
        <div className="flex items-center gap-2 bg-oilfield-800/80 border border-oilfield-700 p-3 rounded-lg mb-4">
          <input
            type="checkbox"
            id="sep-unavail"
            checked={isUnavailable}
            onChange={(e) => setIsUnavailable(e.target.checked)}
            className="w-4 h-4 rounded text-cyan-500 focus:ring-0 cursor-pointer"
          />
          <label htmlFor="sep-unavail" className="text-xs text-slate-300 cursor-pointer select-none">
            {t("modal.mark_unavailable")} (Sensor disconnected / Maintenance offline)
          </label>
        </div>

        {!isUnavailable && (
          <div className="space-y-3.5 mb-4">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Water Cut Value
                </label>
                <input
                  type="number"
                  step="0.01"
                  value={waterCut}
                  onChange={(e) => setWaterCut(e.target.value)}
                  className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Water Cut Unit
                </label>
                <select
                  value={wcUnit}
                  onChange={(e) => setWcUnit(e.target.value as any)}
                  className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-400 cursor-pointer"
                >
                  <option value="%">Percentage (%) [0 - 100]</option>
                  <option value="fraction">Fraction (0.0 - 1.0)</option>
                </select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Pressure (psi)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={pressure}
                  onChange={(e) => setPressure(e.target.value)}
                  className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Gross Liquid Rate (BPD)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={flowRate}
                  onChange={(e) => setFlowRate(e.target.value)}
                  className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Oil Rate (STB/D)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={oilRate}
                  onChange={(e) => setOilRate(e.target.value)}
                  className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Water Rate (BPD)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={waterRate}
                  onChange={(e) => setWaterRate(e.target.value)}
                  className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Gas Rate (Mscf/D)
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={gasRate}
                  onChange={(e) => setGasRate(e.target.value)}
                  className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-1.5 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
            </div>
          </div>
        )}

        {/* Buttons */}
        <div className="flex items-center justify-end gap-3 pt-4 border-t border-oilfield-700">
          <button
            onClick={onClose}
            className="px-4 py-2 text-xs font-semibold rounded-lg bg-oilfield-800 hover:bg-oilfield-700 text-slate-300 border border-oilfield-700 transition"
          >
            {t("modal.cancel")}
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black transition shadow-lg shadow-cyan-500/25 disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{mutation.isPending ? t("modal.submitting") : t("modal.submit")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
