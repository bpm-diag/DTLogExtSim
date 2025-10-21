
import ast
from typing import Dict, List, Any, Optional
import pandas as pd

from support_modules.constants import *

from support_modules.generate_parameters_file import ParamsFile

from .extract_bpmn import *
from .calculate_branching_probabilities import *
from .extract_instance_types import *
from .extract_interarrival_rate import *
from .extract_activity_parameters import *
from .extract_resource_parameters import *
from .extract_other_parameters import *

class SimulationInputExtraction():
    """
    Classe per l'estrazione dei parametri di simulazione da log XES.
    
    Coordina l'estrazione di tutti i parametri necessari per la simulazione
    di processi business, inclusi modelli BPMN, probabilità di branching,
    tipi di istanza, risorse e altri parametri.
    """
    def __init__(self, log, settings, with_start_end_act):
        """
        Inizializza l'estrattore di parametri di simulazione.
        
        Args:
            log: DataFrame contenente il log XES
            settings: Lista di dizionari con le configurazioni
            with_start_end_act: Se includere attività di start/end
        """
        self.log = log.copy()
        self.settings = settings
        self.with_start_end_act = with_start_end_act

        self._validate_inputs()

        self.primary_config = self.settings[0]

        # Risultati delle estrazioni (inizializzati come None)
        self._extract_bpmn = None
        self._branch_prob = None  
        self._instance_types = None
        self._inter_arrival_calc = None
        self._activity_param = None
        self._resource_param = None
        self._other_params = None
        self._id_name_act_match = None

        self.extract_bpmn_model = extract_bpmn_model.__get__(self)

        self.calculate_branching_probabilities = calculate_branching_probabilities.__get__(self)
        self._preprocess_log_for_branching = preprocess_log_for_branching.__get__(self)
        self._load_bpmn_model = load_bpmn_model.__get__(self)
        self._remove_start_end_events = remove_start_end_events.__get__(self)
        self._match_id_name = match_id_name.__get__(self)

        self.extract_instance_types = extract_instance_types.__get__(self)

        self.extract_interarrival_rate = extract_interarrival_rate.__get__(self)

        self.extract_activity_parameters = extract_activity_parameters.__get__(self)

        self.extract_resource_parameters = extract_resource_parameters.__get__(self)
        self._preprocess_log_for_resources = preprocess_log_for_resources.__get__(self)
        self._safe_literal_eval = safe_literal_eval.__get__(self)

        self.extract_other_parameters = extract_other_parameters.__get__(self)

        print(f"SimulationInputExtraction inizializzato per {len(self.log)} eventi")


    def _validate_inputs(self) -> None:
        """Valida gli input forniti al costruttore."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if not self.settings or len(self.settings) == 0:
            raise ValueError("Settings non può essere vuoto")
            
        # Verifica presenza colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
       

    def process_all_extractions(self) -> None:
            """
            Esegue tutte le estrazioni in sequenza.
            
            Metodo principale che coordina l'intera pipeline di estrazione.
            """
            try:
                print("Iniziando estrazione completa dei parametri...")
                
                # 1. Estrazione modello BPMN
                self.extract_bpmn_model()

                # 2. Calcolo probabilità di branching
                self.calculate_branching_probabilities()
                
                # # 3. Estrazione tipi di istanza
                self.extract_instance_types()
                
                # 4. Estrazione tasso inter-arrivo
                self.extract_interarrival_rate()
                
                # 5. Estrazione parametri attività
                self.extract_activity_parameters()
                
                # 6. Estrazione parametri risorse
                self.extract_resource_parameters()
                
                # # 7. Estrazione altri parametri
                self.extract_other_parameters()
                
                print("✓ Estrazione completa terminata con successo")
                
            except Exception as e:
                raise Exception(f"Errore durante l'estrazione completa: {str(e)}")
    
    def generate_params_file(self, start_end_act_bool: bool = False, start_act: Optional[str] = None,
                           end_act: Optional[str] = None, new_flow: Optional[Any] = None,
                           new_forced_instance: Optional[Any] = None, cut_log_bool: bool = False) -> None:
        """
        Genera il file dei parametri per la simulazione.
        
        Args:
            start_end_act_bool: Se includere attività start/end
            start_act: Attività di start
            end_act: Attività di end
            new_flow: Nuove probabilità di flusso
            new_forced_instance: Nuovi tipi di istanza forzati
            cut_log_bool: Se il log ha tracce tagliate
        """
        try:
            print("Generando file parametri...")
            
            # Verifica che tutte le estrazioni siano completate
            self._validate_extractions_completed()
            
            # Preparazione parametri opzionali
            fixed_cost_act = None
            if self.primary_config['fixed_cost'] and self._other_params:
                fixed_cost_act = self._other_params._fixed_cost_avg_per_activity
            
            setup_time_distr = None
            setup_time_max = None
            if (self.primary_config['diag_log'] and self.primary_config['setup_time'] 
                and self._other_params):
                setup_time_distr = self._other_params._duration_distr_setup_time
                setup_time_max = self._other_params._max_usage_before_setup_time_per_resource
            
            cost_hour = None
            if self.primary_config['cost_hour'] and self._other_params:
                cost_hour = self._other_params._group_average_cost_hour
            
            # Generazione file parametri
            ParamsFile(
                self._instance_types._instance_types,
                self._inter_arrival_calc._distribution_params,
                self._resource_param._working_timetables,
                self._resource_param._group_act,
                self._activity_param._duration_distr,
                self._resource_param._worklist,
                fixed_cost_act,
                self._branch_prob._flow_prob,
                self._instance_types._forced_instance_types,
                self._resource_param._group_timetables_association,
                self._resource_param._roles,
                setup_time_distr,
                setup_time_max,
                cost_hour,
                self.settings,
                self._id_name_act_match,
                start_end_act_bool,
                start_act,
                end_act,
                new_flow,
                new_forced_instance,
                cut_log_bool
            )
            
            print("✓ File parametri generato con successo")
            
        except Exception as e:
            raise Exception(f"Errore nella generazione del file parametri: {str(e)}")
    

    def _validate_extractions_completed(self) -> None:
        """Valida che tutte le estrazioni necessarie siano state completate."""
        required_extractions = [
            (self._instance_types, "Tipi di istanza"),
            (self._inter_arrival_calc, "Tasso inter-arrivo"),
            (self._resource_param, "Parametri risorse"),
            (self._activity_param, "Parametri attività"),
            (self._branch_prob, "Probabilità di branching"),
            (self._id_name_act_match, "Matching ID-Nome attività")
        ]
        
        missing = [name for extraction, name in required_extractions if extraction is None]
        
        if missing:
            raise ValueError(f"Estrazioni mancanti: {', '.join(missing)}")
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto delle estrazioni completate.
        
        Returns:
            Dizionario con informazioni sulle estrazioni
        """
        return {
            'log_events': len(self.log),
            'settings_count': len(self.settings),
            'with_start_end_act': self.with_start_end_act,
            'is_diag_log': self.primary_config['diag_log'],
            'extractions_completed': {
                'bpmn_model': self._extract_bpmn is not None,
                'branching_probabilities': self._branch_prob is not None,
                'instance_types': self._instance_types is not None,
                'interarrival_rate': self._inter_arrival_calc is not None,
                'activity_parameters': self._activity_param is not None,
                'resource_parameters': self._resource_param is not None,
                'other_parameters': self._other_params is not None,
                'id_name_matching': self._id_name_act_match is not None
            },
            'optional_features': {
                'cost_hour': self.primary_config.get('cost_hour', False),
                'fixed_cost': self.primary_config.get('fixed_cost', False),
                'setup_time': self.primary_config.get('setup_time', False)
            }
        }