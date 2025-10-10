import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip, Legend } from "recharts";

const COLORS = ["#8884d8", "#82ca9d", "#ffc658", "#ff7f50", "#a0522d", "#8a2be2", "#ff1493", "#00ced1", "#ffa500", "#228b22"];

export default function ItemCostPieChart({ data }: { data: any }) {
  return (
        <div className="bg-white p-6 rounded-xl shadow">
                <h2 className="text-xl font-semibold mb-4 text-gray-800">
                  Average Cost per Item Type
                </h2>
                <div className="flex justify-center">
                <div style={{ width: "100%", maxWidth: 800, height: 400 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={data}
                          dataKey="avg_item_cost"
                          nameKey="instanceType"
                          cx="50%"
                          cy="50%"
                          outerRadius={120}        
                          label={({ percent, payload }) =>
                            `${payload.instanceType}: ${(percent * 100).toFixed(1)}% (€${payload.avg_item_cost.toFixed(0)})`
                          }                          
                        >
                        {data.map((entry: any, index: number) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                        </Pie>
                        <Tooltip
                          formatter={(value: any, name: string) => [`€${value.toFixed(2)}`, "Avg Cost"]}
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
                  Distribution of average total production costs per item type.
                </p>
              </div>
            );
    }
    