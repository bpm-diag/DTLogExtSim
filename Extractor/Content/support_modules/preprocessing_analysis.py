import pm4py
from .constants import *
from typing import Tuple, List, Set
import pandas as pd


class PreProcessing():

    def __init__(self, log):
        self.log = log.copy()

        self.column_names = list(self.log.columns)

        # analyze log
        self._diaglog = False

        # extract parameters
        self._sim_threshold = 0

        self._num_timestamp = 0
        self._setup_time = False

        self._cost_hour = False
        self._fixed_cost = False

        # trace completeness
        self._cut_log_bool = False
        self._log_cut_trace = None
        self._log_entire_trace = None

        self._analyze_log()

    def _analyze_log(self) -> None:
        """Esegue l'analisi completa del log."""
        self._diaglog = self._check_diag_log()
        self._extract_parameters()
        self._cut_log_bool, self._log_cut_trace, self._log_entire_trace = self._analyze_trace_completeness()

    def _check_diag_log(self):
        """
        Controlla se il log è formato del DIAG
        quindi se ha nodeType e poolName
        """
        has_node_type = TAG_NODE_TYPE in self.column_names
        has_pool = TAG_POOL in self.column_names
        return has_node_type and has_pool
    
    def _extract_parameters(self) -> None:
        """Estrae tutti i parametri dal log."""
        self._extract_similarity_threshold()
        self._extract_timestamp_info()
        self._extract_cost_info()

    def _extract_similarity_threshold(self) -> None:
        """Imposta la soglia di similarità basata sul tipo di log."""
        if self._diaglog:
            self._sim_threshold = DEFAULT_SIM_THRESHOLD_DIAG
        else:
            self._sim_threshold = DEFAULT_SIM_THRESHOLD_NORMAL

    def _extract_timestamp_info(self) -> None:
        """
        Analizza i timestamp e determina il numero di timestamp disponibili.
        
        Identifica anche se sono presenti setup time per log DIAG.
        """
        if TAG_LIFECYCLE not in self.column_names:
            self._num_timestamp = 0
            self._setup_time = False
            return
            
        lifecycle_transitions = set(self.log[TAG_LIFECYCLE].unique())
        
        # Verifica presenza di transizioni specifiche
        has_assign = LIFECYCLE_ASSIGN in lifecycle_transitions
        has_start = LIFECYCLE_START in lifecycle_transitions  
        has_complete = LIFECYCLE_COMPLETE in lifecycle_transitions
        has_setup = any(setup in lifecycle_transitions 
                       for setup in [LIFECYCLE_START_SETUP, LIFECYCLE_END_SETUP])
        
        # Determina numero di timestamp
        if has_assign and has_start and has_complete:
            self._num_timestamp = TIMESTAMP_CONFIG['ASSIGN_START_COMPLETE']
        elif has_start and has_complete:
            self._num_timestamp = TIMESTAMP_CONFIG['START_COMPLETE']
        elif has_complete:
            self._num_timestamp = TIMESTAMP_CONFIG['COMPLETE_ONLY']
        else:
            self._num_timestamp = 0
        
        # Setup time disponibile solo per log diag
        self._setup_time = self._diaglog and has_setup

    def _extract_cost_info(self) -> None:
        """Verifica la presenza di informazioni sui costi."""
        self._cost_hour = TAG_COST_HOUR in self.column_names
        self._fixed_cost = TAG_FIXED_COST in self.column_names


    def _analyze_trace_completeness(self) -> Tuple[bool, pd.DataFrame, pd.DataFrame]:
        """
        Analizza la completezza delle tracce nel log.
        
        Separa le tracce complete da quelle incomplete basandosi sulla presenza
        di eventi di fine appropriati per il tipo di log.
        
        Returns:
            Tupla contenente:
            - bool: True se ci sono tracce incomplete
            - DataFrame: Tracce incomplete  
            - DataFrame: Tracce complete
        """
        if self._diaglog:
            return self._analyze_diag_trace_completeness()
        else:
            return self._analyze_normal_trace_completeness()
        
    def _analyze_diag_trace_completeness(self) -> Tuple[bool, pd.DataFrame, pd.DataFrame]:
        """Analizza completezza per log diag (cerca endEvent)."""
        incomplete_traces = (
            self.log.groupby(TAG_TRACE_ID)
            .filter(lambda x: not x[TAG_NODE_TYPE].str.contains("endEvent", na=False).any())
            .reset_index(drop=True)
        )
        
        if not incomplete_traces.empty:
            complete_traces = (
                self.log.groupby(TAG_TRACE_ID)
                .filter(lambda x: x[TAG_NODE_TYPE].str.contains("endEvent", na=False).any())
                .reset_index(drop=True)
            )
            return True, incomplete_traces, complete_traces
        else:
            return False, incomplete_traces, self.log
        
    def _analyze_normal_trace_completeness(self) -> Tuple[bool, pd.DataFrame, pd.DataFrame]:
        """Analizza completezza per log normali (cerca pattern di fine)."""
        incomplete_traces = (
            self.log.groupby(TAG_TRACE_ID)
            .filter(lambda x: not x[TAG_ACTIVITY_NAME].str.contains(PATTERN_END, na=False).any())
            .reset_index(drop=True)
        )
        
        if not incomplete_traces.empty:
            complete_traces = (
                self.log.groupby(TAG_TRACE_ID)
                .filter(lambda x: x[TAG_ACTIVITY_NAME].str.contains(PATTERN_END, na=False).any())
                .reset_index(drop=True)
            )
            return True, incomplete_traces, complete_traces
        else:
            return False, incomplete_traces, self.log
        

    def get_unique_activities(self) -> List[str]:
        """Restituisce la lista delle attività unique nel log."""
        return list(self.log[TAG_ACTIVITY_NAME].unique())
    
    def get_unique_resources(self) -> List[str]:
        """Restituisce la lista delle risorse unique nel log."""
        if TAG_RESOURCE in self.column_names:
            return list(self.log[TAG_RESOURCE].unique())
        return []
    
    def get_trace_count(self) -> int:
        """Restituisce il numero di tracce nel log."""
        return self.log[TAG_TRACE_ID].nunique()
    
    def get_event_count(self) -> int:
        """Restituisce il numero totale di eventi nel log."""
        return len(self.log)
    
    def get_summary(self) -> dict:
        """
        Restituisce un riassunto completo dell'analisi del log.
        
        Returns:
            Dizionario con tutte le informazioni estratte
        """
        return {
            'is_diagnostic_log': self._diaglog,
            'similarity_threshold': self._sim_threshold,
            'timestamp_count': self._num_timestamp,
            'has_cost_hour': self._cost_hour,
            'has_fixed_cost': self._fixed_cost,
            'has_setup_time': self._setup_time,
            'has_incomplete_traces': self._cut_log_bool,
            'total_traces': self.get_trace_count(),
            'total_events': self.get_event_count(),
            'incomplete_traces_count': len(self._log_cut_trace) if self._cut_log_bool else 0,
            'complete_traces_count': len(self._log_entire_trace) if self._cut_log_bool else len(self.log),
            'unique_activities': len(self.get_unique_activities()),
            'unique_resources': len(self.get_unique_resources()),
            'columns_present': self.column_names
        }
    
    # Properties per accesso ai risultati dell'analisi
    @property
    def diaglog(self) -> bool:
        """True se il log è diagnostico."""
        return self._diaglog
    
    @property 
    def sim_threshold(self) -> float:
        """Soglia di similarità per il log."""
        return self._sim_threshold
    
    @property
    def num_timestamp(self) -> int:
        """Numero di timestamp disponibili."""
        return self._num_timestamp
    
    @property
    def cost_hour(self) -> bool:
        """True se sono presenti costi orari."""
        return self._cost_hour
    
    @property
    def fixed_cost(self) -> bool:
        """True se sono presenti costi fissi."""
        return self._fixed_cost
    
    @property
    def setup_time(self) -> bool:
        """True se sono presenti setup time."""
        return self._setup_time
    
    @property
    def cut_log_bool(self) -> bool:
        """True se ci sono tracce incomplete."""
        return self._cut_log_bool
    
    @property
    def log_cut_trace(self) -> pd.DataFrame:
        """DataFrame con le tracce incomplete."""
        return self._log_cut_trace
    
    @property
    def log_entire_trace(self) -> pd.DataFrame:
        """DataFrame con le tracce complete."""
        return self._log_entire_trace