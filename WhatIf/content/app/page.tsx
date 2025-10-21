"use client";

import React, { useEffect, useMemo, useState } from "react";
import { Alert, Box, Chip, CircularProgress, Divider, FormControl, InputLabel, MenuItem, Select, Stack, Tab, Tabs, Typography, Button, FormHelperText, Fab } from "@mui/material";
import ErrorIcon from "@mui/icons-material/Error";
import KeyboardArrowUpIcon from "@mui/icons-material/KeyboardArrowUp";

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
import ResourceUtilizationTable, { ScenarioUtilization } from "@/components/ResourceUtilizationTable";

import { API_BASE } from "@/utils/api";

/* ----------- CONFIG: URL Home (Interface) ----------- */
const INTERFACE_HOME_URL =
  process.env.NEXT_PUBLIC_INTERFACE_HOME_URL || "http://localhost:6660";

/* ----------- Helpers & tipi ----------- */
type RawDuration = {
  activity: string;
  avg_duration: number;
  min_duration: number;
  max_duration: number;
  min_traceId: string;
  max_traceId: string;
};
type RawBreakdown = {
  activity: string;
  avg_cycle_time: number;
  avg_waiting_time: number;
  avg_processing_time: number;
};
type RawCost = {
  activity: string;
  avg_fixed_cost?: number;
  avg_variable_cost?: number;
  avg_total_cost: number;
};

const mean = (arr: number[]) =>
  arr?.length
    ? arr.reduce((a, b) => a + (Number.isFinite(b) ? b : 0), 0) / arr.length
    : 0;


const estimateAvgPercentageUtilization = (result: any): number => {
  const arr = (result?.resource_utilization ?? []) as any[];
  if (!Array.isArray(arr) || arr.length === 0) return 0;
  const vals = arr
    .map((x) => Number(x?.percentage_utilization) || 0)
    .filter(Number.isFinite);
  return mean(vals);
};

const extractKpis = (result: any): KpiBundle => {
  const breakdown: RawBreakdown[] = (result?.breakdown ?? []) as RawBreakdown[];
  const costs: RawCost[] = (result?.costs ?? []) as RawCost[];
  const avgCycleMin = mean(
    breakdown.map((x) => Number(x.avg_cycle_time) || 0)
  );
  const avgWaitMin = mean(
    breakdown.map((x) => Number(x.avg_waiting_time) || 0)
  );
  const avgTotalCost = mean(
    costs.map((x) => Number(x.avg_total_cost) || 0)
  );
  const percentageUtilization = estimateAvgPercentageUtilization(result);
  return { avgCycleMin, avgWaitMin, avgTotalCost, percentageUtilization };
};

const buildActivitySummary = (
  durations: RawDuration[] = [],
  breakdown: RawBreakdown[] = [],
  costs: RawCost[] = []
): ActivitySummary[] => {
  const byActivity = (arr: any[]) =>
    arr.reduce((acc, o) => {
      acc[o.activity] = o;
      return acc;
    }, {} as Record<string, any>);
  const d = byActivity(durations),
    b = byActivity(breakdown),
    c = byActivity(costs);
  const names = new Set([
    ...Object.keys(d),
    ...Object.keys(b),
    ...Object.keys(c),
  ]);
  const safe = (n: number | undefined) => (n !== undefined && !isNaN(n) ? n : 0);
  return Array.from(names).map((act) => ({
    activity: act,
    waitingTimeMin: 0,
    waitingTimeAvg: safe(b[act]?.avg_waiting_time),
    waitingTimeMax: 0,
    durationMin: safe(d[act]?.min_duration),
    durationAvg: safe(d[act]?.avg_duration),
    durationMax: safe(d[act]?.max_duration),
    durationOverMin: 0,
    durationOverAvg: safe(b[act]?.avg_cycle_time),
    durationOverMax: 0,
    costMin: 0,
    costAvg: safe(c[act]?.avg_total_cost),
    costMax: 0,
  }));
};

