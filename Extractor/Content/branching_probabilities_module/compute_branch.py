import pandas as pd
from typing import Dict, Any, List
from collections import defaultdict

from support_modules.constants import *

def compute_branch_probabilities(self, log: pd.DataFrame, branches: Dict) -> Dict[Any, List[Dict]]:
    """
    Calcola le probabilità di branching basate sul log.
    
    Args:
        log: Log XES
        branches: Branch identificati per ogni gateway
        
    Returns:
        Dizionario delle probabilità per ogni gateway
    """
    print("Calcolando probabilità di branching...")
    
    try:
        # Rimuovi self-loop
        no_selfloop_log = self.remove_self_loops(log)
        
        # Crea coppie (source, destination) dai branch
        branches_pairs = []
        node_mapping = {}
        
        for node, paths in branches.items():
            for source in paths['source']:
                for destination in paths['destination']:
                    pair = (source, destination)
                    branches_pairs.append(pair)
                    node_mapping[pair] = node
        
        # Raggruppa per source
        branches_group_dict = defaultdict(list)
        for first, second in branches_pairs:
            branches_group_dict[first].append(second)
        
        branches_group = [(first, tuple(seconds)) for first, seconds in branches_group_dict.items()]
        
        # Conta transizioni nel log
        counts = defaultdict(int)
        for source_act, destination_act_list in branches_group:
            for trace_id, trace_activities in no_selfloop_log.groupby(TAG_TRACE_ID):
                sorted_events = trace_activities.sort_values(TAG_TIMESTAMP).reset_index(drop=True)
                
                for i in range(len(sorted_events) - 1):
                    if source_act == sorted_events.iloc[i][TAG_ACTIVITY_NAME]:
                        # Trova prossima attività diversa
                        for j in range(i + 1, len(sorted_events)):
                            current_activity = sorted_events.iloc[j][TAG_ACTIVITY_NAME]
                            
                            if source_act != current_activity:
                                if current_activity in destination_act_list:
                                    counts[(source_act, current_activity)] += 1
                                    break
                            else:
                                break
        
        # Calcola totali per gateway
        self._tot = {}
        for gateway, paths in branches.items():
            self._tot[gateway] = 0
            for source in paths['source']:
                for destination in paths['destination']:
                    self._tot[gateway] += counts[(source, destination)]
        
        # Calcola probabilità
        branches_probabilities = {}
        for gateway, paths in branches.items():
            branches_probabilities[gateway] = []
            
            for source in paths['source']:
                for destination in paths['destination']:
                    count = counts[(source, destination)]
                    total = self._tot[gateway]
                    
                    probability = count / total if total != 0 else 0.0
                    
                    branches_probabilities[gateway].append({
                        "pair": [source, destination],
                        "probability": str(probability)
                    })
        
        print(f"✓ Calcolate probabilità per {len(branches_probabilities)} gateway")
        return branches_probabilities
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo delle probabilità di branching: {str(e)}")

def compute_branches(self, gateway_path_prec: Dict, gateway_path_succ: Dict) -> Dict[Any, Dict[str, List[str]]]:
    """
    Calcola i branch per ogni gateway.
    
    Args:
        gateway_path_prec: Task predecessori per ogni gateway
        gateway_path_succ: Task successori per ogni gateway
        
    Returns:
        Dizionario dei branch per gateway
    """
    print("Calcolando branch per gateway...")
    
    try:
        branches = {}
        for gateway in gateway_path_prec:
            if gateway in gateway_path_succ:
                branches[gateway] = {
                    "source": self._extract_task_names(gateway_path_prec[gateway]),
                    "destination": self._extract_task_names(gateway_path_succ[gateway])
                }
        
        print(f"✓ Calcolati branch per {len(branches)} gateway")
        return branches
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo dei branch: {str(e)}")