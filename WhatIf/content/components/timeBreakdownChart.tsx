import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";
import { FormControlLabel, Checkbox, FormGroup } from "@mui/material";
import { useState } from "react";
import { FormControl, InputLabel, MenuItem, Select } from "@mui/material";

// funzioni di conversione del tempo 
function convertDuration(minutes: number, unit: string): number {
  switch (unit) {
    case "seconds":
      return minutes * 60;
    case "hours":
      return minutes / 60;
    case "days":
      return minutes / (24*60) ;
    default:
      return minutes;
  }
}

function formatUnitLabel(unit: string): string {
  switch (unit) {
    case "seconds":
      return "s";
    case "hours":
      return "h";
    case "days":
      return "d";
    default:
      return "min";
  }
}

export default function BreakdownChart({ data }: { data: any }) {
    const [unit, setUnit] = useState("minutes");
    const [showCycle, setShowCycle] = useState(true);
    const [showWaiting, setShowWaiting] = useState(true);
    const [showProcessing, setShowProcessing] = useState(true);
    const convertedData = data.map((entry: any) => ({
      ...entry,
      avg_cycle_time: convertDuration(entry.avg_cycle_time, unit),
      avg_waiting_time: convertDuration(entry.avg_waiting_time, unit),
      avg_processing_time: convertDuration(entry.avg_processing_time, unit),
    }));
    
    return (
            <div className="bg-white p-6 rounded-xl shadow">
                <h2 className="text-xl font-semibold mb-4 text-gray-800">
                  Time Breakdown per Activity (Avg)
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
                
                <FormGroup row className="mb-4 justify-center">
                  <FormControlLabel control={<Checkbox checked={showCycle} onChange={() => setShowCycle(!showCycle)} />} label="Cycle Time" />
                  <FormControlLabel control={<Checkbox checked={showWaiting} onChange={() => setShowWaiting(!showWaiting)} />} label="Waiting Time" />
                  <FormControlLabel control={<Checkbox checked={showProcessing} onChange={() => setShowProcessing(!showProcessing)} />} label="Processing Time" />
                </FormGroup>

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
                      label={{ value: `Duration (${formatUnitLabel(unit)})`, angle: -90, position: "insideLeft" }}
                    />

                    <Tooltip
                      formatter={(value: any, name: string) => [
                        `${value.toFixed(2)} ${formatUnitLabel(unit)}`,
                        name.replace("_", " ")
                      ]}
                      labelFormatter={(label) => `Activity: ${label}`}
                    />

                    <Legend 
                    layout="vertical"
                    verticalAlign="top"
                    align="right"
                    iconType="square"
                    />
                    {showCycle && <Bar dataKey="avg_cycle_time" fill="#3b82f6" name="Cycle Time" />}
                    {showWaiting && <Bar dataKey="avg_waiting_time" fill="#f59e0b" name="Waiting Time" />}
                    {showProcessing && <Bar dataKey="avg_processing_time" fill="#10b981" name="Processing Time" />}
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-sm text-gray-600 mt-4">
                  Chart showing average cycle, waiting, and processing times per activity for each trace.
                  <br></br>Note that will be shown only those activities for which are present both ASSIGN and COMPLETE information.
                </p>
              </div>
            );
        }