import pandas as pd
from typing import List, Dict, Optional

from support_modules.constants import *

def reorder_events(self, log: pd.DataFrame) -> pd.DataFrame:
        """
        Riordina gli eventi per creare record strutturati con timestamp multipli.
        
        Args:
            log: Log con eventi singoli
            
        Returns:
            DataFrame con record di attività strutturati
        """
        print("Riordinando eventi per creare timestamp strutturati...")
        
        ordered_event_log = []
        
        if self.num_timestamp == 1:
            # Solo timestamp complete
            ordered_event_log = self._reorder_single_timestamp(log)
        elif self.num_timestamp == 2:
            # Start e complete timestamp
            ordered_event_log = self._reorder_dual_timestamp(log)
        elif self.num_timestamp == 3:
            # Assign, start e complete timestamp
            ordered_event_log = self._reorder_triple_timestamp(log)
        else:
            raise ValueError(f"Numero timestamp non supportato: {self.num_timestamp}")
        
        return pd.DataFrame(ordered_event_log)


def reorder_single_timestamp(self, log: pd.DataFrame) -> List[Dict]:
        """Riordina per singolo timestamp (solo complete)."""
        complete_events = log[log['event_type'] == LIFECYCLE_COMPLETE].copy()
        complete_events = complete_events.rename(columns={'timestamp': 'end_timestamp'})

        complete_events["start_timestamp"] = complete_events["end_timestamp"]

        complete_events = complete_events.drop(columns='event_type')
        complete_events = complete_events[['caseid', 'task', "start_timestamp", 'end_timestamp']]
        
        return complete_events.to_dict('records')
    
def reorder_dual_timestamp(self, log: pd.DataFrame) -> List[Dict]:
        """Riordina per doppio timestamp (start e complete)."""
        ordered_events = []
        
        for caseid, group in log.groupby('caseid'):
            trace = group.to_dict('records')
            
            for i, event in enumerate(trace[:-1]):
                if event['event_type'] == LIFECYCLE_START:
                    reordered_event = self._create_reordered_event(
                        caseid, i, trace, event, 'dual'
                    )
                    if reordered_event:
                        ordered_events.append(reordered_event)
        
        return ordered_events

def reorder_triple_timestamp(self, log: pd.DataFrame) -> List[Dict]:
        """Riordina per triplo timestamp (assign, start, complete)."""
        ordered_events = []
        
        for caseid, group in log.groupby('caseid'):
            trace = group.to_dict('records')
            
            for i, event in enumerate(trace[:-1]):
                if event['event_type'] == LIFECYCLE_ASSIGN:
                    reordered_event = self._create_reordered_event(
                        caseid, i, trace, event, 'triple'
                    )
                    if reordered_event:
                        ordered_events.append(reordered_event)
        
        return ordered_events