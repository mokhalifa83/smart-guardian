"use client";

import React, { useState } from "react";
import { Alert } from "@/types/api";
import { useLanguage } from "@/context/LanguageContext";
import { formatDateTime } from "@/lib/utils";
import { acknowledgeAlert, resolveAlert } from "@/lib/api";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, AlertCircle, CheckCircle2, ShieldAlert } from "lucide-react";

interface AlertListProps {
  alerts: Alert[];
  wellCode?: string;
}

export function AlertList({ alerts, wellCode }: AlertListProps) {
  const { t } = useLanguage();
  const queryClient = useQueryClient();
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const ackMutation = useMutation({
    mutationFn: (alertId: string) => acknowledgeAlert(alertId, "field-operator"),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dashboard", wellCode] });
    },
  });

  const resolveMutation = useMutation({
    mutationFn: (alertId: string) => resolveAlert(alertId, "field-operator", "Investigated & acknowledged"),
    onSuccess: () => {
      setResolvingId(null);
      queryClient.invalidateQueries({ queryKey: ["dashboard", wellCode] });
    },
  });

  if (!alerts || alerts.length === 0) {
    return (
      <div className="rounded-xl border border-oilfield-700 bg-oilfield-800/40 p-6 text-center">
        <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto mb-2 opacity-80" />
        <p className="text-sm text-slate-300 font-medium">{t("alerts.empty")}</p>
        <p className="text-xs text-slate-400 mt-1">{t("alerts.root_cause_disclaimer")}</p>
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-amber-600/40 bg-oilfield-800/90 shadow-xl overflow-hidden">
      {/* Alert Header */}
      <div className="bg-amber-950/40 border-b border-amber-500/30 px-5 py-3.5 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <AlertTriangle className="w-5 h-5 text-amber-400" />
          <h2 className="text-sm font-bold text-amber-200 uppercase tracking-wider">
            {t("alerts.title")} ({alerts.length})
          </h2>
        </div>
        <div className="text-[11px] text-amber-300/80 font-mono">
          {t("alerts.root_cause_disclaimer")}
        </div>
      </div>

      {/* Alert Rows */}
      <div className="divide-y divide-oilfield-700/60">
        {alerts.map((alert) => (
          <div
            key={alert.alert_id}
            className="p-4 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-oilfield-700/30 transition"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5 p-1.5 rounded-lg bg-amber-950/80 border border-amber-500/40">
                <AlertCircle className="w-4 h-4 text-amber-400" />
              </div>
              <div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-mono font-bold px-2 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                    {alert.alert_type}
                  </span>
                  <span className="text-xs font-semibold text-slate-400">
                    {alert.severity}
                  </span>
                  <span className="text-xs text-slate-400 font-mono">
                    {formatDateTime(alert.timestamp)}
                  </span>
                  <span
                    className={`text-[10px] font-semibold px-2 py-0.5 rounded uppercase ${
                      alert.status === "ACTIVE"
                        ? "bg-red-950/80 text-red-300 border border-red-800"
                        : "bg-blue-950/80 text-blue-300 border border-blue-800"
                    }`}
                  >
                    {t(`status.${alert.status}`) || alert.status}
                  </span>
                </div>
                <p className="text-sm text-slate-200 font-medium mt-1">
                  {alert.message}
                </p>
                <p className="text-[11px] text-slate-400 font-mono mt-0.5">
                  ID: {alert.alert_id} | Source: {alert.source}
                </p>
              </div>
            </div>

            {/* Lifecycle Buttons */}
            <div className="flex items-center gap-2 self-end md:self-center shrink-0">
              {alert.status === "ACTIVE" && (
                <button
                  onClick={() => ackMutation.mutate(alert.alert_id)}
                  disabled={ackMutation.isPending}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-oilfield-700 hover:bg-oilfield-600 text-slate-200 border border-oilfield-500 transition"
                >
                  {t("alerts.acknowledge")}
                </button>
              )}
              {alert.status !== "RESOLVED" && (
                <button
                  onClick={() => resolveMutation.mutate(alert.alert_id)}
                  disabled={resolveMutation.isPending}
                  className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-950/80 hover:bg-emerald-900 text-emerald-300 border border-emerald-600 transition"
                >
                  {t("alerts.resolve")}
                </button>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
