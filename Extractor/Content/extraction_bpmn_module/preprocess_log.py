import pandas as pd

from support_modules.constants import *

def preprocess_diag_log(self, log: pd.DataFrame) -> pd.DataFrame:
    """Preprocessing specifico per log diagnostici."""
    gateway_pattern = r'Gateway'
    event_pattern = r'Event'
    
    # Rimozione gateway ed eventi da varie colonne
    log = log[~log[TAG_ACTIVITY_NAME].str.contains(gateway_pattern, case=False, na=False)]
    log = log[~log[TAG_ACTIVITY_NAME].str.contains(event_pattern, case=False, na=False)]
    log = log[~log[TAG_LIFECYCLE].str.contains(gateway_pattern, case=False, na=False)]
    log = log[~log[TAG_NODE_TYPE].str.contains(gateway_pattern, case=False, na=False)]
    
    # Rimozione colonna pool se presente
    if TAG_POOL in log.columns:
        log = log.drop(columns=[TAG_POOL])
    
    return log

def preprocess_log(self) -> pd.DataFrame:
    """
    Preprocessa il log per l'estrazione BPMN.
    
    Returns:
        DataFrame preprocessato
    """
    print("Preprocessing del log per estrazione BPMN...")
    
    try:
        processed_log = self.log.copy()
        
        # 1. Gestione valori NaN nelle risorse
        processed_log = self._handle_missing_resources(processed_log)
        
        # 2. Gestione costi
        processed_log = self._handle_costs(processed_log)
        
        # 3. Gestione setup time
        processed_log = self._handle_setup_time(processed_log)
        
        # 4. Drop fixed_cost column (dopo setup_time)
        processed_log = self._drop_fixed_cost_column(processed_log)

        # 5. Preprocessing specifico per log diag
        if self.diag_log:
            processed_log = self._preprocess_diag_log(processed_log)
        
        # 6. Pulizia valori NaN
        processed_log = processed_log.where(pd.notna(processed_log), None)
        
        # 7. Filtraggio per start/complete events
        processed_log = self._filter_lifecycle_events(processed_log)
        
        # 8. Rimozione start/end events se necessario
        processed_log = self._remove_start_end_events(processed_log)
        
        print(f"✓ Log preprocessato: {len(processed_log)} eventi rimanenti")
        return processed_log
        
    except Exception as e:
        raise Exception(f"Errore nel preprocessing del log: {str(e)}")