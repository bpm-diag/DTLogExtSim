import pandas as pd
from typing import Dict, List, Any, Optional

from support_modules.constants import *

from .extract_elements import *
from .calculate_elements import *
from .fit_distribution import *
from .save_results import *


class InterArrivalCalculation:
    """
    Classe per il calcolo della distribuzione di inter-arrivo dei processi.
    
    Analizza i tempi di arrivo delle tracce nel log per determinare la distribuzione
    e i parametri del tasso di inter-arrivo tra le istanze del processo.
    """
    
    def __init__(self, log: pd.DataFrame, settings: List[Dict[str, Any]]):
        """
        Inizializza il calcolatore di inter-arrivo.
        
        Args:
            log: DataFrame contenente il log XES
            settings: Lista di configurazioni
        """
        self.log = log.copy()
        self.settings = settings
        
        # Validazione input
        self._validate_inputs()
        
        # Configurazione primaria
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        
        # Risultati (inizializzati come None)
        self._start_activities = None
        self._interarrival_times = None
        self._distribution_params = None
        
        self.extract_start_activities = extract_start_activities.__get__(self)
        self._extract_distribution_params = extract_distribution_params.__get__(self)

        self.calculate_interarrival_times = calculate_interarrival_times.__get__(self)
        self._calculate_fixed_mean = calculate_fixed_mean.__get__(self)
        self._calculate_descriptive_stats = calculate_descriptive_stats.__get__(self)
        
        self.fit_distribution = fit_distribution.__get__(self)

        self.save_results = save_results.__get__(self)
        print(f"InterArrivalCalculation inizializzato per {len(self.log)} eventi")
    
    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    
    def calculate_interarrival_distribution(self) -> Dict[str, Any]:
        """
        Metodo principale per calcolare la distribuzione di inter-arrivo.
        
        Returns:
            Dizionario con tutti i risultati del calcolo
        """
        try:
            print("Iniziando calcolo distribuzione di inter-arrivo...")
            
            # 1. Estrai attività di start
            self._start_activities = self.extract_start_activities()
            
            # 2. Calcola tempi di inter-arrivo
            self._interarrival_times = self.calculate_interarrival_times(self._start_activities)
            
            # 3. Identifica distribuzione migliore
            distribution_name, distribution_params = self.fit_distribution([x for x in self._interarrival_times])
            self._distribution_params = [distribution_name, distribution_params]
            
            # 4. Salva risultati
            results_file = self.save_results(self._distribution_params)
            
            # 5. Statistiche descrittive
            stats = self._calculate_descriptive_stats()
            
            result = {
                'distribution_params': self._distribution_params,
                'interarrival_times': self._interarrival_times,
                'start_activities_count': len(self._start_activities),
                'interarrival_count': len(self._interarrival_times),
                'distribution_name': distribution_name,
                'distribution_parameters': distribution_params,
                'descriptive_stats': stats,
                'results_file': results_file
            }
            
            print("✓ Calcolo distribuzione inter-arrivo completato")
            return result
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo della distribuzione di inter-arrivo: {str(e)}")
    
    
    
    def get_calculation_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto del calcolo dell'inter-arrivo.
        
        Returns:
            Dizionario con informazioni sul calcolo
        """
        return {
            'input_events': len(self.log),
            'start_activities_count': len(self._start_activities) if self._start_activities is not None else 0,
            'interarrival_times_count': len(self._interarrival_times) if self._interarrival_times else 0,
            'distribution_name': self._distribution_params[0] if self._distribution_params else None,
            'has_distribution_params': self._distribution_params is not None,
            'model_name': self.name,
            'unique_traces': self.log[TAG_TRACE_ID].nunique()
        }
    
