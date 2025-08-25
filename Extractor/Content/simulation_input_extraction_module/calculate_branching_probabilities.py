import os
import pm4py


import pandas as pd
from typing import Optional, Any, List, Tuple

from support_modules.constants import *

from branching_probabilities_module.branching_probabilities import BranchProbCalculation 


def calculate_branching_probabilities(self, new_model_with_intermediate_points: Optional[Any] = None, 
                                       intermediate_model: bool = False) -> None:
    """
    Calcola le probabilità di branching dal log.
    
    Args:
        new_model_with_intermediate_points: Modello con punti intermedi
        intermediate_model: Se si tratta di un modello intermedio
    """
    try:
        print("Calcolando probabilità di branching...")
        
        # Preprocessing del log per rimuovere gateway
        processed_log = self._preprocess_log_for_branching()
        
        # Caricamento modello BPMN
        if intermediate_model and new_model_with_intermediate_points:
            bpmn_model = new_model_with_intermediate_points
        else:
            bpmn_model = self._load_bpmn_model()
        
        # Matching ID-Nome attività (se necessario)
        if self.with_start_end_act:
            self._id_name_act_match = self._match_id_name(bpmn_model, processed_log)
        
        # Rimozione eventi start/end per log diag
        if self.primary_config['diag_log']:
            processed_log = self._remove_start_end_events(processed_log)
        
        # Calcolo probabilità
        self._branch_prob = BranchProbCalculation(processed_log, bpmn_model, self.settings, intermediate_model)
        results = self._branch_prob.calculate_all_probabilities()

        # Matching ID-Nome per log normali
        if not self.with_start_end_act:
            self._id_name_act_match = self._match_id_name(bpmn_model, processed_log)
        
        print("✓ Probabilità di branching calcolate")
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo delle probabilità di branching: {str(e)}")

def preprocess_log_for_branching(self) -> pd.DataFrame:
    """Preprocessa il log rimuovendo elementi gateway."""
    temp_log = self.log.copy()
    gateway_pattern = r'Gateway'
    
    if self.primary_config['diag_log']:
        # Per log diag, rimuovi gateway da più colonne
        temp_log = temp_log[~temp_log[TAG_ACTIVITY_NAME].str.contains(gateway_pattern, case=False, na=False)]
        temp_log = temp_log[~temp_log[TAG_NODE_TYPE].str.contains(gateway_pattern, case=False, na=False)]
        temp_log = temp_log[~temp_log[TAG_LIFECYCLE].str.contains(gateway_pattern, case=False, na=False)]
        # temp_log = temp_log[~temp_log[TAG_NODE_TYPE].str.contains(gateway_pattern, case=False, na=False)]
    return temp_log

def load_bpmn_model(self) -> Any:
    """Carica il modello BPMN dal file system."""
    model_path = os.path.join(
        self.primary_config['path'],
        'output_data/output_file',
        f"{self.primary_config['namefile']}_pm4py.bpmn"
    )
    
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Modello BPMN non trovato: {model_path}")
        
    return pm4py.read_bpmn(model_path)

def remove_start_end_events(self, log: pd.DataFrame) -> pd.DataFrame:
    """Rimuove eventi di start e end dal log diag."""
    return log[~log[TAG_NODE_TYPE].isin(['startEvent', 'endEvent'])].reset_index(drop=True)

def match_id_name(self, model: Any, log: pd.DataFrame) -> List[Tuple[str, str]]:
    """
    Crea matching tra ID e nomi delle attività.
    
    Args:
        model: Modello BPMN
        log: Log processato
        
    Returns:
        Lista di tuple (nome_attività, id_attività)
    """
    matching = []
    
    # Estrai attività unique dal log
    exploded_activities = log[TAG_ACTIVITY_NAME].explode()
    unique_activities = exploded_activities.drop_duplicates()
    unique_activities = unique_activities[unique_activities.notna()]
    model_activities = unique_activities.tolist()
    
    # Matching con nodi del modello
    for node in model.get_nodes():
        if node.get_name() in model_activities:
            matching.append((node.get_name(), node.get_id()))
    
    print(f"✓ Creato matching per {len(matching)} attività")
    return matching