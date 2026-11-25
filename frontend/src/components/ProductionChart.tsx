"use client";

import React, { useState } from "react";
import { useLanguage } from "@/context/LanguageContext";
import {
  TrendingUp,
  Activity,
  Droplets,
  Gauge,
  Calendar,
  AlertTriangle,
} from "lucide-react";

interface ProductionPoint {
  timeLabel: string;
  waterCut: number;
  pressure: number;
  flowRate: number;
}

interface ProductionChartProps {
  wellCode: string;
  threshold?: number;
}

export function ProductionChart({ wellCode, threshold = 75.0 }: ProductionChartProps) {
  const { t } = useLanguage();
  const [timeRange, setTimeRange] = useState<"24h" | "7d" | "30d">("24h");
  const [activeMetric, setActiveMetric] = useState<"all" | "wc" | "pressure" | "flow">("all");
  const [hoveredPoint, setHoveredPoint] = useState<ProductionPoint | null>(null);

  // Generate realistic oilfield time-series data based on timeframe
  const data24h: ProductionPoint[] = [
    { timeLabel: "00:00", waterCut: 42.1, pressure: 980, flowRate: 2450 },
    { timeLabel: "04:00", waterCut: 43.5, pressure: 995, flowRate: 2430 },
    { timeLabel: "08:00", waterCut: 45.2, pressure: 1010, flowRate: 2410 },
    { timeLabel: "12:00", waterCut: 48.0, pressure: 1005, flowRate: 2390 },
    { timeLabel: "16:00", waterCut: 51.3, pressure: 990, flowRate: 2405 },
    { timeLabel: "20:00", waterCut: 49.8, pressure: 1000, flowRate: 2415 },
    { timeLabel: "Now", waterCut: 50.0, pressure: 1000, flowRate: 2401 },
  ];

  const data7d: ProductionPoint[] = [
    { timeLabel: "Day 1", waterCut: 38.5, pressure: 1040, flowRate: 2520 },
    { timeLabel: "Day 2", waterCut: 40.2, pressure: 1030, flowRate: 2490 },
    { timeLabel: "Day 3", waterCut: 42.0, pressure: 1015, flowRate: 2460 },
    { timeLabel: "Day 4", waterCut: 44.8, pressure: 1005, flowRate: 2440 },
    { timeLabel: "Day 5", waterCut: 46.5, pressure: 995, flowRate: 2420 },
    { timeLabel: "Day 6", waterCut: 48.9, pressure: 1000, flowRate: 2410 },
    { timeLabel: "Today", waterCut: 50.0, pressure: 1000, flowRate: 2401 },
  ];

  const data30d: ProductionPoint[] = [
    { timeLabel: "Wk 1", waterCut: 32.0, pressure: 1080, flowRate: 2600 },
    { timeLabel: "Wk 2", waterCut: 37.4, pressure: 1050, flowRate: 2540 },
    { timeLabel: "Wk 3", waterCut: 43.1, pressure: 1020, flowRate: 2470 },
    { timeLabel: "Wk 4", waterCut: 47.8, pressure: 1005, flowRate: 2420 },
    { timeLabel: "Now", waterCut: 50.0, pressure: 1000, flowRate: 2401 },
  ];

  const activeData = timeRange === "24h" ? data24h : timeRange === "7d" ? data7d : data30d;

  // Chart coordinates calculation
  const svgWidth = 800;
  const svgHeight = 240;
  const paddingX = 40;
  const paddingY = 30;
  const chartW = svgWidth - paddingX * 2;
  const chartH = svgHeight - paddingY * 2;

  // Scale calculations
  const maxWc = 100;
  const minWc = 0;

  const pointsWc = activeData.map((d, i) => {
    const x = paddingX + (i / (activeData.length - 1)) * chartW;
    const y = paddingY + chartH - ((d.waterCut - minWc) / (maxWc - minWc)) * chartH;
    return { x, y, data: d };
  });

  const pathWc = pointsWc.reduce(
    (acc, curr, idx) => (idx === 0 ? `M ${curr.x} ${curr.y}` : `${acc} L ${curr.x} ${curr.y}`),
    ""
  );

  const thresholdY = paddingY + chartH - ((threshold - minWc) / (maxWc - minWc)) * chartH;

  return (
    <div className="rounded-2xl border border-oilfield-700/80 bg-[#0c1527] p-5 shadow-xl space-y-4">
      {/* Chart Header & Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-oilfield-700/60">
        <div className="flex items-center gap-2.5">
          <div className="p-2 rounded-xl bg-cyan-950/60 border border-cyan-800/80 text-cyan-400">
            <TrendingUp className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white flex items-center gap-2">
              <span>Production & Telemetry Trend Curve</span>
              <span className="font-mono text-cyan-300 font-bold text-xs">({wellCode})</span>
            </h3>
            <p className="text-[11px] text-slate-400">
              Multi-parameter surveillance trend (Water Cut % vs Separator Pressure vs Gross Rate)
            </p>
          </div>
        </div>

        {/* Time Range Selector */}
        <div className="flex items-center gap-1.5 bg-[#070c16] border border-oilfield-600 rounded-xl p-1 self-start sm:self-auto">
          {(["24h", "7d", "30d"] as const).map((r) => (
            <button
              key={r}
              onClick={() => setTimeRange(r)}
              className={`px-2.5 py-1 text-xs font-bold rounded-lg transition ${
                timeRange === r
                  ? "bg-cyan-600 text-white shadow-sm"
                  : "text-slate-400 hover:text-white"
              }`}
            >
              {r.toUpperCase()}
            </button>
          ))}
        </div>
      </div>

      {/* SVG Multi-Layer Chart */}
      <div className="relative overflow-hidden rounded-xl bg-[#070c16] border border-oilfield-700/40 p-2">
        <svg
          viewBox={`0 0 ${svgWidth} ${svgHeight}`}
          className="w-full h-56 select-none"
        >
          {/* Subtle Horizontal Grid lines */}
          {[0, 25, 50, 75, 100].map((val) => {
            const y = paddingY + chartH - (val / 100) * chartH;
            return (
              <g key={val}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={svgWidth - paddingX}
                  y2={y}
                  stroke="#1b2a4a"
                  strokeDasharray="4 4"
                  strokeWidth="1"
                />
                <text
                  x={paddingX - 8}
                  y={y + 3}
                  textAnchor="end"
                  fill="#64748b"
                  fontSize="10"
                  fontFamily="monospace"
                >
                  {val}%
                </text>
              </g>
            );
          })}

          {/* Alarm Threshold Reference Line */}
          <line
            x1={paddingX}
            y1={thresholdY}
            x2={svgWidth - paddingX}
            y2={thresholdY}
            stroke="#f59e0b"
            strokeDasharray="6 4"
            strokeWidth="1.5"
          />
          <text
            x={svgWidth - paddingX - 4}
            y={thresholdY - 6}
            textAnchor="end"
            fill="#f59e0b"
            fontSize="10"
            fontFamily="monospace"
            fontWeight="bold"
          >
            Threshold: {threshold}%
          </text>

          {/* Area Fill Gradient under Water Cut curve */}
          <defs>
            <linearGradient id="wcAreaGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.25" />
              <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Area polygon */}
          <polygon
            points={`${pointsWc[0].x},${paddingY + chartH} ${pointsWc
              .map((p) => `${p.x},${p.y}`)
              .join(" ")} ${pointsWc[pointsWc.length - 1].x},${paddingY + chartH}`}
            fill="url(#wcAreaGradient)"
          />

          {/* Water Cut Line */}
          <path
            d={pathWc}
            fill="none"
            stroke="#06b6d4"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Interactive Data Points */}
          {pointsWc.map((p, idx) => (
            <g
              key={idx}
              className="cursor-pointer group"
              onMouseEnter={() => setHoveredPoint(p.data)}
              onMouseLeave={() => setHoveredPoint(null)}
            >
              <circle
                cx={p.x}
                cy={p.y}
                r="4.5"
                fill="#070c16"
                stroke="#06b6d4"
                strokeWidth="2"
                className="transition-all hover:scale-125"
              />
              <text
                x={p.x}
                y={svgHeight - 8}
                textAnchor="middle"
                fill="#94a3b8"
                fontSize="10"
                fontFamily="monospace"
              >
                {p.data.timeLabel}
              </text>
            </g>
          ))}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredPoint && (
          <div className="absolute top-4 right-4 bg-[#0c1527]/95 border border-cyan-500/60 rounded-xl p-3 shadow-xl backdrop-blur-md text-xs space-y-1.5 pointer-events-none animate-in fade-in zoom-in-95 duration-100">
            <div className="text-[11px] font-mono font-bold text-cyan-300 border-b border-oilfield-700/60 pb-1">
              {hoveredPoint.timeLabel} Telemetry
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-slate-400">Water Cut:</span>
              <span className="font-mono font-bold text-cyan-300">{hoveredPoint.waterCut}%</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-slate-400">Sep Pressure:</span>
              <span className="font-mono font-bold text-amber-300">{hoveredPoint.pressure} psi</span>
            </div>
            <div className="flex items-center justify-between gap-4">
              <span className="text-slate-400">Gross Flow:</span>
              <span className="font-mono font-bold text-emerald-300">{hoveredPoint.flowRate} bpd</span>
            </div>
          </div>
        )}
      </div>

      {/* Chart Footer Legend */}
      <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-slate-400 pt-1">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-1 bg-cyan-400 rounded-full"></span>
            <span>Water Cut (%)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="w-3 h-0.5 border-b border-dashed border-amber-400"></span>
            <span className="text-amber-400">Alarm Threshold</span>
          </div>
        </div>

        <span className="text-[11px] text-slate-500 font-mono">
          Hover over points to inspect telemetry details
        </span>
      </div>
    </div>
  );
}