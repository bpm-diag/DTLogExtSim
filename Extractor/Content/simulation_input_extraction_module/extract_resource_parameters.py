import ast

import pandas as pd

from typing import List

from support_modules.constants import *

from resource_extraction_module.resource_extraction import ResourceParameterCalculation 

def extract_resource_parameters(self) -> None:
    """Estrae i parametri delle risorse dal log."""
    try:
        print("Estraendo parametri risorse...")
        
        # Preprocessing del log per risorse
        processed_log = self._preprocess_log_for_resources()
        
        self._resource_param = ResourceParameterCalculation(processed_log, self.settings)
        results = self._resource_param.calculate_all_resource_parameters()

        print("✓ Parametri risorse estratti")
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione dei parametri delle risorse: {str(e)}")


def preprocess_log_for_resources(self) -> pd.DataFrame:
    """Preprocessa il log per l'estrazione dei parametri delle risorse."""
    # Patterns da escludere
    exclude_patterns = [r'Gateway', r'Start', r'End', r'Event']
    exclude_exact = ['Start', 'End', 'start', 'end', 'Gateway']
    
    # Copia del log
    temp_log = self.log.copy()
    
    # Rimozione valori esatti
    temp_log = temp_log[~temp_log[TAG_ACTIVITY_NAME].isin(exclude_exact)].reset_index(drop=True)
    
    # Rimozione pattern
    for pattern in exclude_patterns:
        temp_log = temp_log[~temp_log[TAG_ACTIVITY_NAME].str.contains(pattern, case=False, na=False)]
    
    # Per log diag, rimuovi anche da nodeType
    if self.primary_config['diag_log']:
        temp_log = temp_log[~temp_log[TAG_NODE_TYPE].str.contains(r'Gateway', case=False, na=False)]
    
    # Trasforma risorse in lista
    if TAG_RESOURCE in temp_log.columns:
        temp_log[TAG_RESOURCE] = temp_log[TAG_RESOURCE].apply(self._safe_literal_eval)
    
    return temp_log

def safe_literal_eval(self, x) -> List:
    """
    Valutazione sicura di literal per trasformare stringhe in liste.
    
    Args:
        x: Valore da valutare
        
    Returns:
        Lista o valore originale wrappato in lista
    """
    try:
        evaluated = ast.literal_eval(x)
        return evaluated if isinstance(evaluated, (list, dict)) else [x]
    except (ValueError, SyntaxError):
        return [x]