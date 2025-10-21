import pandas as pd
from typing import Dict, List, Any, Optional

from support_modules.constants import *
from .extract_elements import *
from .compute_branch import *
from .find_elements import *
from .resolve_gateway import *
from .analyze_connection import *
from .remove_loop import *
from .save_results import *

class BranchProbCalculation:
    """
    Classe per il calcolo delle probabilità di branching dai log XES.
    
    Analizza i gateway divergenti nel modello BPMN e calcola le probabilità
    di transizione tra attività basandosi sulla frequenza osservata nel log.
    """
    
    def __init__(self, log: pd.DataFrame, bpmn_model: Any, settings: List[Dict[str, Any]], 
                 intermediate_model: bool = False):
        """
        Inizializza il calcolatore di probabilità di branching.
        
        Args:
            log: DataFrame contenente il log XES
            bpmn_model: Modello BPMN da analizzare
            settings: Lista di configurazioni
            intermediate_model: Se si tratta di un modello intermedio
        """
        self.log = log.copy()
        self.bpmn_model = bpmn_model
        self.settings = settings
        self.intermediate_model = intermediate_model
        
        # Validazione input
        self._validate_inputs()
        
        # Configurazione primaria
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        
        # Risultati (inizializzati come None)
        self._exclusive_diverging_gateways = None
        self._out_task_of_gateway = None
        self._in_task_of_gateway = None
        self._gateway_flows = None
        self._branches = None
        self._branches_probabilities = None
        self._flow_prob = None
        self._tot = None

        self.extract_diverging_gateways = extract_diverging_gateways.__get__(self)
        self._safe_get_name = safe_get_name.__get__(self)
        self._extract_task_names = extract_task_names.__get__(self)
        self.extract_flow_probabilities = extract_flow_probabilities.__get__(self)

        self.compute_branch_probabilities = compute_branch_probabilities.__get__(self)
        self.compute_branches = compute_branches.__get__(self)

        self._find_successor_tasks = find_successor_tasks.__get__(self)
        self._find_predecessor_tasks = find_predecessor_tasks.__get__(self)

        self._nodes_match = nodes_match.__get__(self)
        self._resolve_target_gateways = resolve_target_gateways.__get__(self)
        self._resolve_source_gateways = resolve_source_gateways.__get__(self)

        self._normalize_gateway_flows = normalize_gateway_flows.__get__(self)
        self.analyze_gateway_connections = analyze_gateway_connections.__get__(self)
        
        self.remove_self_loops = remove_self_loops.__get__(self)

        self.save_results = save_results.__get__(self)
        print(f"BranchProbCalculation inizializzato per {len(self.log)} eventi")
    
    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if self.bpmn_model is None:
            raise ValueError("Modello BPMN non può essere None")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    
    
    def calculate_all_probabilities(self) -> Dict[str, Any]:
        """
        Metodo principale per calcolare tutte le probabilità di branching.
        
        Returns:
            Dizionario con tutti i risultati del calcolo
        """
        try:
            print("Iniziando calcolo completo probabilità di branching...")
            
            # 1. Estrai gateway divergenti
            self._exclusive_diverging_gateways = self.extract_diverging_gateways()
            
            # 2. Analizza connessioni gateway
            (self._out_task_of_gateway, 
             self._in_task_of_gateway, 
             self._gateway_flows) = self.analyze_gateway_connections(self._exclusive_diverging_gateways)
            
            # 3. Calcola branch
            self._branches = self.compute_branches(self._in_task_of_gateway, self._out_task_of_gateway)
            
            # 4. Calcola probabilità branch
            self._branches_probabilities = self.compute_branch_probabilities(self.log, self._branches)
            
            # 5. Estrai probabilità flusso
            flow_prob_raw = self.extract_flow_probabilities(self._branches_probabilities, self._gateway_flows)
            
            # 6. Filtra flussi validi
            self._flow_prob = {}
            for node, flows in flow_prob_raw.items():
                filtered_flows = [flow for flow in flows if flow['source'] and flow['destination']]
                if filtered_flows:
                    self._flow_prob[node] = filtered_flows
            
            # 7. Salva risultati
            print("Salvataggio risultati...")
            for node, flows in self._flow_prob.copy().items():
                self._flow_prob.pop(node)
                self._flow_prob[str(node)] = flows
            results_file = self.save_results(self._flow_prob)
            
            result = {
                'flow_probabilities': self._flow_prob,
                'branches': self._branches,
                'branches_probabilities': self._branches_probabilities,
                'gateway_count': len(self._exclusive_diverging_gateways),
                'total_executions': self._tot,
                'results_file': results_file
            }
            
            print("✓ Calcolo probabilità di branching completato")
            return result
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo delle probabilità di branching: {str(e)}")
    
    def get_calculation_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto del calcolo delle probabilità.
        
        Returns:
            Dizionario con informazioni sul calcolo
        """
        return {
            'input_events': len(self.log),
            'is_intermediate_model': self.intermediate_model,
            'gateway_count': len(self._exclusive_diverging_gateways) if self._exclusive_diverging_gateways else 0,
            'branches_count': len(self._branches) if self._branches else 0,
            'flow_probabilities_count': len(self._flow_prob) if self._flow_prob else 0,
            'total_executions': self._tot,
            'model_name': self.name
        }