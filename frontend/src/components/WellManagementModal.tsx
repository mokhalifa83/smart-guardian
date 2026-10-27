"use client";

import React, { useState } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import {
  X,
  Plus,
  Trash2,
  Edit2,
  Check,
  AlertTriangle,
  Building2,
  Activity,
  Layers,
  CheckCircle2,
} from "lucide-react";

interface WellManagementModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function WellManagementModal({ isOpen, onClose }: WellManagementModalProps) {
  const { t } = useLanguage();
  const { wells, selectedWellCode, setSelectedWellCode, addWell, editWell, removeWell } = useWell();

  // Create Form State
  const [isCreating, setIsCreating] = useState(false);
  const [newCode, setNewCode] = useState("");
  const [newField, setNewField] = useState("");
  const [newStatus, setNewStatus] = useState("ACTIVE");
  const [newThreshold, setNewThreshold] = useState("75.0");

  // Edit Form State
  const [editingCode, setEditingCode] = useState<string | null>(null);
  const [editField, setEditField] = useState("");
  const [editStatus, setEditStatus] = useState("ACTIVE");
  const [editThreshold, setEditThreshold] = useState("");

  // Delete Confirm State
  const [deletingCode, setDeletingCode] = useState<string | null>(null);

  // Status message
  const [message, setMessage] = useState<{ text: string; isError: boolean } | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!isOpen) return null;

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCode.trim() || !newField.trim()) {
      setMessage({ text: "Well Code and Field Name are required.", isError: true });
      return;
    }

    try {
      setIsSubmitting(true);
      setMessage(null);
      await addWell({
        well_code: newCode.trim().toUpperCase(),
        field_name: newField.trim(),
        status: newStatus,
        config: {
          wc_threshold: parseFloat(newThreshold) || 75.0,
        },
      });
      setMessage({ text: `Well '${newCode.trim().toUpperCase()}' created successfully!`, isError: false });
      setNewCode("");
      setNewField("");
      setIsCreating(false);
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to create well", isError: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  const startEdit = (w: any) => {
    setEditingCode(w.well_code);
    setEditField(w.field_name);
    setEditStatus(w.status);
    setEditThreshold(w.config?.wc_threshold?.toString() || "75.0");
  };

  const handleSaveEdit = async (code: string) => {
    try {
      setIsSubmitting(true);
      setMessage(null);
      await editWell(code, {
        field_name: editField,
        status: editStatus,
        wc_threshold: parseFloat(editThreshold) || 75.0,
      });
      setMessage({ text: `Well '${code}' updated successfully!`, isError: false });
      setEditingCode(null);
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to update well", isError: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleDelete = async (code: string) => {
    try {
      setIsSubmitting(true);
      setMessage(null);
      await removeWell(code);
      setMessage({ text: `Well '${code}' and records deleted successfully.`, isError: false });
      setDeletingCode(null);
    } catch (err: any) {
      setMessage({ text: err.message || "Failed to delete well", isError: true });
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[90vh] flex flex-col bg-[#0b1322] border border-cyan-500/30 rounded-2xl shadow-2xl shadow-cyan-950/50 overflow-hidden font-cairo">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-oilfield-700 bg-[#0e192e]">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center shadow-lg shadow-cyan-500/20">
              <Layers className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white tracking-wide">
                {t("wells_management.title") || "Field Wells Management"}
              </h2>
              <p className="text-xs text-cyan-300/70">
                {t("wells_management.subtitle") || "Create, rename, configure thresholds, or delete field wells"}
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

        {/* Action Bar */}
        <div className="px-6 py-3 bg-[#0d1627] border-b border-oilfield-700/60 flex items-center justify-between gap-4">
          <div className="text-xs text-slate-400">
            <span>{t("wells_management.total_wells") || "Total Registered Wells"}: </span>
            <span className="font-bold text-cyan-400">{wells.length}</span>
          </div>
          <button
            onClick={() => setIsCreating(!isCreating)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black transition shadow-md shadow-cyan-500/20"
          >
            <Plus className="w-4 h-4" />
            <span>{isCreating ? t("common.cancel") || "Cancel" : t("wells_management.add_new") || "+ Add New Well"}</span>
          </button>
        </div>

        {/* Create Well Form Drawer */}
        {isCreating && (
          <form
            onSubmit={handleCreate}
            className="px-6 py-4 bg-oilfield-850/90 border-b border-cyan-500/20 grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-3 items-end animate-in slide-in-from-top-2 duration-150"
          >
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                {t("wells_management.well_code") || "Well Code / Identifier"} *
              </label>
              <input
                type="text"
                value={newCode}
                onChange={(e) => setNewCode(e.target.value)}
                placeholder="e.g. WELL-002, GHAWAR-12"
                className="w-full bg-[#070c16] border border-oilfield-600 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400 font-mono"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                {t("wells_management.field_name") || "Field / Reservoir Name"} *
              </label>
              <input
                type="text"
                value={newField}
                onChange={(e) => setNewField(e.target.value)}
                placeholder="e.g. North Dome, Sand A"
                className="w-full bg-[#070c16] border border-oilfield-600 rounded-lg px-3 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-400"
                required
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                {t("wells_management.initial_status") || "Operational Status"}
              </label>
              <select
                value={newStatus}
                onChange={(e) => setNewStatus(e.target.value)}
                className="w-full bg-[#070c16] border border-oilfield-600 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-400 cursor-pointer"
              >
                <option value="ACTIVE">ACTIVE</option>
                <option value="SHUT_IN">SHUT_IN</option>
                <option value="SUSPENDED">SUSPENDED</option>
                <option value="DRILLING">DRILLING</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-semibold text-slate-300 mb-1">
                {t("wells_management.wc_threshold") || "Water Cut Alert Threshold (%)"}
              </label>
              <input
                type="number"
                step="0.1"
                min="0"
                max="100"
                value={newThreshold}
                onChange={(e) => setNewThreshold(e.target.value)}
                className="w-full bg-[#070c16] border border-oilfield-600 rounded-lg px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-400"
              />
            </div>
            <div>
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-2 text-xs font-bold rounded-lg bg-emerald-500 hover:bg-emerald-400 text-black transition shadow-md shadow-emerald-500/20 disabled:opacity-50"
              >
                {isSubmitting ? t("common.saving") || "Saving..." : t("wells_management.save_well") || "Save Well"}
              </button>
            </div>
          </form>
        )}

        {/* Wells Directory Table */}
        <div className="flex-1 overflow-y-auto p-6 space-y-3">
          <div className="grid grid-cols-1 gap-2.5">
            {wells.map((w) => {
              const isSelected = w.well_code === selectedWellCode;
              const isEditing = editingCode === w.well_code;
              const isDeleting = deletingCode === w.well_code;

              return (
                <div
                  key={w.well_code}
                  className={`p-4 rounded-xl border transition-all ${
                    isSelected
                      ? "bg-[#111f38] border-cyan-400/60 shadow-lg shadow-cyan-950/30 ring-1 ring-cyan-400/40"
                      : "bg-[#0c1424] border-oilfield-700/60 hover:border-oilfield-500"
                  }`}
                >
                  {isEditing ? (
                    // Edit Mode
                    <div className="grid grid-cols-1 sm:grid-cols-4 gap-3 items-center">
                      <div>
                        <span className="block text-[10px] text-slate-400 font-mono">
                          {w.well_code}
                        </span>
                        <input
                          type="text"
                          value={editField}
                          onChange={(e) => setEditField(e.target.value)}
                          placeholder="Field Name"
                          className="w-full bg-[#070c16] border border-oilfield-600 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-400 mt-1"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400">Status</label>
                        <select
                          value={editStatus}
                          onChange={(e) => setEditStatus(e.target.value)}
                          className="w-full bg-[#070c16] border border-oilfield-600 rounded px-2 py-1 text-xs text-white focus:outline-none focus:border-cyan-400 cursor-pointer mt-1"
                        >
                          <option value="ACTIVE">ACTIVE</option>
                          <option value="SHUT_IN">SHUT_IN</option>
                          <option value="SUSPENDED">SUSPENDED</option>
                        </select>
                      </div>
                      <div>
                        <label className="block text-[10px] text-slate-400">WC Threshold (%)</label>
                        <input
                          type="number"
                          step="0.1"
                          value={editThreshold}
                          onChange={(e) => setEditThreshold(e.target.value)}
                          className="w-full bg-[#070c16] border border-oilfield-600 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-400 mt-1"
                        />
                      </div>
                      <div className="flex items-center gap-2 justify-end">
                        <button
                          onClick={() => handleSaveEdit(w.well_code)}
                          disabled={isSubmitting}
                          className="px-3 py-1.5 text-xs font-bold rounded bg-emerald-500 hover:bg-emerald-400 text-black flex items-center gap-1 transition"
                        >
                          <Check className="w-3.5 h-3.5" />
                          <span>Save</span>
                        </button>
                        <button
                          onClick={() => setEditingCode(null)}
                          className="px-3 py-1.5 text-xs rounded bg-oilfield-700 hover:bg-oilfield-600 text-slate-300 transition"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : isDeleting ? (
                    // Delete Confirmation Prompt
                    <div className="flex items-center justify-between gap-4 p-2 bg-rose-950/40 border border-rose-800/60 rounded-lg">
                      <div className="flex items-center gap-2 text-rose-300 text-xs">
                        <AlertTriangle className="w-4 h-4 text-rose-400 shrink-0" />
                        <span>
                          Are you sure you want to permanently delete well{" "}
                          <strong className="text-white font-mono">{w.well_code}</strong> and its historical telemetry?
                        </span>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <button
                          onClick={() => handleDelete(w.well_code)}
                          disabled={isSubmitting}
                          className="px-3 py-1 text-xs font-bold rounded bg-rose-600 hover:bg-rose-500 text-white transition shadow-sm"
                        >
                          Yes, Delete
                        </button>
                        <button
                          onClick={() => setDeletingCode(null)}
                          className="px-3 py-1 text-xs rounded bg-oilfield-700 hover:bg-oilfield-600 text-slate-300 transition"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    // Display Mode
                    <div className="flex flex-wrap items-center justify-between gap-4">
                      <div className="flex items-center gap-3">
                        <div
                          className={`w-3 h-3 rounded-full ${
                            w.status === "ACTIVE"
                              ? "bg-emerald-400 shadow-sm shadow-emerald-400/50 animate-pulse"
                              : "bg-amber-400"
                          }`}
                        />
                        <div>
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-bold text-white font-mono tracking-tight">
                              {w.well_code}
                            </h3>
                            {isSelected && (
                              <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-950 text-cyan-300 border border-cyan-800">
                                ACTIVE SELECTION
                              </span>
                            )}
                            <span
                              className={`px-2 py-0.2 rounded text-[10px] font-semibold ${
                                w.status === "ACTIVE"
                                  ? "bg-emerald-950 text-emerald-400 border border-emerald-800/60"
                                  : "bg-amber-950 text-amber-400 border border-amber-800/60"
                              }`}
                            >
                              {w.status}
                            </span>
                          </div>
                          <div className="flex items-center gap-3 text-xs text-slate-400 mt-0.5">
                            <span className="flex items-center gap-1">
                              <Building2 className="w-3 h-3 text-slate-500" />
                              {w.field_name}
                            </span>
                            <span>•</span>
                            <span>
                              WC Threshold:{" "}
                              <strong className="text-amber-300 font-mono">
                                {w.config?.wc_threshold ?? 75.0}%
                              </strong>
                            </span>
                          </div>
                        </div>
                      </div>

                      <div className="flex items-center gap-2">
                        {!isSelected && (
                          <button
                            onClick={() => setSelectedWellCode(w.well_code)}
                            className="px-3 py-1.5 text-xs font-semibold rounded-lg bg-oilfield-750 hover:bg-cyan-950 hover:text-cyan-300 text-slate-300 border border-oilfield-600 hover:border-cyan-700 transition"
                          >
                            Select Well
                          </button>
                        )}
                        <button
                          onClick={() => startEdit(w)}
                          title="Edit Well Details"
                          className="p-1.5 rounded-lg bg-oilfield-750 hover:bg-oilfield-650 text-slate-300 hover:text-white border border-oilfield-600 transition"
                        >
                          <Edit2 className="w-3.5 h-3.5 text-cyan-400" />
                        </button>
                        <button
                          onClick={() => setDeletingCode(w.well_code)}
                          title="Delete Well"
                          className="p-1.5 rounded-lg bg-oilfield-750 hover:bg-rose-950 text-slate-300 hover:text-rose-400 border border-oilfield-600 hover:border-rose-800 transition"
                        >
                          <Trash2 className="w-3.5 h-3.5 text-rose-400" />
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-oilfield-700/80 bg-[#0c1424] flex items-center justify-between text-xs text-slate-400">
          <span>{t("wells_management.footer_hint") || "Click 'Select Well' to focus surveillance dashboard on any asset."}</span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 font-bold rounded-lg bg-oilfield-700 hover:bg-oilfield-600 text-white transition"
          >
            {t("common.close") || "Close"}
          </button>
        </div>
      </div>
    </div>
  );
}
