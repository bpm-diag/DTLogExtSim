import pandas as pd

from support_modules.constants import *

def preprocess_log_for_forced_types(self) -> pd.DataFrame:
    """
    Preprocessa il log per l'analisi dei tipi forzati.
    
    Returns:
        DataFrame preprocessato
    """
    print("Preprocessing log per tipi forzati...")
    
    try:
        # Filtra solo eventi complete
        temp_log = self.log[self.log[TAG_LIFECYCLE] == LIFECYCLE_COMPLETE].reset_index(drop=True)
        
        # Pattern da escludere
        exclude_patterns = [r'Gateway', r'Start', r'End', r'Event']
        exclude_exact = ['Start', 'End', 'start', 'end', 'Gateway']
        
        # Rimozione valori esatti
        temp_log = temp_log[~temp_log[TAG_ACTIVITY_NAME].isin(exclude_exact)].reset_index(drop=True)
        
        # Rimozione pattern da activity name
        for pattern in exclude_patterns:
            temp_log = temp_log[~temp_log[TAG_ACTIVITY_NAME].str.contains(pattern, case=False, na=False)]
        
        # Per log diag, rimuovi anche da nodeType
        if self.diag_log and TAG_NODE_TYPE in temp_log.columns:
            temp_log = temp_log[~temp_log[TAG_NODE_TYPE].str.contains(r'Gateway', case=False, na=False)]
        
        print(f"✓ Log preprocessato: {len(temp_log)} eventi rimanenti")
        return temp_log
        
    except Exception as e:
        raise Exception(f"Errore nel preprocessing del log: {str(e)}")