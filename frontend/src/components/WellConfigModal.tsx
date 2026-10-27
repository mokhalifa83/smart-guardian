"use client";

import React, { useState, useEffect } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { fetchWellConfig, updateWellConfig } from "@/lib/api";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { X, Sliders, Check } from "lucide-react";

interface WellConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  wellCode: string;
}

export function WellConfigModal({ isOpen, onClose, wellCode }: WellConfigModalProps) {
  const { t } = useLanguage();
  const queryClient = useQueryClient();

  const { data: config } = useQuery({
    queryKey: ["well_config", wellCode],
    queryFn: () => fetchWellConfig(wellCode),
    enabled: isOpen,
  });

  const [wcThreshold, setWcThreshold] = useState<number>(80.0);
  const [cooldown, setCooldown] = useState<number>(60);
  const [trendWindow, setTrendWindow] = useState<number>(24);
  const [survInterval, setSurvInterval] = useState<number>(5);

  useEffect(() => {
    if (config) {
      setWcThreshold(config.wc_threshold);
      setCooldown(config.alert_cooldown_minutes);
      setTrendWindow(config.wc_trend_window_hours);
      setSurvInterval(config.surveillance_interval_minutes);
    }
  }, [config]);

  const mutation = useMutation({
    mutationFn: () =>
      updateWellConfig(wellCode, {
        wc_threshold: Number(wcThreshold),
        alert_cooldown_minutes: Number(cooldown),
        wc_trend_window_hours: Number(trendWindow),
        surveillance_interval_minutes: Number(survInterval),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["well_config", wellCode] });
      queryClient.invalidateQueries({ queryKey: ["dashboard", wellCode] });
      onClose();
    },
  });

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-lg rounded-2xl border border-oilfield-600 bg-oilfield-900 shadow-2xl p-6 text-white">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-oilfield-700">
          <div className="flex items-center gap-2">
            <Sliders className="w-5 h-5 text-amber-400" />
            <h2 className="text-base font-bold text-white">
              {t("modal.config_title")} ({wellCode})
            </h2>
          </div>
          <button onClick={onClose} className="p-1 rounded-lg text-slate-400 hover:text-white transition">
            <X className="w-5 h-5" />
          </button>
        </div>

        <p className="text-xs text-slate-400 my-3">{t("modal.config_desc")}</p>

        {/* Form Fields */}
        <div className="space-y-4 my-4">
          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              {t("modal.wc_threshold")}
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                step="0.5"
                min="0"
                max="100"
                value={wcThreshold}
                onChange={(e) => setWcThreshold(parseFloat(e.target.value) || 0)}
                className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-amber-400 font-mono"
              />
              <span className="text-sm font-semibold text-slate-400">%</span>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                {t("modal.alert_cooldown")}
              </label>
              <input
                type="number"
                min="1"
                max="1440"
                value={cooldown}
                onChange={(e) => setCooldown(parseInt(e.target.value) || 1)}
                className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                {t("modal.trend_window")}
              </label>
              <input
                type="number"
                min="1"
                max="720"
                value={trendWindow}
                onChange={(e) => setTrendWindow(parseInt(e.target.value) || 1)}
                className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">
              {t("modal.surveillance_interval")}
            </label>
            <input
              type="number"
              min="1"
              max="1440"
              value={survInterval}
              onChange={(e) => setSurvInterval(parseInt(e.target.value) || 1)}
              className="w-full bg-oilfield-800 border border-oilfield-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-cyan-400 font-mono"
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
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white transition shadow-lg shadow-cyan-600/30"
          >
            <Check className="w-4 h-4" />
            <span>{t("modal.save_config")}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
