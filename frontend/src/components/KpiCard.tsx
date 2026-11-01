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
        return <Droplets className="w-5 h-5 text-cyan-400" />;
      case "pressure":
        return <Gauge className="w-5 h-5 text-amber-400" />;
      case "flow_rate":
        return <Activity className="w-5 h-5 text-emerald-400" />;
      default:
        return <Activity className="w-5 h-5 text-slate-400" />;
    }
  };

  const getStatusBadge = () => {
    switch (kpi.status) {
      case "NORMAL":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-emerald-950/80 text-emerald-300 border border-emerald-700/60">
            <CheckCircle2 className="w-3.5 h-3.5" />
            {t("status.NORMAL")}
          </span>
        );
      case "WARNING":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-amber-950/90 text-amber-300 border border-amber-500">
            <AlertTriangle className="w-3.5 h-3.5" />
            {t("status.WARNING")}
          </span>
        );
      case "DATA_UNAVAILABLE":
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded text-xs font-semibold bg-slate-800 text-slate-300 border border-slate-600">
            <HelpCircle className="w-3.5 h-3.5" />
            {t("status.DATA_UNAVAILABLE")}
          </span>
        );
    }
  };

  // Determine card border accent based on state
  const borderClass =
    kpi.status === "WARNING"
      ? "border-amber-500/80 bg-amber-950/10"
      : kpi.status === "NORMAL"
      ? "border-oilfield-700 hover:border-oilfield-600"
      : "border-slate-700/60 bg-slate-900/40";

  return (
    <div
      className={`rounded-xl border ${borderClass} bg-oilfield-800/80 p-5 shadow-lg flex flex-col justify-between transition duration-200`}
    >
      {/* Top Header */}
      <div>
        <div className="flex items-center justify-between gap-2 mb-3">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-oilfield-700/60 border border-oilfield-600">
              {getMetricIcon(kpi.metric_key)}
            </div>
            <div>
              <h3 className="text-sm font-semibold text-slate-200 tracking-wide">
                {t(`kpi.${kpi.metric_key}`) || kpi.title}
              </h3>
              <p className="text-[11px] text-slate-400">
                {kpi.threshold !== null
                  ? `${t("kpi.threshold")}: ${kpi.threshold}%`
                  : `${t("kpi.value_type")}: ${t(`status.${kpi.value_type}`)}`}
              </p>
            </div>
          </div>
          <div>{getStatusBadge()}</div>
        </div>

        {/* Primary Measurement Display */}
        <div className="my-4">
          {kpi.status === "DATA_UNAVAILABLE" ? (
            <div className="py-2">
              <span className="text-lg font-mono font-bold tracking-wider text-slate-400 uppercase bg-slate-800/80 px-3 py-1.5 rounded border border-slate-700">
                DATA_UNAVAILABLE
              </span>
              <p className="text-xs text-slate-400 mt-2">
                External telemetry unavailable. No synthetic 0.0 substitution.
              </p>
            </div>
          ) : (
            <div className="flex items-baseline gap-2">
              <span
                className={`text-3xl lg:text-4xl font-extrabold font-mono tracking-tight ${
                  kpi.status === "WARNING" ? "text-amber-400" : "text-white"
                }`}
              >
                {kpi.display_value}
              </span>
              <span className="text-sm font-semibold text-slate-400 font-mono">
                {kpi.unit}
              </span>
              {kpi.is_threshold_exceeded && (
                <span className="text-xs font-medium text-amber-400 border border-amber-500/50 bg-amber-950/60 px-2 py-0.5 rounded">
                  {t("kpi.warning_exceeded")}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Provenance & Audit Metadata Grid */}
      <div className="border-t border-oilfield-700/60 pt-3 mt-2 grid grid-cols-2 gap-2 text-[11px] text-slate-400">
        <div className="flex items-center gap-1.5 truncate">
          <Database className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="truncate">
            <span className="text-slate-400">{t("kpi.source")}: </span>
            <span className="text-slate-300 font-medium font-mono">
              {kpi.source || "--"}
            </span>
          </span>
        </div>

        <div className="flex items-center gap-1.5 truncate">
          <Tag className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="truncate">
            <span className="text-slate-400">{t("kpi.quality")}: </span>
            <span
              className={`font-medium ${
                kpi.quality_status === "VALID"
                  ? "text-emerald-400"
                  : kpi.quality_status === "DATA_UNAVAILABLE"
                  ? "text-slate-400 font-mono"
                  : "text-amber-400"
              }`}
            >
              {t(`status.${kpi.quality_status}`) || kpi.quality_status}
            </span>
          </span>
        </div>

        <div className="flex items-center gap-1.5 col-span-2 truncate">
          <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
          <span className="truncate text-slate-400">
            {t("kpi.measured_at")}:{" "}
            <span className="text-slate-300 font-mono">
              {formatDateTime(kpi.timestamp)}
            </span>
          </span>
        </div>
      </div>
    </div>
  );
}
