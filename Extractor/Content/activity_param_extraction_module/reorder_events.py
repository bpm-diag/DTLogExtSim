import pandas as pd
from typing import List, Dict, Optional, Tuple, Set

from support_modules.constants import *


def _find_with_index(
    trace: List[Dict],
    start_from: int,
    task_name: str,
    event_type: str,
    consumed: Set[int],
) -> Tuple[Optional[Dict], Optional[int]]:
    """Trova il primo evento non consumato con task e tipo corrispondenti."""
    for idx in range(start_from, len(trace)):
        if idx in consumed:
            continue
        event = trace[idx]
        if event['task'] == task_name and event['event_type'] == event_type:
            return event, idx
    return None, None


def reorder_events(self, log: pd.DataFrame) -> pd.DataFrame:
    """
    Riordina gli eventi per creare record strutturati con timestamp multipli.

    La strategia è per-occorrenza: per ogni evento non ancora consumato,
    si usa come ancora il lifecycle più ricco disponibile:
      - ASSIGN → cerca START poi COMPLETE in avanti
      - START (senza ASSIGN precedente) → cerca COMPLETE in avanti
      - COMPLETE (senza START precedente) → record con solo timestamp di fine

    Schema output: caseid, task, assign_timestamp (None se assente),
                   start_timestamp, end_timestamp
    """
    print("Riordinando eventi per creare timestamp strutturati (per-occorrenza)...")

    ordered_event_log = []

    for caseid, group in log.groupby('caseid'):
        trace = group.to_dict('records')
        consumed: Set[int] = set()

        for i, event in enumerate(trace):
            if i in consumed:
                continue

            task = event['task']
            etype = event['event_type']

            if etype == LIFECYCLE_ASSIGN:
                start_ev, start_idx = _find_with_index(trace, i + 1, task, LIFECYCLE_START, consumed)
                search_from = (start_idx + 1) if start_idx is not None else i + 1
                complete_ev, complete_idx = _find_with_index(trace, search_from, task, LIFECYCLE_COMPLETE, consumed)

                consumed.add(i)
                if start_idx is not None:
                    consumed.add(start_idx)
                if complete_idx is not None:
                    consumed.add(complete_idx)

                ordered_event_log.append({
                    'caseid': caseid,
                    'task': task,
                    'assign_timestamp': event['timestamp'],
                    'start_timestamp': start_ev['timestamp'] if start_ev else None,
                    'end_timestamp': complete_ev['timestamp'] if complete_ev else None,
                })

            elif etype == LIFECYCLE_START:
                complete_ev, complete_idx = _find_with_index(trace, i + 1, task, LIFECYCLE_COMPLETE, consumed)

                consumed.add(i)
                if complete_idx is not None:
                    consumed.add(complete_idx)

                ordered_event_log.append({
                    'caseid': caseid,
                    'task': task,
                    'assign_timestamp': None,
                    'start_timestamp': event['timestamp'],
                    'end_timestamp': complete_ev['timestamp'] if complete_ev else event['timestamp'],
                })

            elif etype == LIFECYCLE_COMPLETE:
                consumed.add(i)
                ordered_event_log.append({
                    'caseid': caseid,
                    'task': task,
                    'assign_timestamp': None,
                    'start_timestamp': event['timestamp'],
                    'end_timestamp': event['timestamp'],
                })

    result = pd.DataFrame(ordered_event_log)
    print(f"✓ Riordinamento completato: {len(result)} record di attività")
    return result
