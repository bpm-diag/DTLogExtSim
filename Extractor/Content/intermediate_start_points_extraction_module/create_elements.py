import pm4py
import os
import pandas as pd
from typing import List, Dict, Any, Tuple, Optional

from support_modules.constants import *

def create_reordered_event_for_analysis(self, caseid: str, event_index: int, 
                                           trace: List[Dict], current_event: Dict) -> Optional[Dict]:
    """Crea evento riordinato per l'analisi."""
    task_name = current_event['task']
    remaining_events = trace[event_index + 1:]
    
    if self.num_timestamp == 2:
        return self._create_dual_timestamp_event_analysis(caseid, current_event, remaining_events, task_name)
    else:  # num_timestamp == 3
        return self._create_triple_timestamp_event_analysis(caseid, current_event, remaining_events, task_name)

def create_dual_timestamp_event_analysis(self, caseid: str, start_event: Dict, 
                                        remaining_events: List[Dict], task_name: str) -> Dict:
    """Crea evento con 2 timestamp per analisi."""
    complete_event = next(
        (event for event in remaining_events 
            if event['task'] == task_name and event['event_type'] == LIFECYCLE_COMPLETE),
        None
    )
    
    return {
        'caseid': caseid,
        'task': start_event['task'],
        'start_timestamp': start_event['timestamp'],
        'end_timestamp': complete_event['timestamp'] if complete_event else "nan"
    }

def create_triple_timestamp_event_analysis(self, caseid: str, assign_event: Dict,
                                            remaining_events: List[Dict], task_name: str) -> Dict:
    """Crea evento con 3 timestamp per analisi."""
    # Trova eventi correlati
    # if self.diaglog and not self.correct_order_diag_log:
    #     start_event = next(
    #         (event for event in remaining_events 
    #             if event['task'] == task_name and event['event_type'] == LIFECYCLE_ASSIGN),
    #         None
    #     )
    # else:
    start_event = next(
        (event for event in remaining_events 
            if event['task'] == task_name and event['event_type'] == LIFECYCLE_START),
        None
    )
        
    complete_event = next(
        (event for event in remaining_events 
            if event['task'] == task_name and event['event_type'] == LIFECYCLE_COMPLETE),
        None
    )
    
    return {
        'caseid': caseid,
        'task': assign_event['task'],
        'assign_timestamp': assign_event['timestamp'],
        'start_timestamp': start_event['timestamp'] if start_event else "nan",
        'end_timestamp': complete_event['timestamp'] if complete_event else "nan"
    }

def create_start_gateway(self, model: Any, gateway_info: Dict[str, Any], index: int,
                        start_gateways: List[Any], start_flow_info: Dict[str, Any],
                        num_final_activities: int) -> Dict[str, Any]:
    """Crea gateway di start per collegamento intermedio."""
    process_id = gateway_info['process_id']
    
    # Crea gateway di start
    start_gateway = pm4py.BPMN.ExclusiveGateway(
        id=f"id_start_{index}",
        gateway_direction=pm4py.BPMN.Gateway.Direction.DIVERGING,
        process=process_id
    )
    
    # Flusso verso gateway intermedio
    intermediate_flow = pm4py.BPMN.Flow(
        start_gateway, gateway_info['gateway'],
        id=f"flow_s_i_a_{index}",
        name=f"flow_s_i_a_{index}",
        process=process_id
    )
    
    gateway_info['gateway'].add_in_arc(intermediate_flow)
    start_gateway.add_out_arc(intermediate_flow)
    
    # Gestisci connessioni con gateway precedenti o source originale
    if start_gateways:
        # Collega al gateway precedente
        prev_gateway = start_gateways[-1]
        gateway_to_gateway_flow = pm4py.BPMN.Flow(
            prev_gateway, start_gateway,
            id=f"flow_g_g_{index}",
            name=f"flow_g_g_{index}",
            process=process_id
        )
        start_gateway.add_in_arc(gateway_to_gateway_flow)
        prev_gateway.add_out_arc(gateway_to_gateway_flow)
        model.add_flow(gateway_to_gateway_flow)
    else:
        # Primo gateway, collega al source originale
        start_to_gateway_flow = pm4py.BPMN.Flow(
            start_flow_info['source'], start_gateway,
            id=f"flow_s_g_{index}",
            name=f"flow_s_g_{index}",
            process=process_id
        )
        start_gateway.add_in_arc(start_to_gateway_flow)
        start_flow_info['source'].add_out_arc(start_to_gateway_flow)
        model.add_flow(start_to_gateway_flow)
    
    # Se è l'ultimo gateway, crea flusso verso target finale
    if index + 1 == num_final_activities:
        final_flow = pm4py.BPMN.Flow(
            start_gateway, start_flow_info['target'],
            id=f"flow_g_t_{index}",
            name=f"flow_g_t_{index}",
            process=process_id
        )
        start_gateway.add_out_arc(final_flow)
        start_flow_info['target'].add_in_arc(final_flow)
        model.add_flow(final_flow)
    
    # Aggiungi elementi al modello
    model.add_node(start_gateway)
    model.add_flow(intermediate_flow)
    
    return {
        'gateway': start_gateway,
        'intermediate_flow': intermediate_flow
    }

