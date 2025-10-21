import pandas as pd
import networkx as nx
from typing import List, Dict, Any, Tuple
from operator import itemgetter

from support_modules.constants import *

def extract_activities(self, log: pd.DataFrame) -> List[str]:
    """
    Estrae le attività unique dal log.
    
    Args:
        log: Log da cui estrarre le attività
        
    Returns:
        Lista delle attività unique
    """
    print("Estraendo attività...")
    
    try:
        # Esplodi e rimuovi duplicati
        exploded_activities = log[TAG_ACTIVITY_NAME].explode()
        unique_activities = exploded_activities.drop_duplicates()
        unique_activities = unique_activities[unique_activities.notna()]
        model_activities = unique_activities.tolist()
        
        print(f"✓ Trovate {len(model_activities)} attività unique")
        return model_activities
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione delle attività: {str(e)}")
    
def extract_resources(self, log: pd.DataFrame) -> List[str]:
    """
    Estrae le risorse unique dal log.
    
    Args:
        log: Log da cui estrarre le risorse
        
    Returns:
        Lista delle risorse unique
    """
    print("Estraendo risorse...")
    
    try:
        # Esplodi e rimuovi duplicati
        exploded_resources = log[TAG_RESOURCE].explode()
        unique_resources = exploded_resources.drop_duplicates()
        unique_resources = unique_resources[unique_resources.notna()]
        model_resources = unique_resources.tolist()
        
        print(f"✓ Trovate {len(model_resources)} risorse unique")
        return model_resources
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione delle risorse: {str(e)}")
    
def extract_resources_by_activity(self, log: pd.DataFrame, activities: List[str]) -> Dict[str, List[List[str]]]:
    """
    Estrae le risorse che eseguono ogni attività.
    
    Args:
        log: Log da analizzare
        activities: Lista delle attività
        
    Returns:
        Dizionario attività -> lista di gruppi di risorse
    """
    print("Estraendo risorse per attività...")
    
    try:
        resources_by_activity = {}
        
        for activity in activities:
            # Filtra log per attività specifica
            filtered_log = log[log[TAG_ACTIVITY_NAME] == activity]
            
            if not filtered_log.empty:
                # Estrai liste di risorse unique
                resource_lists = filtered_log[TAG_RESOURCE].tolist()

                unique_lists = [list(item) for item in set(tuple(sublist) for sublist in resource_lists)]
                unique_lists =  [sublist for sublist in unique_lists if sublist and not any(pd.isna(x) for x in sublist)]
                
                if unique_lists:
                    resources_by_activity[activity] = unique_lists
        
        print(f"✓ Estratte risorse per {len(resources_by_activity)} attività")
        return resources_by_activity
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione risorse per attività: {str(e)}")
    
def extract_activities_by_resource(self, log: pd.DataFrame, resources: List[str]) -> Dict[str, List[str]]:
    """
    Estrae le attività eseguite da ogni risorsa.
    
    Args:
        log: Log da analizzare
        resources: Lista delle risorse
        
    Returns:
        Dizionario risorsa -> lista di attività
    """
    print("Estraendo attività per risorsa...")
    
    try:
        activities_by_resource = {}
        
        for resource in resources:
            # Filtra log dove la risorsa è coinvolta
            filtered_log = log[log[TAG_RESOURCE].apply(
                lambda res_list: resource in res_list
            )]
            
            if not filtered_log.empty:
                # Estrai attività unique
                activities = filtered_log[TAG_ACTIVITY_NAME].drop_duplicates().tolist()
                activities_by_resource[resource] = activities
        
        print(f"✓ Estratte attività per {len(activities_by_resource)} risorse")
        return activities_by_resource
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione attività per risorsa: {str(e)}")
    
def extract_roles(self, correlation_matrix: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """
    Estrae ruoli/gruppi dalle correlazioni tra risorse.
    
    Args:
        correlation_matrix: Matrice di correlazione
        
    Returns:
        Tupla (ruoli, tabella_risorse)
    """
    print("Estraendo ruoli dalle correlazioni...")
    
    try:
        # Crea grafo per clustering
        graph = nx.Graph()
        
        # Aggiungi nodi (risorse)
        for resource in self._resources:
            graph.add_node(resource)
        
        # Aggiungi archi per correlazioni significative
        for correlation in correlation_matrix:
            if (correlation['distance'] > self.sim_threshold and 
                correlation['x'] != correlation['y']):
                graph.add_edge(
                    correlation['x'],
                    correlation['y'],
                    weight=correlation['distance']
                )
        
        # Trova componenti connesse (gruppi)
        subgraphs = list(graph.subgraph(c) for c in nx.connected_components(graph))
        
        # Definisci ruoli
        roles, roles_table = self._define_roles(subgraphs)
        
        print(f"✓ Identificati {len(roles)} ruoli")
        return roles, roles_table
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione dei ruoli: {str(e)}")
    
def define_roles(self, subgraphs: List[nx.Graph]) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Definisce ruoli dai sottografi."""
    records = []
    
    # Crea record per ogni sottografo
    for i, subgraph in enumerate(subgraphs):
        users_names = [resource for resource in self._resources if resource in subgraph]
        records.append({
            'group': f'Group{i + 1}',
            'quantity': len(subgraph),
            'members': users_names
        })
    
    # Ordina per numero di risorse (più grandi prima)
    records = sorted(records, key=itemgetter('quantity'), reverse=True)
    
    # Rinumera gruppi
    for i, record in enumerate(records):
        record['group'] = f'Group{i + 1}'
    
    # Crea tabella risorse
    resource_table = []
    for record in records:
        for member in record['members']:
            resource_table.append({
                'group': record['group'],
                'resource': member
            })
    
    return records, resource_table
    
def extract_groups_by_activity(self, log: pd.DataFrame, activities: List[str]) -> Dict[str, List[List[str]]]:
    """
    Estrae i gruppi che eseguono ogni attività.
    
    Args:
        log: Log con colonna gruppo
        activities: Lista delle attività
        
    Returns:
        Dizionario attività -> lista di gruppi
    """
    print("Estraendo gruppi per attività...")
    
    try:
        groups_by_activity = {}
        
        for activity in activities:
            # Filtra log per attività specifica
            filtered_log = log[log[TAG_ACTIVITY_NAME] == activity]
            
            if not filtered_log.empty:
                # Estrai liste di gruppi unique
                group_lists = filtered_log[TAG_GROUP].tolist()
                
                # Converti in set di tuple per unicità
                unique_sets = set()
                for group_list in group_lists:
                    if isinstance(group_list, list) and group_list and not any(pd.isna(x) for x in group_list):
                        unique_sets.add(tuple(group_list))
                
                unique_lists = [list(item) for item in unique_sets]
                
                if unique_lists:
                    groups_by_activity[activity] = unique_lists
        
        print(f"✓ Estratti gruppi per {len(groups_by_activity)} attività")
        return groups_by_activity
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione gruppi per attività: {str(e)}")