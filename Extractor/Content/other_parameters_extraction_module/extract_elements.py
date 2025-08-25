import pandas as pd
import numpy as np
from typing import Dict, List

from support_modules.constants import *

def extract_cost_hour_per_group(self, log: pd.DataFrame) -> Dict[str, float]:
    """Estrae costo orario medio per gruppo."""
    try:
        cost_hour_per_resource = {}
        
        # Calcola costo orario per risorsa
        for _, row in log.iterrows():
            resource = row[TAG_RESOURCE]
            if resource not in cost_hour_per_resource:
                cost_hour_per_resource[resource] = []
            
            cost = float(row[TAG_COST_HOUR])
            duration = row['end_timestamp'] - row['start_timestamp']
            duration_seconds = float(duration.total_seconds())
            
            # Calcola costo orario solo se durata > 0
            if duration_seconds > 0:
                cost_per_hour = cost / (duration_seconds / 3600)
                cost_hour_per_resource[resource].append(cost_per_hour)
        
        # Mappa risorsa -> gruppo
        resource_to_group = {}
        for group_info in self.group:
            for member in group_info['members']:
                resource_to_group[member] = group_info['group']
        
        # Raccoglie costi per gruppo  
        group_costs = {group_info['group']: [] for group_info in self.group}
        
        for resource, cost_hours in cost_hour_per_resource.items():
            group = resource_to_group.get(resource)
            if group:
                group_costs[group].extend(cost_hours)
        
        # Calcola medie per gruppo
        group_average_cost = {}
        for group, costs in group_costs.items():
            if costs:
                group_average_cost[group] = sum(costs) / len(costs)
            else:
                group_average_cost[group] = 0.0
        
        return group_average_cost
        
    except Exception as e:
        raise Exception(f"Errore nel calcolo costi per gruppo: {str(e)}")
    
def extract_setup_duration_distributions(self, log: pd.DataFrame) -> List[List]:
    """Estrae distribuzioni di durata setup time."""
    setup_time_durations = {}
    
    # Raccoglie durate per risorsa
    for _, row in log.iterrows():
        resource = row[TAG_RESOURCE]
        if resource not in setup_time_durations:
            setup_time_durations[resource] = []
        
        duration = row['end_timestamp'] - row['start_timestamp']
        duration_seconds = float(duration.total_seconds())
        
        # Aggiungi solo durate positive
        if duration_seconds > 0:
            setup_time_durations[resource].append(duration_seconds)
    
    # Calcola distribuzioni
    setup_time_distributions = []
    for resource, duration_list in setup_time_durations.items():
        if duration_list:  # Solo se ci sono durate valide
            distribution_params = self._fit_distribution(duration_list)
            setup_time_distributions.append([resource, distribution_params[0], distribution_params[1]])
    
    return setup_time_distributions

def extract_cost_hour_diag_log(self, local_log: pd.DataFrame) -> Dict[str, float]:
    """Estrae costi orari per log diagnostici."""
    try:
        # Trasforma risorse e costi in liste
        local_log[TAG_RESOURCE] = local_log[TAG_RESOURCE].apply(self._safe_literal_eval)
        local_log[TAG_COST_HOUR] = local_log[TAG_COST_HOUR].apply(self._safe_literal_eval)
        
        # Filtra eventi complete ed escludi pattern
        temp_log = local_log[local_log[TAG_LIFECYCLE] == LIFECYCLE_COMPLETE].reset_index(drop=True)
        temp_log = self._filter_gateway_events(temp_log)
        
        # Espandi liste di risorse e costi
        df_expanded = temp_log.explode([TAG_RESOURCE, TAG_COST_HOUR])
        
        # Normalizza costi
        df_expanded[TAG_COST_HOUR] = df_expanded[TAG_COST_HOUR].apply(
            lambda x: x[0] if isinstance(x, list) else x
        )
        df_expanded[TAG_COST_HOUR] = pd.to_numeric(df_expanded[TAG_COST_HOUR], errors='coerce')
        
        # Raggruppa costi per risorsa
        resource_cost_df = df_expanded.groupby(TAG_RESOURCE)[TAG_COST_HOUR].agg(list).reset_index()
        resource_to_costs = resource_cost_df.set_index(TAG_RESOURCE)[TAG_COST_HOUR].to_dict()
        
        # Calcola costi per gruppo
        return self._calculate_group_costs(resource_to_costs)
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione costi diag log: {str(e)}")

def extract_cost_hour_normal_log(self, local_log: pd.DataFrame) -> Dict[str, float]:
    """Estrae costi orari per log normali."""
    try:
        # Filtra eventi start e complete
        local_log = local_log[local_log[TAG_LIFECYCLE].isin([LIFECYCLE_START, LIFECYCLE_COMPLETE])].reset_index(drop=True)
        
        # Riordina log per creare eventi strutturati
        reordered_log = self._reorder_events_for_cost_hour(local_log)
        reordered_df = pd.DataFrame(reordered_log)
        
        # Estrai costi orari per gruppo
        return self._extract_cost_hour_per_group(reordered_df)
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione costi normal log: {str(e)}")
    

def extract_distribution_params(self, data: List[float], distribution_type: str) -> Dict[str, float]:
    """Estrae parametri per tipo di distribuzione."""
    try:
        if distribution_type == 'fixed':
            mean_value = 0 if data[0] == 0.00001 else data[0]
            return {'mean': round(mean_value, 2), 'arg1': 0, 'arg2': 0}
        
        elif distribution_type == 'norm':
            return {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.std(data), 2),
                'arg2': 0
            }
        
        elif distribution_type == 'expon':
            return {
                'mean': round(np.mean(data), 2),
                'arg1': 0,
                'arg2': 0
            }
        
        elif distribution_type == 'uniform':
            return {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.min(data), 2),
                'arg2': round(np.max(data), 2)
            }
        
        elif distribution_type == 'triang':
            return {
                'mean': round(np.mean(data), 2),
                'arg1': 0,
                'arg2': 0
            }
        
        elif distribution_type in ['lognorm', 'gamma']:
            return {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.var(data), 2),
                'arg2': 0
            }
        
        else:
            # Default fallback
            return {
                'mean': round(np.mean(data), 2),
                'arg1': round(np.std(data), 2),
                'arg2': 0
            }
            
    except Exception as e:
        print(f"Errore nell'estrazione parametri: {e}")
        return {
            'mean': round(np.mean(data), 2),
            'arg1': round(np.std(data), 2),
            'arg2': 0
        }
    
def calculate_group_costs(self, resource_to_costs: Dict[str, List[float]]) -> Dict[str, float]:
    """Calcola costi medi per gruppo."""
    group_costs = {}
    
    # Raccoglie costi per gruppo
    for group_info in self.group:
        group_name = group_info['group']
        members = group_info['members']
        combined_costs = []
        
        for member in members:
            combined_costs.extend(resource_to_costs.get(member, []))
        
        group_costs[group_name] = combined_costs
    
    # Calcola medie
    group_average_cost = {}
    for group, costs in group_costs.items():
        if costs:
            group_average_cost[group] = sum(costs) / len(costs)
        else:
            group_average_cost[group] = 0.0
    
    return group_average_cost