def create_gateway_for_activity(self, model: Any, flow_to_modify: Any, 
                                   activity_type: str, index: int) -> Dict[str, Any]:
    """Crea gateway per un'attività specifica."""
    source_flow = flow_to_modify.get_source()
    target_flow = flow_to_modify.get_target()
    process_id = target_flow.get_process()
    
    # Crea nuovo gateway
    gateway = pm4py.BPMN.ExclusiveGateway(
        id=f"id_{index}",
        gateway_direction=pm4py.BPMN.Gateway.Direction.DIVERGING,
        process=process_id
    )
    
    # Crea flussi
    if activity_type == "interrupted":
        new_flow = pm4py.BPMN.Flow(
            source_flow, gateway, 
            id=flow_to_modify.get_id(), 
            name=flow_to_modify.get_id(), 
            process=process_id
        )
        new_flow1 = pm4py.BPMN.Flow(
            gateway, target_flow,
            id=f"flow_b_{index}",
            name=f"flow_b_{index}",
            process=process_id
        )
    else:  # ended
        new_flow = pm4py.BPMN.Flow(
            source_flow, gateway,
            id=f"flow_a_{index}",
            name=f"flow_a_{index}",
            process=process_id
        )
        new_flow1 = pm4py.BPMN.Flow(
            gateway, target_flow,
            id=f"flow_b_{index}",
            name=f"flow_b_{index}",
            process=process_id
        )
    
    # Configura connessioni
    gateway.add_in_arc(new_flow)
    gateway.add_out_arc(new_flow1)
    
    # Rimuovi vecchio flusso (rimuove automaticamente da in_arcs e out_arcs)
    print(f"DEBUG: Rimuovendo flow_to_modify con ID: {flow_to_modify.get_id()}")
    model.remove_flow(flow_to_modify)
    print(f"DEBUG: Flow rimosso con successo")
    
    # Aggiungi nuove connessioni
    target_flow.add_in_arc(new_flow1)
    source_flow.add_out_arc(new_flow)
    
    # Aggiungi elementi al modello
    model.add_node(gateway)
    model.add_flow(new_flow)
    model.add_flow(new_flow1)
    
    return {
        'gateway': gateway,
        'new_flow': new_flow,
        'new_flow1': new_flow1,
        'process_id': process_id
    }

