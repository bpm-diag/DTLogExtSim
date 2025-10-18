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
  percentageUtilization: number; 
};

type RadarDatum = {
  metric: string;
  [scenarioName: string]: number | string;
};

// normalize to 0..1; optionally invert (lower is better)
function normalize(values: number[], invert: boolean) {
  const finite = values.map((v) => (Number.isFinite(v) ? v : 0));
  const min = Math.min(...finite);
  const max = Math.max(...finite);
  if (!isFinite(min) || !isFinite(max) || max <= min) {
    return finite.map(() => 1);
  }
  const norm = finite.map((v) => (v - min) / (max - min));
  return invert ? norm.map((x) => 1 - x) : norm;
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
      { key: "avgCycleMin", label: "Avg cycle time", invert: true },
      { key: "avgWaitMin", label: "Avg waiting time", invert: true },
      { key: "avgTotalCost", label: "Avg total cost", invert: true },
      { key: "percentageUtilization", label: "Avg resource utilization", invert: false },
    ] as const;

    const perMetricValues: Record<string, number[]> = {};
    metrics.forEach((m) => {
      perMetricValues[m.key] = scenarios.map((s) => (s as any)[m.key] as number);
    });

    const normalized: Record<string, number[]> = {};
    metrics.forEach((m) => {
      normalized[m.key] = normalize(perMetricValues[m.key], m.invert);
    });

    return metrics.map((m) => {
      const row: RadarDatum = { metric: m.label };
      scenarios.forEach((s, i) => {
        row[`Scenario ${s.name}`] = Number(normalized[m.key][i].toFixed(2));
      });
      return row;
    });
  }, [scenarios]);

  const scenarioNames = scenarios.map((s) => `Scenario ${s.name}`);

  return (
    <Box sx={{ height: 420, bgcolor: "background.paper", borderRadius: 2, p: 2, boxShadow: 1 }}>
      <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", mb: 1.5 }}>
        <Typography
          variant="h6"
          sx={{
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
          PaperProps={{ sx: { p: 2, maxWidth: 460 } }}
        >
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            Radar Chart — normalization
          </Typography>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            KPIs are normalized to 0–1 so that <b>higher KPI score means better performance</b> for that scenario.
            <br /> For metrics where lower values are better (like time and cost), the scenario with the lowest
            value gets a score of 1, while the highest gets 0. For metrics where higher values are better
            (like resource utilization), the scenario with the highest value gets a score of 1.
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

          <Tooltip formatter={(value, name) => [`${value}`, `${name}`]} />
          <Legend iconType="square" />
        </RadarChart>
      </ResponsiveContainer>
    </Box>
  );
}
