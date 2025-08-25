import pm4py
from typing import Dict, Any, List

def extract_diverging_gateways(self) -> Dict[int, Any]:
    """
    Estrae i gateway divergenti esclusivi dal modello BPMN.
    
    Returns:
        Dizionario dei gateway divergenti
    """
    print("Estraendo gateway divergenti...")
    
    try:
        exclusive_gateways = {}
        gateway_index = 0
        
        for node in self.bpmn_model.get_nodes():
            if isinstance(node, pm4py.BPMN.ExclusiveGateway):
                if node.get_gateway_direction() == pm4py.BPMN.Gateway.Direction.DIVERGING:
                    exclusive_gateways[gateway_index] = node
                    gateway_index += 1
        
        print(f"✓ Trovati {len(exclusive_gateways)} gateway divergenti")
        return exclusive_gateways
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione dei gateway divergenti: {str(e)}")
    
def safe_get_name(self, obj: Any) -> str:
    """
    Estrae il nome da un oggetto in modo sicuro.
    
    Args:
        obj: Oggetto da cui estrarre il nome
        
    Returns:
        Nome dell'oggetto o 'event' se non disponibile
    """
    if isinstance(obj, str):
        return obj
    elif isinstance(obj, list):
        # Se è una lista, prendi il primo elemento
        if obj:
            return self._safe_get_name(obj[0])
        else:
            return "event"
    elif hasattr(obj, 'get_name'):
        name = obj.get_name()
        return name if name != "" else "event"
    else:
        return "event"
    
def extract_task_names(self, task_list: List[Any]) -> List[str]:
    """
    Estrae i nomi dai task nella lista.
    
    Args:
        task_list: Lista di task
        
    Returns:
        Lista dei nomi delle attività
    """
    if not task_list:
        return []
        
    result = []
    for elem in task_list:
        try:
            if isinstance(elem, list):
                # Se è una lista, estrai ricorsivamente
                nested_names = self._extract_task_names(elem)
                result.extend(nested_names)
            elif hasattr(elem, 'get_name'):
                # Se ha il metodo get_name, usalo
                name = elem.get_name()
                result.append(name if name and name != "" else "event")
            elif isinstance(elem, str):
                # Se è già una stringa, usala direttamente
                result.append(elem if elem != "" else "event")
            else:
                # Fallback per altri tipi
                result.append("event")
        except (AttributeError, IndexError) as e:
            print(f"Errore nell'estrazione nome task: {e}")
            result.append("event")
            
    return result

def extract_flow_probabilities(self, branch_probabilities: Dict, gateway_flows: Dict) -> Dict[Any, List[Dict]]:
        """
        Estrae le probabilità di flusso per ogni gateway.
        
        Args:
            branch_probabilities: Probabilità dei branch
            gateway_flows: Flussi dei gateway
            
        Returns:
            Dizionario delle probabilità di flusso
        """
        print("Estraendo probabilità di flusso...")
        
        try:
            result = {}
            
            for node, flow_list in gateway_flows.items():
                result[node] = []
                
                for flow_id, activities in flow_list:
                    # Normalizza activities in lista
                    if isinstance(activities, list):
                        activity_list = activities
                    else:
                        activity_list = [activities]
                    
                    if node in branch_probabilities:
                        total_probability = 0.0
                        source = set()
                        destination = set()
                        
                        for prob_info in branch_probabilities[node]:
                            act1, act2 = prob_info['pair']
                            prob = float(prob_info['probability'])
                            
                            if act2 in activity_list:
                                source.add(act1)
                                destination.add(act2)
                                total_probability += prob
                        
                        result[node].append({
                            'flow': flow_id,
                            'total_probability': round(total_probability, 2),
                            'source': source,
                            'destination': destination
                        })
            
            # Normalizza probabilità (assicura che sommino a 1)
            for node, flows in result.items():
                total_probability = sum(flow['total_probability'] for flow in flows)
                if total_probability != 1 and flows:
                    difference = 1 - total_probability
                    flows[0]['total_probability'] = round(flows[0]['total_probability'] + difference, 2)
            
            print(f"✓ Estratte probabilità di flusso per {len(result)} gateway")
            return result
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione delle probabilità di flusso: {str(e)}")
    