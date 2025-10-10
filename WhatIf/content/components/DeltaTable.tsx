import React from "react";
import { Box, Typography, Table, TableBody, TableCell, TableHead, TableRow } from "@mui/material";

export type KpiBundle = {
  avgCycleMin: number;
  avgWaitMin: number;
  avgTotalCost: number;
  avgTotalResource: number;
};

function deltaPct(a: number, b: number): string {
  if (!Number.isFinite(a) || a === 0) return "—";
  const pct = ((b - a) / a) * 100;
  const sign = pct > 0 ? "+" : "";
  return `${sign}${pct.toFixed(1)}%`;
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
  return (
    <Box sx={{ mt: 3 }}>
      <Typography variant="h6" sx={{
                fontFamily: "'Roboto', sans-serif",
                fontWeight: 700,
                fontSize: "1.25rem",
                color: "#000000ff", 
                lineHeight: 1.2,
              }}
            >
              {title}
            </Typography>
      <Table size="medium">
        <TableHead>
          <TableRow>
            <TableCell><b>KPI</b></TableCell>
            <TableCell><b>{nameA}</b></TableCell>
            <TableCell><b>{nameB}</b></TableCell>
            <TableCell><b>Absolute Δ</b></TableCell>
            <TableCell><b>Δ % (vs {nameA})</b></TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          <TableRow>
            <TableCell><b>Avg cycle time (min)</b></TableCell>
            <TableCell>{kpiA.avgCycleMin.toFixed(2)}</TableCell>
            <TableCell>{kpiB.avgCycleMin.toFixed(2)}</TableCell>
            <TableCell>{(kpiB.avgCycleMin - kpiA.avgCycleMin).toFixed(2)}</TableCell>
            <TableCell>{deltaPct(kpiA.avgCycleMin, kpiB.avgCycleMin)}</TableCell>
          </TableRow>

          <TableRow>
            <TableCell><b>Avg waiting time (min)</b></TableCell>
            <TableCell>{kpiA.avgWaitMin.toFixed(2)}</TableCell>
            <TableCell>{kpiB.avgWaitMin.toFixed(2)}</TableCell>
            <TableCell>{(kpiB.avgWaitMin - kpiA.avgWaitMin).toFixed(2)}</TableCell>
            <TableCell>{deltaPct(kpiA.avgWaitMin, kpiB.avgWaitMin)}</TableCell>
          </TableRow>

          <TableRow>
            <TableCell><b>Avg total cost (€)</b></TableCell>
            <TableCell>{kpiA.avgTotalCost.toFixed(2)}</TableCell>
            <TableCell>{kpiB.avgTotalCost.toFixed(2)}</TableCell>
            <TableCell>{(kpiB.avgTotalCost - kpiA.avgTotalCost).toFixed(2)}</TableCell>
            <TableCell>{deltaPct(kpiA.avgTotalCost, kpiB.avgTotalCost)}</TableCell>
          </TableRow>

          <TableRow>
            <TableCell><b>Avg total resource consumption</b></TableCell>
            <TableCell>{kpiA.avgTotalResource.toFixed(2)}</TableCell>
            <TableCell>{kpiB.avgTotalResource.toFixed(2)}</TableCell>
            <TableCell>{(kpiB.avgTotalResource - kpiA.avgTotalResource).toFixed(2)}</TableCell>
            <TableCell>{deltaPct(kpiA.avgTotalResource, kpiB.avgTotalResource)}</TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </Box>
  );
}
