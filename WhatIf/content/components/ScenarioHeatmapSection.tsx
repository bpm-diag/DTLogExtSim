import React from "react";
import {
  Box,
  Stack,
  Typography,
  List,
  ListItem,
  ListItemText,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
} from "@mui/material";
import BpmnViewerBox, { FlowMetric } from "@/components/BpmnViewer";

/** Tipi esposti per riuso in page.tsx */
export type BottleneckRow = {
  activity: string;
  next_activity: string;
  wait_time: number; // in secondi
  sequenceFlowIds?: string[];
};

export type TimeUnit = "s" | "min" | "h";

/* ================= shared layout ================= */
const HEATMAP_HEIGHT = 520; //px

/* ================= helpers ================= */

const unitLabel: Record<TimeUnit, string> = { s: "s", min: "min", h: "h" };

const convertFromMinutes = (valuesec: number, unit: TimeUnit) => {
  if (!Number.isFinite(valuesec)) return 0;
  switch (unit) {
    case "min":
      return valuesec / 60;
    case "h":
      return valuesec / (60*60);
    default:
      return valuesec;
  }
};

/**
 Usiamo gli stessi bucket di BpmnViewer.tsx → bucketOf(value in minuti)
 e gli stessi colori definiti in globals.css (.heat-0 ... .heat-5).
 */

// Copia del bucket di BpmnViewer (tenere sincronizzato se cambi):
const bucketOf = (vMin: number): 0 | 1 | 2 | 3 | 4 | 5 => {
  if (!Number.isFinite(vMin)) return 0;
  if (vMin <= 0) return 0;
  if (vMin <= 5) return 1;
  if (vMin <= 10) return 2;
  if (vMin <= 20) return 3;
  if (vMin <= 40) return 4;
  return 5;
};

const HEAT_COLORS: Record<0 | 1 | 2 | 3 | 4 | 5, string> = {
  0: "hsl(120, 70%, 45%)",
  1: "hsl(74, 82%, 49%)",
  2: "hsl(55, 100%, 50%)",
  3: "hsl(28, 90%, 51%)",
  4: "hsl(8, 95%, 47%)",
  5: "hsl(0, 98%, 24%)",
};

// Colore neutro usato da .heat-none (in caso di fallback)
const NEUTRAL_COLOR = "#646868";

/** Dato un tempo in seocndi restituisce il colore coerente con i flussi BPMN */
function waitMinutesToHeatColor(valuesec: number): string {
  if (!Number.isFinite(valuesec)) return NEUTRAL_COLOR;
  const b = bucketOf(valuesec);
  return HEAT_COLORS[b];
}

/* ================ sotto-component: lista flussi ================= */

function FlowWaitList({
  rows,
  unit,
  title = "Tempi di attraversamento (A → B)",
  height = "100%",
}: {
  rows: BottleneckRow[];
  unit: TimeUnit;
  title?: string;
  height?: number | string;
}) {
  // Ordinamento per wait_time (minuti) decrescente
  const sorted = React.useMemo(
    () => [...rows].sort((a, b) => (b.wait_time ?? 0) - (a.wait_time ?? 0)),
    [rows]
  );

  return (
    <Box
      sx={{
        width: 380,
        maxWidth: "100%",
        height,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <Typography variant="h6" sx={{ mb: 1 }}>
        {title}
      </Typography>

      {/* Contenitore scrollabile della lista */}
      <Box sx={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
        <List dense sx={{ bgcolor: "background.paper", borderRadius: 2, boxShadow: 1 }}>
          {sorted.map((r, idx) => {
            const color = waitMinutesToHeatColor(r.wait_time || 0);
            const valConv = convertFromMinutes(r.wait_time || 0, unit);

            return (
              <ListItem
                key={`${r.activity}->${r.next_activity}-${idx}`}
                sx={{
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  "&:last-child": { borderBottom: "none" },
                }}
              >
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    mr: 1.25,
                    mt: "6px",
                    backgroundColor: color,
                    flexShrink: 0,
                  }}
                />
                <ListItemText
                  primary={
                    <span>
                      <b>{String(r.activity)}</b> → <b>{String(r.next_activity)}</b>
                    </span>
                  }
                  secondary={
                    <span>
                      {valConv.toFixed(2)} {unitLabel[unit]}
                    </span>
                  }
                />
              </ListItem>
            );
          })}
        </List>
      </Box>

      {/* legenda in basso, fuori dall'area scroll (già coerente con la palette) */}
      <Box sx={{ mt: 1.25, display: "flex", alignItems: "center", gap: 1 }}>
        <Box sx={{ width: 14, height: 14, borderRadius: "50%", background: "hsl(120,70%,45%)" }} />
        <Typography variant="caption" sx={{ fontFamily: "'Roboto', sans-serif" }}>
          Faster
        </Typography>
        <Box
          sx={{
            flex: 1,
            height: 12,
            background:
              "linear-gradient(90deg, hsl(120,70%,45%) 0%, hsl(74, 82%, 49%) 16%, hsla(55, 100%, 50%, 1.00) 33%, hsl(28, 90%, 51%) 50%, hsl(8, 95%, 47%) 66%, hsl(0, 98%, 24%) 100%)",
            borderRadius: 2,
          }}
        />
        <Typography variant="caption">Slower</Typography>
        <Box sx={{ width: 14, height: 14, borderRadius: "50%", background: "hsl(0, 98%, 24%)" }} />
      </Box>
    </Box>
  );
}

/* ================ componente principale ================= */

export default function ScenarioHeatmapSection({
  title,
  bpmnFile,
  rows,
}: {
  title: string;
  bpmnFile: File;
  rows: BottleneckRow[];
}) {
  const [unit, setUnit] = React.useState<TimeUnit>("min");

  const flows: FlowMetric[] = React.useMemo(
    () =>
      (rows ?? []).map((x) => ({
        from: String(x.activity),
        to: String(x.next_activity),
        value: Number.isFinite(x.wait_time) ? Number(x.wait_time) : 0, // minuti → coerente con viewer
        flowIds: Array.isArray(x.sequenceFlowIds) ? x.sequenceFlowIds : undefined,
      })),
    [rows]
  );

  return (
    <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="flex-start">
      <Box sx={{ flex: 1, minWidth: 0 }}>
        <BpmnViewerBox
          title={title}
          file={bpmnFile}
          height={HEATMAP_HEIGHT}
          minStroke={2}
          maxStroke={8}
          enableHeat={true}
          flows={flows}
        />
      </Box>

      {/* Colonna destra: stessa altezza della heatmap; la lista scorre internamente */}
      <Box
        sx={{
          width: 380,
          maxWidth: "100%",
          height: 600,
          display: "flex",
          flexDirection: "column",
        }}
      >
        <FormControl size="small" fullWidth sx={{ mb: 1.5, flexShrink: 0 }}>
          <InputLabel id={`${title}-unit`}>Unit</InputLabel>
          <Select
            labelId={`${title}-unit`}
            label="Unità"
            value={unit}
            onChange={(e) => setUnit(e.target.value as TimeUnit)}
          >
            <MenuItem value="s">Seconds</MenuItem>
            <MenuItem value="min">Minutes</MenuItem>
            <MenuItem value="h">Hours</MenuItem>
          </Select>
        </FormControl>

        {/* FlowWaitList occupa tutto lo spazio rimanente (scroll interno) */}
        <Box sx={{ flex: 1, minHeight: 0 }}>
          <FlowWaitList
            rows={rows}
            unit={unit}
            title={`${title} – Waiting time between activities`}
            height="100%"
          />
        </Box>
      </Box>
    </Stack>
  );
}
