import pandas as pd
from typing import List, Dict
import numpy as np

from support_modules.constants import *

def calculate_interarrival_times(self, start_activities: pd.DataFrame) -> List[float]:
    """
    Calcola i tempi di inter-arrivo tra le tracce.
    
    Raggruppa per giorno e calcola i delta temporali tra arrivi consecutivi
    per evitare bias dovuti a pause notturne o weekend.
    
    Args:
        start_activities: DataFrame delle attività di start
        
    Returns:
        Lista dei tempi di inter-arrivo in secondi
    """
    print("Calcolando tempi di inter-arrivo...")
    
    try:
        # Crea colonna data (floor a livello giornaliero)
        start_activities_copy = start_activities.copy()
        start_activities_copy['date'] = start_activities_copy[TAG_TIMESTAMP].dt.floor('d')
        
        inter_arrival_times = []
        
        # Raggruppa per giorno per evitare bias
        for date, group in start_activities_copy.groupby('date'):
            # Ordina i timestamp del giorno
            daily_timestamps = sorted(list(group[TAG_TIMESTAMP]))
            
            # Calcola delta tra arrivi consecutivi
            for i in range(1, len(daily_timestamps)):
                delta = (daily_timestamps[i] - daily_timestamps[i-1]).total_seconds()
                
                # Evita delta zero per problemi di calcolo distribuzione
                if delta == 0:
                    delta = 0.00001
                
                inter_arrival_times.append(delta)
        
        print(f"✓ Calcolati {len(inter_arrival_times)} tempi di inter-arrivo")
        return inter_arrival_times
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo dei tempi di inter-arrivo: {str(e)}")

def calculate_fixed_mean(self, data: List[float], most_common_value: float, count: int) -> float:
    """
    Calcola la media per distribuzione fissa.
    
    Args:
        data: Dati originali
        most_common_value: Valore più comune
        count: Conteggio del valore più comune
        
    Returns:
        Media calcolata
    """
    if count == len(data):
        if data[0] == 0.00001:
            return 0.0
        return data[0]
    else:
        return most_common_value
    

def calculate_descriptive_stats(self) -> Dict[str, float]:
    """
    Calcola statistiche descrittive sui tempi di inter-arrivo.
    
    Returns:
        Dizionario con statistiche descrittive
    """
    try:
        if not self._interarrival_times:
            return {}
        
        data = np.array(self._interarrival_times)
        
        stats = {
            'mean': round(np.mean(data), 2),
            'std': round(np.std(data), 2),
            'min': round(np.min(data), 2),
            'max': round(np.max(data), 2),
            'median': round(np.median(data), 2),
            'q25': round(np.percentile(data, 25), 2),
            'q75': round(np.percentile(data, 75), 2)
        }
        
        return stats
        
    except Exception as e:
        print(f"Errore nel calcolo delle statistiche descrittive: {e}")
        return {}