type TimeUnit = "min" | "sec" | "hour" | "day";
const convertTimeValue = (value: number, unit: TimeUnit) =>
  unit === "sec"
    ? value * 60
    : unit === "hour"
    ? value / 60
    : unit === "day"
    ? value / 1440
    : value;
const formatTimeLabel = (unit: TimeUnit) =>
  unit === "sec" ? "(sec)" : unit === "hour" ? "(h)" : unit === "day" ? "(days)" : "(min)";

/* ----------- Component ----------- */
export default function Page() {
  // query: ?root=<string>&scenarios=0,1,2
  const [root, setRoot] = useState<string | null>(null);
  const [scenarioIds, setScenarioIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // dati multi-scenario
  const [scenariosData, setScenariosData] = useState<Record<string, any>>({});
  const [scenarioOrder, setScenarioOrder] = useState<string[]>([]);

  // BPMN viewer
  const [bpmnFile, setBpmnFile] = useState<File | null>(null);

  // UI
  const [tab, setTab] = useState<"per-scenario" | "compare">("per-scenario");
  const [selectedScenario, setSelectedScenario] = useState<string | null>(null);
  const [timeUnit, setTimeUnit] = useState<TimeUnit>("min");

  // --- multi-selezione per CHARTS/HEATMAPS (N scenari) ---
  const [selectedIds, setSelectedIds] = useState<string[]>([]);

  // --- selezione dedicata per la DeltaTable (max 2 scenari) ---
  const [tableCompareIds, setTableCompareIds] = useState<string[]>([]);
  const handleTableSelectChange = (e: any) => {
    const next = e.target.value as string[];
    if (next.length <= 2) {
      setTableCompareIds(next);
    } else {
      const uniq = Array.from(new Set(next));
      setTableCompareIds(uniq.slice(-2)); // mantieni le ultime 2 scelte
    }
  };

  // Leggi parametri da URL
  useEffect(() => {
    const sp = new URLSearchParams(window.location.search);
    const rt = sp.get("root");
    const sc =
      sp
        .get("scenarios")
        ?.split(",")
        .map((s) => s.trim())
        .filter(Boolean) ?? [];
    setRoot(rt);
    setScenarioIds(sc);
    setSelectedScenario(sc[0] ?? null);
  }, []);

  // Fetch BPMN + multi metrics
  useEffect(() => {
    if (!root || scenarioIds.length < 2) return;
    (async () => {
      try {
        setLoading(true);
        setError(null);

        // BPMN dalla root
        const bpmnRes = await fetch(
          `${API_BASE}/api/bpmn-from-root?root=${encodeURIComponent(root)}`
        );
        if (bpmnRes.ok) {
          const xml = await bpmnRes.text();
          const blob = new Blob([xml], { type: "text/xml" });
          setBpmnFile(new File([blob], "model.bpmn", { type: "text/xml" }));
        } else {
          throw new Error("BPMN not available in selected root");
        }

        // metriche multi-scenario
        const url = `${API_BASE}/api/analyze-multi-from-uploads?root=${encodeURIComponent(
          root
        )}&scenarios=${encodeURIComponent(scenarioIds.join(","))}`;
        const r = await fetch(url);
        if (!r.ok) {
          const t = await r.text();
          throw new Error(`Analyze error (${r.status}): ${t}`);
        }
        const json = await r.json();
        setScenarioOrder(json.scenario_order ?? scenarioIds);
        setScenariosData(json.scenarios ?? {});
      } catch (e: any) {
        setError(e?.message ?? "Unexpected error");
      } finally {
        setLoading(false);
      }
    })();
  }, [root, scenarioIds.join(",")]);

  // Defaults per multi-select e DeltaTable quando arrivano i dati
  useEffect(() => {
    if (scenarioOrder.length) setSelectedIds(scenarioOrder);
    if (scenarioOrder.length >= 2)
      setTableCompareIds([scenarioOrder[0], scenarioOrder[1]]);
    else setTableCompareIds([]);
  }, [scenarioOrder.join(",")]);

  // helpers per UI 
  const handleScrollTop = () => window.scrollTo({ top: 0, behavior: "smooth" });
  const names = scenarioOrder;
  const current = selectedScenario ? scenariosData[selectedScenario] : null;
  const activitySummary = useMemo(
    () =>
      current
        ? buildActivitySummary(
            current?.durations,
            current?.breakdown,
            current?.costs
          )
        : [],
    [current]
  );

  // --- DERIVATE per COMPARISON basate sulla selezione multipla ---
  const selectedNames = useMemo(
    () => selectedIds.filter((id) => scenarioOrder.includes(id)),
    [selectedIds.join(","), scenarioOrder.join(",")]
  );

  const compareRowsSelected: CompareDatum[] = useMemo(() => {
    const rows: CompareDatum[] = [];
    const add = (metric: string, getter: (x: any) => number) => {
      const row: any = { metric };
      for (const s of selectedNames)
        row[s] = Number(getter(scenariosData[s] ?? {}).toFixed(2));
      rows.push(row);
    };
    const getKPIs = (x: any): KpiBundle => {
      const breakdown: RawBreakdown[] = (x?.breakdown ?? []) as RawBreakdown[];
      const costs: RawCost[] = (x?.costs ?? []) as RawCost[];
      const avgCycleMin = mean(
        breakdown.map((o) => Number(o.avg_cycle_time) || 0)
      );
      const avgWaitMin = mean(
        breakdown.map((o) => Number(o.avg_waiting_time) || 0)
      );
      const avgTotalCost = mean(
        costs.map((o) => Number(o.avg_total_cost) || 0)
      );
      return {
        avgCycleMin,
        avgWaitMin,
        avgTotalCost,
        percentageUtilization: estimateAvgPercentageUtilization(x),
      };
    };
    if (selectedNames.length) {
      add("Avg cycle time", (x) => getKPIs(x).avgCycleMin);
      add("Avg waiting time", (x) => getKPIs(x).avgWaitMin);
      add("Avg total cost", (x) => getKPIs(x).avgTotalCost);
    }
    return rows;
  }, [scenariosData, selectedNames.join(",")]);

  const radarDataSelected: RadarKpi[] = useMemo(
    () =>
      selectedNames.map((name) => {
        const v = extractKpis(scenariosData[name] ?? {});
        return { name, ...v };
      }),
    [scenariosData, selectedNames.join(",")]
  );

  // Per la DeltaTable: prendi i 2 scelti
  const tableA = tableCompareIds[0] ? scenariosData[tableCompareIds[0]] : null;
  const tableB = tableCompareIds[1] ? scenariosData[tableCompareIds[1]] : null;
  const tableNameA = tableCompareIds[0] ?? "";
  const tableNameB = tableCompareIds[1] ?? "";

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Stack alignItems="center" spacing={2}>
          <CircularProgress />
          <Typography>Loading multi-scenario analysis…</Typography>
        </Stack>
      </div>
    );
  }

  if (error || !bpmnFile || !names.length) {
    return (
      <div className="min-h-screen p-6 flex items-center justify-center">
        <Alert icon={<ErrorIcon fontSize="inherit" />} severity="error">
          {error ?? "Missing data"}
        </Alert>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6 flex flex-col items-center">
      <div className="w-full max-w-7xl">
        <h1 className="text-3xl font-bold text-gray-800 mb-1 text-center">
          What-If: Multi-scenario
        </h1>

        {/* Pulsante HOME */}
        <Box sx={{ display: "flex", justifyContent: "right", mb: 2 }}>
          <Button
            variant="contained"
            color="primary"
            onClick={() => (window.location.href = INTERFACE_HOME_URL)}
          >
            ⬅ Home
          </Button>
        </Box>

        <Typography className="text-center text-gray-600 mb-6">
          Root: <code>{root}</code> — Scenari:{" "}
          <code>{names.join(", ")}</code>
        </Typography>

        <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 3, mt: 1 }}>
          <Tab value="per-scenario" label="Per-scenario" />
          <Tab value="compare" label="Multi-Scenario comparison" />
        </Tabs>

        {/* -------------- PER-SCENARIO -------------- */}
        {tab === "per-scenario" && (
          <div className="mt-2">
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
              <FormControl size="small">
                <InputLabel id="scenario-label">Scenario</InputLabel>
                <Select
                  labelId="scenario-label"
                  value={selectedScenario ?? names[0]}
                  label="Scenario"
                  onChange={(e) => setSelectedScenario(e.target.value as string)}
                  sx={{ minWidth: 160 }}
                >
                  {names.map((s) => (
                    <MenuItem key={s} value={s}>
                      {s}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Box>

            {selectedScenario ? (
              <>
                <BpmnViewerBox
                  file={bpmnFile}
                  height={460}
                  title={`Scenario ${selectedScenario} — BPMN`}
                  onClose={() => null}
                />

                {/* Summary & charts */}
                {current?.simulation_summary && (
                  <div className="mt-6">
                    <SummaryTable data={current.simulation_summary} />
                  </div>
                )}
                {activitySummary.length > 0 && (
                  <ActivitySummaryTable data={activitySummary} />
                )}
                {current?.durations?.length > 0 && (
                  <DurationChart data={current.durations} />
                )}
                {current?.breakdown?.length > 0 && (
                  <BreakdownChart data={current.breakdown} />
                )}

                {/* Heatmap */}
                {current?.bottleneck?.length > 0 && (
                  <div className="mt-6">
                    <ScenarioHeatmapSection
                      title={`Scenario ${selectedScenario} – Heatmap`}
                      bpmnFile={bpmnFile}
                      rows={current.bottleneck as BottleneckRow[]}
                    />
                  </div>
                )}

                {current?.costs?.length > 0 && (
                  <CostChart data={current.costs} />
                )}
                {current?.itemCosts?.length > 0 && (
                  <ItemCostPieChart data={current.itemCosts} />
                )}
                {current?.itemDurations?.length > 0 && (
                  <ItemDurationPieChart data={current.itemDurations} />
                )}
                {current?.resource_bubble?.length > 0 && (
                  <ResourceUsageBubble data={current.resource_bubble} />
                )}
              </>
            ) : (
              <Alert severity="info">Seleziona uno scenario</Alert>
            )}
          </div>
        )}

        {/* -------------- COMPARISON -------------- */}
        {tab === "compare" && (
          <div className="mt-2">
            {/* MULTI-SELECT (charts & heatmaps) */}
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              sx={{ mb: 2 }}
            >
              <FormControl sx={{ minWidth: 320 }}>
                <InputLabel id="sel-multi">
                  Scenarios (charts & heatmaps)
                </InputLabel>
                <Select
                  labelId="sel-multi"
                  label="Scenarios (charts & heatmaps)"
                  multiple
                  value={selectedIds}
                  onChange={(e) => setSelectedIds(e.target.value as string[])}
                  renderValue={(ids) => (ids as string[]).join(", ")}
                >
                  {names.map((n) => (
                    <MenuItem key={n} value={n}>
                      {n}
                    </MenuItem>
                  ))}
                </Select>
                <FormHelperText>
                  Seleziona uno o più scenari da visualizzare nei grafici e
                  nelle heatmap.
                </FormHelperText>
              </FormControl>
            </Stack>

            {/* Time unit + charts */}
            <Box sx={{ display: "flex", alignItems: "center", gap: 2, mb: 2 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                Time unit:
              </Typography>
              <Select
                size="small"
                value={timeUnit}
                onChange={(e) => setTimeUnit(e.target.value as TimeUnit)}
                sx={{ minWidth: 120 }}
              >
                <MenuItem value="min">Minutes</MenuItem>
                <MenuItem value="sec">Seconds</MenuItem>
                <MenuItem value="hour">Hours</MenuItem>
                <MenuItem value="day">Days</MenuItem>
              </Select>
            </Box>

            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              alignItems="stretch"
            >
              <Box sx={{ flex: 1, minWidth: 280 }}>
                <CompareBarChart
                  title={`Cycle & Waiting ${formatTimeLabel(timeUnit)}`}
                  data={(() => {
                    const rows = compareRowsSelected
                      .filter((r) => r.metric.includes("time"))
                      .map((r) => {
                        const row: any = { metric: r.metric };
                        for (const s of selectedNames) {
                          row[s] = convertTimeValue(
                            Number((r as any)[s] ?? 0),
                            timeUnit
                          );
                        }
                        return row;
                      });
                    return rows;
                  })()}
                  scenarioKeys={selectedNames}
                  valueFormatter={(v) => v.toFixed(2)}
                />
              </Box>
              <Box sx={{ flex: 1, minWidth: 280 }}>
                <CompareBarChart
                  title="Average Total Cost (€)"
                  data={compareRowsSelected.filter((r) =>
                    r.metric.includes("cost")
                  )}
                  scenarioKeys={selectedNames}
                />
              </Box>
            </Stack>

            {selectedNames.length >= 1 && (
              <Box sx={{ mt: 3 }}>
                <CompareRadar scenarios={radarDataSelected} />
              </Box>
            )}

            {/* Resource Utilization Table */}
            {selectedNames.length > 0 && (
              <Box sx={{ mt: 3 }}>
                <ResourceUtilizationTable
                  title="Resource percentage utilization by scenario (%)"
                  scenarios={
                    selectedNames.map((sn) => ({
                      name: sn,
                      rows: (scenariosData[sn]?.resource_utilization ?? []) as any[],
                    })) as ScenarioUtilization[]
                  }
                  height={420}
                />
              </Box>
            )}
            
            {/* Delta table: selezione dedicata (max 2) */}
            <Divider sx={{ my: 3 }}>
              <Chip label="Compare table: pick up to 2 scenarios" />
            </Divider>
            <Stack
              direction={{ xs: "column", md: "row" }}
              spacing={2}
              sx={{ mb: 2 }}
            >
              <FormControl sx={{ minWidth: 320 }}>
                <InputLabel id="sel-table">Scenarios for table (max 2)</InputLabel>
                <Select
                  labelId="sel-table"
                  label="Scenarios for table (max 2)"
                  multiple
                  value={tableCompareIds}
                  onChange={handleTableSelectChange}
                  renderValue={(ids) => (ids as string[]).join(", ")}
                >
                  {names.map((n) => (
                    <MenuItem key={n} value={n}>
                      {n}
                    </MenuItem>
                  ))}
                </Select>
                <FormHelperText>
                  Seleziona esattamente 2 scenari per compilare la Delta table.
                </FormHelperText>
              </FormControl>
            </Stack>

            {tableCompareIds.length === 2 && tableA && tableB ? (
              <DeltaTable
                nameA={tableNameA}
                nameB={tableNameB}
                kpiA={extractKpis(tableA)}
                kpiB={extractKpis(tableB)}
              />
            ) : (
              <Alert severity="info">
                Seleziona <b>esattamente due</b> scenari per la tabella di
                confronto.
              </Alert>
            )}

            {/* HEATMAP: una per ciascuno degli scenari selezionati */}
            {bpmnFile && selectedNames.length > 0 && (
              <Box sx={{ mt: 4 }}>
                <Typography variant="h5" sx={{ mb: 1.5 }}>
                  Flow Heatmaps
                </Typography>
                <Stack direction="column" spacing={2}>
                  {selectedNames.map((n) => {
                    const cur = scenariosData[n];
                    return cur?.bottleneck?.length > 0 ? (
                      <Box key={n}>
                        <ScenarioHeatmapSection
                          title={`Scenario ${n} – Heatmap`}
                          bpmnFile={bpmnFile}
                          rows={cur.bottleneck as BottleneckRow[]}
                        />
                      </Box>
                    ) : null;
                  })}
                </Stack>
              </Box>
            )}
          </div>
        )}
      </div>
      {/* Scroll to top */}
        <div style={{ position: "fixed", bottom: 30, right: 30, zIndex: 1000 }}>
          <Fab color="primary" size="large" onClick={() => handleScrollTop()} aria-label="scroll to top">
            <KeyboardArrowUpIcon />
          </Fab>
        </div>
    </div>
  );
}
