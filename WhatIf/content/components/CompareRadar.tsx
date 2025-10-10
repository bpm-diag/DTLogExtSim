import React, { useMemo, useState } from "react";
import {
  Box,
  Typography,
  useTheme,
  IconButton,
  Tooltip as MuiTooltip,
  Popover,
} from "@mui/material";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Legend,
  Tooltip,
} from "recharts";

export type RadarKpi = {
  name: string;
  avgCycleMin: number;
  avgWaitMin: number;
  avgTotalCost: number;
  avgTotalResource: number;
};

type RadarDatum = {
  metric: string;
  [scenarioName: string]: number | string;
};

function normalizeInvert(values: number[]) {
  const min = Math.min(...values);
  const max = Math.max(...values);
  if (!isFinite(min) || !isFinite(max) || max <= min) return values.map(() => 1);
  return values.map((v) => 1 - (v - min) / (max - min));
}

export default function CompareRadar({
  title = "Radar KPI (normalized 0–1)",
  scenarios,
}: {
  title?: string;
  scenarios: RadarKpi[];
}) {
  const theme = useTheme();
  const palette = [
    theme.palette.primary.main,
    theme.palette.secondary.main,
    "#4caf50",
    "#ff9800",
    "#2196f3",
    "#9c27b0",
    "#e91e63",
    "#00bcd4",
    "#8bc34a",
    "#ffc107",
  ];

  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const openInfo = Boolean(anchorEl);
  const handleOpenInfo = (e: React.MouseEvent<HTMLElement>) => setAnchorEl(e.currentTarget);
  const handleCloseInfo = () => setAnchorEl(null);

  const data: RadarDatum[] = useMemo(() => {
    const metrics = [
      { key: "avgCycleMin", label: "Avg cycle time (min)" },
      { key: "avgWaitMin", label: "Avg waiting time (min)" },
      { key: "avgTotalCost", label: "Avg total cost (€)" },
      { key: "avgTotalResource", label: "Avg total resource consumption" },
    ] as const;

    const perMetricValues: Record<string, number[]> = {};
    metrics.forEach((m) => {
      perMetricValues[m.key] = scenarios.map((s) => (s as any)[m.key] as number);
    });

    const normalized: Record<string, number[]> = {};
    metrics.forEach((m) => {
      normalized[m.key] = normalizeInvert(perMetricValues[m.key]);
    });

    return metrics.map((m) => {
      const row: RadarDatum = { metric: m.label };
      scenarios.forEach((s, i) => {
        row[s.name] = normalized[m.key][i].toFixed(2);
      });
      return row;
    });
  }, [scenarios]);

  const scenarioNames = scenarios.map((s) => s.name);

  return (
    <Box sx={{ height: 420, bgcolor: "background.paper", borderRadius: 2, p: 2, boxShadow: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
        <Typography variant="h6" sx={{
          fontFamily: "'Roboto', sans-serif",
          fontWeight: 700,
          fontSize: "1.25rem",
          color: "#1e293b", 
          lineHeight: 1.2,
        }}
      >
        {title}
      </Typography>


        <MuiTooltip title="How to read the radar">
          <IconButton aria-label="How to read" onClick={handleOpenInfo} size="small">
            <HelpOutlineIcon fontSize="small" />
          </IconButton>
        </MuiTooltip>

        <Popover
          open={openInfo}
          anchorEl={anchorEl}
          onClose={handleCloseInfo}
          anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
          transformOrigin={{ vertical: "top", horizontal: "right" }}
          PaperProps={{ sx: { p: 2, maxWidth: 420 } }}
        >
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Radar Chart interpretation (how to read it)
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            The radar chart compares KPIs across scenarios.
            Each axis is one KPI (cycle time, waiting time, total cost, resource
            consumption). Each colored shape is a scenario: the larger and more
            outward the shape, the better the performance on that KPI. Values are
            normalized (0–1) and inverted, so <b>higher values mean better performance </b>
            (e.g., lower time, lower cost, lower resource usage). Overlapping areas
            highlight trade-offs where one scenario outperforms the other.
          </Typography>
        </Popover>
      </Box>

      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data}>
          <PolarGrid />
          <PolarAngleAxis dataKey="metric" />
          <PolarRadiusAxis angle={30} domain={[0, 1]} />
          {scenarioNames.map((name, idx) => {
            const color = palette[idx % palette.length];
            return (
              <Radar
                key={name}
                name={name}
                dataKey={name}
                stroke={color}
                fill={color}
                fillOpacity={0.28}
                dot={false}
                isAnimationActive={false}
              />
            );
          })}
          <Tooltip />
          <Legend iconType="circle" />
        </RadarChart>
      </ResponsiveContainer>
    </Box>
  );
}
