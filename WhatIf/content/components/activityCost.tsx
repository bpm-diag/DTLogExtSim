import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend } from "recharts";

export default function CostChart({ data }: { data: any }) {
  return (
<div className="bg-white p-6 rounded-xl shadow">
                <h2 className="text-xl font-semibold mb-4 text-gray-800">
                  Cost Analysis per Activity (Fixed vs Variable)
                </h2>
                <ResponsiveContainer width="100%" height={400}>
                  <BarChart
                    data={data}
                    margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                    stackOffset="sign"
                  >
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
                      label={{ value: "Average Cost (€) ", angle: -90, position: "insideLeft" }}
                    />
                    <Tooltip
                      formatter={(value: any, name: string) => [`€${value.toFixed(2)}`, name.replace("_", " ") ]}
                      content={({ payload, label }) => {
                        if (!payload || payload.length === 0) return null;

                        const fixed = payload.find((p: any) => p.dataKey === "avg_fixed_cost")?.value || 0;
                        const variable = payload.find((p: any) => p.dataKey === "avg_variable_cost")?.value || 0;
                        const total = fixed + variable;

                        return (
                          <div style={{ backgroundColor: "white", border: "1px solid #ccc", padding: 10 }}>
                            <strong>Activity: {label}</strong>
                            <br />
                            <span style={{ color: "#60a5fa" }}><strong>Fixed Cost: </strong></span>€ {fixed.toFixed(2)} <br />
                            <span style={{ color: "#facc15" }}><strong>Variable Cost: </strong></span>€ {variable.toFixed(2)} <br />
                            <hr />
                            <strong>Total Cost:</strong> € {total.toFixed(2)}
                          </div>
                        );
                      }}
                    />

                    <Legend 
                    layout="vertical"
                    verticalAlign="top"
                    align="right"
                    iconType="square"
                    />
                    <Bar dataKey="avg_fixed_cost" stackId="a" fill="#60a5fa" name="Fixed Cost" />
                    <Bar dataKey="avg_variable_cost" stackId="a" fill="#facc15" name="Variable Cost" />
                  </BarChart>
                </ResponsiveContainer>
                <p className="text-sm text-gray-600 mt-4">
                  Each bar represents the average fixed and variable costs of an activity for each trace the activity is present.
                </p>
              </div>
            );
        }