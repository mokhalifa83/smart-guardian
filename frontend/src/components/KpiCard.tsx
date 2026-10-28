"use client";

import React from "react";
import { KpiCardData } from "@/types/api";
import { useLanguage } from "@/context/LanguageContext";
import { formatDateTime } from "@/lib/utils";
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Clock,
  Database,
  Tag,
  Gauge,
  Droplets,
  Activity
} from "lucide-react";

interface KpiCardProps {
  kpi?: KpiCardData;
  data?: KpiCardData;
}

export function KpiCard({ kpi: propKpi, data: propData }: KpiCardProps) {
  const kpi = propKpi || propData;
  const { t } = useLanguage();

  if (!kpi) return null;

  const getMetricIcon = (metricKey: string) => {
    switch (metricKey) {
      case "water_cut":
        return <Droplets className="w-7 h-7 text-red-500" />;
      case "pressure":
        return <Gauge className="w-7 h-7 text-zinc-300" />;
      case "flow_rate":
        return <Activity className="w-7 h-7 text-red-400" />;
      default:
        return <Activity className="w-7 h-7 text-zinc-400" />;
    }
  };

  const getStatusBadge = () => {
    switch (kpi.status) {
      case "NORMAL":
        return (
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold bg-zinc-800 text-zinc-200 border border-zinc-700">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            {t("status.NORMAL")}
          </span>
        );
      case "WARNING":
        return (
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-black bg-red-950 text-red-300 border border-red-600 shadow-sm shadow-red-600/30 animate-pulse">
            <AlertTriangle className="w-4 h-4 text-red-400" />
            {t("status.WARNING")}
          </span>
        );
      case "DATA_UNAVAILABLE":
      default:
        return (
          <span className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-bold bg-zinc-900 text-zinc-400 border border-zinc-800">
            <HelpCircle className="w-4 h-4" />
            {t("status.DATA_UNAVAILABLE")}
          </span>
        );
    }
  };

  // Determine card border accent based on state
  const borderClass =
    kpi.status === "WARNING"
      ? "border-red-600 bg-gradient-to-b from-red-950/30 to-[#0e0e11] shadow-lg shadow-red-950/40"
      : kpi.status === "NORMAL"
      ? "border-zinc-800 hover:border-zinc-600 bg-[#0e0e11]"
      : "border-zinc-900 bg-[#0a0a0d]";

  return (
    <div
      className={`rounded-2xl border ${borderClass} p-6 shadow-xl flex flex-col justify-between transition-all duration-200 hover:-translate-y-1`}
    >
      {/* Top Header */}
      <div>
        <div className="flex items-center justify-between gap-3 mb-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-zinc-900 border border-zinc-700 shadow-inner">
              {getMetricIcon(kpi.metric_key)}
            </div>
            <div>
              <h3 className="text-base font-bold text-white tracking-wide">
                {t(`kpi.${kpi.metric_key}`) || kpi.title}
              </h3>
              <p className="text-xs text-zinc-400 font-medium mt-0.5">
                {kpi.threshold !== null
                  ? `${t("kpi.threshold")}: ${kpi.threshold}%`
                  : `${t("kpi.value_type")}: ${t(`status.${kpi.value_type}`)}`}
              </p>
            </div>
          </div>
          <div>{getStatusBadge()}</div>
        </div>

        {/* Primary Measurement Display */}
        <div className="my-5">
          {kpi.status === "DATA_UNAVAILABLE" ? (
            <div className="py-2">
              <span className="text-base font-mono font-bold tracking-wider text-zinc-400 uppercase bg-zinc-900 px-4 py-2 rounded-lg border border-zinc-700 block text-center">
                DATA_UNAVAILABLE
              </span>
              <p className="text-xs text-zinc-400 mt-2 text-center">
                External telemetry unavailable. No synthetic 0.0 substitution.
              </p>
            </div>
          ) : (
            <div className="flex items-baseline gap-3">
              <span
                className={`text-4xl sm:text-5xl font-black font-mono tracking-tight ${
                  kpi.status === "WARNING" ? "text-red-500 drop-shadow-[0_2px_10px_rgba(239,68,68,0.3)]" : "text-white"
                }`}
              >
                {kpi.display_value}
              </span>
              <span className="text-lg font-bold text-zinc-400 font-mono">
                {kpi.unit}
              </span>
              {kpi.is_threshold_exceeded && (
                <span className="text-xs font-black text-red-300 border border-red-600 bg-red-950 px-2.5 py-1 rounded-md shadow-sm">
                  {t("kpi.warning_exceeded")}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Provenance & Audit Metadata Grid */}
      <div className="border-t border-zinc-800/80 pt-4 mt-2 grid grid-cols-2 gap-3 text-xs text-zinc-400 font-medium">
        <div className="flex items-center gap-2 truncate">
          <Database className="w-4 h-4 text-zinc-500 shrink-0" />
          <span className="truncate">
            {t("kpi.source")}: <strong className="text-zinc-200">{kpi.source}</strong>
          </span>
        </div>

        <div className="flex items-center gap-2 truncate">
          <Tag className="w-4 h-4 text-zinc-500 shrink-0" />
          <span className="truncate">
            {t("kpi.quality")}:{" "}
            <strong
              className={
                kpi.quality_status === "VALID"
                  ? "text-emerald-400"
                  : kpi.quality_status === "DATA_UNAVAILABLE"
                  ? "text-zinc-400 font-mono"
                  : "text-amber-400"
              }
            >
              {t(`status.${kpi.quality_status}`) || kpi.quality_status}
            </strong>
          </span>
        </div>

        <div className="flex items-center gap-2 col-span-2 truncate">
          <Clock className="w-4 h-4 text-zinc-500 shrink-0" />
          <span className="truncate">
            {t("kpi.measured_at")}: <span className="text-zinc-300 font-mono">{formatDateTime(kpi.timestamp)}</span>
          </span>
        </div>
      </div>
    </div>
  );
}
