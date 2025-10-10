import {TableContainer, Table, TableHead, TableRow, TableCell, TableBody, Paper} from '@mui/material';

// funzione per convertire i minuti in un formato leggibile
function formatDuration(minutes: number): string {
  if (minutes < 1) {
    const seconds = minutes * 60;
    return `${seconds.toFixed(0)} sec`;
  } else if (minutes < 60) {
    return `${minutes.toFixed(1)} min`;
  } else if (minutes < 1440) {
    const hours = minutes / 60;
    return `${hours.toFixed(1)} hours`;
  } else {
    const days = minutes / 1440;
    return `${days.toFixed(1)} day(s)`;
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
                    <TableCell align="center"><strong>Total Trace Executions</strong></TableCell>
                    <TableCell align="center"><strong>Pools</strong></TableCell>
                    <TableCell align="center"><strong>Total costs by Item Type</strong></TableCell>
                    <TableCell align="center"><strong>Total execution Time by Item</strong></TableCell>

                  </TableRow>
                </TableHead>
                <TableBody>
                  <TableRow>
                    <TableCell align="center">{data.total_traces}</TableCell>
                    <TableCell align="center">
                      {Array.isArray(data.unique_pools)
                        ? data.unique_pools.join(', ')
                        : "No pools found"}
                    </TableCell>
                    <TableCell align="center">
                    {Array.isArray(data.costs_by_item) && data.costs_by_item.length > 0 ? (() => {
                      const total = data.costs_by_item.reduce((sum: number, item: any) => sum + item.total_item_cost, 0);
                      return (
                        <div className="text-sm text-center">
                          {data.costs_by_item.map((item: any) => (
                            <div key={item.instanceType}>
                              <strong>{item.instanceType}:</strong> € {item.total_item_cost.toFixed(2)}
                            </div>
                          ))}
                          <hr className="my-1" />
                          <div><strong>Total:</strong> € {total.toFixed(2)}</div>
                        </div>
                      );
                    })() : "No cost data"}

                    </TableCell>
                    <TableCell align="center">
                    {Array.isArray(data.execution_by_item) && data.execution_by_item.length > 0 ? (() => {
                      const total = data.execution_by_item.reduce((sum: number, item: any) => sum + item.total_execution_minutes, 0);
                      return (
                        <div className="text-sm text-center">
                          {data.execution_by_item.map((item: any) => (
                            <div key={item.instanceType}>
                              <strong>{item.instanceType}:</strong> {formatDuration(item.total_execution_minutes)}                             </div>
                          ))}
                          <hr className="my-1" />
                          <div><strong>Total: </strong>{formatDuration(total)}</div>
                        </div>
                      );
                    })() : "No execution data"}

                    </TableCell>

                  </TableRow>
                </TableBody>
              </Table>
            </TableContainer>
          </div>
        );
    }
