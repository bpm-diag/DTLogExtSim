import pandas as pd
import numpy as np
from typing import List, Dict

from support_modules.constants import *

def extract_start_activities(self) -> pd.DataFrame:
    """
    Estrae le attività di start per ogni traccia.
    
    Identifica il primo evento (timestamp minimo) per ogni traccia
    come attività di start per il calcolo dell'inter-arrivo.
    
    Returns:
        DataFrame con le attività di start ordinate per timestamp
    """
    print("Estraendo attività di start...")
    
    try:
        # Trova il timestamp minimo per ogni traccia
        min_timestamp_indices = self.log.groupby(TAG_TRACE_ID)[TAG_TIMESTAMP].idxmin()
        
        # Estrai le righe corrispondenti
        start_activities = self.log.loc[min_timestamp_indices]
        
        # Ordina per timestamp
        start_activities = start_activities.sort_values(by=TAG_TIMESTAMP)
        
        print(f"✓ Estratte {len(start_activities)} attività di start")
        return start_activities
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione delle attività di start: {str(e)}")
    
def extract_distribution_params(self, data: List[float], distribution_type: str) -> Dict[str, float]:
    """
    Estrae i parametri per il tipo di distribuzione specificato.
    
    Args:
        data: Dati numerici
        distribution_type: Tipo di distribuzione
        
    Returns:
        Dizionario con parametri della distribuzione
    """
    try:
        if distribution_type == 'fixed':
            mean_value = 0 if data[0] == 0.00001 else data[0]
            return {'mean': round(mean_value, 2), 'arg1': 0, 'arg2': 0}
        
        elif distribution_type == 'norm':
            return {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.std(data), 2),
                'arg2': 0
            }
        
        elif distribution_type == 'expon':
            return {
                'mean': round(np.mean(data), 2),
                'arg1': 0,
                'arg2': 0
            }
        
        elif distribution_type == 'uniform':
            return {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.min(data), 2),
                'arg2': round(np.max(data), 2)
            }
        
        elif distribution_type == 'triang':
            return {
                'mean': round(np.mean(data), 2),
                'arg1': 0,  # Parametri triangolari semplificati
                'arg2': 0
            }
        
        elif distribution_type in ['lognorm', 'gamma']:
            return {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.var(data), 2),
                'arg2': 0
            }
        
        else:
            # Default fallback
            return {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.std(data), 2),
                'arg2': 0
            }
            
    except Exception as e:
        print(f"Errore nell'estrazione parametri per {distribution_type}: {e}")
        # Fallback sicuro
        return {
            'mean': round(np.mean(data), 2),
            'arg1': round(np.std(data), 2),
            'arg2': 0
        }