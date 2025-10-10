import { ResponsiveContainer, ScatterChart, Scatter, XAxis, YAxis, ZAxis, CartesianGrid, Tooltip, Cell, Legend } from "recharts";

export default function ResourceUsageBubble({ data }: { data: any }) {
  const usageCounts = data.map((d: any) => d.usage_count);
  const minUsage = Math.min(...usageCounts);
  const maxUsage = Math.max(...usageCounts);

  const getBubbleColor = (usage: number) => {
    const clamp = (v: number, min: number, max: number) => Math.max(min, Math.min(v, max));
    if (maxUsage === minUsage) return "hsl(120, 80%, 50%)"; // fallback verde

    const ratio = clamp((usage - minUsage) / (maxUsage - minUsage), 0, 1);
    const hue = 120 - (ratio * 120); // verde (120) → rosso (0)
    return `hsl(${hue}, 80%, 50%)`;
  };

  return (
    <div className="bg-white p-6 rounded-xl shadow">
      <h2 className="text-xl font-semibold mb-4 text-gray-800">
        Resource Usage and Average Cost
      </h2>
      <ResponsiveContainer width="100%" height={400}>
        <ScatterChart margin={{ top: 20, right: 30, left: 20, bottom: 60 }}>
          <CartesianGrid />
          <XAxis
            type="category"
            dataKey="resource"
            name="Resource"
            interval={0}
            angle={-45}
            textAnchor="end"
            height={80}
            label={{ value: "Resource", position: "insideBottom", offset: -50 }}
          />
          <YAxis
            type="number"
            dataKey="avg_cost"
            name="Average Cost (€)"
            label={{ value: "Avg Cost (€)", angle: -90, position: "insideLeft" }}
          />
          <ZAxis type="number" dataKey="usage_count" range={[60, 400]} name="Usage Count" />
          <Tooltip
            cursor={{ strokeDasharray: '3 3' }}
            formatter={(value: any, name: string) => {
              if (name === "avg_cost") {
                return [`€${Number(value).toFixed(2)}`, "Avg Cost"];
              } else if (name === "usage_count") {
                return [`${value}`, "Usage Count"];
              } else {
                return [String(value), name];
              }
            }}
            labelFormatter={(label) => `Resource: ${label}`}
          />
          <Scatter name="Resources" data={data}>
            {data.map((entry: any, index: number) => (
              <Cell
                key={`cell-${index}`}
                fill={getBubbleColor(entry.usage_count)}
              />
            ))}
          </Scatter>
        </ScatterChart>
      </ResponsiveContainer>

      {/* Scala colore sotto il grafico */}
      <div className="flex justify-center mt-4">
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-700">Low usage</span>
          <div style={{
            background: 'linear-gradient(to right, hsl(120, 80%, 50%), hsl(60, 80%, 50%), hsl(0, 80%, 50%))',
            width: 200,
            height: 15,
            borderRadius: 4
          }} />
          <span className="text-sm text-gray-700">High usage</span>
        </div>
      </div>

      <p className="text-sm text-gray-600 mt-4 text-center">
        Bubble size reflects usage count; bubble color ranges from green (low usage) to red (high usage).<br />
        Cost and usage of resources are referred to the average cost and usage for each traceId.
      </p>
    </div>
  );
}