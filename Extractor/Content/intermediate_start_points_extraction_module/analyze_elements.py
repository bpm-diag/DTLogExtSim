from typing import Tuple, List, Dict, Set, Optional
import pandas as pd

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


def analyze_final_activities(self) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Analizza le attività finali nelle tracce tagliate.

    Returns:
        Tupla (attività_interrotte, attività_completate)
    """
    print("Analizzando attività finali nelle tracce tagliate...")

    try:
        # Preprocessing del log
        processed_log = self._preprocess_log_for_analysis()

        # Riordina eventi per creare timestamp strutturati
        reordered_log = self._reorder_events_for_analysis(processed_log)
        reordered_df = pd.DataFrame(reordered_log)

        # Identifica attività interrotte (timestamp mancanti)
        interrupted_activities = self._identify_interrupted_activities(reordered_df)

        # Identifica attività completate finali
        completed_activities = self._identify_final_completed_activities(reordered_df, interrupted_activities)

        print(f"✓ Trovate {len(interrupted_activities)} attività interrotte")
        print(f"✓ Trovate {len(completed_activities)} attività completate finali")

        return interrupted_activities, completed_activities

    except Exception as e:
        raise Exception(f"Errore nell'analisi delle attività finali: {str(e)}")


def preprocess_log_for_analysis(self) -> pd.DataFrame:
    """Preprocessa il log per l'analisi delle attività finali."""
    log = self.log.copy()

    # Rinomina colonne
    column_mapping = {
        TAG_TRACE_ID: 'caseid',
        TAG_ACTIVITY_NAME: 'task',
        TAG_LIFECYCLE: 'event_type',
        TAG_TIMESTAMP: 'timestamp'
    }
    log = log.rename(columns=column_mapping)

    # Rimuovi eventi start/end
    exclude_activities = ['Start', 'End', 'start', 'end']
    log = log[~log['task'].isin(exclude_activities)].reset_index(drop=True)

    return log


def reorder_events_for_analysis(self, log: pd.DataFrame) -> List[Dict]:
    """
    Riordina eventi per creare timestamp strutturati (per-occorrenza).

    Stessa logica di ActivityParamExtraction.reorder_events: per ogni occorrenza
    usa come ancora il lifecycle più ricco (ASSIGN > START > COMPLETE).
    Le attività con solo start+complete vengono incluse correttamente.
    I timestamp mancanti sono None (rilevabili con pd.isna).
    """
    ordered_events = []

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

                ordered_events.append({
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

                ordered_events.append({
                    'caseid': caseid,
                    'task': task,
                    'assign_timestamp': None,
                    'start_timestamp': event['timestamp'],
                    'end_timestamp': complete_ev['timestamp'] if complete_ev else None,
                })

            elif etype == LIFECYCLE_COMPLETE:
                consumed.add(i)
                ordered_events.append({
                    'caseid': caseid,
                    'task': task,
                    'assign_timestamp': None,
                    'start_timestamp': event['timestamp'],
                    'end_timestamp': event['timestamp'],
                })

    return ordered_events
