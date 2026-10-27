"use client";

import React, { useState, useEffect } from "react";
import { useLanguage } from "@/context/LanguageContext";
import {
  fetchFieldControlMode,
  toggleFieldControlMode,
  writeOpcuaTag,
} from "@/lib/api";
import {
  X,
  ShieldCheck,
  ShieldAlert,
  Sliders,
  CheckCircle2,
  AlertTriangle,
  Radio,
  Send,
} from "lucide-react";

interface SupervisoryModeModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SupervisoryModeModal({ isOpen, onClose }: SupervisoryModeModalProps) {
  const { t } = useLanguage();
  const [controlState, setControlState] = useState<{
    enabled: boolean;
    authorized_by?: string;
    authorized_at?: string;
    reason?: string;
  }>({ enabled: false });

  const [operatorName, setOperatorName] = useState("Chief Petroleum Engineer");
  const [reason, setReason] = useState("Operational field test and choke calibration");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);

  // Live test write state
  const [testTag, setTestTag] = useState("ns=2;s=Wellhead.ChokeOpening");
  const [testValue, setTestValue] = useState("36.0");
  const [writeResult, setWriteResult] = useState<any>(null);

  useEffect(() => {
    if (isOpen) {
      loadMode();
    }
  }, [isOpen]);

  const loadMode = async () => {
    try {
      const mode = await fetchFieldControlMode();
      setControlState(mode);
    } catch (err) {
      console.error("Failed to load control mode:", err);
    }
  };

  if (!isOpen) return null;

  const handleToggle = async (targetEnabled: boolean) => {
    try {
      setIsSubmitting(true);
      setMessage(null);
      const res = await toggleFieldControlMode(targetEnabled, operatorName, reason);
      setControlState(res);
      setMessage({
        text: targetEnabled
          ? "SUPERVISORY CONTROL ACTIVATED: Full Read & Write functionality is now enabled."
          : "READ-ONLY SURVEILLANCE RESTORED: Control commands and write actions are safely locked.",
        isError: false,
      });
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to change operational mode", isError: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleExecuteWrite = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      setIsSubmitting(true);
      setMessage(null);
      const val = parseFloat(testValue);
      const res = await writeOpcuaTag(testTag, val, operatorName);
      setWriteResult(res);
      setMessage({
        text: `OPC UA Write Successful: Tag '${testTag}' set to ${val}.`,
        isError: false,
      });
    } catch (err: any) {
      setMessage({ text: err.message || "Write command rejected", isError: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-2xl bg-[#0b1322] border border-cyan-500/30 rounded-2xl shadow-2xl shadow-cyan-950/50 overflow-hidden font-cairo">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-oilfield-700 bg-[#0e192e]">
          <div className="flex items-center gap-3">
            <div
              className={`w-9 h-9 rounded-xl flex items-center justify-center shadow-lg ${
                controlState.enabled
                  ? "bg-gradient-to-br from-amber-500 to-rose-600 shadow-amber-500/20"
                  : "bg-gradient-to-br from-cyan-500 to-blue-600 shadow-cyan-500/20"
              }`}
            >
              {controlState.enabled ? (
                <ShieldAlert className="w-5 h-5 text-white" />
              ) : (
                <ShieldCheck className="w-5 h-5 text-white" />
              )}
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide">
                Operational Control & Supervisory Write Mode
              </h2>
              <p className="text-xs text-cyan-300/70">
                Configure field boundary permissions (Read-Only vs Authorized Read & Write)
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-oilfield-700 transition"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Message Banner */}
        {message && (
          <div
            className={`px-6 py-2.5 text-xs font-semibold flex items-center gap-2 border-b ${
              message.isError
                ? "bg-rose-950/60 border-rose-800 text-rose-300"
                : "bg-emerald-950/60 border-emerald-800 text-emerald-300"
            }`}
          >
            {message.isError ? (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            )}
            <span>{message.text}</span>
          </div>
        )}

        {/* Mode Status Cards */}
        <div className="p-6 space-y-5">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Mode 1: Read-Only */}
            <div
              className={`p-4 rounded-xl border transition ${
                !controlState.enabled
                  ? "bg-[#0f1d36] border-cyan-400 shadow-lg shadow-cyan-950/30 ring-1 ring-cyan-400/30"
                  : "bg-[#0c1424] border-oilfield-700 opacity-60 hover:opacity-100"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-cyan-300 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  READ-ONLY SURVEILLANCE
                </span>
                {!controlState.enabled && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
                    ACTIVE
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Default industrial safety boundary. High-integrity passive monitoring with complete protection against unauthorized field actuation.
              </p>
              {controlState.enabled && (
                <button
                  onClick={() => handleToggle(false)}
                  disabled={isSubmitting}
                  className="mt-3 w-full py-1.5 text-xs font-semibold rounded bg-oilfield-700 hover:bg-oilfield-600 text-slate-200 transition"
                >
                  Switch to Read-Only
                </button>
              )}
            </div>

            {/* Mode 2: Supervisory Read & Write */}
            <div
              className={`p-4 rounded-xl border transition ${
                controlState.enabled
                  ? "bg-[#251508] border-amber-400 shadow-lg shadow-amber-950/30 ring-1 ring-amber-400/40"
                  : "bg-[#0c1424] border-oilfield-700 opacity-70 hover:opacity-100"
              }`}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-bold text-amber-300 flex items-center gap-1.5">
                  <Sliders className="w-4 h-4 text-amber-400" />
                  SUPERVISORY WRITE MODE
                </span>
                {controlState.enabled && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-950 text-amber-300 border border-amber-800 animate-pulse">
                    ACTIVE (WRITE ENABLED)
                  </span>
                )}
              </div>
              <p className="text-xs text-slate-300 leading-relaxed">
                Full bidirectional functionality. Authorizes remote choke adjustments, setpoint modifications, and OPC UA writes with cryptographic audit logging.
              </p>
              {!controlState.enabled && (
                <button
                  onClick={() => handleToggle(true)}
                  disabled={isSubmitting}
                  className="mt-3 w-full py-1.5 text-xs font-bold rounded bg-amber-500 hover:bg-amber-400 text-black transition shadow-sm shadow-amber-500/20"
                >
                  Authorize Full Read & Write
                </button>
              )}
            </div>
          </div>

          {/* Authorization Metadata */}
          {controlState.enabled && (
            <div className="p-3 bg-amber-950/30 border border-amber-500/30 rounded-xl text-xs space-y-1">
              <div className="flex items-center justify-between text-amber-300 font-semibold">
                <span>Authorized Operator: {controlState.authorized_by}</span>
                <span>Time: {controlState.authorized_at ? new Date(controlState.authorized_at).toLocaleTimeString() : "N/A"}</span>
              </div>
              <div className="text-slate-400">Reason: {controlState.reason}</div>
            </div>
          )}

          {/* Live Write Execution Form (Visible when write mode is active) */}
          <div className="p-4 bg-[#090f1a] border border-oilfield-700 rounded-xl space-y-3">
            <h3 className="text-xs font-bold text-white flex items-center gap-2">
              <Radio className="w-4 h-4 text-cyan-400" />
              Direct Field Tag / Setpoint Write Simulator
            </h3>
            <form onSubmit={handleExecuteWrite} className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end">
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">Target Tag Node ID</label>
                <input
                  type="text"
                  value={testTag}
                  onChange={(e) => setTestTag(e.target.value)}
                  className="w-full bg-[#05080f] border border-oilfield-600 rounded px-2.5 py-1 text-xs text-white font-mono"
                  required
                />
              </div>
              <div>
                <label className="block text-[10px] text-slate-400 mb-1">New Value</label>
                <input
                  type="number"
                  step="0.1"
                  value={testValue}
                  onChange={(e) => setTestValue(e.target.value)}
                  className="w-full bg-[#05080f] border border-oilfield-600 rounded px-2.5 py-1 text-xs text-white"
                  required
                />
              </div>
              <div>
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full py-1.5 text-xs font-bold rounded bg-cyan-500 hover:bg-cyan-400 text-black flex items-center justify-center gap-1.5 transition disabled:opacity-50"
                >
                  <Send className="w-3.5 h-3.5" />
                  <span>Execute Write</span>
                </button>
              </div>
            </form>

            {writeResult && (
              <div className="p-2.5 bg-cyan-950/40 border border-cyan-800 rounded text-[11px] font-mono text-cyan-300">
                {JSON.stringify(writeResult, null, 2)}
              </div>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-oilfield-700/80 bg-[#0c1424] flex items-center justify-between text-xs text-slate-400">
          <span>{controlState.enabled ? "Write commands are recorded to immutable audit log." : "Read-only mode protects field devices from unauthorized commands."}</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 font-bold rounded-lg bg-oilfield-700 hover:bg-oilfield-600 text-white transition"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
