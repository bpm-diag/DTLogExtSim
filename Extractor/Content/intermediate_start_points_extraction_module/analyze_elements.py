from typing import Tuple, List, Dict
import pandas as pd

from support_modules.constants import *

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

def should_process_event(self, event_type: str) -> bool:
    """Determina se processare un evento basato sul tipo e configurazione."""
    if self.num_timestamp == 3:
        # Per 3 timestamp, inizia da assign
        # if self.diaglog and not self.correct_order_diag_log:
        #     return event_type == LIFECYCLE_START
        # else:
        return event_type == LIFECYCLE_ASSIGN
    else:
        # Per 2 timestamp, inizia da start (o assign se ordine sbagliato)
        # if self.diaglog and not self.correct_order_diag_log:
        #     return event_type == LIFECYCLE_ASSIGN
        # else:
        return event_type == LIFECYCLE_START

def reorder_events_for_analysis(self, log: pd.DataFrame) -> List[Dict]:
    """Riordina eventi per creare timestamp strutturati (simile ad ActivityParamExtraction)."""
    ordered_events = []
    
    if self.num_timestamp == 1:
        # Solo complete
        complete_events = log[log['event_type'] == LIFECYCLE_COMPLETE].copy()
        complete_events = complete_events.rename(columns={'timestamp': 'end_timestamp'})
        complete_events = complete_events[['caseid', 'task', 'end_timestamp']]
        return complete_events.to_dict('records')
    
    # Per timestamp multipli
    for caseid, group in log.groupby('caseid'):
        trace = group.to_dict('records')
        
        for i, event in enumerate(trace):
            if self._should_process_event(event['event_type']):
                reordered_event = self._create_reordered_event_for_analysis(
                    caseid, i, trace, event
                )
                if reordered_event:
                    ordered_events.append(reordered_event)
    
    return ordered_events