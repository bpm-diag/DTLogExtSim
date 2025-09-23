from typing import Optional, Any, Dict
import xml.etree.ElementTree as ET
import pandas as pd

from support_modules.constants import *

def extract_process_id(self, bpmn_file_path: str) -> Optional[str]:
    """Estrae process ID dal file BPMN."""
    try:
        tree = ET.parse(bpmn_file_path)
        root = tree.getroot()
        
        for process in root.findall(".//{*}process"):
            process_id = process.get("id")
            if process_id:
                return process_id
        return None
    except Exception:
        return None
    
def identify_interrupted_activities(self, reordered_log: pd.DataFrame) -> pd.DataFrame:
    """Identifica attività con timestamp mancanti (interrotte)."""
    if self.num_timestamp == 1:
        # Per singolo timestamp, non ci sono interruzioni da rilevare
        return pd.DataFrame()
    
    # Identifica righe con timestamp "nan"
    nan_conditions = []
    
    if 'assign_timestamp' in reordered_log.columns:
        nan_conditions.append(reordered_log['assign_timestamp'] == "nan")
    if 'start_timestamp' in reordered_log.columns:
        nan_conditions.append(reordered_log['start_timestamp'] == "nan")
    if 'end_timestamp' in reordered_log.columns:
        nan_conditions.append(reordered_log['end_timestamp'] == "nan")
    
    if nan_conditions:
        # Combina tutte le condizioni con OR
        combined_condition = nan_conditions[0]
        for condition in nan_conditions[1:]:
            combined_condition |= condition
        
        return reordered_log[combined_condition]
    
    return pd.DataFrame()

def identify_final_completed_activities(self, reordered_log: pd.DataFrame, 
                                        interrupted_activities: pd.DataFrame) -> pd.DataFrame:
    """Identifica le attività finali completate dalle tracce non interrotte."""
    # Esclude tracce con attività interrotte
    interrupted_trace_ids = interrupted_activities['caseid'].unique() if not interrupted_activities.empty else []
    completed_traces = reordered_log[~reordered_log['caseid'].isin(interrupted_trace_ids)]
    
    if completed_traces.empty:
        return pd.DataFrame()
    
    # Trova l'ultima attività per ogni traccia (basata su end_timestamp)
    if 'end_timestamp' in completed_traces.columns:
        # Filtra solo eventi con end_timestamp valido
        valid_completed = completed_traces[completed_traces['end_timestamp'] != "nan"]
        if not valid_completed.empty:
            # Converte timestamp per trovare il massimo
            valid_completed = valid_completed.copy()
            valid_completed['end_timestamp'] = pd.to_datetime(valid_completed['end_timestamp'])
            return valid_completed.loc[valid_completed.groupby('caseid')['end_timestamp'].idxmax()]
    
    return pd.DataFrame()

def identify_start_activity(self) -> str:
    """
    Identifica l'attività di start dal log con logica migliorata.
    
    Returns:
        Nome dell'attività di start
        
    Raises:
        ValueError: Se nessuna attività di start viene trovata
    """
    print("Identificando attività di start...")
    
    try:
        start_events = pd.DataFrame()
        
        # STRATEGIA 1: Log diagnostico - cerca nodeType="startEvent"
        if self.diaglog and TAG_NODE_TYPE in self.log.columns:
            start_events = self.log[self.log[TAG_NODE_TYPE] == 'startEvent']
            if not start_events.empty:
                start_activity = start_events[TAG_ACTIVITY_NAME].iloc[0]
                print(f"✓ Start activity trovata (nodeType): {start_activity}")
                return start_activity
        
        # STRATEGIA 2: Pattern testuale "Start" (case-insensitive)
        start_patterns = [r'Start', r'start', r'BEGIN', r'begin']
        for pattern in start_patterns:
            start_events = self.log[self.log[TAG_ACTIVITY_NAME].str.contains(pattern, case=False, na=False)]
            if not start_events.empty:
                start_activity = start_events[TAG_ACTIVITY_NAME].iloc[0]
                print(f"✓ Start activity trovata (pattern '{pattern}'): {start_activity}")
                return start_activity
        
        # STRATEGIA 3: Prima attività cronologicamente (fallback)
        print("⚠ Nessun evento start esplicito trovato, usando prima attività cronologica...")
        
        # Trova la prima attività per ogni traccia, poi quella più comune
        first_activities = []
        for trace_id, trace_group in self.log.groupby(TAG_TRACE_ID):
            trace_sorted = trace_group.sort_values(TAG_TIMESTAMP)
            if not trace_sorted.empty:
                first_activity = trace_sorted.iloc[0][TAG_ACTIVITY_NAME]
                first_activities.append(first_activity)
        
        if first_activities:
            # Usa l'attività più comune come start
            from collections import Counter
            most_common_start = Counter(first_activities).most_common(1)[0][0]
            print(f"✓ Start activity dedotta (più comune): {most_common_start}")
            return most_common_start
        
        # STRATEGIA 4: Crea attività di start virtuale
        print("⚠ Creando attività di start virtuale...")
        return "VirtualStart"
        
    except Exception as e:
        raise Exception(f"Errore nell'identificazione attività start: {str(e)}")
    
def identify_start_activity_old(self) -> str:
    """Identifica l'attività di start dal log."""
    start_pattern = r'Start'
    start_events = self.log[self.log[TAG_ACTIVITY_NAME].str.contains(start_pattern, case=False, na=False)]
    
    if start_events.empty:
        raise ValueError("Attività di start non trovata nel log")
        
    return start_events[TAG_ACTIVITY_NAME].unique()[0]

def find_target_flow_for_activity(self, app_model: Any, activity_name: str, activity_type: str) -> Optional[Any]:
    """Trova il flusso target per un'attività specifica."""
    for flow in app_model.get_flows():
        if activity_type == 'interrupted':
            # Per attività interrotte, cerca il flusso che ha l'attività come target
            if flow.get_target().get_name() == activity_name:
                return flow
        else:  # 'ended'
            # Per attività completate, cerca il flusso che ha l'attività come source
            if flow.get_source().get_name() == activity_name:
                return flow
    return None

def find_corresponding_flow(self, model: Any, target_flow: Any) -> Optional[Any]:
    """Trova il flusso corrispondente nel modello principale."""
    for flow in model.get_flows():
        if flow.get_id() == target_flow.get_id():
            return flow
    return None

def find_start_flow_info(self, app_model: Any, model: Any, start_activity: str) -> Dict[str, Any]:
    """Trova informazioni sul flusso di start."""
    flow_info = {
        'source': None,
        'target': None,
        'flow_to_delete': None
    }
    
    # Trova flusso di start nel modello app
    for flow in app_model.get_flows():
        if flow.get_source().get_name() == start_activity:
            # Trova flusso corrispondente nel modello principale
            for model_flow in model.get_flows():
                if model_flow.get_id() == flow.get_id():
                    flow_info['flow_to_delete'] = model_flow
                    flow_info['source'] = model_flow.get_source()
                    flow_info['target'] = model_flow.get_target()
                    break
            break
    
    return flow_info