from typing import List, Tuple, Dict
from collections import Counter
from fitter import Fitter
import numpy as np

def fit_distribution(self, data: List[float]) -> Tuple[str, Dict[str, float]]:
        """
        Identifica la distribuzione migliore per i dati di inter-arrivo.
        
        Args:
            data: Lista dei tempi di inter-arrivo
            
        Returns:
            Tupla (nome_distribuzione, parametri)
        """
        print("Identificando distribuzione migliore...")
        
        try:
            if not data:
                raise ValueError("Dati vuoti per il fitting della distribuzione")
            
            # Controlla se la maggior parte dei valori è uguale (distribuzione fissa)
            most_common_value, count = Counter(data).most_common(1)[0]
            
            if count > 0.9 * len(data):
                print("✓ Distribuzione fissa identificata")
                mean_value = self._calculate_fixed_mean(data, most_common_value, count)
                params = {'mean': round(mean_value, 2), 'arg1': 0, 'arg2': 0}
                return 'fixed', params
            
            # Fit distribuzioni statistiche
            distributions = ['norm', 'expon', 'uniform', 'triang', 'lognorm', 'gamma']
            fitter = Fitter(data, distributions=distributions)
            fitter.fit()
            
            # Ottieni la migliore distribuzione
            best_distribution = list(fitter.get_best(method='sumsquare_error').keys())[0]
            params = self._extract_distribution_params(data, best_distribution)
            
            print(f"✓ Distribuzione identificata: {best_distribution}")
            return best_distribution, params
            
        except Exception as e:
            print(f"Errore nel fitting: {e}")
            # Fallback a distribuzione normale
            params = {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.std(data), 2),
                'arg2': 0
            }
            return 'norm', params