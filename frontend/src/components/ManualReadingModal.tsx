"use client";

import React, { useState } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import { ingestManualReading } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Database, Send, PlusCircle } from "lucide-react";

interface ManualReadingModalProps {
  isOpen: boolean;
  onClose: () => void;
  wellCode: string;
}

export function ManualReadingModal({ isOpen, onClose, wellCode: initialWellCode }: ManualReadingModalProps) {
  const { t } = useLanguage();
  const { wells, addWell, setSelectedWellCode } = useWell();
  const queryClient = useQueryClient();

  const [activeWell, setActiveWell] = useState<string>(initialWellCode || (wells[0]?.well_code ?? "WELL-001"));
  const [isCustomWell, setIsCustomWell] = useState<boolean>(false);
  const [customWellCode, setCustomWellCode] = useState<string>("");
  const [customFieldName, setCustomFieldName] = useState<string>("Field Alpha");

  const [measurementType, setMeasurementType] = useState<"WATER_CUT" | "OIL_API_GRAVITY" | "SEPARATOR_PRESSURE">("WATER_CUT");
  const [value, setValue] = useState<string>("75.0");
  const [unit, setUnit] = useState<string>("%");
  const [enteredBy, setEnteredBy] = useState<string>("Eng. Tariq Al-Mansoor");
  const [isUnavailable, setIsUnavailable] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleTypeChange = (newType: "WATER_CUT" | "OIL_API_GRAVITY" | "SEPARATOR_PRESSURE") => {
    setMeasurementType(newType);
    if (newType === "WATER_CUT") {
      setUnit("%");
      setValue("75.0");
    } else if (newType === "OIL_API_GRAVITY") {
      setUnit("°API");
      setValue("33.5");
    } else if (newType === "SEPARATOR_PRESSURE") {
      setUnit("psi");
      setValue("450.0");
    }
  };

  const mutation = useMutation({
    mutationFn: async () => {
      setErrorMessage(null);
      let targetCode = activeWell;

      if (isCustomWell) {
        if (!customWellCode.trim()) {
          throw new Error("Please provide a valid custom well code.");
        }
        targetCode = customWellCode.trim().toUpperCase();
        // Check if exists, else create
        const exists = wells.some((w) => w.well_code === targetCode);
        if (!exists) {
          await addWell({
            well_code: targetCode,
            field_name: customFieldName.trim() || "Main Field",
            status: "ACTIVE",
          });
        }
      }

      await ingestManualReading({
        well_code: targetCode,
        measurement_type: measurementType,
        value: isUnavailable ? null : parseFloat(value),
        unit: unit,
        timestamp: new Date().toISOString(),
        entered_by: enteredBy,
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
      setErrorMessage(err.message || "Failed to ingest manual reading");
    },
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 animate-in fade-in duration-150">
      <div className="w-full max-w-lg rounded-2xl border border-cyan-500/30 bg-[#0b1322] shadow-2xl p-6 text-white font-cairo">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-oilfield-700">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/20 border border-emerald-500/40 flex items-center justify-center">
              <Database className="w-4 h-4 text-emerald-400" />
            </div>
            <div>
              <h2 className="text-base font-bold text-white">
                {t("modal.manual_title")}
              </h2>
              <p className="text-xs text-slate-400">
                Enter validated field data points for any monitored or new well
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

        {/* Form Fields */}
        <div className="space-y-4 my-4">
          {/* Well Selection / Custom Input */}
          <div className="p-3 bg-[#0e192e] border border-oilfield-600 rounded-xl space-y-2">
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
                    placeholder="New Well Code (e.g. WELL-003)"
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

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              {t("modal.measurement_type")}
            </label>
            <select
              value={measurementType}
              onChange={(e) => handleTypeChange(e.target.value as any)}
              className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400 font-medium cursor-pointer"
            >
              <option value="WATER_CUT">{t("kpi.water_cut")} (%)</option>
              <option value="OIL_API_GRAVITY">Oil API Gravity (°API)</option>
              <option value="SEPARATOR_PRESSURE">{t("kpi.pressure")} (psi)</option>
            </select>
          </div>

          {/* Explicit DATA_UNAVAILABLE checkbox */}
          <div className="flex items-center gap-2 bg-oilfield-800/80 border border-oilfield-700 p-3 rounded-lg">
            <input
              type="checkbox"
              id="unavail"
              checked={isUnavailable}
              onChange={(e) => setIsUnavailable(e.target.checked)}
              className="w-4 h-4 rounded text-cyan-500 focus:ring-0 cursor-pointer"
            />
            <label htmlFor="unavail" className="text-xs text-slate-300 cursor-pointer select-none">
              {t("modal.mark_unavailable")} (Record genuine missing telemetry without fake values)
            </label>
          </div>

          {!isUnavailable && (
            <div className="grid grid-cols-3 gap-3">
              <div className="col-span-2">
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  {t("modal.value")}
                </label>
                <input
                  type="number"
                  step="0.1"
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  {t("modal.unit")}
                </label>
                <input
                  type="text"
                  value={unit}
                  onChange={(e) => setUnit(e.target.value)}
                  className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
                />
              </div>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              {t("modal.entered_by")}
            </label>
            <input
              type="text"
              value={enteredBy}
              onChange={(e) => setEnteredBy(e.target.value)}
              className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400"
            />
          </div>
        </div>

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
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black transition shadow-lg shadow-emerald-500/25 disabled:opacity-50"
          >
            <Send className="w-3.5 h-3.5" />
            <span>{mutation.isPending ? t("modal.submitting") : t("modal.submit")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
