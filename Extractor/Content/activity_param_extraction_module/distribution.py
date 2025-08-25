import numpy as np
from typing import Dict, List, Tuple
from fitter import Fitter
from collections import Counter

def fit_distribution(self, data: List[float]) -> Tuple[str, Dict[str, float]]:
        """
        Identifica la distribuzione migliore per i dati.
        
        Args:
            data: Lista di valori numerici
            
        Returns:
            Tupla (nome_distribuzione, parametri)
        """
        if not data:
            return 'fixed', {'mean': 0.0, 'arg1': 0, 'arg2': 0}
        
        # Controlla se la maggior parte dei valori è uguale (distribuzione fissa)
        most_common_value, count = Counter(data).most_common(1)[0]
        if count > 0.9 * len(data):
            mean_value = 1 if count == len(data) and data[0] == 0.00001 else round(most_common_value, 2)
            return 'fixed', {'mean': mean_value, 'arg1': 0, 'arg2': 0}
        
        # Fit distribuzioni statistiche
        try:
            distributions = ['norm', 'expon', 'uniform', 'triang', 'lognorm', 'gamma']
            fitter = Fitter(data, distributions=distributions)
            fitter.fit()
            
            best_distribution = list(fitter.get_best(method='sumsquare_error').keys())[0]
            params = self._extract_distribution_params(data, best_distribution)
            
            return best_distribution, params
            
        except Exception as e:
            print(f"Errore nel fitting della distribuzione: {e}")
            # Fallback a distribuzione normale
            return 'norm', {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.std(data), 2),
                'arg2': 0
            }
    
def extract_distribution_params(self, data: List[float], distribution_type: str) -> Dict[str, float]:
    """
    Estrae i parametri per il tipo di distribuzione specificato.
    
    Args:
        data: Dati numerici
        distribution_type: Tipo di distribuzione
        
    Returns:
        Dizionario con parametri della distribuzione
    """
    if distribution_type == 'fixed':
        mean = 0 if data[0] == 0.00001 else data[0]
        return {'mean': round(mean, 2), 'arg1': 0, 'arg2': 0}
    
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
            'arg1': 0,
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