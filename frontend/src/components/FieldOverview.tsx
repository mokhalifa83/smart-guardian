"use client";

import React, { useState } from "react";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import {
  LayoutDashboard,
  Droplets,
  Flame,
  Activity,
  AlertTriangle,
  CheckCircle2,
  Search,
  Filter,
  ArrowRight,
  ExternalLink,
} from "lucide-react";

interface FieldOverviewProps {
  onSelectWellToMonitor: (wellCode: string) => void;
  onLaunchDiagnostics: (wellCode: string) => void;
}

export function FieldOverview({
  onSelectWellToMonitor,
  onLaunchDiagnostics,
}: FieldOverviewProps) {
  const { t } = useLanguage();
  const { wells, setSelectedWellCode } = useWell();

  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("ALL");

  // Simulated live field-wide telemetry for all registered wells
  const wellRows = (wells || []).map((w, index) => {
    // Generate realistic variance per well
    const baseWc = 25 + ((index * 13) % 65);
    const baseRate = 800 + ((index * 270) % 2200);
    const threshold = w.config?.wc_threshold || 75.0;
    const isWarning = baseWc >= threshold;

    return {
      well_code: w.well_code,
      field_name: w.field_name,
      status: w.status,
      water_cut: baseWc,
      flow_rate: baseRate,
      threshold,
      surveillance_state: isWarning ? "WARNING" : "NORMAL",
    };
  });

  const filteredRows = wellRows.filter((r) => {
    const matchesSearch =
      r.well_code.toLowerCase().includes(searchQuery.toLowerCase()) ||
      r.field_name.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus =
      statusFilter === "ALL" ||
      (statusFilter === "WARNING" && r.surveillance_state === "WARNING") ||
      (statusFilter === "ACTIVE" && r.status === "ACTIVE") ||
      (statusFilter === "SHUT_IN" && r.status === "SHUT_IN");

    return matchesSearch && matchesStatus;
  });

  // Calculate field totals
  const totalLiquid = wellRows.reduce((acc, r) => acc + (r.status === "ACTIVE" ? r.flow_rate : 0), 0);
  const totalActive = wellRows.filter((r) => r.status === "ACTIVE").length;
  const totalWarnings = wellRows.filter((r) => r.surveillance_state === "WARNING").length;
  const avgWc = wellRows.length > 0 ? (wellRows.reduce((acc, r) => acc + r.water_cut, 0) / wellRows.length).toFixed(1) : "0.0";

  return (
    <div className="space-y-6">
      {/* Field Totalizer Summary KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Total Liquid Rate */}
        <div className="rounded-2xl border border-oilfield-700/80 bg-[#0c1527] p-5 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">
              Field Gross Liquid
            </span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-extrabold font-mono text-white">
                {totalLiquid.toLocaleString()}
              </span>
              <span className="text-xs text-slate-400 font-mono font-semibold">bpd</span>
            </div>
            <span className="text-[11px] text-emerald-400 font-medium mt-1 block">
              Across {totalActive} Active Wells
            </span>
          </div>
          <div className="p-3 rounded-xl bg-cyan-950/60 border border-cyan-800/80 text-cyan-400">
            <Activity className="w-6 h-6" />
          </div>
        </div>

        {/* Field Average Water Cut */}
        <div className="rounded-2xl border border-oilfield-700/80 bg-[#0c1527] p-5 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">
              Field Average Water Cut
            </span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-extrabold font-mono text-cyan-300">
                {avgWc}%
              </span>
              <span className="text-xs text-slate-400 font-mono font-semibold">WC</span>
            </div>
            <span className="text-[11px] text-slate-400 font-medium mt-1 block">
              Weighted Reservoir Average
            </span>
          </div>
          <div className="p-3 rounded-xl bg-cyan-950/60 border border-cyan-800/80 text-cyan-400">
            <Droplets className="w-6 h-6" />
          </div>
        </div>

        {/* Active Producers */}
        <div className="rounded-2xl border border-oilfield-700/80 bg-[#0c1527] p-5 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">
              Producers Online
            </span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className="text-3xl font-extrabold font-mono text-emerald-400">
                {totalActive}
              </span>
              <span className="text-xs text-slate-400 font-mono font-semibold">/ {wells.length}</span>
            </div>
            <span className="text-[11px] text-emerald-400 font-medium mt-1 block">
              {wells.length - totalActive} Shut-in or Suspended
            </span>
          </div>
          <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-800/80 text-emerald-400">
            <CheckCircle2 className="w-6 h-6" />
          </div>
        </div>

        {/* Active Field Warnings */}
        <div className="rounded-2xl border border-oilfield-700/80 bg-[#0c1527] p-5 shadow-lg flex items-center justify-between">
          <div>
            <span className="text-xs text-slate-400 font-semibold uppercase tracking-wider block">
              Wells in Warning State
            </span>
            <div className="flex items-baseline gap-2 mt-2">
              <span className={`text-3xl font-extrabold font-mono ${totalWarnings > 0 ? "text-amber-400" : "text-white"}`}>
                {totalWarnings}
              </span>
              <span className="text-xs text-slate-400 font-mono font-semibold">Exceedances</span>
            </div>
            <span className="text-[11px] text-amber-400 font-medium mt-1 block">
              {totalWarnings > 0 ? "Engineering Diagnostics Required" : "All Wells Operating in Envelope"}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-amber-950/60 border border-amber-800/80 text-amber-400">
            <AlertTriangle className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Wells Matrix Table */}
      <div className="rounded-2xl border border-oilfield-700/80 bg-[#0c1527] shadow-xl overflow-hidden">
        {/* Table Filter & Search Controls */}
        <div className="p-4 bg-[#0a1120] border-b border-oilfield-700/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <LayoutDashboard className="w-5 h-5 text-cyan-400" />
            <h3 className="text-sm font-bold text-white">
              Field Wells Surveillance Matrix ({filteredRows.length})
            </h3>
          </div>

          <div className="flex flex-wrap items-center gap-2.5">
            {/* Search Input */}
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2 rtl:left-auto rtl:right-3" />
              <input
                type="text"
                placeholder="Search well code or field..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="bg-[#070c16] border border-oilfield-600 rounded-xl pl-9 pr-3 rtl:pl-3 rtl:pr-9 py-1.5 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-cyan-500 w-48 sm:w-56"
              />
            </div>

            {/* Status Filter */}
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="bg-[#070c16] border border-oilfield-600 rounded-xl px-3 py-1.5 text-xs text-white focus:outline-none focus:border-cyan-500 cursor-pointer"
            >
              <option value="ALL">All Statuses</option>
              <option value="WARNING">Warnings Only</option>
              <option value="ACTIVE">Active Producers</option>
              <option value="SHUT_IN">Shut-In Wells</option>
            </select>
          </div>
        </div>

        {/* Table Content */}
        <div className="overflow-x-auto">
          <table className="w-full text-start text-xs">
            <thead className="bg-[#070c16]/80 border-b border-oilfield-700/60 text-slate-400 uppercase text-[10px] tracking-wider font-semibold">
              <tr>
                <th className="px-5 py-3 text-start">Well Code</th>
                <th className="px-5 py-3 text-start">Field / Reservoir</th>
                <th className="px-5 py-3 text-start">Status</th>
                <th className="px-5 py-3 text-start">Water Cut</th>
                <th className="px-5 py-3 text-start">Gross Rate</th>
                <th className="px-5 py-3 text-start">Surveillance Condition</th>
                <th className="px-5 py-3 text-end">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-oilfield-700/50">
              {filteredRows.map((row) => (
                <tr
                  key={row.well_code}
                  className="hover:bg-slate-800/40 transition group"
                >
                  <td className="px-5 py-3.5 font-bold font-mono text-cyan-300">
                    {row.well_code}
                  </td>
                  <td className="px-5 py-3.5 text-slate-300 font-medium">
                    {row.field_name}
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold ${
                        row.status === "ACTIVE"
                          ? "bg-emerald-950/80 text-emerald-300 border border-emerald-800"
                          : "bg-slate-800 text-slate-300 border border-slate-700"
                      }`}
                    >
                      {row.status}
                    </span>
                  </td>
                  <td className="px-5 py-3.5 font-mono">
                    <span className={row.water_cut >= row.threshold ? "text-amber-400 font-bold" : "text-white"}>
                      {row.water_cut}%
                    </span>
                    <span className="text-[10px] text-slate-500 ml-1">/ {row.threshold}%</span>
                  </td>
                  <td className="px-5 py-3.5 font-mono text-white font-semibold">
                    {row.flow_rate.toLocaleString()} bpd
                  </td>
                  <td className="px-5 py-3.5">
                    <span
                      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg text-[11px] font-semibold ${
                        row.surveillance_state === "WARNING"
                          ? "bg-amber-950/80 text-amber-300 border border-amber-600/60"
                          : "bg-emerald-950/60 text-emerald-300 border border-emerald-800/60"
                      }`}
                    >
                      {row.surveillance_state === "WARNING" ? (
                        <AlertTriangle className="w-3 h-3 text-amber-400" />
                      ) : (
                        <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                      )}
                      <span>{row.surveillance_state}</span>
                    </span>
                  </td>
                  <td className="px-5 py-3.5 text-end">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        onClick={() => onSelectWellToMonitor(row.well_code)}
                        className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-cyan-600/20 hover:bg-cyan-600/40 text-cyan-300 border border-cyan-500/40 transition"
                        title="Focus Surveillance Dashboard on this well"
                      >
                        Monitor
                      </button>
                      {row.surveillance_state === "WARNING" && (
                        <button
                          onClick={() => onLaunchDiagnostics(row.well_code)}
                          className="px-2.5 py-1 text-xs font-semibold rounded-lg bg-amber-600/20 hover:bg-amber-600/40 text-amber-300 border border-amber-500/40 transition flex items-center gap-1"
                          title="Launch Chan Diagnostic Plot for this well"
                        >
                          <span>Diagnose</span>
                          <ArrowRight className="w-3 h-3 rtl:rotate-180" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}