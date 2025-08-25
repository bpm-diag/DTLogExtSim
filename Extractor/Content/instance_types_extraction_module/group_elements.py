from typing import Dict, Any, Tuple, Optional, List

def group_forced_types_by_gateway(self, forced_instance_types: Dict[Tuple[str, str], Optional[str]],
                                    node_mapping: Dict[Tuple[str, str], Any]) -> Dict[Any, List[Tuple[Tuple[str, str], Optional[str]]]]:
        """
        Raggruppa i tipi forzati per gateway.
        
        Args:
            forced_instance_types: Tipi forzati per coppia
            node_mapping: Mapping coppia -> gateway
            
        Returns:
            Dizionario gateway -> lista (coppia, tipo_forzato)
        """
        try:
            gateway_forced_instance_types = {}
            
            for pair, instance_type in forced_instance_types.items():
                node = node_mapping.get(pair)
                if node:
                    if node not in gateway_forced_instance_types:
                        gateway_forced_instance_types[node] = []
                    gateway_forced_instance_types[node].append((pair, instance_type))
            
            print(f"✓ Raggruppati tipi forzati per {len(gateway_forced_instance_types)} gateway")
            return gateway_forced_instance_types
            
        except Exception as e:
            raise Exception(f"Errore nel raggruppamento per gateway: {str(e)}")