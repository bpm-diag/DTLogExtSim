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
    try:
        return [elem.get_name() if elem.get_name() != "" else "event" for elem in task_list]
    except Exception as e:
        raise Exception(f"Errore nell'estrazione dei task: {str(e)}")

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
                        source = list()
                        destination = list()
                        
                        for prob_info in branch_probabilities[node]:
                            act1, act2 = prob_info['pair']
                            prob = float(prob_info['probability'])
                            
                            if act2 in activity_list:
                                source.append(act1)
                                destination.append(act2)
                                total_probability += prob
                        
                        result[node].append({
                            'flow': flow_id,
                            'total_probability': total_probability,
                            'source': source,
                            'destination': destination
                        })
            
            # Normalizza probabilità PER OGNI GATEWAY separatamente
            for node, flows in result.items():
                if not flows:
                    continue
                
                # Calcola somma totale (senza arrotondamenti)
                total = sum(flow['total_probability'] for flow in flows)
                
                # Usa tolleranza invece di confronto esatto
                if abs(total - 1.0) > 0.001:  # ← Tolleranza per errori float
                    print(f"⚠️ Gateway {node.get_id() if hasattr(node, 'get_id') else node}: somma probabilità = {total:.4f}")
                    
                    if total > 0:
                        # METODO 1: Normalizza proporzionalmente TUTTI i flussi
                        for flow in flows:
                            flow['total_probability'] = flow['total_probability'] / total
                        
                        print(f"   Normalizzate proporzionalmente → somma = 1.0")
                    else:
                        # Somma è 0 - distribuisci uniformemente
                        uniform_prob = 1.0 / len(flows)
                        for flow in flows:
                            flow['total_probability'] = uniform_prob
                        
                        print(f"   Distribuzione uniforme: {uniform_prob:.4f} per flusso")
                
                # ARROTONDA SOLO ALLA FINE, dopo normalizzazione
                for flow in flows:
                    flow['total_probability'] = round(flow['total_probability'], 2)
                
                # Verifica finale e correggi se necessario
                final_total = sum(flow['total_probability'] for flow in flows)
                
                if abs(final_total - 1.0) > 0.01:  # Dopo arrotondamento, tolleranza più alta
                    # Aggiusta il flusso con probabilità più alta (non il primo!)
                    max_flow = max(flows, key=lambda f: f['total_probability'])
                    difference = 1.0 - final_total
                    max_flow['total_probability'] = round(max_flow['total_probability'] + difference, 2)
                    
                    print(f"   Aggiustato flusso {max_flow['flow']}: +{difference:.2f}")
                
                # Log finale
                final_total = sum(flow['total_probability'] for flow in flows)
                print(f"✓ Gateway {node.get_id() if hasattr(node, 'get_id') else node}: somma finale = {final_total:.4f}")
            
            print(f"✓ Estratte probabilità di flusso per {len(result)} gateway")
            return result
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione delle probabilità di flusso: {str(e)}")
    