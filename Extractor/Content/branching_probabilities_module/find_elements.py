import pm4py
from typing import List, Any

def find_successor_tasks(self, node: Any) -> List[Any]:
    """
    Trova ricorsivamente i task successori di un nodo.
    
    Args:
        node: Nodo da cui iniziare la ricerca
        
    Returns:
        Lista dei task successori
    """
    try:
        if isinstance(node, pm4py.BPMN.Task):
            return [node]
        
        tasks_list = []
        for flow in self.bpmn_model.get_flows():
            if flow.get_source() == node:
                tasks_list.append(self._find_successor_tasks(flow.get_target()))
        
        return tasks_list
        
    except Exception as e:
        print(f"Errore in _find_successor_tasks: {e}")
        return []
    
def find_predecessor_tasks(self, node: Any) -> List[Any]:
    """
    Trova ricorsivamente i task predecessori di un nodo.
    
    Args:
        node: Nodo da cui iniziare la ricerca
        
    Returns:
        Lista dei task predecessori
    """
    try:
        if isinstance(node, pm4py.BPMN.Task):
            return [node]
        
        tasks_list = []
        for flow in self.bpmn_model.get_flows():
            if flow.get_target() == node:
                tasks_list.append(self._find_predecessor_tasks(flow.get_source()))
        
        return tasks_list
        
    except Exception as e:
        print(f"Errore in _find_predecessor_tasks: {e}")
        return []