import React from "react";
import { Box, Typography, useTheme } from "@mui/material";
import {
  ResponsiveContainer,
  BarChart as RBarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
} from "recharts";

export type CompareDatum = {
  metric: string;
  [scenarioName: string]: string | number;
};

export default function CompareBarChart({
  title = "Main KPI comparison",
  data,
  scenarioKeys,
  valueFormatter, 
}: {
  title?: string;
  data: CompareDatum[];
  scenarioKeys: string[];
  valueFormatter?: (value: number) => string | number; 
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
    "#795548",
  ];

  return (
    <Box sx={{ height: 360, bgcolor: "background.paper", borderRadius: 2, p: 2, boxShadow: 1 }}>
      <Typography variant="h6" sx={{ fontWeight: 700, fontSize: "1.25rem", color: "#1e293b", lineHeight: 1.2 }}>
        {title}
      </Typography>

      <ResponsiveContainer width="100%" height="100%">
        <RBarChart data={data}>
          <XAxis dataKey="metric" />
          <YAxis />
          <Tooltip formatter={valueFormatter} /> 
          <Legend />
          {scenarioKeys.map((key, idx) => (
            <Bar key={key} dataKey={key} fill={palette[idx % palette.length]} radius={[4, 4, 0, 0]} />
          ))}
        </RBarChart>
      </ResponsiveContainer>
    </Box>
  );
}
