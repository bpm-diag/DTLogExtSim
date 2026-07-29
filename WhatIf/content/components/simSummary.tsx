import {
  TableContainer,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  Paper
} from '@mui/material';

// funzione per convertire i secondi (come restituiti dal backend) in un formato leggibile
function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(0)} sec`;
  } else if (seconds < 3600) {
    return `${(seconds / 60).toFixed(1)} min`;
  } else if (seconds < 86400) {
    return `${(seconds / 3600).toFixed(1)} hours`;
  } else {
    return `${(seconds / 86400).toFixed(1)} day(s)`;
  }
}

export default function SummaryTable({ data }: { data: any }) {
  return (
    <div className="mb-10 mx-auto p-6 rounded-xl shadow inline-block bg-gray-100 w-[90%]">
      <h2 className="text-2xl font-bold text-gray-800 mb-4">Simulation Summary</h2>

      <TableContainer component={Paper}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell align="center">
                <strong>Total Trace Executions</strong>
              </TableCell>
              <TableCell align="center">
                <strong>Pools</strong>
              </TableCell>
              <TableCell align="center">
                <strong>Total costs by Item Type</strong>
              </TableCell>
              <TableCell align="center">
                <strong>Average simulation Time by Item</strong>
              </TableCell>
              <TableCell align="center">
                <strong>Resources</strong>
              </TableCell>
            </TableRow>
          </TableHead>

          <TableBody>
            <TableRow>
              {/* TOTAL TRACES */}
              <TableCell align="center">
                {data?.total_traces ?? '—'}
              </TableCell>

              {/* POOLS */}
              <TableCell align="center">
                {Array.isArray(data?.unique_pools) && data.unique_pools.length > 0
                  ? data.unique_pools.join(', ')
                  : 'No pools found'}
              </TableCell>

              {/* TOTAL COSTS BY ITEM TYPE */}
              <TableCell align="center">
                {Array.isArray(data?.costs_by_item) && data.costs_by_item.length > 0 ? (() => {
                  const total = data.costs_by_item.reduce(
                    (sum: number, item: any) => sum + (item.total_item_cost ?? 0),
                    0
                  );
                  return (
                    <div className="text-sm text-center">
                      {data.costs_by_item.map((item: any) => (
                        <div key={item.instanceType}>
                          <strong>{item.instanceType}:</strong>{' '}
                          € {Number(item.total_item_cost || 0).toFixed(2)}
                        </div>
                      ))}
                      <hr className="my-1" />
                      <div>
                        <strong>Total:</strong> € {total.toFixed(2)}
                      </div>
                    </div>
                  );
                })() : 'No cost data'}
              </TableCell>

              {/* TOTAL EXECUTION TIME BY ITEM */}
              <TableCell align="center">
                {Array.isArray(data?.execution_by_item) &&
                data.execution_by_item.length > 0 ? (() => {
                  const total = data.execution_by_item.reduce(
                    (sum: number, item: any) =>
                      sum + (item.avg_execution_seconds ?? 0),
                    0
                  );
                  const overallAverage = total / data.execution_by_item.length;
                  return (
                    <div className="text-sm text-center">
                      {data.execution_by_item.map((item: any) => (
                        <div key={item.instanceType}>
                          <strong>{item.instanceType}:</strong>{' '}
                          {formatDuration(
                            Number(item.avg_execution_seconds || 0)
                          )}
                        </div>
                      ))}
                      <hr className="my-1" />
                      <div>
                        <strong>Average simulation time across item types:</strong> {formatDuration(overallAverage)}
                      </div>
                    </div>
                  );
                })() : 'No execution data'}
              </TableCell>

              {/* RESOURCES (da extra.json per scenario corrispondente) */}
              <TableCell align="center">
                {data?.resources &&
                typeof data.resources === 'object' &&
                Object.keys(data.resources).length > 0 ? (
                  <div className="text-sm text-center">
                    {Object.entries(data.resources).map(
                      ([role, qty]: [string, any]) => (
                        <div key={role}>
                          <strong>{role}:</strong> {qty}
                        </div>
                      )
                    )}
                  </div>
                ) : (
                  'No resource data'
                )}
              </TableCell>
            </TableRow>
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
}
