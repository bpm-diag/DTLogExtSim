import React from "react";
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  Paper,
  Tooltip,
} from "@mui/material";

export type KpiBundle = {
  avgCycleMin: number;
  avgWaitMin: number;
  avgTotalCost: number;
  percentageUtilization: number; // Avg resource utilization (%)
};

function fmt2(n: number) {
  return Number.isFinite(n) ? n.toFixed(2) : "—";
}
function deltaAbs(a: number, b: number) {
  if (!Number.isFinite(a) || !Number.isFinite(b)) return NaN;
  return b - a;
}
function deltaPctNum(a: number, b: number) {
  if (!Number.isFinite(a) || a === 0 || !Number.isFinite(b)) return NaN;
  return ((b - a) / a) * 100;
}

/**
 * Badge colorato per Absolute Δ o Δ %, con logica differenziata:
 * - metriche "lower is better": verde se negativo, rosso se positivo
 * - metriche "higher is better": verde se positivo, rosso se negativo
 */
function DeltaBadge({
  value,
  positiveIsGood,
  isPercent = false,
}: {
  value: number;
  positiveIsGood: boolean;
  isPercent?: boolean;
}) {
  if (!Number.isFinite(value)) return <>—</>;
  const positive = value > 0;
  let good = positiveIsGood ? positive : !positive;

  const bg = good ? "#16a34a" /* green-600 */ : "#ef4444" /* red-500 */;
  const text = "#ffffff";
  const sign = value > 0 ? "+" : "";

  return (
    <Box
      sx={{
        display: "inline-block",
        minWidth: 72,
        px: 1,
        py: 0.5,
        borderRadius: 1,
        background: bg,
        color: text,
        fontWeight: 700,
        textAlign: "right",
        boxShadow: "0 0 3px rgba(0,0,0,0.2)",
      }}
    >
      {`${sign}${value.toFixed(1)}${isPercent ? "%" : ""}`}
    </Box>
  );
}

export default function DeltaTable({
  title = "Scenario differences comparison (Δ)",
  nameA,
  nameB,
  kpiA,
  kpiB,
}: {
  title?: string;
  nameA: string;
  nameB: string;
  kpiA: KpiBundle;
  kpiB: KpiBundle;
}) {
  // pre-calcolo dei delta con info su quale KPI è "higher is better"
  const rows = [
    {
      label: "Avg cycle time (min)",
      a: kpiA.avgCycleMin,
      b: kpiB.avgCycleMin,
      abs: deltaAbs(kpiA.avgCycleMin, kpiB.avgCycleMin),
      pct: deltaPctNum(kpiA.avgCycleMin, kpiB.avgCycleMin),
      tooltip: "Lower is better",
      positiveIsGood: false,
    },
    {
      label: "Avg waiting time (min)",
      a: kpiA.avgWaitMin,
      b: kpiB.avgWaitMin,
      abs: deltaAbs(kpiA.avgWaitMin, kpiB.avgWaitMin),
      pct: deltaPctNum(kpiA.avgWaitMin, kpiB.avgWaitMin),
      tooltip: "Lower is better",
      positiveIsGood: false,
    },
    {
      label: "Avg total cost (€)",
      a: kpiA.avgTotalCost,
      b: kpiB.avgTotalCost,
      abs: deltaAbs(kpiA.avgTotalCost, kpiB.avgTotalCost),
      pct: deltaPctNum(kpiA.avgTotalCost, kpiB.avgTotalCost),
      tooltip: "Lower is better",
      positiveIsGood: false,
    },
    {
      label: "Avg resource utilization (%)",
      a: kpiA.percentageUtilization,
      b: kpiB.percentageUtilization,
      abs: deltaAbs(kpiA.percentageUtilization, kpiB.percentageUtilization),
      pct: deltaPctNum(kpiA.percentageUtilization, kpiB.percentageUtilization),
      tooltip: "Higher is better",
      positiveIsGood: true,
    },
  ];

  return (
    <Paper sx={{ mt: 3, p: 2, borderRadius: 2, boxShadow: 1 }}>
      <Typography
        variant="h6"
        sx={{
          fontFamily: "'Roboto', sans-serif",
          fontWeight: 700,
          fontSize: "1.1rem",
          color: "#1e293b",
          mb: 1,
        }}
      >
        {title}
      </Typography>

      <Box sx={{ borderRadius: 1, border: "1px solid #e5e7eb" }}>
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell>
                <b>KPI</b>
              </TableCell>
              <TableCell align="right">
                <b>Scenario {nameA}</b>
              </TableCell>
              <TableCell align="right">
                <b>Scenario {nameB}</b>
              </TableCell>
              <TableCell align="right">
                <b>Absolute Δ</b>
              </TableCell>
              <TableCell align="right">
                <b>Δ % (vs {nameA})</b>
              </TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            {rows.map((r) => (
              <TableRow key={r.label} hover>
                <TableCell sx={{ fontWeight: 600 }}>
                  <Tooltip title={r.tooltip} placement="top">
                    <span>{r.label}</span>
                  </Tooltip>
                </TableCell>

                <TableCell align="right">{fmt2(r.a)}</TableCell>
                <TableCell align="right">{fmt2(r.b)}</TableCell>

                <TableCell align="right">
                  <DeltaBadge
                    value={r.abs}
                    positiveIsGood={r.positiveIsGood}
                    isPercent={false}
                  />
                </TableCell>
                <TableCell align="right">
                  <DeltaBadge
                    value={r.pct}
                    positiveIsGood={r.positiveIsGood}
                    isPercent={true}
                  />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Paper>
  );
}
