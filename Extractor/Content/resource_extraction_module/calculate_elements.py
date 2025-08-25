import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from pandas import DataFrame
from collections import defaultdict
from scipy.stats import pearsonr
from datetime import datetime, timedelta

from support_modules.constants import *
from timetables_extraction_module.timetables_extraction import TimeTablesCalculation
from worklist_res_extraction_module.worklist_res_extraction import WorklistCalculation

def calculate_correlation_matrix(self, log: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Calcola la matrice di correlazione tra risorse.
    
    Args:
        log: Log da analizzare
        
    Returns:
        Lista di correlazioni tra risorse
    """
    print("Calcolando matrice di correlazione...")
    
    try:
        # Aggiungi colonna momento del giorno
        log_with_moments = log.copy()
        log_with_moments[TAG_MOMENT_OF_DAY] = log_with_moments[TAG_TIMESTAMP].apply(self._get_part_of_day)
        
        # Costruisci dizionario conoscenze risorse
        res_knowledge_dict = defaultdict(lambda: defaultdict(int))
        
        for _, event in log_with_moments.iterrows():
            activity = event[TAG_ACTIVITY_NAME]
            moment_of_day = event[TAG_MOMENT_OF_DAY]
            resource_list = event[TAG_RESOURCE]
            
            if isinstance(resource_list, list) and resource_list and not pd.isna(resource_list[0]):
                for resource in resource_list:
                    pair = (activity, moment_of_day)
                    res_knowledge_dict[resource][pair] += 1
        
        # Crea DataFrame e calcola correlazioni
        df = DataFrame.from_dict(res_knowledge_dict, orient='index').fillna(0)
        correlation_matrix = self.calculate_correlation_matrix_pearson(df)
        
        print(f"✓ Calcolate {len(correlation_matrix)} correlazioni")
        return correlation_matrix
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo della matrice di correlazione: {str(e)}")
    
def calculate_correlation_matrix_pearson(self, profiles: DataFrame) -> List[Dict[str, Any]]:
    """Calcola la matrice di correlazione Pearson tra profili."""
    correlation_matrix = []
    
    for user_id_x, row_x in profiles.iterrows():
        for user_id_y, row_y in profiles.iterrows():
            x = np.array(row_x.values, dtype=int)
            y = np.array(row_y.values, dtype=int)
            
            try:
                r_value, _ = pearsonr(x, y)
                # Gestisci NaN (correlazione indefinita)
                if np.isnan(r_value):
                    r_value = 0.0
            except:
                r_value = 0.0
            
            correlation_matrix.append({
                'x': user_id_x,
                'y': user_id_y,
                'distance': r_value
            })
    
    return correlation_matrix

def calculate_group_schedules(self, log: pd.DataFrame, roles: List[Dict[str, Any]]) -> Dict[str, Dict[str, set]]:
    """
    Calcola gli schedule per ogni gruppo.
    
    Args:
        log: Log da analizzare
        roles: Lista dei ruoli identificati
        
    Returns:
        Dizionario gruppo -> giorno -> set di orari
    """
    print("Calcolando schedule per gruppi...")
    
    try:
        group_schedule = defaultdict(lambda: defaultdict(set))
        
        for _, row in log.iterrows():
            resource_list = row[TAG_RESOURCE]
            timestamp = row[TAG_TIMESTAMP]
            
            if isinstance(resource_list, list) and resource_list and not pd.isna(resource_list[0]):
                # Trova ruoli contenenti almeno una risorsa dell'evento
                for role in roles:
                    if any(resource in role['members'] for resource in resource_list):
                        day_of_week = self._get_day_of_week(timestamp)
                        rounded_time = self._round_time_to_5_minutes(timestamp)
                        rounded_time_str = rounded_time.strftime('%H:%M')
                        
                        group_schedule[role['group']][day_of_week].add(rounded_time_str)
        
        print(f"✓ Calcolati schedule per {len(group_schedule)} gruppi")
        return dict(group_schedule)
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo degli schedule: {str(e)}")
    
def compute_timetables(self, log: pd.DataFrame, res_groups: Dict[str, List[str]]) -> Dict[str, Dict[str, str]]:
    """
    Calcola le timetables usando il modulo esterno.
    
    Args:
        log: Log da analizzare
        res_groups: Gruppi di risorse
        
    Returns:
        Dizionario delle timetables
    """
    print("Calcolando timetables...")
    
    try:
        # Usa il modulo esterno per calcolo timetables
        timetables_calc = TimeTablesCalculation(log, self.settings, res_groups, self._group_schedule)
        results = timetables_calc._initialize_calculation()

        self._group_timetables_association = timetables_calc._timetables_def
        
        # Ottieni timetables raw
        app_timetables = timetables_calc.compute_timetables()
        
        # Formatta timetables
        timetables = {}
        for timetable, schedule in app_timetables.items():
            timetables[timetable] = {}
            for day, intervals in schedule.items():
                # Converti intervalli in stringhe formattate
                interval_strings = []
                for interval in intervals:
                    min_time = min(interval).strftime('%H:%M')
                    max_time_obj = datetime.combine(datetime.today(), max(interval)) + timedelta(minutes=5)
                    max_time = max_time_obj.time().strftime('%H:%M')
                    if max_time == '00:00':
                        max_time = '23:59'
                    interval_strings.append(f"{min_time} - {max_time}")
                
                timetables[timetable][day.capitalize()] = ', '.join(interval_strings)
        
        print(f"✓ Calcolate {len(timetables)} timetables")
        return timetables
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo delle timetables: {str(e)}")
    
def compute_worklist(self, log: pd.DataFrame, res_groups: Dict[str, List[str]], 
                        activities: List[str], res_act: Dict[str, List[List[str]]]) -> List[Tuple[str, str]]:
    """
    Calcola la worklist usando il modulo esterno.
    
    Args:
        log: Log da analizzare
        res_groups: Gruppi di risorse
        activities: Lista attività
        res_act: Risorse per attività
        
    Returns:
        Lista di tuple (task1, task2) per worklist
    """
    print("Calcolando worklist...")
    
    try:
        # Usa il modulo esterno per calcolo worklist
        worklist_calc = WorklistCalculation(log, self.settings, res_groups, activities, res_act)
        worklist_calc._initialize_calculation()
        worklist = worklist_calc.compute_worklist_with_intr_value()
        
        print(f"✓ Calcolata worklist con {len(worklist)} elementi")
        return worklist
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo della worklist: {str(e)}")