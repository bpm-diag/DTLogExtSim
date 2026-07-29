// src/utils/bottleneckFlows.ts
export type BottleneckRow = {
  traceId: string | number;
  activity: string;
  next_activity: string;
  wait_time: number;   // in secondi (come dal backend)
  order: number;
};

// stessa logica della tua heatmap (seconds/minutes/hours/days)
export function convertDuration(seconds: number, unit: "seconds"|"minutes"|"hours"|"days"): number {
  switch (unit) {
    case "minutes": return seconds / 60;
    case "hours":   return seconds / 3600;
    case "days":    return seconds / 86400;
    default:        return seconds;
  }
}

/** Trace con wait totale più alto (come fai nella heatmap) */
export function getTopTraceId(rows: BottleneckRow[]): string {
  const totals = new Map<string, number>();
  for (const r of rows) {
    const id = String(r.traceId);
    totals.set(id, (totals.get(id) || 0) + r.wait_time);
  }
  return [...totals.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? "";
}

/** Flussi per una specifica trace, ordinati per order */
export function flowsForTrace(
  rows: BottleneckRow[],
  traceId: string,
  unit: "seconds"|"minutes"|"hours"|"days" = "minutes"
) {
  return rows
    .filter(r => String(r.traceId) === traceId)
    .sort((a, b) => a.order - b.order)
    .map(r => ({
      from: r.activity,
      to: r.next_activity,
      value: convertDuration(r.wait_time, unit),
    }));
}

/** Flussi aggregati su tutte le trace: somma i wait per (from -> to) */
export function flowsAggregated(
  rows: BottleneckRow[],
  unit: "seconds"|"minutes"|"hours"|"days" = "minutes"
) {
  const map = new Map<string, { from: string; to: string; value: number }>();
  for (const r of rows) {
    const key = `${r.activity}__${r.next_activity}`;
    const cur = map.get(key) || { from: r.activity, to: r.next_activity, value: 0 };
    cur.value += convertDuration(r.wait_time, unit);
    map.set(key, cur);
  }
  return [...map.values()];
}
