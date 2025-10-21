import numpy as np

from typing import Dict, List, Tuple
from collections import Counter
from fitter import Fitter

def calculate_fixed_mean(self, data: List[float], most_common_value: float, count: int) -> float:
    """Calcola media per distribuzione fissa."""
    if count == len(data):
        if data[0] == 0.00001:
            return 0.0
        else:
            return data[0]
    else:
        return round(most_common_value, 2)
    
def fit_distribution(self, data: List[float]) -> Tuple[str, Dict[str, float]]:
    """
    Identifica la distribuzione migliore per i dati.
    
    Args:
        data: Lista di valori numerici
        
    Returns:
        Tupla (nome_distribuzione, parametri)
    """
    try:
        if not data:
            return 'fixed', {'mean': 0.0, 'arg1': 0, 'arg2': 0}
        
        # Controlla distribuzione fissa
        most_common_value, count = Counter(data).most_common(1)[0]
        
        if count > 0.9 * len(data):
            mean_value = self._calculate_fixed_mean(data, most_common_value, count)
            params = {'mean': round(mean_value, 2), 'arg1': 0, 'arg2': 0}
            return 'fixed', params
        
        # Fit distribuzioni statistiche
        distributions = ['norm', 'expon', 'uniform', 'triang', 'lognorm', 'gamma']
        fitter = Fitter(data, distributions=distributions)
        fitter.fit()
        
        best_distribution = list(fitter.get_best(method='sumsquare_error').keys())[0]
        params = self._extract_distribution_params(data, best_distribution)
        
        return best_distribution, params
        
    except Exception as e:
        print(f"Errore nel fitting distribuzione: {e}")
        # Fallback a distribuzione normale
        return 'norm', {
            'mean': round(np.mean(data), 2),
            'arg1': round(np.std(data), 2),
            'arg2': 0
        }