from typing import List, Dict, Optional

from support_modules.constants import *

def create_reordered_event(self, caseid: str, event_index: int, trace: List[Dict], 
                               current_event: Dict, timestamp_type: str) -> Optional[Dict]:
        """
        Crea un evento riordinato con timestamp multipli.
        
        Args:
            caseid: ID della traccia
            event_index: Indice dell'evento corrente
            trace: Lista degli eventi della traccia
            current_event: Evento corrente
            timestamp_type: Tipo di timestamp ('dual' o 'triple')
            
        Returns:
            Dizionario con evento riordinato o None
        """
        task_name = current_event['task']
        remaining_events = trace[event_index + 1:]
        
        # Trova eventi correlati
        start_event = self._find_matching_event(remaining_events, task_name, LIFECYCLE_START)
        complete_event = self._find_matching_event(remaining_events, task_name, LIFECYCLE_COMPLETE)
        
        if timestamp_type == 'dual':
            return self._create_dual_timestamp_event(caseid, current_event, complete_event)
        else:  # triple
            return self._create_triple_timestamp_event(caseid, current_event, start_event, complete_event)
        

def create_dual_timestamp_event(self, caseid: str, start_event: Dict, 
                                   complete_event: Optional[Dict]) -> Dict:
        """Crea evento con start e complete timestamp."""
        return {
            'caseid': caseid,
            'task': start_event['task'],
            'start_timestamp': start_event['timestamp'],
            'end_timestamp': complete_event['timestamp'] if complete_event else start_event['timestamp']
        }

def create_triple_timestamp_event(self, caseid: str, assign_event: Dict,
                                     start_event: Optional[Dict], 
                                     complete_event: Optional[Dict]) -> Dict:
        """Crea evento con assign, start e complete timestamp."""
        return {
            'caseid': caseid,
            'task': assign_event['task'],
            'assign_timestamp': assign_event['timestamp'],
            'start_timestamp': start_event['timestamp'] if start_event else None,
            'end_timestamp': complete_event['timestamp'] if complete_event else None
        }