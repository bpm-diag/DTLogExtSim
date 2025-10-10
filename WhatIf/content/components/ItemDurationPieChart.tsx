import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend} from "recharts";
import { FormControl, InputLabel, MenuItem, Select } from "@mui/material";
import { useState, useEffect } from "react";

const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#ff7f50", "#a0522d", "#8a2be2", "#ff1493", "#00ced1", "#ffa500", "#228b22"];

// funzione per convertire il tempo 
function convertDuration(minutes: number, unit: string): number {
    switch (unit) {
      case "seconds": return minutes * 60;
      case "hours": return minutes / 60;
      case "days": return minutes / 1440;
      default: return minutes;
    }
  }
  
  function formatUnit(unit: string): string {
    switch (unit) {
      case "seconds": return "sec";
      case "hours": return "h";
      case "days": return "d";
      default: return "min";
    }
  }
export default function ItemDurationPieChart({ data }: { data: any }) {
    const [unit, setUnit] = useState("minutes");
    useEffect(() => {
        if (!data || data.length === 0) return;
      
        const allMinutes = data.map((item: any) => item.avg_duration_minutes);
        const mean = allMinutes.reduce((a: number, b: number) => a + b, 0) / allMinutes.length;     
        if (mean < 1) setUnit("seconds");
        else if (mean < 60) setUnit("minutes");
        else if (mean < 1440) setUnit("hours");
        else setUnit("days");
      }, [data]);
  
    const convertedData = data.map((item: any) => ({
      ...item,
      duration: convertDuration(item.avg_duration_minutes, unit)
    }));
  
    return (
      <div className="bg-white p-6 rounded-xl shadow">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">
          Average Duration per Item Type
        </h2>
  
        <FormControl size="small" style={{ marginBottom: 16 }}>
          <InputLabel>Unit</InputLabel>
          <Select
            value={unit}
            label="Unit"
            onChange={(e) => setUnit(e.target.value)}
            style={{ width: 140 }}
          >
            <MenuItem value="seconds">Seconds</MenuItem>
            <MenuItem value="minutes">Minutes</MenuItem>
            <MenuItem value="hours">Hours</MenuItem>
            <MenuItem value="days">Days</MenuItem>
          </Select>
        </FormControl>
  
        <div className="flex justify-center">
          <div style={{ width: "100%", maxWidth: 800, height: 400 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={convertedData}
                  dataKey="duration"
                  nameKey="instanceType"
                  cx="50%"
                  cy="50%"
                  outerRadius={120}
                  label={({ percent, payload }) =>
                    `${payload.instanceType}: ${(percent * 100).toFixed(1)}% (${payload.duration.toFixed(1)} ${formatUnit(unit)})`
                  }
                >
                  {convertedData.map((entry: any, index: number) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(value: any) => [`${value.toFixed(1)} ${formatUnit(unit)}`, "Avg Duration"]}
                  labelFormatter={(label) => `Item: ${label}`}
                />
                <Legend
                  layout="vertical"
                  verticalAlign="top"
                  align="right"
                  iconType="square"
                  formatter={(value, entry, index) => (
                    <span style={{ color: COLORS[index % COLORS.length] }}>{value}</span>
                  )}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>
  
        <p className="text-sm text-gray-600 mt-4 text-center">
          Distribution of average production durations per item type, shown in your selected unit.
        </p>
      </div>
    );
  }