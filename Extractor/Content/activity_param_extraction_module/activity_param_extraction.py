import pandas as pd
from typing import Dict, List, Any, Optional

from support_modules.constants import *
from .duration_distribution import *
from .waiting_distribution import *
from .reorder_events import *
from .filtering_events import *
from .create_events import *
from .distribution import *

class ActivityParamExtraction:
    """
    Classe per l'estrazione dei parametri delle attività da log XES.
    
    Calcola le distribuzioni di durata (processing time) e tempo di attesa (waiting time)
    per ogni attività nel processo, gestendo diversi tipi di timestamp (assign, start, complete).
    """
    
    def __init__(self, log: pd.DataFrame, settings: List[Dict[str, Any]]):
        """
        Inizializza l'estrattore di parametri delle attività.
        
        Args:
            log: DataFrame contenente il log XES
            settings: Lista di configurazioni
        """
        self.log = log.copy()
        self.settings = settings

        self._validate_inputs()
        

        # Configurazione primaria
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        self.num_timestamp = self.config['num_timestamp']
        self.diaglog = self.config['diag_log']

        # Risultati (inizializzati come None)
        self._duration_distr = None
        self._waiting_distr = None
        self._processed_log = None
        self._abort_events = None
        
        self.extract_duration_distribution = extract_duration_distribution.__get__(self)
        self.save_duration_distributions = save_duration_distributions.__get__(self)

        self.extract_waiting_distribution = extract_waiting_distribution.__get__(self)
        self.save_waiting_distributions = save_waiting_distributions.__get__(self)
        
        self._reorder_events = reorder_events.__get__(self)
        self._reorder_single_timestamp = reorder_single_timestamp.__get__(self)
        self._reorder_dual_timestamp = reorder_dual_timestamp.__get__(self)
        self._reorder_triple_timestamp = reorder_triple_timestamp.__get__(self)

        self._create_reordered_event = create_reordered_event.__get__(self)
        self._create_dual_timestamp_event = create_dual_timestamp_event.__get__(self)
        self._create_triple_timestamp_event = create_triple_timestamp_event.__get__(self)


        self._filter_lifecycle_events = filter_lifecycle_events.__get__(self)
        self._remove_start_end_events = remove_start_end_events.__get__(self)
        self._identify_abort_events = identify_abort_events.__get__(self)
        self._clean_outliers = clean_outliers.__get__(self)
        self._find_matching_event = find_matching_event.__get__(self)
        
        self._fit_distribution = fit_distribution.__get__(self)
        self._extract_distribution_params = extract_distribution_params.__get__(self)
        print(f"ActivityParamExtraction inizializzato per {len(self.log)} eventi")

    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP, TAG_LIFECYCLE]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    
    def _rename_columns(self, log: pd.DataFrame) -> pd.DataFrame:
        """Rinomina le colonne per standardizzazione interna."""
        column_mapping = {
            TAG_TRACE_ID: 'caseid',
            TAG_ACTIVITY_NAME: 'task',
            TAG_LIFECYCLE: 'event_type',
            TAG_TIMESTAMP: 'timestamp'
        }
        
        return log.rename(columns=column_mapping)
    
    def preprocess_log(self) -> pd.DataFrame:
        """
        Preprocessa il log per l'estrazione dei parametri delle attività.
        
        Returns:
            DataFrame preprocessato e rinominato
        """
        print("Preprocessing log per parametri attività...")
        
        try:
            processed_log = self.log.copy()
            
            # 1. Rimozione eventi start/end per log normali
            if not self.diaglog:
                processed_log = self._remove_start_end_events(processed_log)
            
            # 2. Identificazione eventi abort per log diag
            self._abort_events = self._identify_abort_events(processed_log)
            
            # 3. Rinomina colonne per standardizzazione
            processed_log = self._rename_columns(processed_log)
            
            # 4. Filtra solo eventi lifecycle rilevanti
            processed_log = self._filter_lifecycle_events(processed_log)
            
            # 5. Riordina eventi per creare timestamp strutturati
            processed_log = self._reorder_events(processed_log)
            
            print(f"✓ Log preprocessato: {len(processed_log)} record di attività")
            return processed_log
            
        except Exception as e:
            raise Exception(f"Errore nel preprocessing del log: {str(e)}")
    
    def extract_all_parameters(self) -> Dict[str, Any]:
        """
        Metodo principale per estrarre tutti i parametri delle attività.
        
        Returns:
            Dizionario con tutti i risultati dell'estrazione
        """
        try:
            print("Iniziando estrazione completa parametri attività...")
            
            # 1. Preprocessing del log
            self._processed_log = self.preprocess_log()
            
            # 2. Estrazione distribuzioni durata
            self._duration_distr = self.extract_duration_distribution(self._processed_log)
            duration_file = self.save_duration_distributions(self._duration_distr)
            
            # 3. Estrazione distribuzioni tempo di attesa (se applicabile)
            waiting_file = None
            if self.num_timestamp == 3:
                self._waiting_distr = self.extract_waiting_distribution(self._processed_log)
                waiting_file = self.save_waiting_distributions(self._waiting_distr)
            
            result = {
                'duration_distributions': self._duration_distr,
                'waiting_distributions': self._waiting_distr,
                'duration_file': duration_file,
                'waiting_file': waiting_file,
                'processed_events': len(self._processed_log),
                'abort_events': self._abort_events,
                'timestamp_count': self.num_timestamp
            }
            
            print("✓ Estrazione parametri attività completata")
            return result
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione dei parametri delle attività: {str(e)}")
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto dell'estrazione dei parametri.
        
        Returns:
            Dizionario con informazioni sull'estrazione
        """
        return {
            'input_events': len(self.log),
            'processed_events': len(self._processed_log) if self._processed_log is not None else 0,
            'duration_distributions_count': len(self._duration_distr) if self._duration_distr else 0,
            'waiting_distributions_count': len(self._waiting_distr) if self._waiting_distr else 0,
            'abort_events_count': len(self._abort_events) if self._abort_events else 0,
            'timestamp_type': self.num_timestamp,
            'is_diag_log': self.diaglog,
            'has_waiting_times': self.num_timestamp == 3
        }
