import pm4py
import os
import re
import pandas as pd
from typing import Dict, Tuple, List

from support_modules.constants import *

from branching_probabilities_module.branching_probabilities import BranchProbCalculation

def calculate_forced_instance_types(self, forced_flows: Dict[str, Tuple[str, str, str]],
                                      interrupted_activities: pd.DataFrame,
                                      completed_activities: pd.DataFrame) -> pd.DataFrame:
    """
    Calcola i tipi di istanza forzati per gli stati intermedi.
    
    Args:
        forced_flows: Dizionario dei flussi forzati
        interrupted_activities: Attività interrotte
        completed_activities: Attività completate
        
    Returns:
        DataFrame con tipi di istanza forzati
    """
    print("Calcolando tipi di istanza forzati...")
    
    try:
        # Conta ripetizioni per attività interrotte e completate
        rep_interrupted = interrupted_activities.groupby('task').size() if not interrupted_activities.empty else pd.Series()
        rep_completed = completed_activities.groupby('task').size() if not completed_activities.empty else pd.Series()
        
        result = []
        
        for i, (flow_id, (status, source, activity_target)) in enumerate(forced_flows.items()):
            repetition_count = 0
            
            if status == 'interrupted' and activity_target in rep_interrupted:
                repetition_count = rep_interrupted[activity_target]
            elif status == 'ended' and activity_target in rep_completed:
                repetition_count = rep_completed[activity_target]
            
            result.append({
                'Flow': flow_id,
                'Status': status,
                'Instance Type': f'A{i}',
                'Repetition Instance Type': repetition_count
            })
        
        df_result = pd.DataFrame(result)
        print(f"✓ Calcolati {len(df_result)} tipi di istanza forzati")
        return df_result
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo dei tipi di istanza forzati: {str(e)}")

def calculate_flow_probabilities(self, forced_instance_types: pd.DataFrame) -> List[Tuple[str, float]]:
    """
    Calcola le probabilità di flusso per i gateway intermedi.
    
    Args:
        forced_instance_types: DataFrame con tipi di istanza forzati
        
    Returns:
        Lista di tuple (flow_id, probabilità)
    """
    print("Calcolando probabilità di flusso...")
    
    try:
        if forced_instance_types.empty:
            return []
        
        # Estrai numeri dai flow ID
        flow_numbers = []
        for flow_id in forced_instance_types['Flow']:
            # Estrai numero dalla fine dell'ID
            match = re.search(r'_(\d+)', flow_id)
            if match:
                flow_numbers.append(int(match.group(1)))
        
        if not flow_numbers:
            return []
        
        flow_numbers.sort()
        flow_probabilities = []
        
        # Crea probabilità per flussi gateway-to-gateway e gateway-to-target
        for i, flow_num in enumerate(flow_numbers):
            if flow_num == flow_numbers[-1]:
                # Ultimo gateway -> target finale
                flow_id = f"flow_g_t_{flow_num}"
            else:
                # Gateway -> prossimo gateway
                flow_id = f"flow_g_g_{flow_num + 1}"
            
            flow_probabilities.append((flow_id, 0.9))
        
        # Aggiungi probabilità per flussi intermedi (più basse)
        for flow_id in forced_instance_types['Flow']:
            flow_probabilities.append((flow_id, 0.1))
        
        print(f"✓ Calcolate {len(flow_probabilities)} probabilità di flusso")
        return flow_probabilities
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo delle probabilità di flusso: {str(e)}")

def calculate_branching_probabilities_for_modified_model(self) -> List[Tuple[str, float]]:
    """
    Calcola le probabilità di branching per il modello modificato.
    
    Returns:
        Lista delle probabilità di flusso
    """
    print("Calcolando probabilità di branching per modello modificato...")
    
    try:
        # Preprocessing del log
        temp_log = self.log.copy()
        gateway_pattern = r'Gateway'
        
        if self.diaglog:
            # Rimuovi gateway da log diagnostici
            temp_log = temp_log[~temp_log[TAG_ACTIVITY_NAME].str.contains(gateway_pattern, case=False, na=False)]
            temp_log = temp_log[~temp_log[TAG_NODE_TYPE].str.contains(gateway_pattern, case=False, na=False)]
            temp_log = temp_log[~temp_log[TAG_LIFECYCLE].str.contains(gateway_pattern, case=False, na=False)]
            temp_log = temp_log[~temp_log[TAG_NODE_TYPE].str.contains(gateway_pattern, case=False, na=False)]
        
        # Carica modello modificato
        model_path = os.path.join(self.path, "output_data", f"{self.output_name}_intermediate_start_points.bpmn")
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Modello modificato non trovato: {model_path}")
        
        bpmn_model = pm4py.read_bpmn(model_path)
        
        # Calcola probabilità di branching
        branch_calc = BranchProbCalculation(temp_log, bpmn_model, self.settings, True)

        results = branch_calc.calculate_all_probabilities()
        # Accesso ai risultati
        flow_probabilities = branch_calc.flow_prob
        branches = branch_calc.branches
        print("✓ Probabilità di branching calcolate per modello modificato")
        return flow_probabilities
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo probabilità branching: {str(e)}")
