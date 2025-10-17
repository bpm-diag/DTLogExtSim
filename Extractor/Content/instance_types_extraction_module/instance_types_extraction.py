import pandas as pd
import os
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple

from support_modules.constants import *

from .preprocess_log import *
from .extract_elements import *
from .create_pair import *
from .analyze_pair import *
from .save_results import *
from .calculate_elements import *
from .group_elements import *


class InstanceTypesCalculation:
    """
    Classe per l'estrazione e calcolo dei tipi di istanza dai log XES.
    
    Analizza il log per identificare i diversi tipi di istanza del processo
    e calcola i tipi di istanza forzati per i gateway basandosi sui branch.
    """
    
    def __init__(self, log: pd.DataFrame, settings: List[Dict[str, Any]], 
                 branches: Dict, tot_execute_per_branch: Dict):
        """
        Inizializza il calcolatore di tipi di istanza.
        
        Args:
            log: DataFrame contenente il log XES
            settings: Lista di configurazioni
            branches: Branch identificati per ogni gateway
            tot_execute_per_branch: Totale esecuzioni per branch
        """
        self.log = log.copy()
        self.settings = settings
        self.branches = branches
        self.tot_execute_per_branch = tot_execute_per_branch
        
        # Validazione input
        self._validate_inputs()
        
        # Configurazione primaria
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        self.diag_log = self.config['diag_log']
        
        # Risultati (inizializzati come None)
        self._instance_types = None
        self._forced_instance_types = None
        self._num_types_instance = 0
        self._total_num_trace = 0
        
        self.preprocess_log_for_forced_types = preprocess_log_for_forced_types.__get__(self)
        
        self.extract_instance_types = extract_instance_types.__get__(self)
        self.extract_branch_pairs = extract_branch_pairs.__get__(self)
        self.extract_forced_instance_types = extract_forced_instance_types.__get__(self)
        self.count_total_traces = count_total_traces.__get__(self)

        self.create_pair_totals_mapping = create_pair_totals_mapping.__get__(self)
        self.create_pair_gateway_mapping = create_pair_gateway_mapping.__get__(self)
        
        self.analyze_pair_executions = analyze_pair_executions.__get__(self)
        self.analyze_forced_instance_types = analyze_forced_instance_types.__get__(self)
        
        self.calculate_gateway_instance_types = calculate_gateway_instance_types.__get__(self)

        self.group_forced_types_by_gateway = group_forced_types_by_gateway.__get__(self)

        self.save_results = save_results.__get__(self)
        print(f"InstanceTypesCalculation inizializzato per {len(self.log)} eventi")
    
    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        if self.branches is None:
            raise ValueError("Branches non può essere None")
            
        if self.tot_execute_per_branch is None:
            raise ValueError("Tot execute per branch non può essere None")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    
    
    def calculate_all_instance_types(self) -> Dict[str, Any]:
        """
        Metodo principale per calcolare tutti i tipi di istanza.
        
        Returns:
            Dizionario con tutti i risultati del calcolo
        """
        try:
            print("Iniziando calcolo completo tipi di istanza...")
            
            # 1. Estrai tipi di istanza base
            self._instance_types = self.extract_instance_types()
            self._num_types_instance = len(self._instance_types[TAG_INSTANCE_TYPE])
            
            self._forced_instance_types = None
            # 2. Estrai tipi forzati se necessario
            if self._num_types_instance > 1:
                self._forced_instance_types = self.extract_forced_instance_types()
            else:
                self._forced_instance_types = None
                print("Un solo tipo di istanza trovato, skip tipi forzati")
            
            # 3. Salva risultati
            results_file = self.save_results()
            
            result = {
                'instance_types': self._instance_types,
                'forced_instance_types': self._forced_instance_types,
                'num_types_instance': self._num_types_instance,
                'total_traces': self._total_num_trace,
                'results_file': results_file
            }
            
            print("✓ Calcolo tipi di istanza completato")
            return result
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo dei tipi di istanza: {str(e)}")
    
    def get_calculation_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto del calcolo dei tipi di istanza.
        
        Returns:
            Dizionario con informazioni sul calcolo
        """
        return {
            'input_events': len(self.log),
            'is_diag_log': self.diag_log,
            'num_instance_types': self._num_types_instance,
            'total_traces': self._total_num_trace,
            'has_forced_types': self._forced_instance_types is not None,
            'forced_types_count': len(self._forced_instance_types) if self._forced_instance_types else 0,
            'branches_count': len(self.branches),
            'model_name': self.name
        }
