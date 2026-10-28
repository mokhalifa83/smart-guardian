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
      <div className="rounded-2xl border border-zinc-800 bg-[#0e0e11] p-8 text-center shadow-lg">
        <CheckCircle2 className="w-10 h-10 text-emerald-500 mx-auto mb-3 opacity-90" />
        <p className="text-base text-zinc-200 font-bold">{t("alerts.empty")}</p>
        <p className="text-sm text-zinc-400 mt-1">{t("alerts.root_cause_disclaimer")}</p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-red-600/50 bg-[#0e0e11] shadow-2xl overflow-hidden">
      {/* Alert Header */}
      <div className="bg-gradient-to-r from-red-950 via-[#180a0a] to-[#0e0e11] border-b border-red-600/40 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <AlertTriangle className="w-6 h-6 text-red-500 animate-pulse" />
          <h2 className="text-base font-black text-white uppercase tracking-wider">
            {t("alerts.title")} ({alerts.length})
          </h2>
        </div>
        <div className="text-xs text-red-300/80 font-mono">
          {t("alerts.root_cause_disclaimer")}
        </div>
      </div>

      {/* Alert Rows */}
      <div className="divide-y divide-zinc-800/80">
        {alerts.map((alert) => (
          <div
            key={alert.alert_id}
            className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-5 hover:bg-zinc-900/60 transition"
          >
            <div className="flex items-start gap-4">
              <div className="mt-1 p-2 rounded-xl bg-red-950 border border-red-600/60 shadow-sm">
                <AlertCircle className="w-5 h-5 text-red-400" />
              </div>
              <div>
                <div className="flex items-center gap-2.5 flex-wrap">
                  <span className="text-xs font-mono font-black px-2.5 py-1 rounded-md bg-red-950 text-red-300 border border-red-800">
                    {alert.alert_type}
                  </span>
                  <span className="text-xs font-bold text-zinc-300">
                    {alert.severity}
                  </span>
                  <span className="text-xs text-zinc-400 font-mono">
                    {formatDateTime(alert.timestamp)}
                  </span>
                  <span
                    className={`text-xs font-bold px-2.5 py-0.5 rounded-md uppercase ${
                      alert.status === "ACTIVE"
                        ? "bg-red-600 text-white shadow-sm shadow-red-600/40"
                        : "bg-zinc-800 text-zinc-300 border border-zinc-700"
                    }`}
                  >
                    {t(`status.${alert.status}`) || alert.status}
                  </span>
                </div>
                <p className="text-base text-white font-bold mt-2">
                  {alert.message}
                </p>
                <p className="text-xs text-zinc-400 font-mono mt-1">
                  ID: {alert.alert_id} | Source: {alert.source}
                </p>
              </div>
            </div>

            {/* Lifecycle Buttons */}
            <div className="flex items-center gap-3 self-end md:self-center shrink-0">
              {alert.status === "ACTIVE" && (
                <button
                  onClick={() => ackMutation.mutate(alert.alert_id)}
                  disabled={ackMutation.isPending}
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-100 border border-zinc-600 transition shadow-sm"
                >
                  {t("alerts.acknowledge")}
                </button>
              )}
              {alert.status !== "RESOLVED" && (
                <button
                  onClick={() => resolveMutation.mutate(alert.alert_id)}
                  disabled={resolveMutation.isPending}
                  className="px-4 py-2 text-xs font-bold rounded-xl bg-emerald-950 hover:bg-emerald-900 text-emerald-300 border border-emerald-600 transition shadow-sm"
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
