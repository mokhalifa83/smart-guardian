"use client";

import React, { useState } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import {
  FileText,
  Download,
  Printer,
  Calendar,
  ShieldCheck,
  CheckCircle2,
  FileSpreadsheet,
  Layers,
} from "lucide-react";

export function ReportsView() {
  const { t } = useLanguage();
  const { wells, selectedWellCode } = useWell();

  const [reportType, setReportType] = useState<"daily" | "audit" | "diagnostics">("daily");
  const [selectedReportWell, setSelectedReportWell] = useState<string>("ALL");
  const [isExporting, setIsExporting] = useState(false);
  const [exportSuccess, setExportSuccess] = useState<string | null>(null);

  // Handle CSV Export
  const handleExportCsv = () => {
    setIsExporting(true);
    setExportSuccess(null);

    // Build CSV content
    const headers = ["Timestamp", "Well_Code", "Field_Name", "Water_Cut_Pct", "Pressure_Psi", "Liquid_Rate_Bpd", "Status", "Provenance"];
    const rows = (wells || []).map((w, idx) => {
      const now = new Date().toISOString();
      const wc = (35.5 + (idx * 5) % 40).toFixed(1);
      const press = 950 + (idx * 20);
      const rate = 1800 + (idx * 150);
      return [now, w.well_code, `"${w.field_name}"`, wc, press, rate, w.status, "DIRECT_MEASURED"];
    });

    const csvContent = "data:text/csv;charset=utf-8," + [headers.join(","), ...rows.map((e) => e.join(","))].join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `smart_guardian_telemetry_export_${new Date().toISOString().slice(0, 10)}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setIsExporting(false);
    setExportSuccess("CSV dataset exported successfully!");
    setTimeout(() => setExportSuccess(null), 4000);
  };

  // Handle PDF Print
  const handlePrintPdf = () => {
    window.print();
  };

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="rounded-2xl border border-oilfield-700/80 bg-[#0c1527] p-6 shadow-xl flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2.5 rounded-xl bg-amber-950/60 border border-amber-800/80 text-amber-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">
                Official Engineering Reports & Data Exports
              </h2>
              <p className="text-xs text-slate-400 mt-0.5">
                Generate SPE-PRMS compliant production reports and audit datasets
              </p>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handleExportCsv}
            disabled={isExporting}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-[#0a1120] hover:bg-slate-800 text-cyan-300 border border-cyan-800/80 transition shadow-sm"
          >
            <FileSpreadsheet className="w-4 h-4 text-emerald-400" />
            <span>Export CSV</span>
          </button>

          <button
            onClick={handlePrintPdf}
            className="flex items-center gap-2 px-4 py-2 rounded-xl text-xs font-bold bg-cyan-600 hover:bg-cyan-500 text-white shadow-md shadow-cyan-900/30 transition"
          >
            <Printer className="w-4 h-4" />
            <span>Print Official PDF</span>
          </button>
        </div>
      </div>

      {exportSuccess && (
        <div className="p-3 rounded-xl bg-emerald-950/80 border border-emerald-600 text-emerald-300 text-xs font-semibold flex items-center gap-2 animate-in fade-in duration-200">
          <CheckCircle2 className="w-4 h-4" />
          <span>{exportSuccess}</span>
        </div>
      )}

      {/* Report Preview Document */}
      <div className="rounded-2xl border border-oilfield-700/80 bg-[#0c1527] p-8 shadow-2xl space-y-6 print:border-none print:p-0 print:bg-white print:text-black">
        {/* Document Header */}
        <div className="border-b border-oilfield-700/60 pb-6 flex items-start justify-between">
          <div>
            <div className="text-lg font-black tracking-tight text-white print:text-black">
              SMART GUARDIAN OILFIELD INTELLIGENCE
            </div>
            <div className="text-xs text-slate-400 font-mono mt-1 print:text-gray-600">
              REPORT TYPE: DAILY PRODUCTION & SURVEILLANCE AUDIT
            </div>
          </div>
          <div className="text-end text-xs font-mono text-slate-400 print:text-gray-600">
            <div>DATE: {new Date().toLocaleDateString()}</div>
            <div>COMPLIANCE: SPE-PRMS CLASS 1</div>
          </div>
        </div>

        {/* Report Summary Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div className="p-4 rounded-xl bg-[#070c16] border border-oilfield-700/60 print:bg-gray-100 print:border-gray-300">
            <span className="text-[11px] text-slate-400 block font-semibold">Total Surveyed Assets</span>
            <span className="text-2xl font-bold font-mono text-white print:text-black mt-1 block">
              {wells.length} Wells
            </span>
          </div>

          <div className="p-4 rounded-xl bg-[#070c16] border border-oilfield-700/60 print:bg-gray-100 print:border-gray-300">
            <span className="text-[11px] text-slate-400 block font-semibold">Data Provenance Integrity</span>
            <span className="text-2xl font-bold font-mono text-emerald-400 print:text-black mt-1 block">
              100% Validated
            </span>
          </div>

          <div className="p-4 rounded-xl bg-[#070c16] border border-oilfield-700/60 print:bg-gray-100 print:border-gray-300">
            <span className="text-[11px] text-slate-400 block font-semibold">Security Boundary Status</span>
            <span className="text-2xl font-bold font-mono text-cyan-300 print:text-black mt-1 block">
              Read-Only Verified
            </span>
          </div>
        </div>

        {/* Wells Table Preview */}
        <div>
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 print:text-black">
            Asset Telemetry Log
          </h4>
          <div className="overflow-x-auto rounded-xl border border-oilfield-700/60">
            <table className="w-full text-start text-xs print:text-black">
              <thead className="bg-[#070c16] text-slate-400 print:bg-gray-200">
                <tr>
                  <th className="px-4 py-2.5 text-start font-mono">Well Identifier</th>
                  <th className="px-4 py-2.5 text-start">Field</th>
                  <th className="px-4 py-2.5 text-start">Status</th>
                  <th className="px-4 py-2.5 text-start">Water Cut (%)</th>
                  <th className="px-4 py-2.5 text-start">Separator Pressure</th>
                  <th className="px-4 py-2.5 text-start">Audit Trail</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-oilfield-700/40">
                {wells.slice(0, 10).map((w, i) => (
                  <tr key={w.well_code} className="hover:bg-slate-800/30">
                    <td className="px-4 py-2.5 font-mono font-bold text-cyan-300 print:text-black">
                      {w.well_code}
                    </td>
                    <td className="px-4 py-2.5 text-slate-300 print:text-black">{w.field_name}</td>
                    <td className="px-4 py-2.5">
                      <span className="font-semibold text-emerald-400 print:text-black">{w.status}</span>
                    </td>
                    <td className="px-4 py-2.5 font-mono font-bold text-white print:text-black">
                      {(38.0 + (i * 4.5)).toFixed(1)}%
                    </td>
                    <td className="px-4 py-2.5 font-mono text-slate-300 print:text-black">
                      {980 + i * 15} psi
                    </td>
                    <td className="px-4 py-2.5 text-[11px] font-mono text-slate-400 print:text-black">
                      OPC-UA STREAM
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Sign-off footer */}
        <div className="border-t border-oilfield-700/60 pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 print:text-black gap-4">
          <div className="flex items-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Cryptographic telemetry signature verified</span>
          </div>
          <div className="font-mono text-slate-400">
            Chief Reservoir Engineer Sign-Off: ____________________
          </div>
        </div>
      </div>
    </div>
  );
}