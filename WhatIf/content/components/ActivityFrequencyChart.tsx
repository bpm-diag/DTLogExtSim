import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

type FrequencyRow = {
  activity: string;
  total_count: number;
};

export default function ActivityFrequencyChart({ data }: { data: FrequencyRow[] }) {
  return (
    <div className="mt-8 w-full">
      <div className="bg-white p-6 rounded-xl shadow">
        <h2 className="text-xl font-semibold mb-4 text-gray-800">
          Activity Execution Frequency
        </h2>

        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={data}
            margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
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
              allowDecimals={false}
              label={{
                value: "Total executions",
                angle: -90,
                position: "insideLeft",
              }}
            />
            <Tooltip
              formatter={(value: any) => [Number(value).toFixed(0), "Total executions"]}
              labelFormatter={(label) => `Activity: ${label}`}
            />
            <Bar dataKey="total_count" fill="#6366f1" name="Total executions" radius={[4, 4, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>

        <p className="text-sm text-gray-600 mt-4">
          Total number of completions for each activity across the entire log.
          Only activities with both assign and complete events are shown.
        </p>
      </div>
    </div>
  );
}
