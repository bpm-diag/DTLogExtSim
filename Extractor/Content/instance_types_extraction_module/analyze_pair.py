import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
from collections import Counter


from support_modules.constants import *

def analyze_pair_executions(self, temp_log: pd.DataFrame, branches_pairs: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Counter]:
    """
    Analizza le esecuzioni per ogni coppia di branch.
    
    Args:
        temp_log: Log preprocessato
        branches_pairs: Coppie di branch da analizzare
        
    Returns:
        Dizionario con contatori per ogni coppia
    """
    print("Analizzando esecuzioni per coppia...")
    
    try:
        results = {pair: Counter() for pair in branches_pairs}
        
        # Verifica presenza colonna instanceType
        if TAG_INSTANCE_TYPE not in temp_log.columns:
            print("⚠ Colonna instanceType non trovata, usando valore di default 'A'")
            temp_log = temp_log.copy()
            temp_log[TAG_INSTANCE_TYPE] = 'A'
        
        # Analizza ogni traccia
        for trace_id, group in temp_log.groupby(TAG_TRACE_ID):
            sorted_events = group.sort_values(TAG_TIMESTAMP).reset_index(drop=True)
            
            for i in range(len(sorted_events) - 1):
                source_row = sorted_events.iloc[i]
                dest_row = sorted_events.iloc[i + 1]
                
                source_activity = source_row[TAG_ACTIVITY_NAME]
                destination_activity = dest_row[TAG_ACTIVITY_NAME]
                pair = (source_activity, destination_activity)
                
                if pair in branches_pairs:
                    instance_type = dest_row[TAG_INSTANCE_TYPE]
                    results[pair][instance_type] += 1
        
        print(f"✓ Analizzate esecuzioni per {len(results)} coppie")
        return results
        
    except Exception as e:
        raise Exception(f"Errore nell'analisi delle esecuzioni: {str(e)}")
    
def analyze_forced_instance_types(self, results: Dict[Tuple[str, str], Counter],
                                    pair_tot: Dict[Tuple[str, str], int],
                                    pair_gateway_associated: Dict[Tuple[str, str], Any],
                                    gateway_type_instances: Dict[Any, Counter]) -> Dict[Tuple[str, str], Optional[str]]:
        """
        Analizza i tipi di istanza forzati per ogni coppia.
        
        Args:
            results: Risultati esecuzioni per coppia
            pair_tot: Totali per coppia
            pair_gateway_associated: Mapping coppia-gateway
            gateway_type_instances: Tipi istanza per gateway
            
        Returns:
            Dizionario coppia -> tipo istanza forzato (o None)
        """
        print("Analizzando tipi di istanza forzati...")
        
        try:
            forced_instance_types = {}
            execution_threshold = 0.3  # 30% delle tracce
            
            for pair, counter in results.items():
                try:
                    # Calcola ratio di esecuzione del gateway
                    if pair in pair_tot and self._total_num_trace > 0:
                        ratio_gateway_execution = pair_tot[pair] / self._total_num_trace
                    else:
                        ratio_gateway_execution = 0
                    
                    # Analizza solo se il gateway è eseguito abbastanza frequentemente
                    if ratio_gateway_execution > execution_threshold:
                        if len(counter) > 1:
                            # Più tipi di istanza -> nessun forzamento
                            forced_instance_types[pair] = None
                        elif len(counter) == 1:
                            # Un solo tipo di istanza -> analizza se è forzato
                            num_instance = counter.most_common(1)[0][1]
                            instance_type_name = counter.most_common(1)[0][0]
                            
                            if pair in pair_gateway_associated:
                                gateway = pair_gateway_associated[pair]
                                
                                if gateway in gateway_type_instances:
                                    tot_rep_of_that_instance_for_that_gateway = gateway_type_instances[gateway].get(instance_type_name, 0)
                                    
                                    if tot_rep_of_that_instance_for_that_gateway > 0:
                                        ratio = num_instance / tot_rep_of_that_instance_for_that_gateway
                                        
                                        # Se ratio = 1, il tipo istanza passa sempre su questo branch
                                        if ratio == 1.0:
                                            forced_instance_types[pair] = instance_type_name
                                        else:
                                            forced_instance_types[pair] = None
                                    else:
                                        forced_instance_types[pair] = None
                                else:
                                    forced_instance_types[pair] = None
                            else:
                                forced_instance_types[pair] = None
                        else:
                            # Nessuna esecuzione
                            forced_instance_types[pair] = None
                    else:
                        # Gateway non eseguito abbastanza frequentemente
                        forced_instance_types[pair] = None
                        
                except Exception as e:
                    print(f"Errore nell'analisi della coppia {pair}: {e}")
                    forced_instance_types[pair] = None
            
            # Conta tipi forzati trovati
            forced_count = sum(1 for v in forced_instance_types.values() if v is not None)
            print(f"✓ Trovati {forced_count} tipi di istanza forzati")
            
            return forced_instance_types
            
        except Exception as e:
            raise Exception(f"Errore nell'analisi dei tipi forzati: {str(e)}")