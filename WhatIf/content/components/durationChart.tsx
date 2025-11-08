import { useState } from "react";
import { FormControl, InputLabel, MenuItem, Select } from "@mui/material";
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";

// funzioni per convertire il tempo in una forma più leggibile all'utente
function convertDuration(minutes: number, unit: string): number {
  switch (unit) {
    case "seconds":
      return minutes * 60;
    case "hours":
      return minutes / 60;
    case "days":
      return minutes / (24*60);
    default:
      return minutes;
  }
}

function formatUnitLabel(unit: string): string {
  switch (unit) {
    case "seconds":
      return "s";
    case "minutes":
      return "min";
    case "days":
      return "d";
    default:
      return "h";
  }
}


export default function DurationChart({ data }: { data: any }) {
  const [unit, setUnit] = useState("minutes");
  const convertedData = data.map((entry: any) => ({
    ...entry,
    avg_duration: convertDuration(entry.avg_duration, unit),
    min_duration: convertDuration(entry.min_duration, unit),
    max_duration: convertDuration(entry.max_duration, unit),
  }));
  

  return (
    <div className="mt-8 w-full space-y-12">
      <div className="bg-white p-6 rounded-xl shadow">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">
          Average Activity Duration for each Trace
        </h2>
        <FormControl size="small" style={{ marginBottom: 16 }}>
          <InputLabel>Unit</InputLabel>
          <Select
            value={unit}
            label="Unit"
            onChange={(e) => setUnit(e.target.value)}
            style={{ width: 120 }}
          >
            <MenuItem value="seconds">Seconds</MenuItem>
            <MenuItem value="minutes">Minutes</MenuItem>
            <MenuItem value="hours">Hours</MenuItem>
            <MenuItem value="days">Days</MenuItem>
          </Select>
        </FormControl>

        <ResponsiveContainer width="100%" height={400}>
          <BarChart data={convertedData} margin={{ top: 20, right: 30, left: 20, bottom: 80 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="activity"
              angle={-45}
              textAnchor="end"
              interval={0}
              height={80}
              label={{ value: "Activity", position: "insideBottom", offset: -60 }}
            />
            <YAxis
              domain={['auto', 'auto']}
              label={{
                value: `Duration (${formatUnitLabel(unit)})`,
                angle: -90,
                position: "insideLeft"
              }}
            />

            <Tooltip
              formatter={(value: any, name: string) => [
                `${convertDuration(value, unit).toFixed(2)} ${formatUnitLabel(unit)}`,
                name.replace("_", " ")
              ]}
              labelFormatter={(label) => `Activity: ${label}`}
            />

            <Legend layout="vertical" verticalAlign="top"
                    align="right"
                    iconType="square"
                    />
            <Bar dataKey="avg_duration" fill="#3b82f6" name="Avg Duration" />
            <Bar dataKey="min_duration" fill="#10b981" name="Min Duration" />
            <Bar dataKey="max_duration" fill="#ef4444" name="Max Duration" />
          </BarChart>
        </ResponsiveContainer>
        <p className="text-sm text-gray-600 mt-4">
          Chart showing min, avg, and max durations per activity for each trace.
          <br />Note that will be shown only those activities for which are present both ASSIGN and COMPLETE information.
        </p>
      </div>
    </div>
  );
}