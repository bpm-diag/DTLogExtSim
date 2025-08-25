import pandas as pd
from typing import Dict, List

from support_modules.constants import *

def reorder_events_for_cost_hour(self, temp_data: pd.DataFrame) -> List[Dict]:
    """Riordina eventi per calcolo costi orari."""
    ordered_event_log = []
    
    for caseid, group in temp_data.groupby(TAG_TRACE_ID):
        trace = group.to_dict('records')
        temp_trace = []
        
        for i in range(len(trace) - 1):
            if trace[i][TAG_LIFECYCLE] == LIFECYCLE_START:
                self._reorder_single_event_for_cost(caseid, i, temp_trace, trace)
        
        ordered_event_log.extend(temp_trace)
    
    return ordered_event_log

def reorder_single_event_for_cost(self, caseid: str, i: int, temp_trace: List, trace: List) -> None:
    """Riordina un singolo evento per costo orario."""
    task_name = trace[i][TAG_ACTIVITY_NAME]
    remaining = trace[i + 1:]
    
    # Trova evento complete corrispondente
    complete_event = next(
        (event for event in remaining 
            if event[TAG_ACTIVITY_NAME] == task_name and event[TAG_LIFECYCLE] == LIFECYCLE_COMPLETE),
        None
    )
    
    # Crea evento strutturato
    structured_event = {
        TAG_TRACE_ID: caseid,
        TAG_ACTIVITY_NAME: trace[i][TAG_ACTIVITY_NAME],
        TAG_RESOURCE: trace[i][TAG_RESOURCE],
        TAG_COST_HOUR: complete_event[TAG_COST_HOUR] if complete_event else trace[i][TAG_COST_HOUR],
        'start_timestamp': trace[i][TAG_TIMESTAMP],
        'end_timestamp': complete_event[TAG_TIMESTAMP] if complete_event else trace[i][TAG_TIMESTAMP]
    }
    
    temp_trace.append(structured_event)

def reorder_setup_events(self, temp_data: pd.DataFrame) -> List[Dict]:
    """Riordina eventi di setup time."""
    ordered_event_log = []
    
    for caseid, group in temp_data.groupby(TAG_TRACE_ID):
        trace = group.to_dict('records')
        temp_trace = []
        
        for i in range(len(trace) - 1):
            if trace[i][TAG_LIFECYCLE] == LIFECYCLE_START_SETUP:
                self._reorder_single_setup_event(caseid, i, temp_trace, trace)
        
        ordered_event_log.extend(temp_trace)
    
    return ordered_event_log

def reorder_single_setup_event(self, caseid: str, i: int, temp_trace: List, trace: List) -> None:
    """Riordina un singolo evento di setup."""
    task_name = trace[i][TAG_ACTIVITY_NAME]
    remaining = trace[i + 1:]
    
    # Trova evento endSetupTime corrispondente
    complete_event = next(
        (event for event in remaining 
            if event[TAG_ACTIVITY_NAME] == task_name and event[TAG_LIFECYCLE] == LIFECYCLE_END_SETUP),
        None
    )
    
    # Estrai info risorsa (formato: [[risorsa, max_usage]])
    resource_info = trace[i][TAG_RESOURCE][0]
    resource_name = resource_info[0]
    max_usage = resource_info[1]
    
    # Crea evento strutturato
    structured_event = {
        TAG_TRACE_ID: caseid,
        TAG_ACTIVITY_NAME: trace[i][TAG_ACTIVITY_NAME],
        TAG_RESOURCE: resource_name,
        'max_usage_before_setup_time': max_usage,
        'start_timestamp': trace[i][TAG_TIMESTAMP],
        'end_timestamp': complete_event[TAG_TIMESTAMP] if complete_event else trace[i][TAG_TIMESTAMP]
    }
    
    temp_trace.append(structured_event)