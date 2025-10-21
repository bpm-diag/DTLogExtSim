import pandas as pd


from typing import Dict, List, Any

from support_modules.constants import *


from .extract_elements import *
from .calculate_elements import *
from .save_results import *


class ResourceParameterCalculation:
    """
    Classe per l'estrazione dei parametri delle risorse dai log XES.
    
    Analizza le risorse per identificare ruoli, calcolare timetables,
    estrarre worklist e determinare associazioni attività-risorse.
    """
    
    def __init__(self, log: pd.DataFrame, settings: List[Dict[str, Any]]):
        """
        Inizializza il calcolatore di parametri delle risorse.
        
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
        self.sim_threshold = self.config['sim_threshold']
        
        # Risultati (inizializzati come None)
        self._activities = None
        self._resources = None
        self._res_act = None
        self._act_res = None
        self._roles = None
        self._roles_tables = None
        self._group_schedule = None
        self._res_groups = None
        self._working_timetables = None
        self._group_timetables_association = None
        self._group_act = None
        self._worklist = None

        self.extract_activities = extract_activities.__get__(self)
        self.extract_resources = extract_resources.__get__(self)
        self.extract_resources_by_activity = extract_resources_by_activity.__get__(self)
        self.extract_activities_by_resource = extract_activities_by_resource.__get__(self)
        self.extract_roles =  extract_roles.__get__(self)
        self._define_roles = define_roles.__get__(self)
        self.extract_groups_by_activity = extract_groups_by_activity.__get__(self)

        self.calculate_correlation_matrix = calculate_correlation_matrix.__get__(self)
        self.calculate_correlation_matrix_pearson = calculate_correlation_matrix_pearson.__get__(self)
        self.calculate_group_schedules = calculate_group_schedules.__get__(self)
        self.compute_timetables = compute_timetables.__get__(self)
        self.compute_worklist = compute_worklist.__get__(self)

        self.save_group_schedule = save_group_schedule.__get__(self)
        self.save_timetables = save_timetables.__get__(self)
        self.save_worklists = save_worklists.__get__(self)
        self.save_resources_of_activities = save_resources_of_activities.__get__(self)

        print(f"ResourceParameterCalculation inizializzato per {len(self.log)} eventi")
    
    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_RESOURCE, TAG_TIMESTAMP, TAG_LIFECYCLE]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    
    def preprocess_log(self) -> pd.DataFrame:
        """
        Preprocessa il log filtrando solo eventi rilevanti.
        
        Returns:
            DataFrame preprocessato
        """
        print("Preprocessing log per parametri risorse...")
        
        try:
            # Filtra solo eventi assign, start, complete
            relevant_events = [LIFECYCLE_ASSIGN, LIFECYCLE_START, LIFECYCLE_COMPLETE]
            processed_log = self.log[self.log[TAG_LIFECYCLE].isin(relevant_events)].reset_index(drop=True)
            
            print(f"✓ Log preprocessato: {len(processed_log)} eventi rimanenti")
            return processed_log
            
        except Exception as e:
            raise Exception(f"Errore nel preprocessing del log: {str(e)}")
    
    def _get_part_of_day(self, timestamp: pd.Timestamp) -> str:
        """Determina la parte del giorno dal timestamp."""
        hour = timestamp.hour
        if 5 <= hour < 12:
            return 'Morning'
        elif 12 <= hour < 17:
            return 'Afternoon'
        elif 17 <= hour < 21:
            return 'Evening'
        else:
            return 'Night'
    
    def _get_day_of_week(self, timestamp: pd.Timestamp) -> str:
        """Ottiene il giorno della settimana."""
        day_of_week = timestamp.weekday()  # 0=lunedì, 6=domenica
        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        return days_of_week[day_of_week]
    
    def _round_time_to_5_minutes(self, timestamp: pd.Timestamp) -> pd.Timestamp:
        """Arrotonda il timestamp al blocco di 5 minuti precedente."""
        minute_ranges = [
            (0, 5, 0), (5, 10, 5), (10, 15, 10), (15, 20, 15),
            (20, 25, 20), (25, 30, 25), (30, 35, 30), (35, 40, 35),
            (40, 45, 40), (45, 50, 45), (50, 55, 50), (55, 60, 55)
        ]
        
        for min_start, min_end, rounded_min in minute_ranges:
            if min_start <= timestamp.minute < min_end:
                return timestamp.replace(minute=rounded_min, second=0, microsecond=0)
        
        return timestamp.replace(minute=55, second=0, microsecond=0)
    
    def assign_groups_to_log(self, log: pd.DataFrame, res_groups: Dict[str, List[str]]) -> pd.DataFrame:
        """
        Assegna gruppi alle risorse nel log.
        
        Args:
            log: Log da processare
            res_groups: Mapping gruppo -> lista risorse
            
        Returns:
            Log con colonna gruppo aggiunta
        """
        print("Assegnando gruppi alle risorse nel log...")
        
        try:
            log_with_groups = log.copy()
            log_with_groups[TAG_GROUP] = log_with_groups[TAG_RESOURCE].apply(
                lambda res_list: self._assign_group_to_resources(res_list, res_groups)
            )
            
            print("✓ Gruppi assegnati al log")
            return log_with_groups
            
        except Exception as e:
            raise Exception(f"Errore nell'assegnazione gruppi: {str(e)}")
    
    def _assign_group_to_resources(self, res_list: List[str], res_groups: Dict[str, List[str]]) -> List[str]:
        groups = []
        for resource in res_list:
            for group_name, group_members in res_groups.items():
                if resource in group_members:
                    groups.append(group_name)
        
        return list(set(groups))  # Rimuovi duplicati
    
    
    def calculate_all_resource_parameters(self) -> Dict[str, Any]:
        """
        Metodo principale per calcolare tutti i parametri delle risorse.
        
        Returns:
            Dizionario con tutti i risultati del calcolo
        """
        try:
            print("Iniziando calcolo completo parametri risorse...")
            
            # 1. Preprocessing log
            processed_log = self.preprocess_log()
            
            # 2. Estrazione base
            self._activities = self.extract_activities(processed_log)
            self._resources = self.extract_resources(processed_log)
            
            # 3. Associazioni risorse-attività
            self._res_act = self.extract_resources_by_activity(processed_log, self._activities)
            self._act_res = self.extract_activities_by_resource(processed_log, self._resources)
            
            # 4. Analisi correlazioni e ruoli
            correlation_matrix = self.calculate_correlation_matrix(processed_log)
            self._roles, self._roles_tables = self.extract_roles(correlation_matrix)
            
            # 5. Schedule gruppi
            self._group_schedule = self.calculate_group_schedules(processed_log, self._roles)
            group_schedule_file = self.save_group_schedule(self._group_schedule, self._roles)
            
            # 6. Assegnazione gruppi al log
            self._res_groups = {item['group']: item['members'] for item in self._roles}
            log_with_groups = self.assign_groups_to_log(processed_log, self._res_groups)
            
            # 7. Timetables
            self._working_timetables = self.compute_timetables(log_with_groups, self._res_groups)
            timetables_file = self.save_timetables(self._working_timetables)
            
            # 8. Gruppi per attività
            self._group_act = self.extract_groups_by_activity(log_with_groups, self._activities)
            group_act_file = self.save_resources_of_activities(self._group_act)
            
            # 9. Worklist
            self._worklist = self.compute_worklist(log_with_groups, self._res_groups, self._activities, self._res_act)
            worklist_file = self.save_worklists(self._worklist)
            
            result = {
                'activities': self._activities,
                'resources': self._resources,
                'res_act': self._res_act,
                'act_res': self._act_res,
                'roles': self._roles,
                'roles_tables': self._roles_tables,
                'group_schedule': self._group_schedule,
                'res_groups': self._res_groups,
                'working_timetables': self._working_timetables,
                'group_timetables_association': self._group_timetables_association,
                'group_act': self._group_act,
                'worklist': self._worklist,
                'files': {
                    'group_schedule': group_schedule_file,
                    'timetables': timetables_file,
                    'group_activities': group_act_file,
                    'worklist': worklist_file
                }
            }
            
            print("✓ Calcolo parametri risorse completato")
            return result
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo dei parametri delle risorse: {str(e)}")
    
    def get_calculation_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto del calcolo dei parametri delle risorse.
        
        Returns:
            Dizionario con informazioni sul calcolo
        """
        return {
            'input_events': len(self.log),
            'activities_count': len(self._activities) if self._activities else 0,
            'resources_count': len(self._resources) if self._resources else 0,
            'roles_count': len(self._roles) if self._roles else 0,
            'timetables_count': len(self._working_timetables) if self._working_timetables else 0,
            'worklist_size': len(self._worklist) if self._worklist else 0,
            'group_activities_count': len(self._group_act) if self._group_act else 0,
            'sim_threshold': self.sim_threshold,
            'has_group_timetables_association': self._group_timetables_association is not None,
            'model_name': self.name
        }
    
