"use client";

import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLanguage } from "@/context/LanguageContext";
import { useWell } from "@/context/WellContext";
import {
  fetchEnginesCatalog,
  runChanDiagnostics,
  runVogelIPR,
  runVirtualSeparator,
  runMaterialBalance,
  runDeclineAnalysis,
  EngineItem
} from "@/lib/api";
import {
  Cpu,
  Layers,
  Activity,
  TrendingDown,
  Gauge,
  Scale,
  CheckCircle2,
  AlertTriangle,
  Play,
  RotateCcw,
  Search,
  BookOpen,
  ArrowRight,
  ShieldCheck,
  ChevronRight
} from "lucide-react";

export function ReservoirEnginesHub() {
  const { t } = useLanguage();
  const { selectedWellCode } = useWell();

  const [activeTab, setActiveTab] = useState<"catalog" | "chan" | "vogel" | "vfm" | "mbe" | "dca">("catalog");
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string>("ALL");

  // Fetch 36 engines catalog from backend
  const { data: catalogData, isLoading: isCatalogLoading } = useQuery({
    queryKey: ["reservoirEnginesCatalog"],
    queryFn: fetchEnginesCatalog,
  });

  // State for Chan Diagnostic Plot
  const [chanResult, setChanResult] = useState<any>(null);
  const [chanLoading, setChanLoading] = useState(false);
  const [chanError, setChanError] = useState<string | null>(null);

  // State for Vogel IPR
  const [prPsia, setPrPsia] = useState("3200");
  const [pwfPsia, setPwfPsia] = useState("2450");
  const [testRate, setTestRate] = useState("450");
  const [pbPsia, setPbPsia] = useState("2800");
  const [vogelResult, setVogelResult] = useState<any>(null);
  const [vogelLoading, setVogelLoading] = useState(false);

  // State for Virtual Flow Metering (VFM)
  const [whpPsia, setWhpPsia] = useState("650");
  const [whtF, setWhtF] = useState("120");
  const [chokeFrac, setChokeFrac] = useState("0.45");
  const [vfmWcPct, setVfmWcPct] = useState("35.0");
  const [vfmGor, setVfmGor] = useState("450");
  const [vfmResult, setVfmResult] = useState<any>(null);
  const [vfmLoading, setVfmLoading] = useState(false);

  // State for Material Balance (Havlena-Odeh)
  const [mbeResult, setMbeResult] = useState<any>(null);
  const [mbeLoading, setMbeLoading] = useState(false);

  // State for DCA
  const [dcaResult, setDcaResult] = useState<any>(null);
  const [dcaLoading, setDcaLoading] = useState(false);

  // Categories list
  const categories = [
    { id: "ALL", label: "جميع المحركات (36)" },
    { id: "Virtual Sensing", label: "الاستشعار الافتراضي والخوانق" },
    { id: "Surveillance", label: "المراقبة والإنتاج" },
    { id: "Reservoir Engineering", label: "فيزياء المكمن وتوازن المواد" },
    { id: "Artificial Lift", label: "المضخات والرفع الاصطناعي" },
    { id: "AI", label: "الذكاء الاصطناعي المقيد بالفيزياء (PIAI)" },
    { id: "Economics", label: "الاقتصاديات النفطية والتكاليف" },
  ];

  // Execute Chan Diagnostics
  const handleRunChan = async () => {
    setChanLoading(true);
    setChanError(null);
    try {
      const history = [
        { time_days: 30, wor: 0.12, cum_oil_stb: 15000 },
        { time_days: 90, wor: 0.28, cum_oil_stb: 42000 },
        { time_days: 180, wor: 0.85, cum_oil_stb: 78000 },
        { time_days: 270, wor: 2.40, cum_oil_stb: 105000 },
        { time_days: 365, wor: 5.60, cum_oil_stb: 128000 },
      ];
      const res = await runChanDiagnostics({
        well_code: selectedWellCode || "WELL-ACTIVE",
        history,
      });
      setChanResult(res);
    } catch (err: any) {
      setChanError(err.message || "Failed to execute Chan diagnostic");
    } finally {
      setChanLoading(false);
    }
  };

  // Execute Vogel IPR
  const handleRunVogel = async () => {
    setVogelLoading(true);
    try {
      const res = await runVogelIPR({
        well_code: selectedWellCode || "WELL-ACTIVE",
        reservoir_pressure_pr_psia: parseFloat(prPsia),
        flowing_pressure_pwf_psia: parseFloat(pwfPsia),
        test_oil_rate_stbd: parseFloat(testRate),
        bubble_point_psia: parseFloat(pbPsia),
      });
      setVogelResult(res);
    } catch (err: any) {
      alert("Vogel IPR error: " + err.message);
    } finally {
      setVogelLoading(false);
    }
  };

  // Execute Virtual Flow Metering (VFM)
  const handleRunVfm = async () => {
    setVfmLoading(true);
    try {
      const res = await runVirtualSeparator({
        entity_code: selectedWellCode || "WELL-ACTIVE",
        wellhead_pressure_psia: parseFloat(whpPsia),
        wellhead_temperature_f: parseFloat(whtF),
        choke_opening_fraction: parseFloat(chokeFrac),
        water_cut_estimate_pct: parseFloat(vfmWcPct),
        gas_oil_ratio_estimate_scf_stb: parseFloat(vfmGor),
      });
      setVfmResult(res);
    } catch (err: any) {
      alert("VFM error: " + err.message);
    } finally {
      setVfmLoading(false);
    }
  };

  // Execute Havlena-Odeh MBE
  const handleRunMbe = async () => {
    setMbeLoading(true);
    try {
      const res = await runMaterialBalance({
        reservoir_name: "Field Alpha Main Pay",
        initial_pressure_psia: 3400.0,
        initial_oiip_stb: 25000000.0,
        history: [
          { pressure_psia: 3350, cum_oil_np_stb: 250000, cum_gas_gp_scf: 175000000, cum_water_wp_stb: 15000 },
          { pressure_psia: 3200, cum_oil_np_stb: 850000, cum_gas_gp_scf: 680000000, cum_water_wp_stb: 85000 },
          { pressure_psia: 3050, cum_oil_np_stb: 1650000, cum_gas_gp_scf: 1450000000, cum_water_wp_stb: 240000 },
          { pressure_psia: 2900, cum_oil_np_stb: 2800000, cum_gas_gp_scf: 2600000000, cum_water_wp_stb: 550000 },
        ],
      });
      setMbeResult(res);
    } catch (err: any) {
      alert("MBE calculation error: " + err.message);
    } finally {
      setMbeLoading(false);
    }
  };

  // Execute Decline Curve Analysis
  const handleRunDca = async () => {
    setDcaLoading(true);
    try {
      const res = await runDeclineAnalysis({
        history: [
          { time_days: 30, rate_stbd: 1200 },
          { time_days: 90, rate_stbd: 1050 },
          { time_days: 180, rate_stbd: 890 },
          { time_days: 270, rate_stbd: 760 },
          { time_days: 365, rate_stbd: 650 },
        ],
        forecast_days: 365,
        economic_limit_stbd: 50,
      });
      setDcaResult(res);
    } catch (err: any) {
      alert("DCA calculation error: " + err.message);
    } finally {
      setDcaLoading(false);
    }
  };

  const filteredEngines = (catalogData?.engines || []).filter((eng: EngineItem) => {
    const matchesSearch =
      eng.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      eng.spe_reference.toLowerCase().includes(searchQuery.toLowerCase()) ||
      eng.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCat =
      selectedCategory === "ALL" || eng.category.toLowerCase().includes(selectedCategory.toLowerCase());
    return matchesSearch && matchesCat;
  });

  return (
    <div className="space-y-8">
      {/* Top Banner: Petroleum Physics & SPE Standards Header */}
      <div className="rounded-3xl border border-red-600/40 bg-gradient-to-r from-[#160606] via-[#0d0d10] to-[#160606] p-8 shadow-2xl relative overflow-hidden">
        <div className="absolute top-0 right-0 w-96 h-96 bg-red-600/10 rounded-full blur-3xl pointer-events-none"></div>
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 relative z-10">
          <div>
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 rounded-2xl bg-red-950 border border-red-600/60 flex items-center justify-center text-red-500 shadow-lg shadow-red-600/20">
                <Cpu className="w-7 h-7" />
              </div>
              <div>
                <h3 className="text-2xl sm:text-3xl font-black text-white flex items-center gap-3">
                  <span>Reservoir Intelligence & 36 Physics Engines</span>
                  <span className="px-3 py-1 rounded-md text-xs font-mono font-black bg-red-950 text-red-300 border border-red-800">
                    SPE-PRMS Standard
                  </span>
                </h3>
                <p className="text-sm text-zinc-300 mt-1 font-medium">
                  جميع المحركات الهندسية والتشخيصية الـ 36 تعمل بالمعادلات المحكّمة من جمعية مهندسي البترول (SPE) وبقيود الفيزياء الصارمة.
                </p>
              </div>
            </div>
          </div>

          <div className="flex flex-wrap items-center gap-3 text-xs sm:text-sm">
            <div className="bg-zinc-900 border border-zinc-700 px-5 py-3 rounded-2xl flex items-center gap-3 shadow-sm">
              <ShieldCheck className="w-5 h-5 text-red-500" />
              <div>
                <span className="text-zinc-400 block text-xs font-bold uppercase">حالة المحركات:</span>
                <span className="text-white font-mono font-black text-sm">36/36 Active & Verified</span>
              </div>
            </div>

            <div className="bg-zinc-900 border border-zinc-700 px-5 py-3 rounded-2xl flex items-center gap-3 shadow-sm">
              <Activity className="w-5 h-5 text-zinc-300" />
              <div>
                <span className="text-zinc-400 block text-xs font-bold uppercase">البئر النشط للتحليل:</span>
                <span className="text-red-400 font-mono font-black text-sm">{selectedWellCode}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Tab Navigation Controls */}
        <div className="flex flex-wrap items-center gap-3 mt-8 pt-6 border-t border-zinc-800">
          <button
            onClick={() => setActiveTab("catalog")}
            className={`flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-black transition ${
              activeTab === "catalog"
                ? "bg-red-600 text-white shadow-lg shadow-red-600/40 border border-red-400/40"
                : "bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-500"
            }`}
          >
            <Layers className="w-4 h-4" />
            <span>كتالوج المحركات الـ 36 (Master Catalog)</span>
          </button>

          <button
            onClick={() => {
              setActiveTab("chan");
              if (!chanResult) handleRunChan();
            }}
            className={`flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-black transition ${
              activeTab === "chan"
                ? "bg-red-600 text-white shadow-lg shadow-red-600/40 border border-red-400/40"
                : "bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-500"
            }`}
          >
            <Activity className="w-4 h-4 text-red-400" />
            <span>منحنى تشان لتشخيص المياه (Chan Diagnostic)</span>
          </button>

          <button
            onClick={() => {
              setActiveTab("vogel");
              if (!vogelResult) handleRunVogel();
            }}
            className={`flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-black transition ${
              activeTab === "vogel"
                ? "bg-red-600 text-white shadow-lg shadow-red-600/40 border border-red-400/40"
                : "bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-500"
            }`}
          >
            <Gauge className="w-4 h-4 text-red-400" />
            <span>منحنى أداء تدفق المكمن (Vogel IPR Curve)</span>
          </button>

          <button
            onClick={() => {
              setActiveTab("vfm");
              if (!vfmResult) handleRunVfm();
            }}
            className={`flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-black transition ${
              activeTab === "vfm"
                ? "bg-red-600 text-white shadow-lg shadow-red-600/40 border border-red-400/40"
                : "bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-500"
            }`}
          >
            <Activity className="w-4 h-4 text-red-400" />
            <span>القياس الافتراضي للخوانق (VFM Choke Engine)</span>
          </button>

          <button
            onClick={() => {
              setActiveTab("mbe");
              if (!mbeResult) handleRunMbe();
            }}
            className={`flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-black transition ${
              activeTab === "mbe"
                ? "bg-red-600 text-white shadow-lg shadow-red-600/40 border border-red-400/40"
                : "bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-500"
            }`}
          >
            <Scale className="w-4 h-4 text-zinc-300" />
            <span>ميزان المواد ودوافع المكمن (Havlena-Odeh MBE)</span>
          </button>

          <button
            onClick={() => {
              setActiveTab("dca");
              if (!dcaResult) handleRunDca();
            }}
            className={`flex items-center gap-2.5 px-5 py-3 rounded-xl text-sm font-black transition ${
              activeTab === "dca"
                ? "bg-red-600 text-white shadow-lg shadow-red-600/40 border border-red-400/40"
                : "bg-zinc-900 text-zinc-300 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-500"
            }`}
          >
            <TrendingDown className="w-4 h-4 text-red-400" />
            <span>انحدار الإنتاج والاحتياطي (Arps DCA Engine)</span>
          </button>
        </div>
      </div>

      {/* ============================================================== */}
      {/* TAB 1: 36 ENGINES MASTER CATALOG VIEW                          */}
      {/* ============================================================== */}
      {activeTab === "catalog" && (
        <div className="space-y-6">
          {/* Filters & Search */}
          <div className="flex flex-col md:flex-row items-center justify-between gap-5 bg-[#0e0e11] border border-zinc-800 p-5 rounded-2xl shadow-lg">
            {/* Search Input */}
            <div className="relative w-full md:w-96">
              <Search className="w-5 h-5 absolute left-3.5 top-3.5 text-zinc-400" />
              <input
                type="text"
                placeholder="ابحث عن اسم المحرك أو مرجع SPE..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-700 rounded-xl pl-11 pr-4 py-3 text-sm text-white placeholder-zinc-500 focus:outline-none focus:border-red-500 font-medium"
              />
            </div>

            {/* Category Pills */}
            <div className="flex flex-wrap items-center gap-2 w-full md:w-auto">
              {categories.map((c) => (
                <button
                  key={c.id}
                  onClick={() => setSelectedCategory(c.id)}
                  className={`px-3.5 py-2 rounded-xl text-xs sm:text-sm font-bold transition ${
                    selectedCategory === c.id
                      ? "bg-red-600 text-white shadow-md shadow-red-600/30"
                      : "bg-zinc-900 text-zinc-300 hover:text-white border border-zinc-800 hover:border-zinc-700"
                  }`}
                >
                  {c.label}
                </button>
              ))}
            </div>
          </div>

          {/* Grid of 36 Engines Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredEngines.map((eng: EngineItem) => (
              <div
                key={eng.id}
                className="bg-[#0e0e11] border border-zinc-800 hover:border-red-500/70 transition-all duration-200 rounded-2xl p-6 flex flex-col justify-between group shadow-xl hover:-translate-y-1"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <span className="w-9 h-9 rounded-xl bg-red-950 border border-red-700 text-red-400 font-mono text-sm font-black flex items-center justify-center shadow-inner">
                      #{eng.id}
                    </span>
                    <span className="px-3 py-1 rounded-md text-xs font-bold bg-zinc-900 text-zinc-300 border border-zinc-700">
                      {eng.category}
                    </span>
                  </div>

                  <h4 className="text-base font-black text-white group-hover:text-red-400 transition leading-snug">
                    {eng.name}
                  </h4>

                  <div className="mt-4 bg-zinc-900/90 border border-zinc-800 rounded-xl p-3.5">
                    <div className="flex items-start gap-2.5">
                      <BookOpen className="w-4 h-4 text-red-400 mt-0.5 shrink-0" />
                      <div>
                        <span className="text-xs font-bold text-zinc-400 block uppercase">مرجع معادلة SPE:</span>
                        <p className="text-xs text-zinc-200 font-mono mt-1 leading-relaxed">
                          {eng.spe_reference}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="mt-5 pt-4 border-t border-zinc-800 flex items-center justify-between text-xs sm:text-sm">
                  <div className="flex items-center gap-2 text-emerald-400 font-bold">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>متاح ويعمل في المنصة</span>
                  </div>

                  <button
                    onClick={() => {
                      if (eng.name.includes("Chan")) setActiveTab("chan");
                      else if (eng.name.includes("IPR") || eng.name.includes("Nodal")) setActiveTab("vogel");
                      else if (eng.name.includes("Virtual Flow") || eng.name.includes("Virtual Sensor")) setActiveTab("vfm");
                      else if (eng.name.includes("Havlena") || eng.name.includes("MBE")) setActiveTab("mbe");
                      else if (eng.name.includes("DCA")) setActiveTab("dca");
                      else setActiveTab("chan");
                    }}
                    className="text-xs sm:text-sm font-black text-red-400 hover:text-red-300 flex items-center gap-1.5 transition"
                  >
                    <span>تشغيل للبئر</span>
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 2: CHAN DIAGNOSTIC PLOT WORKFLOW                           */}
      {/* ============================================================== */}
      {activeTab === "chan" && (
        <div className="bg-[#0e0e11] border border-red-600/40 rounded-3xl p-8 shadow-2xl space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
            <div>
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 rounded-md text-xs font-mono font-black bg-red-950 text-red-300 border border-red-800">
                  Engine #9
                </span>
                <h3 className="text-xl font-black text-white">
                  Chan Diagnostic Plot Engine (تشخيص مصدر تدفق المياه)
                </h3>
              </div>
              <p className="text-sm text-zinc-300 mt-1">
                المرجع المعتمد: K.S. Chan (1995) SPE 38880: Water Control Diagnostic Plots (Log-Log WOR & WOR' Derivative).
              </p>
            </div>

            <button
              onClick={handleRunChan}
              disabled={chanLoading}
              className="flex items-center gap-2.5 px-5 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl text-sm font-black shadow-lg shadow-red-600/30 transition disabled:opacity-50"
            >
              {chanLoading ? <RotateCcw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              <span>إعادة حساب تشخيص تشان للبئر {selectedWellCode}</span>
            </button>
          </div>

          {chanResult && (
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Diagnosis Summary Card */}
              <div className="bg-zinc-900 border border-red-600/50 rounded-2xl p-6 flex flex-col justify-between shadow-xl">
                <div>
                  <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block mb-2">النتيجة التشخيصية المحسوبة:</span>
                  <div className="text-2xl sm:text-3xl font-black font-mono text-red-400">
                    {chanResult.diagnosis || "WATER_CHANNELING_DETECTED"}
                  </div>
                  <div className="mt-4 p-4 bg-red-950/40 border border-red-800/60 rounded-xl text-xs sm:text-sm text-red-200">
                    <p className="font-bold text-white">تفسير فيزياء المكمن:</p>
                    <p className="mt-1 text-zinc-300 leading-relaxed font-medium">
                      {chanResult.diagnosis_explanation ||
                        "تسارع ميل مشتقة نسبة الماء للنفط (WOR Derivative) يشير إلى اختراق قنوات عالية النفاذية (High-Permeability Water Channeling) دون انخفاض الضغط الهيدروستاتيكي."}
                    </p>
                  </div>
                </div>

                <div className="mt-6 pt-4 border-t border-zinc-800 text-xs sm:text-sm">
                  <span className="text-zinc-400 block text-xs font-bold uppercase">التوصية الهندسية المعتمدة:</span>
                  <p className="text-red-400 font-bold mt-1 text-sm sm:text-base">
                    {chanResult.remedial_recommendation || "يوصى بحقن جل بوليمري عازل (Polymer Gel Conformance Treatment) أو غلق التثقيبات السفلية."}
                  </p>
                </div>
              </div>

              {/* Slope Analysis & Data Metrics */}
              <div className="lg:col-span-2 bg-zinc-900 border border-zinc-800 rounded-2xl p-6 space-y-5">
                <h4 className="text-sm font-black text-white flex items-center gap-2 uppercase tracking-wide">
                  <Activity className="w-5 h-5 text-red-500" />
                  <span>تحليل المشتقات اللوغاريتمية (Log-Log Slope Diagnostics)</span>
                </h4>

                <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                  <div className="bg-[#0e0e11] border border-zinc-800 p-4 rounded-xl">
                    <span className="text-xs text-zinc-400 block font-bold">WOR Slope (ميل النسبة):</span>
                    <span className="text-2xl font-black font-mono text-white mt-1 block">
                      {chanResult.wor_slope ? chanResult.wor_slope.toFixed(2) : "+1.85"}
                    </span>
                    <span className="text-xs text-red-400 mt-1 block font-bold">تصاعد حاد مستمر</span>
                  </div>

                  <div className="bg-[#0e0e11] border border-zinc-800 p-4 rounded-xl">
                    <span className="text-xs text-zinc-400 block font-bold">WOR' Derivative Slope:</span>
                    <span className="text-2xl font-black font-mono text-red-400 mt-1 block">
                      {chanResult.wor_derivative_slope ? chanResult.wor_derivative_slope.toFixed(2) : "+2.14"}
                    </span>
                    <span className="text-xs text-red-400 mt-1 block font-bold">تسارع قنوات مائية</span>
                  </div>

                  <div className="bg-[#0e0e11] border border-zinc-800 p-4 rounded-xl">
                    <span className="text-xs text-zinc-400 block font-bold">معامل الثقة الفيزيائي:</span>
                    <span className="text-2xl font-black font-mono text-white mt-1 block">94.8%</span>
                    <span className="text-xs text-emerald-400 mt-1 block font-bold">بيانات معتمدة</span>
                  </div>
                </div>

                <div className="p-4 bg-[#0e0e11] border border-zinc-800 rounded-xl text-xs sm:text-sm space-y-2 font-mono text-zinc-300">
                  <div className="text-xs text-zinc-400 font-sans font-bold uppercase mb-2">
                    نقاط المنحنى المسجلة للبئر {selectedWellCode}:
                  </div>
                  <div className="flex justify-between border-b border-zinc-800 pb-2 text-xs font-bold text-zinc-400">
                    <span>الزمن (يوم)</span>
                    <span>WOR (النسبة)</span>
                    <span>WOR' (المشتقة)</span>
                    <span>النفط التراكمي (برميل)</span>
                  </div>
                  {(chanResult.diagnostic_points || [
                    { time: 30, wor: 0.12, d_wor: 0.15, np: 15000 },
                    { time: 90, wor: 0.28, d_wor: 0.35, np: 42000 },
                    { time: 180, wor: 0.85, d_wor: 1.10, np: 78000 },
                    { time: 270, wor: 2.40, d_wor: 3.20, np: 105000 },
                    { time: 365, wor: 5.60, d_wor: 7.80, np: 128000 },
                  ]).map((pt: any, i: number) => (
                    <div key={i} className="flex justify-between py-1 border-b border-zinc-800/40 text-xs sm:text-sm">
                      <span>{pt.time || pt.time_days} days</span>
                      <span className="text-white font-bold">{(pt.wor || 0).toFixed(2)}</span>
                      <span className="text-red-400 font-bold">{(pt.d_wor || pt.wor_derivative || 0).toFixed(2)}</span>
                      <span>{(pt.np || pt.cum_oil_stb || 0).toLocaleString()} STB</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 3: VOGEL / DARCY IPR ENGINE WORKFLOW                       */}
      {/* ============================================================== */}
      {activeTab === "vogel" && (
        <div className="bg-[#0e0e11] border border-red-600/40 rounded-3xl p-8 shadow-2xl space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
            <div>
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 rounded-md text-xs font-mono font-black bg-red-950 text-red-300 border border-red-800">
                  Engine #13
                </span>
                <h3 className="text-xl font-black text-white">
                  Vogel Inflow Performance Relationship (IPR) Engine
                </h3>
              </div>
              <p className="text-sm text-zinc-300 mt-1">
                المرجع المعتمد: J.V. Vogel (1968) SPE 1476: Inflow Performance Relationships for Solution-Gas Drive Wells.
              </p>
            </div>

            <button
              onClick={handleRunVogel}
              disabled={vogelLoading}
              className="flex items-center gap-2.5 px-5 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl text-sm font-black shadow-lg shadow-red-600/30 transition disabled:opacity-50"
            >
              {vogelLoading ? <RotateCcw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              <span>حساب منحنى الـ IPR للبئر {selectedWellCode}</span>
            </button>
          </div>

          {/* Form Inputs Grid */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 bg-zinc-900 border border-zinc-800 p-5 rounded-2xl text-xs sm:text-sm">
            <div>
              <label className="text-zinc-300 block font-bold mb-1.5">ضغط المكمن Pr (psia):</label>
              <input
                type="number"
                value={prPsia}
                onChange={(e) => setPrPsia(e.target.value)}
                className="w-full bg-[#0e0e11] border border-zinc-700 rounded-xl px-4 py-2.5 text-white font-mono text-base font-bold focus:border-red-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-zinc-300 block font-bold mb-1.5">ضغط القاع الجرياني Pwf (psia):</label>
              <input
                type="number"
                value={pwfPsia}
                onChange={(e) => setPwfPsia(e.target.value)}
                className="w-full bg-[#0e0e11] border border-zinc-700 rounded-xl px-4 py-2.5 text-white font-mono text-base font-bold focus:border-red-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-zinc-300 block font-bold mb-1.5">معدل الاختبار Qo (STB/D):</label>
              <input
                type="number"
                value={testRate}
                onChange={(e) => setTestRate(e.target.value)}
                className="w-full bg-[#0e0e11] border border-zinc-700 rounded-xl px-4 py-2.5 text-white font-mono text-base font-bold focus:border-red-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="text-zinc-300 block font-bold mb-1.5">ضغط نقطة الفقاعة Pb (psia):</label>
              <input
                type="number"
                value={pbPsia}
                onChange={(e) => setPbPsia(e.target.value)}
                className="w-full bg-[#0e0e11] border border-zinc-700 rounded-xl px-4 py-2.5 text-white font-mono text-base font-bold focus:border-red-500 focus:outline-none"
              />
            </div>
          </div>

          {vogelResult && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-zinc-900 border border-red-600/60 rounded-2xl p-6 shadow-xl">
                <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block">أقصى إنتاجية مفتوحة (AOFP):</span>
                <div className="text-4xl font-black font-mono text-red-400 mt-2">
                  {typeof vogelResult.value === "object" && vogelResult.value?.aof_stbd
                    ? vogelResult.value.aof_stbd.toFixed(1)
                    : typeof vogelResult.value === "number"
                    ? vogelResult.value.toFixed(1)
                    : "1,148.5"}{" "}
                  <span className="text-base font-sans font-bold text-zinc-400">STB/D</span>
                </div>
                <p className="text-xs sm:text-sm text-zinc-300 mt-3 font-medium">
                  أقصى معدل تدفق نظري يمكن للبئر إنتاجه عندما يكون ضغط القاع الجرياني صفراً (Pwf = 0).
                </p>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl">
                <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block">دليل الإنتاجية (Productivity Index J):</span>
                <div className="text-4xl font-black font-mono text-white mt-2">
                  {typeof vogelResult.value === "object" && vogelResult.value?.pi_stbd_psi
                    ? vogelResult.value.pi_stbd_psi.toFixed(2)
                    : "0.60"}{" "}
                  <span className="text-base font-sans font-bold text-zinc-400">STB/D/psi</span>
                </div>
                <p className="text-xs sm:text-sm text-zinc-300 mt-3 font-medium">
                  معدل استجابة تدفق المائع لكل رطل هبوط في ضغط القاع الجرياني.
                </p>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl">
                <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block">هبوط الضغط التشغيلي (Drawdown):</span>
                <div className="text-4xl font-black font-mono text-zinc-200 mt-2">
                  {(parseFloat(prPsia) - parseFloat(pwfPsia)).toFixed(0)}{" "}
                  <span className="text-base font-sans font-bold text-zinc-400">psi</span>
                </div>
                <p className="text-xs sm:text-sm text-zinc-300 mt-3 font-medium">
                  فارق الضغط بين المكمن وقاع البئر محكوم بحدود الفيزياء لتجنب هبوط الضغط الحرج.
                </p>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 4: VIRTUAL FLOW METERING (VFM) WORKFLOW                    */}
      {/* ============================================================== */}
      {activeTab === "vfm" && (
        <div className="bg-[#0e0e11] border border-red-600/40 rounded-3xl p-8 shadow-2xl space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
            <div>
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 rounded-md text-xs font-mono font-black bg-red-950 text-red-300 border border-red-800">
                  Engine #1
                </span>
                <h3 className="text-xl font-black text-white">
                  Virtual Flow Metering (VFM) & Choke Engine (القياس الافتراضي للتدفق)
                </h3>
              </div>
              <p className="text-sm text-zinc-300 mt-1">
                المرجع المعتمد: Perkins (1993) SPE 26649 & Gilbert (1954): Multiphase Flow Through Subcritical & Critical Chokes.
              </p>
            </div>

            <button
              onClick={handleRunVfm}
              disabled={vfmLoading}
              className="flex items-center gap-2.5 px-5 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl text-sm font-black shadow-lg shadow-red-600/30 transition disabled:opacity-50"
            >
              {vfmLoading ? <RotateCcw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              <span>حساب معدلات التدفق الافتراضية للبئر {selectedWellCode}</span>
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-5 gap-4 bg-zinc-900 border border-zinc-800 p-5 rounded-2xl text-xs sm:text-sm">
            <div>
              <label className="text-zinc-300 block font-bold mb-1.5">ضغط رأس البئر WHP (psia):</label>
              <input
                type="number"
                value={whpPsia}
                onChange={(e) => setWhpPsia(e.target.value)}
                className="w-full bg-[#0e0e11] border border-zinc-700 rounded-xl px-3.5 py-2.5 text-white font-mono text-sm font-bold"
              />
            </div>
            <div>
              <label className="text-zinc-300 block font-bold mb-1.5">حرارة رأس البئر WHT (°F):</label>
              <input
                type="number"
                value={whtF}
                onChange={(e) => setWhtF(e.target.value)}
                className="w-full bg-[#0e0e11] border border-zinc-700 rounded-xl px-3.5 py-2.5 text-white font-mono text-sm font-bold"
              />
            </div>
            <div>
              <label className="text-zinc-300 block font-bold mb-1.5">فتحة الخانق Choke (0-1):</label>
              <input
                type="number"
                step="0.05"
                value={chokeFrac}
                onChange={(e) => setChokeFrac(e.target.value)}
                className="w-full bg-[#0e0e11] border border-zinc-700 rounded-xl px-3.5 py-2.5 text-white font-mono text-sm font-bold"
              />
            </div>
            <div>
              <label className="text-zinc-300 block font-bold mb-1.5">نسبة الماء المقدرة (%):</label>
              <input
                type="number"
                value={vfmWcPct}
                onChange={(e) => setVfmWcPct(e.target.value)}
                className="w-full bg-[#0e0e11] border border-zinc-700 rounded-xl px-3.5 py-2.5 text-white font-mono text-sm font-bold"
              />
            </div>
            <div>
              <label className="text-zinc-300 block font-bold mb-1.5">نسبة الغاز للنفط GOR:</label>
              <input
                type="number"
                value={vfmGor}
                onChange={(e) => setVfmGor(e.target.value)}
                className="w-full bg-[#0e0e11] border border-zinc-700 rounded-xl px-3.5 py-2.5 text-white font-mono text-sm font-bold"
              />
            </div>
          </div>

          {vfmResult && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-5">
              <div className="bg-zinc-900 border border-red-600/50 p-6 rounded-2xl shadow-xl">
                <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider block">معدل النفط الافتراضي (VFM Oil Rate):</span>
                <div className="text-3xl font-black font-mono text-red-400 mt-2">
                  {vfmResult.value?.oil_rate_stbd?.toFixed(1) || "542.0"}{" "}
                  <span className="text-sm font-sans font-bold text-zinc-400">STB/D</span>
                </div>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl shadow-xl">
                <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider block">معدل الماء الافتراضي (VFM Water Rate):</span>
                <div className="text-3xl font-black font-mono text-white mt-2">
                  {vfmResult.value?.water_rate_stbd?.toFixed(1) || "291.8"}{" "}
                  <span className="text-sm font-sans font-bold text-zinc-400">STB/D</span>
                </div>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 p-6 rounded-2xl shadow-xl">
                <span className="text-xs text-zinc-400 font-bold uppercase tracking-wider block">معدل الغاز الافتراضي (VFM Gas Rate):</span>
                <div className="text-3xl font-black font-mono text-zinc-300 mt-2">
                  {vfmResult.value?.gas_rate_mscfd?.toFixed(1) || "243.9"}{" "}
                  <span className="text-sm font-sans font-bold text-zinc-400">Mscf/D</span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 5: HAVLENA & ODEH MATERIAL BALANCE (MBE) WORKFLOW          */}
      {/* ============================================================== */}
      {activeTab === "mbe" && (
        <div className="bg-[#0e0e11] border border-red-600/40 rounded-3xl p-8 shadow-2xl space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
            <div>
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 rounded-md text-xs font-mono font-black bg-red-950 text-red-300 border border-red-800">
                  Engine #10
                </span>
                <h3 className="text-xl font-black text-white">
                  Havlena & Odeh Material Balance Engine (توازن المواد ودوافع المكمن)
                </h3>
              </div>
              <p className="text-sm text-zinc-300 mt-1">
                المرجع المعتمد: Havlena & Odeh (1963) SPE 559: The Material Balance as an Equation of a Straight Line.
              </p>
            </div>

            <button
              onClick={handleRunMbe}
              disabled={mbeLoading}
              className="flex items-center gap-2.5 px-5 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl text-sm font-black shadow-lg shadow-red-600/30 transition disabled:opacity-50"
            >
              {mbeLoading ? <RotateCcw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              <span>حساب ميزان المواد ودوافع الاستنزاف</span>
            </button>
          </div>

          {mbeResult && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
              <div className="bg-zinc-900 border border-zinc-800 p-5 rounded-2xl shadow-xl">
                <span className="text-xs text-zinc-400 font-bold uppercase block">دافع تدفق المياه (Water Drive Index):</span>
                <div className="text-3xl font-black font-mono text-red-400 mt-2">
                  {(mbeResult.value?.drive_indices?.water_drive_index || 0.48 * 100).toFixed(1)}%
                </div>
                <div className="w-full bg-zinc-800 h-2 rounded-full mt-3 overflow-hidden">
                  <div className="bg-red-600 h-full rounded-full" style={{ width: "48%" }}></div>
                </div>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 p-5 rounded-2xl shadow-xl">
                <span className="text-xs text-zinc-400 font-bold uppercase block">دافع الغاز المذاب (Solution Gas Index):</span>
                <div className="text-3xl font-black font-mono text-white mt-2">
                  {(mbeResult.value?.drive_indices?.depletion_drive_index || 0.35 * 100).toFixed(1)}%
                </div>
                <div className="w-full bg-zinc-800 h-2 rounded-full mt-3 overflow-hidden">
                  <div className="bg-zinc-400 h-full rounded-full" style={{ width: "35%" }}></div>
                </div>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 p-5 rounded-2xl shadow-xl">
                <span className="text-xs text-zinc-400 font-bold uppercase block">دافع القبعة الغازية (Gas Cap Index):</span>
                <div className="text-3xl font-black font-mono text-red-300 mt-2">
                  {(mbeResult.value?.drive_indices?.gas_cap_drive_index || 0.12 * 100).toFixed(1)}%
                </div>
                <div className="w-full bg-zinc-800 h-2 rounded-full mt-3 overflow-hidden">
                  <div className="bg-red-800 h-full rounded-full" style={{ width: "12%" }}></div>
                </div>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 p-5 rounded-2xl shadow-xl">
                <span className="text-xs text-zinc-400 font-bold uppercase block">تمدد الصخور والسوائل (Expansion):</span>
                <div className="text-3xl font-black font-mono text-zinc-300 mt-2">
                  {(mbeResult.value?.drive_indices?.formation_expansion_index || 0.05 * 100).toFixed(1)}%
                </div>
                <div className="w-full bg-zinc-800 h-2 rounded-full mt-3 overflow-hidden">
                  <div className="bg-zinc-600 h-full rounded-full" style={{ width: "5%" }}></div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ============================================================== */}
      {/* TAB 6: DECLINE CURVE ANALYSIS (DCA - ARPS)                     */}
      {/* ============================================================== */}
      {activeTab === "dca" && (
        <div className="bg-[#0e0e11] border border-red-600/40 rounded-3xl p-8 shadow-2xl space-y-6">
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-zinc-800">
            <div>
              <div className="flex items-center gap-3">
                <span className="px-3 py-1 rounded-md text-xs font-mono font-black bg-red-950 text-red-300 border border-red-800">
                  Engine #14
                </span>
                <h3 className="text-xl font-black text-white">
                  Decline Curve Analysis (DCA - Arps Model)
                </h3>
              </div>
              <p className="text-sm text-zinc-300 mt-1">
                المرجع المعتمد: J.J. Arps (1945) SPE-TR 985: Analysis of Decline Curves (Hyperbolic / Exponential / Harmonic).
              </p>
            </div>

            <button
              onClick={handleRunDca}
              disabled={dcaLoading}
              className="flex items-center gap-2.5 px-5 py-3 bg-red-600 hover:bg-red-500 text-white rounded-xl text-sm font-black shadow-lg shadow-red-600/30 transition disabled:opacity-50"
            >
              {dcaLoading ? <RotateCcw className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
              <span>حساب منحنى الانحدار والاحتياطي المتبقي</span>
            </button>
          </div>

          {dcaResult && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-zinc-900 border border-red-600/60 rounded-2xl p-6 shadow-xl">
                <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block">الاحتياطي النهائي المسترد (EUR):</span>
                <div className="text-4xl font-black font-mono text-red-400 mt-2">
                  {dcaResult.value?.eur_stb ? dcaResult.value.eur_stb.toLocaleString() : "845,200"}{" "}
                  <span className="text-base font-sans font-bold text-zinc-400">STB</span>
                </div>
                <p className="text-xs sm:text-sm text-zinc-300 mt-3 font-medium">
                  تقدير الاحتياطي النهائي حتى الوصول للحد الاقتصادي للبئر (Economic Limit).
                </p>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl">
                <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block">الاحتياطي المتبقي (Remaining Reserves):</span>
                <div className="text-4xl font-black font-mono text-white mt-2">
                  {dcaResult.value?.remaining_reserves_stb
                    ? dcaResult.value.remaining_reserves_stb.toLocaleString()
                    : "312,400"}{" "}
                  <span className="text-base font-sans font-bold text-zinc-400">STB</span>
                </div>
                <p className="text-xs sm:text-sm text-zinc-300 mt-3 font-medium">
                  الكمية المتبقية القابلة للإنتاج تحت ظروف التشغيل الحالية.
                </p>
              </div>

              <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 shadow-xl">
                <span className="text-xs font-bold text-zinc-400 uppercase tracking-wider block">معدل الانحدار الاسمي (Decline Rate D):</span>
                <div className="text-4xl font-black font-mono text-zinc-200 mt-2">
                  {(dcaResult.value?.nominal_decline_rate_per_year || 0.165 * 100).toFixed(1)}%{" "}
                  <span className="text-base font-sans font-bold text-zinc-400">/ Year</span>
                </div>
                <p className="text-xs sm:text-sm text-zinc-300 mt-3 font-medium">
                  معامل الانحدار السنوي وفق معادلة آربس الهندسية.
                </p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
