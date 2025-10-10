"use client";
import React, { useEffect, useMemo, useState } from "react";
import { Alert, Box, Chip, CircularProgress, Divider, FormControl, InputLabel, MenuItem, Select, Stack, Tab, Tabs, Typography, Button} from "@mui/material";
import ErrorIcon from "@mui/icons-material/Error";

import DurationChart from "@/components/durationChart";
import BreakdownChart from "@/components/timeBreakdownChart";
import CostChart from "@/components/activityCost";
import ItemCostPieChart from "@/components/itemCost";
import ResourceUsageBubble from "@/components/resourceCostAndUsage";
import SummaryTable from "@/components/simSummary";
import ItemDurationPieChart from "@/components/ItemDurationPieChart";
import type { ActivitySummary } from "@/components/ActivitySummaryTable";
import ActivitySummaryTable from "@/components/ActivitySummaryTable";
import BpmnViewerBox from "@/components/BpmnViewer";
import CompareBarChart, { CompareDatum } from "@/components/CompareBarChart";
import DeltaTable, { KpiBundle } from "@/components/DeltaTable";
import ScenarioHeatmapSection, { BottleneckRow } from "@/components/ScenarioHeatmapSection";
import CompareRadar, { RadarKpi } from "@/components/CompareRadar";
import { API_BASE } from "@/utils/api";

const INTERFACE_HOME_URL = process.env.NEXT_PUBLIC_INTERFACE_HOME_URL || "http://localhost:6660";

/* helpers */
type RawBreakdown = { activity: string; avg_cycle_time: number; avg_waiting_time: number; avg_processing_time: number; };
type RawCost = { activity: string; avg_total_cost: number; };
const mean = (arr: number[]) => (arr?.length ? arr.reduce((a, b) => a + (Number.isFinite(b) ? b : 0), 0) / arr.length : 0);
const estimateAvgTotalResourceConsumption = (r: any): number => {
  const b: any[] = r?.resource_bubble ?? [];
  if (b.length) {
    const k = ["usage","total_usage","utilization","total_time","work_time","busy_time"].find(K=>Number.isFinite(Number(b[0]?.[K])));
    if (k) return mean(b.map(x => Number(x?.[k]) || 0).filter(Number.isFinite));
  }
  const br: RawBreakdown[] = r?.breakdown ?? [];
  return mean(br.map(x => Number(x.avg_processing_time) || 0));
};
const extractKpis = (r: any): KpiBundle => {
  const br: RawBreakdown[] = r?.breakdown ?? [];
  const cs: RawCost[] = r?.costs ?? [];
  return {
    avgCycleMin: mean(br.map(x => Number(x.avg_cycle_time) || 0)),
    avgWaitMin: mean(br.map(x => Number(x.avg_waiting_time) || 0)),
    avgTotalCost: mean(cs.map(x => Number(x.avg_total_cost) || 0)),
    avgTotalResource: estimateAvgTotalResourceConsumption(r),
  };
};

type TimeUnit = "min" | "sec" | "hour" | "day";
const convertTimeValue = (v: number, u: TimeUnit) => (u==="sec"? v*60 : u==="hour"? v/60 : u==="day"? v/1440 : v);
const formatTimeLabel = (u: TimeUnit) => (u==="sec"?"(sec)":u==="hour"?"(h)":u==="day"?"(days)":"(min)");