def create_intermediate_gateways(self, model: Any, app_model: Any, 
                                    final_activities: List[Tuple[str, str]], 
                                    start_flow_info: Dict[str, Any]) -> Dict[str, Tuple[str, str, str]]:
    """Crea gateway intermedi nel modello BPMN."""
    forced_flows = {}
    start_gateways = []
    num_final_activities = len(final_activities)
    
    for i, (activity_type, activity_name) in enumerate(final_activities):
        # Trova flusso da modificare nell'app model
        target_flow = self._find_target_flow_for_activity(app_model, activity_name, activity_type)
        
        if target_flow:
            # Trova flusso corrispondente nel modello principale
            flow_to_modify = self._find_corresponding_flow(model, target_flow)
            
            if flow_to_modify:
                print(f"DEBUG: Processing activity '{activity_name}' (type: {activity_type})")
                print(f"DEBUG: flow_to_modify ID: {flow_to_modify.get_id()}")
                # Crea gateway intermedio
                gateway_info = self._create_gateway_for_activity(
                    model, flow_to_modify, activity_type, i
                )
                
                # Crea gateway di start
                start_gateway_info = self._create_start_gateway(
                    model, gateway_info, i, start_gateways, 
                    start_flow_info, num_final_activities
                )
                
                # Registra flusso forzato
                flow_id = start_gateway_info['intermediate_flow'].get_id()
                forced_flows[flow_id] = (activity_type, start_gateway_info['gateway'].get_id(), activity_name)
                
                start_gateways.append(start_gateway_info['gateway'])
    
    # Rimuovi flusso di start originale
    if start_flow_info['flow_to_delete']:
        flow_to_delete_id = start_flow_info['flow_to_delete'].get_id()
        print(f"DEBUG: Tentativo di rimuovere flow_to_delete con ID: {flow_to_delete_id}")
        # Verifica se il flusso esiste ancora nel modello
        flow_exists = any(f.get_id() == flow_to_delete_id for f in model.get_flows())
        print(f"DEBUG: Il flusso esiste ancora nel modello? {flow_exists}")
        if flow_exists:
            model.remove_flow(start_flow_info['flow_to_delete'])
            print(f"DEBUG: Flow di start rimosso con successo")
        else:
            print(f"DEBUG: Flow già rimosso, skip")
    
    return forced_flows

def prepare_final_activities_list(self, interrupted_activities: pd.DataFrame, 
                                    completed_activities: pd.DataFrame) -> List[Tuple[str, str]]:
    """Prepara lista delle attività finali con il loro stato."""
    final_activities = []
    
    if not interrupted_activities.empty:
        interrupted_tasks = [('interrupted', task) for task in interrupted_activities['task'].unique()]
        final_activities.extend(interrupted_tasks)
    
    if not completed_activities.empty:
        completed_tasks = [('ended', task) for task in completed_activities['task'].unique()]
        final_activities.extend(completed_tasks)
    
    return final_activities

def create_modified_bpmn_model(self, interrupted_activities: pd.DataFrame, 
                                  completed_activities: pd.DataFrame) -> Dict[str, Tuple[str, str, str]]:
    """
    Crea un modello BPMN modificato con gateway intermedi.
    
    Args:
        interrupted_activities: DataFrame delle attività interrotte
        completed_activities: DataFrame delle attività completate
        
    Returns:
        Dizionario dei flussi forzati per stati intermedi
    """
    print("Creando modello BPMN modificato con gateway intermedi...")
    
    try:
        # Carica modello base
        base_model_path = os.path.join(self.path, 'output_data', 'output_file', self.model_name)
        app_model = pm4py.read_bpmn(base_model_path)
        
        # Copia modello per modifiche
        model = self.model_bpmn
        
        # Identifica attività di start
        start_activity = self._identify_start_activity()
        start_flow_info = self._find_start_flow_info(app_model, model, start_activity)
        
        # Prepara lista attività finali
        final_activities = self._prepare_final_activities_list(interrupted_activities, completed_activities)
        
        # Crea gateway e flussi intermedi
        forced_flows = self._create_intermediate_gateways(
            model, app_model, final_activities, start_flow_info
        )
        
        # Salva modello modificato
        self._save_modified_model(model)
        
        print(f"✓ Modello BPMN modificato creato con {len(forced_flows)} stati intermedi")
        return forced_flows
        
    except Exception as e:
        raise Exception(f"Errore nella creazione del modello BPMN modificato: {str(e)}")
