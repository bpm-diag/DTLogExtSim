import pandas as pd

from support_modules.constants import *

def filter_gateway_events(self, log: pd.DataFrame) -> pd.DataFrame:
    """Filtra eventi gateway ed eventi di sistema."""
    exclude_patterns = [r'Gateway', r'Event']
    
    for pattern in exclude_patterns:
        log = log[~log[TAG_ACTIVITY_NAME].str.contains(pattern, case=False, na=False)]
    
    return log



def has_setup_time_events(self, log: pd.DataFrame) -> bool:
    """Controlla se il log contiene eventi di setup time."""
    if TAG_LIFECYCLE not in log.columns:
        return False
    
    setup_events = [LIFECYCLE_START_SETUP, LIFECYCLE_END_SETUP]
    return any(event in log[TAG_LIFECYCLE].values for event in setup_events)