export default function Page() {
  // query: ?root=<string>&scenarios=0,1,2
  const [root, setRoot] = useState<string | null>(null);
  const [scenarioIds, setScenarioIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [bpmnFile, setBpmnFile] = useState<File | null>(null);
  const [scenariosData, setScenariosData] = useState<Record<string, any>>({});
  const [scenarioOrder, setScenarioOrder] = useState<string[]>([]);

  const [tab, setTab] = useState<"per-scenario" | "compare">("per-scenario");
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [timeUnit, setTimeUnit] = useState<TimeUnit>("min");

  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const rt = sp.get("root");
    const sc = sp.get("scenarios")?.split(",").map(s=>s.trim()).filter(Boolean) ?? [];
    setRoot(rt); setScenarioIds(sc); setSelectedScenario(sc[0] ?? null);
  }, []);

  useEffect(() => {
    if (!root || scenarioIds.length < 2) return;
    (async () => {
      try {
        setLoading(true); setError(null);

        // BPMN dalla root
        const bpmnRes = await fetch(`${API_BASE}/api/bpmn-from-root?root=${encodeURIComponent(root)}`);
        if (!bpmnRes.ok) throw new Error("BPMN not available in selected root");
        const xml = await bpmnRes.text();
        const blob = new Blob([xml], { type: "text/xml" });
        setBpmnFile(new File([blob], "model.bpmn", { type: "text/xml" }));

        // Analisi multi-scenario (media sulle run)
        const url = `${API_BASE}/api/analyze-multi-from-uploads?root=${encodeURIComponent(root)}&scenarios=${encodeURIComponent(scenarioIds.join(","))}`;
        const r = await fetch(url);
        if (!r.ok) throw new Error(`Analyze error (${r.status}): ${await r.text()}`);
        const json = await r.json();
        setScenarioOrder(json.scenario_order ?? scenarioIds);
        setScenariosData(json.scenarios ?? {});
      } catch (e: any) {
        setError(e?.message ?? "Unexpected error");
      } finally { setLoading(false); }
    })();
  }, [root, scenarioIds.join(",")]);

  const names = scenarioOrder;
  const current = selectedScenario ? scenariosData[selectedScenario] : null;

  // tabelle per attività
  const buildActivitySummary = (cur: any): ActivitySummary[] => {
    const d = (cur?.durations ?? []) as any[];
    const b = (cur?.breakdown ?? []) as any[];
    const c = (cur?.costs ?? []) as any[];
    const byA = (arr: any[]) => arr.reduce((acc,o)=>{acc[o.activity]=o;return acc;},{} as Record<string,any>);
    const D=byA(d), B=byA(b), C=byA(c);
    const acts = new Set([...Object.keys(D),...Object.keys(B),...Object.keys(C)]);
    const safe = (n:any)=> (n!==undefined && !isNaN(n)? Number(n):0);
    return Array.from(acts).map(a=>({
      activity:a,
      waitingTimeMin:0, waitingTimeAvg:safe(B[a]?.avg_waiting_time), waitingTimeMax:0,
      durationMin:safe(D[a]?.min_duration), durationAvg:safe(D[a]?.avg_duration), durationMax:safe(D[a]?.max_duration),
      durationOverMin:0, durationOverAvg:safe(B[a]?.avg_cycle_time), durationOverMax:0,
      costMin:0, costAvg:safe(C[a]?.avg_total_cost), costMax:0,
    }));
  };

  // comparison rows
  const compareRows: CompareDatum[] = useMemo(() => {
    const rows: CompareDatum[] = [];
    const add = (metric:string, g:(x:any)=>number) => {
      const row:any = { metric };
      for (const s of names) row[s] = Number(g(scenariosData[s] ?? {}).toFixed(2));
      rows.push(row);
    };
    const KPIs = (x:any): KpiBundle => {
      const br: RawBreakdown[] = x?.breakdown ?? [];
      const cs: RawCost[] = x?.costs ?? [];
      return {
        avgCycleMin: mean(br.map(o=>Number(o.avg_cycle_time)||0)),
        avgWaitMin:  mean(br.map(o=>Number(o.avg_waiting_time)||0)),
        avgTotalCost: mean(cs.map(o=>Number(o.avg_total_cost)||0)),
        avgTotalResource: estimateAvgTotalResourceConsumption(x),
      };
    };
    if (names.length) {
      add("Avg cycle time (min)", (x)=>KPIs(x).avgCycleMin);
      add("Avg waiting time (min)", (x)=>KPIs(x).avgWaitMin);
      add("Avg total cost (€)", (x)=>KPIs(x).avgTotalCost);
    }
    return rows;
  }, [scenariosData, names.join(",")]);

  const radarData: RadarKpi[] = useMemo(
    () => names.map(n => ({ name:n, ...extractKpis(scenariosData[n] ?? {}) })),
    [scenariosData, names.join(",")]
  );

  if (loading) {
    return (<div className="min-h-screen flex items-center justify-center">
      <Stack alignItems="center" spacing={2}><CircularProgress/><Typography>Loading multi-scenario…</Typography></Stack></div>);
  }
  if (error || !bpmnFile || !names.length) {
    return (<div className="min-h-screen p-6 flex items-center justify-center">
      <Alert icon={<ErrorIcon fontSize="inherit" />} severity="error">{error ?? "Missing data"}</Alert></div>);
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6 flex flex-col items-center">
      <div className="w-full max-w-7xl">
        <h1 className="text-3xl font-bold text-gray-800 mb-1 text-center">What-If: Multi-scenario</h1>
        <Typography className="text-center text-gray-600 mb-6">Root: <code>{root}</code> — Scenari: <code>{names.join(", ")}</code></Typography>

        <Tabs value={tab} onChange={(_,v)=>setTab(v)} sx={{ mb:3, mt:1 }}>
          <Tab value="per-scenario" label="Per-scenario" />
          <Tab value="compare" label="Comparison" />
        </Tabs>
        
        <Box sx={{ display: "flex", justifyContent: "right", mb: 3 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => window.location.href = INTERFACE_HOME_URL}
          >
            Home
          </Button>
        </Box>

        {/* PER-SCENARIO */}
        {tab==="per-scenario" && (
          <div className="mt-2">
            <Box sx={{ display:"flex", alignItems:"center", gap:2, mb:2 }}>
              <FormControl size="small">
                <InputLabel id="scenario-label">Scenario</InputLabel>
                <Select labelId="scenario-label" value={selectedScenario ?? names[0]} label="Scenario"
                        onChange={(e)=>setSelectedScenario(e.target.value as string)} sx={{ minWidth:160 }}>
                  {names.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                </Select>
              </FormControl>
            </Box>

            {selectedScenario && (() => {
              const cur = scenariosData[selectedScenario];
              return (
                <>
                  <BpmnViewerBox file={bpmnFile} height={460} title={`Scenario ${selectedScenario} — BPMN`} onClose={()=>null} />

                  {cur?.simulation_summary && <div className="mt-6"><SummaryTable data={cur.simulation_summary}/></div>}
                  {buildActivitySummary(cur).length>0 && <ActivitySummaryTable data={buildActivitySummary(cur)} />}
                  {cur?.durations?.length>0 && <DurationChart data={cur.durations} />}
                  {cur?.breakdown?.length>0 && <BreakdownChart data={cur.breakdown} />}

                  {cur?.bottleneck?.length>0 && (
                    <div className="mt-6">
                      <ScenarioHeatmapSection title={`Scenario ${selectedScenario} – Heatmap`} bpmnFile={bpmnFile}
                                              rows={(cur.bottleneck as BottleneckRow[])} />
                    </div>
                  )}

                  {cur?.costs?.length>0 && <CostChart data={cur.costs} />}
                  {cur?.itemCosts?.length>0 && <ItemCostPieChart data={cur.itemCosts} />}
                  {cur?.itemDurations?.length>0 && <ItemDurationPieChart data={cur.itemDurations} />}
                  {cur?.resource_bubble?.length>0 && <ResourceUsageBubble data={cur.resource_bubble} />}
                </>
              );
            })()}
          </div>
        )}

        {/* COMPARISON */}
        {tab==="compare" && (
          <div className="mt-2">
            <Box sx={{ display:"flex", alignItems:"center", gap:2, mb:2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight:600 }}>Time unit:</Typography>
              <Select size="small" value={timeUnit} onChange={(e)=>setTimeUnit(e.target.value as TimeUnit)} sx={{ minWidth:120 }}>
                <MenuItem value="min">Minutes</MenuItem>
                <MenuItem value="sec">Seconds</MenuItem>
                <MenuItem value="hour">Hours</MenuItem>
                <MenuItem value="day">Days</MenuItem>
              </Select>
            </Box>

            <Stack direction={{ xs:"column", md:"row" }} spacing={2} alignItems="stretch">
              <Box sx={{ flex:1, minWidth:280 }}>
                <CompareBarChart
                  title={`Cycle & Waiting ${formatTimeLabel(timeUnit)}`}
                  data={(() => {
                    const rows = compareRows.filter(r => r.metric.includes("time")).map(r => {
                      const row:any = { metric:r.metric };
                      for (const s of names) row[s] = convertTimeValue(Number((r as any)[s]), timeUnit);
                      return row;
                    });
                    return rows;
                  })()}
                  scenarioKeys={names}
                  valueFormatter={(v)=>v.toFixed(2)}
                />
              </Box>
              <Box sx={{ flex:1, minWidth:280 }}>
                <CompareBarChart
                  title="Average Total Cost (€)"
                  data={compareRows.filter(r => r.metric.includes("cost"))}
                  scenarioKeys={names}
                />
              </Box>
            </Stack>

            {names.length>=2 && <Box sx={{ mt:3 }}><CompareRadar scenarios={radarData} /></Box>}

            <Divider sx={{ my:3 }}><Chip label="Delta table (A vs B)" /></Divider>
            {names.length>=2 && (
              <DeltaTable
                nameA={names[0]}
                nameB={names[names.length-1]}
                kpiA={extractKpis(scenariosData[names[0]])}
                kpiB={extractKpis(scenariosData[names[names.length-1]])}
              />
            )}

            {selectedScenario && scenariosData[selectedScenario]?.bottleneck?.length>0 && bpmnFile && (
              <Box sx={{ mt:3 }}>
                {/* scenario selector*/}
                <FormControl size="small" sx={{ ml:"auto" }}>
                <InputLabel id="scenario-heatmap-label">Heatmap scenario</InputLabel>
                <Select labelId="scenario-heatmap-label" value={selectedScenario ?? names[0]}
                        label="Heatmap scenario" onChange={(e)=>setSelectedScenario(e.target.value as string)} sx={{ minWidth:170 }}>
                  {names.map(s => <MenuItem key={s} value={s}>{s}</MenuItem>)}
                </Select>
              </FormControl>
              {/* fine scenario selector */}
                <ScenarioHeatmapSection title={`Scenario ${selectedScenario} – Heatmap (comparison)`}
                  bpmnFile={bpmnFile} rows={(scenariosData[selectedScenario].bottleneck as BottleneckRow[])} />
              </Box>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
