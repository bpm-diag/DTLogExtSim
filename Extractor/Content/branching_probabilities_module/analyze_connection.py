import pm4py
from typing import Dict, Any, Tuple


def normalize_gateway_flows(self, gateway_flows: Dict) -> Dict:
    """Normalizza i nomi delle attività nei flussi gateway."""
    for gateway in gateway_flows:
        for i, (flow_id, activity) in enumerate(gateway_flows[gateway]):
            gateway_flows[gateway][i] = [flow_id, activity if isinstance(activity, str) else self._safe_get_name(activity)]
    
    return gateway_flows

def analyze_gateway_connections(self, exclusive_gateways: Dict[int, Any]) -> Tuple[Dict, Dict, Dict]:
        """
        Analizza le connessioni dei gateway (input/output) e i flussi.
        
        Args:
            exclusive_gateways: Dizionario dei gateway da analizzare
            
        Returns:
            Tupla (out_tasks, in_tasks, gateway_flows)
        """
        print("Analizzando connessioni dei gateway...")
        
        try:
            gateway_flows = {}
            gateway_path_succ = {}
            gateway_path_prec = {}
            gateway_node_targets = []
            gateway_node_sources = []
            
            # Analisi connessioni per ogni gateway
            for gateway in exclusive_gateways.values():
                gateway_path_succ[gateway] = []
                gateway_path_prec[gateway] = []
                gateway_flows[gateway] = []
                
                # Analizza flussi in entrata e uscita
                for flow in self.bpmn_model.get_flows():
                    if flow.get_source() == gateway:
                        # Flusso in uscita dal gateway
                        gateway_path_succ[gateway].append(flow.get_target())
                        gateway_flows[gateway].append((flow.get_id(), flow.get_target()))
                        
                        if isinstance(flow.get_target(), pm4py.BPMN.Gateway):
                            gateway_node_targets.append(flow.get_target())
                            
                    elif flow.get_target() == gateway:
                        # Flusso in entrata al gateway
                        gateway_path_prec[gateway].append(flow.get_source())
                        gateway_flows[gateway].append((flow.get_id(), flow.get_source()))
                        
                        if isinstance(flow.get_source(), pm4py.BPMN.Gateway):
                            gateway_node_sources.append(flow.get_source())
            
            # Risolvi gateway annidati per target
            if gateway_node_targets:
                gateway_path_succ, gateway_flows = self._resolve_target_gateways(
                    gateway_path_succ, gateway_flows, gateway_node_targets
                )
            
            # Risolvi gateway annidati per source
            if gateway_node_sources:
                gateway_path_prec, gateway_flows = self._resolve_source_gateways(
                    gateway_path_prec, gateway_flows, gateway_node_sources
                )
            
            # Normalizza nomi attività nei flussi
            # if len(gateway_node_sources) == 0 and len(gateway_node_targets) == 0:
            gateway_flows = self._normalize_gateway_flows(gateway_flows)
            
            print(f"✓ Analizzate connessioni per {len(exclusive_gateways)} gateway")
            return gateway_path_succ, gateway_path_prec, gateway_flows
            
        except Exception as e:
            raise Exception(f"Errore nell'analisi delle connessioni dei gateway: {str(e)}")
    