import * as React from "react";
import {
  Box,
  Typography,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  TableSortLabel,
  Paper,
  Tooltip,
} from "@mui/material";

type UtilRow = { resource: string; percentage_utilization: number };
export type ScenarioUtilization = {
  name: string;
  rows: UtilRow[];
};

type Order = "asc" | "desc";

/**
 * Gradiente invertito:
 * 0% → rosso scuro, 100% → verde vivo
 */
function colorFor(value: number) {
  const v = Math.max(0, Math.min(100, value));

  // definizione del gradiente 0=rosso, 100=verde
  const stops = [
    { p: 0, h: 0, s: 98, l: 24 },   // rosso scuro
    { p: 16, h: 8, s: 95, l: 47 },
    { p: 33, h: 28, s: 90, l: 51 },
    { p: 50, h: 55, s: 100, l: 50 },
    { p: 66, h: 74, s: 82, l: 49 },
    { p: 100, h: 120, s: 70, l: 45 }, // verde
  ];

  // interpolazione lineare tra due punti del gradiente
  const i = stops.findIndex((s) => v <= s.p);
  if (i <= 0) {
    const s = stops[0];
    return `hsl(${s.h}, ${s.s}%, ${s.l}%)`;
  }
  const prev = stops[i - 1];
  const next = stops[i];
  const ratio = (v - prev.p) / (next.p - prev.p);
  const h = prev.h + (next.h - prev.h) * ratio;
  const s = prev.s + (next.s - prev.s) * ratio;
  const l = prev.l + (next.l - prev.l) * ratio;
  return `hsl(${h}, ${s}%, ${l}%)`;
}

function compact(value: number) {
  return Number.isFinite(value) ? value.toFixed(1) : "—";
}

export default function ResourceUtilizationTable({
  title = "Resource utilization by scenario",
  scenarios,
  height = 420,
}: {
  title?: string;
  scenarios: ScenarioUtilization[];
  height?: number;
}) {
  const scenarioNames = scenarios.map((s) => s.name);

  const resourceSet = React.useMemo(() => {
    const set = new Set<string>();
    scenarios.forEach((s) => s.rows.forEach((r) => set.add(r.resource)));
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [scenarios]);

  const index = React.useMemo(() => {
    const map: Record<string, Record<string, number>> = {};
    scenarios.forEach((s) => {
      const inner: Record<string, number> = {};
      s.rows.forEach((r) => (inner[r.resource] = Number(r.percentage_utilization) || 0));
      map[s.name] = inner;
    });
    return map;
  }, [scenarios]);

  const [orderBy, setOrderBy] = React.useState<string>("resource");
  const [order, setOrder] = React.useState<Order>("asc");
  const handleSort = (id: string) => {
    if (orderBy === id) setOrder((prev) => (prev === "asc" ? "desc" : "asc"));
    else {
      setOrderBy(id);
      setOrder("desc");
    }
  };

  const sortedResources = React.useMemo(() => {
    const arr = [...resourceSet];
    const cmp = (a: string, b: string) => {
      if (orderBy === "resource") {
        return order === "asc" ? a.localeCompare(b) : b.localeCompare(a);
      }
      const va = index[orderBy]?.[a] ?? -Infinity;
      const vb = index[orderBy]?.[b] ?? -Infinity;
      return order === "asc" ? va - vb : vb - va;
    };
    return arr.sort(cmp);
  }, [resourceSet, orderBy, order, index]);

  const bestByResource = React.useMemo(() => {
    const best: Record<string, string> = {};
    resourceSet.forEach((res) => {
      let bestName = "";
      let bestVal = -Infinity;
      scenarioNames.forEach((sn) => {
        const v = index[sn]?.[res] ?? -Infinity;
        if (v > bestVal) {
          bestVal = v;
          bestName = sn;
        }
      });
      best[res] = bestName;
    });
    return best;
  }, [resourceSet, scenarioNames, index]);

  return (
    <Paper sx={{ p: 2, borderRadius: 2, boxShadow: 1 }}>
      <Typography
        variant="h6"
        sx={{ fontWeight: 700, fontSize: "1.1rem", color: "#1e293b", mb: 1 }}
      >
        {title}
      </Typography>

      <Box
        sx={{
          maxHeight: height,
          overflow: "auto",
          borderRadius: 1,
          border: "1px solid #e5e7eb",
        }}
      >
        <Table stickyHeader size="small">
          <TableHead>
            <TableRow>
              <TableCell sortDirection={orderBy === "resource" ? order : false}>
                <TableSortLabel
                  active={orderBy === "resource"}
                  direction={orderBy === "resource" ? order : "asc"}
                  onClick={() => handleSort("resource")}
                >
                  Resource
                </TableSortLabel>
              </TableCell>
              {scenarioNames.map((sn) => (
                <TableCell
                  key={sn}
                  align="right"
                  sortDirection={orderBy === sn ? order : false}
                >
                  <TableSortLabel
                    active={orderBy === sn}
                    direction={orderBy === sn ? order : "desc"}
                    onClick={() => handleSort(sn)}
                  >
                    Scenario {sn}
                  </TableSortLabel>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>

          <TableBody>
            {sortedResources.map((res) => (
              <TableRow key={res} hover>
                <TableCell sx={{ fontWeight: 600 }}>{res}</TableCell>
                {scenarioNames.map((sn) => {
                  const v = index[sn]?.[res];
                  const isBest = bestByResource[res] === sn;
                  const bg = Number.isFinite(v) ? colorFor(v as number) : "transparent";
                  // testo leggibile in base alla luminosità
                  const fg =
                    !Number.isFinite(v) || v == null
                      ? "inherit"
                      : (v as number) > 40
                      ? "#202020ff"
                      : "#fff";

                  return (
                    <TableCell key={`${res}-${sn}`} align="right" sx={{ p: 1 }}>
                      {Number.isFinite(v) ? (
                        <Tooltip title={`${compact(v as number)}%`}>
                          <Box
                            sx={{
                              display: "inline-block",
                              minWidth: 64,
                              px: 1,
                              py: 0.5,
                              borderRadius: 1,
                              background: bg,
                              color: fg,
                              fontWeight: isBest ? 700 : 500,
                              textAlign: "right",
                              boxShadow: "0 0 3px rgba(0,0,0,0.2)",
                              transition: "transform 0.15s ease",
                              "&:hover": { transform: "scale(1.05)" },
                            }}
                          >
                            {compact(v as number)}%
                          </Box>
                        </Tooltip>
                      ) : (
                        "—"
                      )}
                    </TableCell>
                  );
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </Box>
    </Paper>
  );
}
