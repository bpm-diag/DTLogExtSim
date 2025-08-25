from typing import List, Dict, Tuple, Any
from pandas.core.common import flatten

def nodes_match(self, activity: Any, node: Any) -> bool:
    """
    Verifica se un'attività corrisponde a un nodo.
    
    Args:
        activity: Attività da confrontare
        node: Nodo da confrontare
        
    Returns:
        True se corrispondono
    """
    try:
        # Normalizza entrambi gli oggetti
        activity_normalized = activity[0] if isinstance(activity, list) and activity else activity
        node_normalized = node[0] if isinstance(node, list) and node else node
        
        # Confronta direttamente se sono lo stesso oggetto
        if activity_normalized == node_normalized:
            return True
        
        # Confronta per nome se hanno il metodo get_name
        if (hasattr(activity_normalized, 'get_name') and 
            hasattr(node_normalized, 'get_name')):
            return activity_normalized.get_name() == node_normalized.get_name()
        
        # Confronta per ID se hanno il metodo get_id
        if (hasattr(activity_normalized, 'get_id') and 
            hasattr(node_normalized, 'get_id')):
            return activity_normalized.get_id() == node_normalized.get_id()
        
        return False
        
    except (IndexError, AttributeError):
        return False

def resolve_target_gateways(self, gateway_path_succ: Dict, gateway_flows: Dict, 
                               gateway_node_targets: List[Any]) -> Tuple[Dict, Dict]:
        """Risolve gateway annidati come target."""
        target_nodes = {}
        
        # Trova task successori per ogni gateway target
        for node in gateway_node_targets:
            successors = self._find_successor_tasks(node)
            target_nodes[node] = list(flatten(successors)) if successors else []
        
        # Processa ogni gateway
        for gateway in list(gateway_path_succ.keys()):
            if gateway not in gateway_path_succ:
                continue
                
            nodes_to_process = list(gateway_path_succ[gateway])
            
            for node in nodes_to_process:
                if node in target_nodes and target_nodes[node]:
                    # Rimuovi il gateway node
                    if node in gateway_path_succ[gateway]:
                        gateway_path_succ[gateway].remove(node)
                    
                    # Aggiorna gateway_flows - trova il flusso corrispondente
                    for i, (flow_id, activity) in enumerate(gateway_flows[gateway]):
                        if self._nodes_match(activity, node):
                            # Sostituisci con i task risolti
                            resolved_names = self._extract_task_names(target_nodes[node])
                            if resolved_names:
                                gateway_flows[gateway][i] = (flow_id, resolved_names[0] if len(resolved_names) == 1 else resolved_names)
                            else:
                                gateway_flows[gateway][i] = (flow_id, "event")
                    
                    # Aggiungi task risolti al path
                    for elem in target_nodes[node]:
                        if elem not in gateway_path_succ[gateway]:
                            gateway_path_succ[gateway].append(elem)
        
        return gateway_path_succ, gateway_flows
    
def resolve_source_gateways(self, gateway_path_prec: Dict, gateway_flows: Dict,
                            gateway_node_sources: List[Any]) -> Tuple[Dict, Dict]:
    """Risolve gateway annidati come source."""
    target_nodes = {}
    
    # Trova task predecessori per ogni gateway source
    for node in gateway_node_sources:
        predecessors = self._find_predecessor_tasks(node)
        target_nodes[node] = list(flatten(predecessors)) if predecessors else []
    
    # Processa ogni gateway
    for gateway in list(gateway_path_prec.keys()):
        if gateway not in gateway_path_prec:
            continue
            
        nodes_to_process = list(gateway_path_prec[gateway])
        
        for node in nodes_to_process:
            if node in target_nodes and target_nodes[node]:
                # Rimuovi il gateway node
                if node in gateway_path_prec[gateway]:
                    gateway_path_prec[gateway].remove(node)
                
                # Aggiorna gateway_flows - trova il flusso corrispondente
                for i, (flow_id, activity) in enumerate(gateway_flows[gateway]):
                    if self._nodes_match(activity, node):
                        # Sostituisci con i task risolti
                        resolved_names = self._extract_task_names(target_nodes[node])
                        if resolved_names:
                            gateway_flows[gateway][i] = (flow_id, resolved_names[0] if len(resolved_names) == 1 else resolved_names)
                        else:
                            gateway_flows[gateway][i] = (flow_id, "event")
                
                # Aggiungi task risolti al path
                for elem in target_nodes[node]:
                    if elem not in gateway_path_prec[gateway]:
                        gateway_path_prec[gateway].append(elem)
    
    return gateway_path_prec, gateway_flows