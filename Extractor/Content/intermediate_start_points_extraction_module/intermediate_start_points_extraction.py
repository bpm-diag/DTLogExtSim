import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

from support_modules.constants import *

from .calculate_elements import *
from .create_elements import *
from .identify_elements import *
from .analyze_elements import *
from .save_results import *


class IntermediateStartPoint:
    """
    Classe per l'estrazione di punti di partenza intermedi da tracce incomplete.
    
    Analizza le tracce tagliate per identificare attività finali interrotte/completate,
    modifica il modello BPMN per aggiungere gateway intermedi e calcola le probabilità
    di flusso per permettere simulazioni che iniziano da stati intermedi.
    """
    
    def __init__(self, log: pd.DataFrame, model_bpmn: Any, settings: List[Dict[str, Any]]):
        """
        Inizializza l'estrattore di punti intermedi.
        
        Args:
            log: DataFrame contenente il log XES delle tracce tagliate
            model_bpmn: Modello BPMN di base
            settings: Lista di configurazioni
        """
        self.log = log.copy()
        self.model_bpmn = model_bpmn
        self.settings = settings
        
        # Validazione input
        self._validate_inputs()
        
        # Configurazione primaria
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        self.num_timestamp = self.config['num_timestamp']
        self.diaglog = self.config['diag_log']
        self.model_name = self.config['model_name']
        self.output_name = self.config['output_name']
        
        # Auto-detect ordine eventi per log diag
        # self.correct_order_diag_log = self._detect_event_order()
        
        # Risultati (inizializzati come None)
        self._final_activities_interrupted = None
        self._final_activities_ended = None
        self._forced_flow_intermediate_states = None
        self._forced_instance_types = None
        self._flow_probabilities = None
        self._modified_model = None

        self.calculate_forced_instance_types = calculate_forced_instance_types.__get__(self)
        self.calculate_flow_probabilities = calculate_flow_probabilities.__get__(self)
        self.calculate_branching_probabilities_for_modified_model = calculate_branching_probabilities_for_modified_model.__get__(self)
        
        self._create_reordered_event_for_analysis = create_reordered_event_for_analysis.__get__(self)
        self._create_dual_timestamp_event_analysis = create_dual_timestamp_event_analysis.__get__(self)
        self._create_triple_timestamp_event_analysis = create_triple_timestamp_event_analysis.__get__(self)
        self._create_start_gateway = create_start_gateway.__get__(self)
        self._create_gateway_for_activity = create_gateway_for_activity.__get__(self)
        self._create_intermediate_gateways = create_intermediate_gateways.__get__(self)
        self._prepare_final_activities_list = prepare_final_activities_list.__get__(self)
        self.create_modified_bpmn_model = create_modified_bpmn_model.__get__(self)
        
        self._extract_process_id = extract_process_id.__get__(self)
        self._identify_interrupted_activities = identify_interrupted_activities.__get__(self)
        self._identify_final_completed_activities = identify_final_completed_activities.__get__(self)
        self._identify_start_activity = identify_start_activity.__get__(self)
        self._find_target_flow_for_activity = find_target_flow_for_activity.__get__(self)
        self._find_corresponding_flow = find_corresponding_flow.__get__(self)
        self._find_start_flow_info = find_start_flow_info.__get__(self)

        self.analyze_final_activities = analyze_final_activities.__get__(self)
        self._preprocess_log_for_analysis = preprocess_log_for_analysis.__get__(self)
        self._should_process_event = should_process_event.__get__(self)
        self._reorder_events_for_analysis = reorder_events_for_analysis.__get__(self)

        self.save_results = save_results.__get__(self)
        self._save_modified_model = save_modified_model.__get__(self)
        self._add_collaboration_to_bpmn = add_collaboration_to_bpmn.__get__(self)
        self._adapt_bpmn_format = adapt_bpmn_format.__get__(self)
        print(f"IntermediateStartPoint inizializzato per {len(self.log)} eventi")
        # if self.diaglog:
        #     print(f"Ordine eventi diagnostico corretto: {self.correct_order_diag_log}")
    
    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if self.model_bpmn is None:
            raise ValueError("Modello BPMN non può essere None")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP, TAG_LIFECYCLE]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    
    # def _detect_event_order(self) -> bool:
    #     """
    #     Rileva se l'ordine degli eventi nel log diagnostico è corretto.
        
    #     Returns:
    #         True se l'ordine è corretto (assign prima di start)
    #     """
    #     if not self.diaglog or len(self.log) < 2:
    #         return False
        
    #     try:
    #         # Prendi la prima traccia
    #         first_trace_id = self.log[TAG_TRACE_ID].iloc[0]
    #         first_trace = self.log[self.log[TAG_TRACE_ID] == first_trace_id]
            
    #         if len(first_trace) < 2:
    #             return False
                
    #         # Controlla il secondo elemento
    #         second_element = first_trace.iloc[1]
    #         return second_element[TAG_LIFECYCLE] == LIFECYCLE_ASSIGN
            
    #     except Exception:
    #         return False
        
    
    def extract_all_intermediate_points(self) -> Dict[str, Any]:
        """
        Metodo principale per estrarre tutti i punti di partenza intermedi.
        
        Returns:
            Dizionario con tutti i risultati dell'estrazione
        """
        try:
            print("Iniziando estrazione completa punti intermedi...")
            
            # 1. Analizza attività finali
            self._final_activities_interrupted, self._final_activities_ended = self.analyze_final_activities()
            
            # 2. Crea modello BPMN modificato
            self._forced_flow_intermediate_states = self.create_modified_bpmn_model(
                self._final_activities_interrupted, self._final_activities_ended
            )
            
            # 3. Calcola tipi di istanza forzati
            self._forced_instance_types = self.calculate_forced_instance_types(
                self._forced_flow_intermediate_states,
                self._final_activities_interrupted,
                self._final_activities_ended
            )
            
            # 4. Calcola probabilità di flusso
            self._flow_probabilities = self.calculate_flow_probabilities(self._forced_instance_types)
            
            # 5. Salva risultati
            results_file = self.save_results(
                self._forced_flow_intermediate_states,
                self._forced_instance_types,
                self._flow_probabilities
            )
            
            result = {
                'forced_flow_intermediate_states': self._forced_flow_intermediate_states,
                'forced_instance_types': self._forced_instance_types,
                'flow_probabilities': self._flow_probabilities,
                'final_activities_interrupted': self._final_activities_interrupted,
                'final_activities_ended': self._final_activities_ended,
                'results_file': results_file,
                'interrupted_count': len(self._final_activities_interrupted),
                'completed_count': len(self._final_activities_ended),
                'intermediate_states_count': len(self._forced_flow_intermediate_states)
            }
            
            print("✓ Estrazione punti intermedi completata")
            return result
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione dei punti intermedi: {str(e)}")
    
    def get_extraction_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto dell'estrazione dei punti intermedi.
        
        Returns:
            Dizionario con informazioni sull'estrazione
        """
        return {
            'input_events': len(self.log),
            'interrupted_activities': len(self._final_activities_interrupted) if self._final_activities_interrupted is not None else 0,
            'completed_activities': len(self._final_activities_ended) if self._final_activities_ended is not None else 0,
            'intermediate_states': len(self._forced_flow_intermediate_states) if self._forced_flow_intermediate_states else 0,
            'forced_instance_types': len(self._forced_instance_types) if self._forced_instance_types is not None else 0,
            'flow_probabilities': len(self._flow_probabilities) if self._flow_probabilities else 0,
            'timestamp_type': self.num_timestamp,
            'is_diag_log': self.diaglog,
            # 'correct_event_order': self.correct_order_diag_log
        }
    