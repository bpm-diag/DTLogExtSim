import React, { useState } from 'react';
import {
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Paper, FormControl, InputLabel, MenuItem, Select, SelectChangeEvent
} from '@mui/material';

export type ActivitySummary = {
  activity: string;
  waitingTimeMin: number;
  waitingTimeAvg: number;
  waitingTimeMax: number;
  durationMin: number;
  durationAvg: number;
  durationMax: number;
  costMin: number;
  costAvg: number;
  costMax: number;
};

type Props = {
  data: ActivitySummary[];
};

const ActivitySummaryTable: React.FC<Props> = ({ data }) => {
  const [unit, setUnit] = useState<'seconds' | 'minutes' | 'hours' | 'days'>('minutes');

  const handleChange = (event: SelectChangeEvent) => {
    setUnit(event.target.value as typeof unit);
  };

  const unitLabel = unit === 'seconds' ? 's' : unit === 'hours' ? 's' : unit === 'days' ? 'd' : 'min';

  const convertTime = (value: number) => {
    switch (unit) {
      case 'seconds': return value * 60;
      case 'hours': return value / 60;
      case 'days': return value / (24*60);
      default: return value;
    }
  };

  const borderLeft = { borderLeft: '2px solid rgba(0, 0, 0, 0.12)' };

  return (
    <div className="mb-10 mx-auto p-6 rounded-xl shadow inline-block bg-gray-100 w-[90%]">

        <h2 className="text-2xl font-bold text-gray-800 mb-4">Activity Summary Table</h2>
      <div className="flex justify-end items-center gap-2 mb-4">
        <FormControl size="small" style={{ minWidth: 120 }}>
          <InputLabel>Unit</InputLabel>
          <Select
            value={unit}
            label="Unit"
            onChange={handleChange}
          >
            <MenuItem value="seconds">Seconds</MenuItem>
            <MenuItem value="minutes">Minutes</MenuItem>
            <MenuItem value="hours">Hours</MenuItem>
            <MenuItem value="days">Days</MenuItem>
          </Select>
        </FormControl>
      </div>

      <TableContainer component={Paper} sx={{ maxHeight: 600 }}>
        <Table stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell><strong>Activity name</strong></TableCell>
              <TableCell colSpan={3} sx={borderLeft} align="center"><strong>Waiting time ({unitLabel})</strong></TableCell>
              <TableCell colSpan={3} sx={borderLeft} align="center"><strong>Duration ({unitLabel})</strong></TableCell>
              <TableCell colSpan={3} sx={borderLeft} align="center"><strong>Cost</strong></TableCell>
            </TableRow>
            <TableRow>
              <TableCell />
              <TableCell sx={borderLeft}>Min</TableCell>
              <TableCell>Avg</TableCell>
              <TableCell>Max</TableCell>
              <TableCell sx={borderLeft}>Min</TableCell>
              <TableCell>Avg</TableCell>
              <TableCell>Max</TableCell>
              <TableCell sx={borderLeft}>Min</TableCell>
              <TableCell>Avg</TableCell>
              <TableCell>Max</TableCell>
            </TableRow>
          </TableHead>
          <TableBody >
            {data.map((row) => (
              <TableRow key={row.activity}>
                <TableCell>{row.activity}</TableCell>
                <TableCell sx={borderLeft}>{convertTime(row.waitingTimeMin).toFixed(2)}</TableCell>
                <TableCell>{convertTime(row.waitingTimeAvg).toFixed(2)}</TableCell>
                <TableCell>{convertTime(row.waitingTimeMax).toFixed(2)}</TableCell>
                <TableCell sx={borderLeft}>{convertTime(row.durationMin).toFixed(2)}</TableCell>
                <TableCell>{convertTime(row.durationAvg).toFixed(2)}</TableCell>
                <TableCell>{convertTime(row.durationMax).toFixed(2)}</TableCell>
                <TableCell sx={borderLeft}>{row.costMin.toFixed(2)}</TableCell>
                <TableCell>{row.costAvg.toFixed(2)}</TableCell>
                <TableCell>{row.costMax.toFixed(2)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </div>
  );
};

export default ActivitySummaryTable;
