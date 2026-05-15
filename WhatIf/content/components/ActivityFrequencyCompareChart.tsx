import React from "react";
import { Box, Typography, useTheme } from "@mui/material";
import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

type FrequencyRow = {
  activity: string;
  total_count: number;
};

function formatScenarioName(key: string): string {
  return key.toLowerCase().startsWith("scenario") ? key : `Scenario ${key}`;
}

export default function ActivityFrequencyCompareChart({
  scenariosData,
  scenarioNames,
}: {
  scenariosData: Record<string, any>;
  scenarioNames: string[];
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

  // Union of all activities across selected scenarios
  const activitySet = new Set<string>();
  for (const name of scenarioNames) {
    for (const row of (scenariosData[name]?.activity_frequency ?? []) as FrequencyRow[]) {
      activitySet.add(row.activity);
    }
  }

  const data = Array.from(activitySet).map((activity) => {
    const point: Record<string, string | number> = { activity };
    for (const name of scenarioNames) {
      const freq = (scenariosData[name]?.activity_frequency ?? [] as FrequencyRow[]).find(
        (r: FrequencyRow) => r.activity === activity
      );
      point[name] = freq ? Math.round(freq.total_count) : 0;
    }
    return point;
  });

  if (data.length === 0) return null;

  return (
    <Box
      sx={{
        bgcolor: "background.paper",
        borderRadius: 2,
        p: 2,
        boxShadow: 1,
        mt: 3,
      }}
    >
      <Typography variant="h6" sx={{ fontWeight: 700, fontSize: "1.25rem", color: "#1e293b", mb: 2 }}>
        Activity Execution Frequency Comparison
      </Typography>

      <ResponsiveContainer width="100%" height={420}>
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, left: 20, bottom: 90 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="activity"
            angle={-45}
            textAnchor="end"
            interval={0}
            height={90}
          />
          <YAxis
            allowDecimals={false}
            label={{
              value: "Total executions",
              angle: -90,
              position: "insideLeft",
            }}
          />
          <Tooltip
            formatter={(value, name) => [
              Math.round(Number(value)),
              formatScenarioName(name as string),
            ]}
            labelFormatter={(label) => `Activity: ${label}`}
          />
          <Legend formatter={(value) => formatScenarioName(value)} />
          {scenarioNames.map((name, idx) => (
            <Bar
              key={name}
              dataKey={name}
              name={name}
              fill={palette[idx % palette.length]}
              radius={[4, 4, 0, 0]}
            />
          ))}
        </BarChart>
      </ResponsiveContainer>

      <Typography variant="caption" sx={{ color: "text.secondary", mt: 1, display: "block" }}>
        Total executions per activity across the log, compared across scenarios.
        With multiple repetitions per scenario the value is averaged across runs.
        Only activities with both assign and complete events are shown.
      </Typography>
    </Box>
  );
}
