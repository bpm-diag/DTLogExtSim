import pandas as pd
from typing import Tuple, List, Dict, Any, Optional

from support_modules.constants import *


def count_total_traces(self) -> int:
    """
    Conta il numero totale di tracce nel log.
    
    Returns:
        Numero totale di tracce
    """
    try:
        grouped_log = self.log.groupby(TAG_TRACE_ID)
        total_traces = len(grouped_log)
        
        print(f"✓ Contate {total_traces} tracce totali")
        return total_traces
        
    except Exception as e:
        raise Exception(f"Errore nel conteggio delle tracce: {str(e)}")

def extract_instance_types(self) -> pd.DataFrame:
    """
    Estrae i tipi di istanza dal log.
    
    Returns:
        DataFrame con i tipi di istanza e il loro conteggio
    """
    print("Estraendo tipi di istanza...")
    
    try:
        if self.diag_log and TAG_INSTANCE_TYPE in self.log.columns:
            # Per log diagnostici con instanceType
            unique_cases = self.log[[TAG_TRACE_ID, TAG_INSTANCE_TYPE]].drop_duplicates()
            instance_types = unique_cases.groupby(TAG_INSTANCE_TYPE).size().reset_index(name='number_of_traces')
        else:
            # Per log normali o senza instanceType
            grouped_log = self.log.groupby(TAG_TRACE_ID)
            total_num_trace = len(grouped_log)
            
            data = {
                TAG_INSTANCE_TYPE: ['A'], 
                'number_of_traces': [total_num_trace]
            }
            instance_types = pd.DataFrame(data)
        
        print(f"✓ Trovati {len(instance_types)} tipi di istanza")
        return instance_types
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione dei tipi di istanza: {str(e)}")
    
def extract_branch_pairs(self) -> Tuple[List[Tuple[str, str]], Dict[Tuple[str, str], Any]]:
    """
    Estrae le coppie (source, destination) dai branch.
    
    Returns:
        Tupla (branch_pairs, node_mapping)
    """
    print("Estraendo coppie di branch...")
    
    try:
        branches_pairs = []
        node_mapping = {}
        
        for node, paths in self.branches.items():
            for source in paths['source']:
                for destination in paths['destination']:
                    pair = (source, destination)
                    branches_pairs.append(pair)
                    node_mapping[pair] = node
        
        print(f"✓ Estratte {len(branches_pairs)} coppie di branch")
        return branches_pairs, node_mapping
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione delle coppie di branch: {str(e)}")

def extract_forced_instance_types(self) -> Dict[Any, List[Tuple[Tuple[str, str], Optional[str]]]]:
    """
    Estrae i tipi di istanza forzati per i gateway.
    
    Returns:
        Dizionario dei tipi forzati per gateway
    """
    print("Estraendo tipi di istanza forzati...")
    
    try:
        # 1. Conta tracce totali
        self._total_num_trace = self.count_total_traces()
        
        # 2. Preprocessa log
        temp_log = self.preprocess_log_for_forced_types()
        
        # 3. Estrai coppie di branch
        branches_pairs, node_mapping = self.extract_branch_pairs()
        
        # 4. Crea mapping coppia-gateway
        pair_gateway_associated = self.create_pair_gateway_mapping(branches_pairs)
        
        # 5. Analizza esecuzioni
        results = self.analyze_pair_executions(temp_log, branches_pairs)
        
        # 6. Crea mapping totali
        pair_tot = self.create_pair_totals_mapping()
        
        # 7. Calcola tipi istanza per gateway
        gateway_type_instances = self.calculate_gateway_instance_types(results)
        
        # 8. Analizza tipi forzati
        forced_instance_types = self.analyze_forced_instance_types(
            results, pair_tot, pair_gateway_associated, gateway_type_instances
        )
        
        # 9. Raggruppa per gateway
        gateway_forced_instance_types = self.group_forced_types_by_gateway(
            forced_instance_types, node_mapping
        )
        
        print("✓ Estrazione tipi forzati completata")
        return gateway_forced_instance_types
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione dei tipi forzati: {str(e)}")
    