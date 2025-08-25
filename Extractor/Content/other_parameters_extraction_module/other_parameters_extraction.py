import pandas as pd
import ast
from typing import Dict, List, Any, Optional

from support_modules.constants import *

from .extract_elements import *
from .reorder_elements import *
from .fit_distribution import *
from .check_and_filter_elements import *
from .save_results import *



class OtherParametersCalculation:
    """
    Classe per l'estrazione di parametri aggiuntivi dai log XES.
    
    Gestisce l'estrazione di costi orari, costi fissi per attività,
    e parametri di setup time per le risorse quando disponibili nel log.
    """
    
    def __init__(self, log: pd.DataFrame, settings: List[Dict[str, Any]], group: List[Dict[str, Any]]):
        """
        Inizializza il calcolatore di parametri aggiuntivi.
        
        Args:
            log: DataFrame contenente il log XES
            settings: Lista di configurazioni
            group: Lista dei gruppi di risorse
        """
        self.log = log.copy()
        self.settings = settings
        self.group = group
        
        # Validazione input
        self._validate_inputs()
        
        # Configurazione primaria
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        self.diag_log = self.config['diag_log']
        
        # Risultati (inizializzati come None)
        self._group_average_cost_hour = None
        self._fixed_cost_avg_per_activity = None
        self._duration_distr_setup_time = None
        self._max_usage_before_setup_time_per_resource = None
        
        self._extract_cost_hour_per_group = extract_cost_hour_per_group.__get__(self)
        self._extract_setup_duration_distributions = extract_setup_duration_distributions.__get__(self)
        self._extract_cost_hour_diag_log = extract_cost_hour_diag_log.__get__(self)
        self._extract_cost_hour_normal_log = extract_cost_hour_normal_log.__get__(self)
        self._extract_distribution_params = extract_distribution_params.__get__(self)
        self._calculate_group_costs = calculate_group_costs.__get__(self)

        self._calculate_fixed_mean = calculate_fixed_mean.__get__(self)
        self._fit_distribution = fit_distribution.__get__(self)

        self._reorder_events_for_cost_hour = reorder_events_for_cost_hour.__get__(self)
        self._reorder_single_event_for_cost = reorder_single_event_for_cost.__get__(self)
        self._reorder_setup_events = reorder_setup_events.__get__(self)
        self._reorder_single_setup_event = reorder_single_setup_event.__get__(self)

        self._filter_gateway_events = filter_gateway_events.__get__(self)
        self._has_setup_time_events = has_setup_time_events.__get__(self)
        
        self._save_group_cost_hour = save_group_cost_hour.__get__(self)
        self._save_fixed_activity_cost = save_fixed_activity_cost.__get__(self)
        self._save_setup_time_params = save_setup_time_params.__get__(self)
        print(f"OtherParametersCalculation inizializzato per {len(self.log)} eventi")
    
    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        if self.group is None:
            raise ValueError("Group non può essere None")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    
    @staticmethod
    def _safe_literal_eval(x) -> Any:
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
        
    def cost_hour_parameter(self, log: pd.DataFrame) -> None:
        """
        Estrae parametri di costo orario per le risorse.
        
        Args:
            log: Log da cui estrarre i costi orari
        """
        print("Estraendo parametri costo orario...")
        
        try:
            if TAG_COST_HOUR not in log.columns:
                print("⚠ Colonna cost hour non trovata nel log")
                self._group_average_cost_hour = None
                return
            
            local_log = log.copy()
            
            if self.diag_log:
                self._group_average_cost_hour = self._extract_cost_hour_diag_log(local_log)
            else:
                self._group_average_cost_hour = self._extract_cost_hour_normal_log(local_log)
            
            # Salva risultati
            self._save_group_cost_hour(self._group_average_cost_hour)
            
            print(f"✓ Costi orari estratti per {len(self._group_average_cost_hour)} gruppi")
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione costi orari: {str(e)}")
        
    def fixed_activity_cost(self, log: pd.DataFrame) -> None:
        """
        Estrae costi fissi per attività.
        
        Args:
            log: Log da cui estrarre i costi fissi
        """
        print("Estraendo costi fissi per attività...")
        
        try:
            if TAG_FIXED_COST not in log.columns:
                print("⚠ Colonna fixed cost non trovata nel log")
                self._fixed_cost_avg_per_activity = None
                return
            
            local_log = log.copy()
            
            # Filtra eventi e pattern
            local_log = self._filter_gateway_events(local_log)
            local_log = local_log[local_log[TAG_LIFECYCLE] == LIFECYCLE_COMPLETE].reset_index(drop=True)
            
            # Converti in numerico e rimuovi NaN
            local_log[TAG_FIXED_COST] = pd.to_numeric(local_log[TAG_FIXED_COST], errors='coerce')
            local_log = local_log.dropna(subset=[TAG_FIXED_COST])
            
            # Calcola media per attività
            self._fixed_cost_avg_per_activity = local_log.groupby(TAG_ACTIVITY_NAME)[TAG_FIXED_COST].mean()
            
            # Salva risultati
            self._save_fixed_activity_cost(self._fixed_cost_avg_per_activity)
            
            print(f"✓ Costi fissi estratti per {len(self._fixed_cost_avg_per_activity)} attività")
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione costi fissi: {str(e)}")
        
    def setup_time_act(self, log: pd.DataFrame) -> None:
        """
        Estrae parametri di setup time per le risorse.
        
        Args:
            log: Log da cui estrarre i setup time
        """
        print("Estraendo parametri setup time...")
        
        try:
            # Controlla presenza eventi setup time
            if not self._has_setup_time_events(log):
                print("⚠ Eventi setup time non trovati nel log")
                self._duration_distr_setup_time = None
                self._max_usage_before_setup_time_per_resource = None
                return
            
            local_log = log.copy()
            
            # Filtra eventi setup time
            local_log = local_log[local_log[TAG_LIFECYCLE].isin([LIFECYCLE_START_SETUP, LIFECYCLE_END_SETUP])].reset_index(drop=True)
            
            # Trasforma risorse in liste
            local_log[TAG_RESOURCE] = local_log[TAG_RESOURCE].apply(self._safe_literal_eval)
            
            # Riordina eventi setup
            reordered_log = self._reorder_setup_events(local_log)
            reordered_df = pd.DataFrame(reordered_log)
            
            # Estrai distribuzioni durata
            duration_distributions = self._extract_setup_duration_distributions(reordered_df)
            
            # Mappa membro -> gruppo
            member_to_group = {
                member: group['group'] 
                for group in self.group 
                for member in group['members']
            }
            
            # Arricchisci con info gruppo
            self._duration_distr_setup_time = []
            for item in duration_distributions:
                member = item[0]
                group = member_to_group.get(member, None)
                enriched_item = item + [group]
                self._duration_distr_setup_time.append(enriched_item)
            
            # Estrai max usage
            max_usage = reordered_df.groupby(TAG_RESOURCE)['max_usage_before_setup_time'].unique()
            self._max_usage_before_setup_time_per_resource = [
                (member_to_group.get(resource, resource), usage[0]) 
                for resource, usage in max_usage.items()
            ]
            
            # Salva risultati
            self._save_setup_time_params(
                self._duration_distr_setup_time, 
                self._max_usage_before_setup_time_per_resource
            )
            
            print(f"✓ Setup time estratto per {len(self._duration_distr_setup_time)} risorse")
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione setup time: {str(e)}")
    
    def get_calculation_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto del calcolo dei parametri aggiuntivi.
        
        Returns:
            Dizionario con informazioni sul calcolo
        """
        return {
            'input_events': len(self.log),
            'is_diag_log': self.diag_log,
            'groups_count': len(self.group),
            'has_cost_hour': self._group_average_cost_hour is not None,
            'has_fixed_cost': self._fixed_cost_avg_per_activity is not None,
            'has_setup_time': self._duration_distr_setup_time is not None,
            'cost_hour_groups': len(self._group_average_cost_hour) if self._group_average_cost_hour else 0,
            'fixed_cost_activities': len(self._fixed_cost_avg_per_activity) if self._fixed_cost_avg_per_activity is not None else 0,
            'setup_time_resources': len(self._duration_distr_setup_time) if self._duration_distr_setup_time else 0,
            'model_name': self.name
        }
    
    # Properties per accesso ai risultati
    @property
    def group_average_cost_hour(self) -> Optional[Dict[str, float]]:
        """Costi orari medi per gruppo."""
        return self._group_average_cost_hour
    
    @property
    def fixed_cost_avg_per_activity(self) -> Optional[pd.Series]:
        """Costi fissi medi per attività."""
        return self._fixed_cost_avg_per_activity
    
    @property
    def duration_distr_setup_time(self) -> Optional[List]:
        """Distribuzioni durata setup time."""
        return self._duration_distr_setup_time
    
    @property
    def max_usage_before_setup_time_per_resource(self) -> Optional[List]:
        """Max usage prima del setup time per risorsa."""
        return self._max_usage_before_setup_time_per_resource