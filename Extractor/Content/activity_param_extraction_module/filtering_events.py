import pandas as pd
from typing import List, Dict, Optional
import numpy as np

from support_modules.constants import *




def filter_lifecycle_events(self, log: pd.DataFrame) -> pd.DataFrame:
        """Filtra solo eventi assign, start, complete."""
        valid_events = [LIFECYCLE_ASSIGN, LIFECYCLE_START, LIFECYCLE_COMPLETE]
        return log[log['event_type'].isin(valid_events)].reset_index(drop=True)


def remove_start_end_events(self, log: pd.DataFrame) -> pd.DataFrame:
    """Rimuove eventi di start e end per log normali."""
    start_pattern = r'Start'
    end_pattern = r'End'
    
    log = log[~log[TAG_ACTIVITY_NAME].str.contains(start_pattern, case=False, na=False)]
    log = log[~log[TAG_ACTIVITY_NAME].str.contains(end_pattern, case=False, na=False)]
    
    return log

def identify_abort_events(self, log: pd.DataFrame) -> List[str]:
    """Identifica eventi di abort nei log diagnostici."""
    abort_events = []
    
    if self.diaglog and TAG_NODE_TYPE in log.columns:
        abort_pattern = r'endEvent/terminateEventDefinition'
        abort_event_log = log[log[TAG_NODE_TYPE].str.contains(abort_pattern, case=False, na=False)]
        abort_events = abort_event_log[TAG_ACTIVITY_NAME].unique().tolist()
        
        if abort_events:
            print(f"Eventi abort identificati: {abort_events}")
    
    return abort_events

def clean_outliers(self, data: List[float]) -> List[float]:
        """
        Rimuove outliers dai dati usando la mediana.
        
        Args:
            data: Lista di valori numerici
            
        Returns:
            Lista pulita senza outliers
        """
        if not data:
            return data
        
        median_value = np.median(data)
        threshold = 5 * median_value
        
        return [x for x in data if x <= threshold]
    

    
def find_matching_event(self, events: List[Dict], task_name: str, event_type: str) -> Optional[Dict]:
    """Trova un evento corrispondente nella lista."""
    return next(
        (event for event in events 
            if event['task'] == task_name and event['event_type'] == event_type),
        None
    )