from collections import Counter
from typing import Dict, Tuple, Any

def calculate_gateway_instance_types(self, results: Dict[Tuple[str, str], Counter]) -> Dict[Any, Counter]:
        """
        Calcola i tipi di istanza per ogni gateway.
        
        Args:
            results: Risultati delle esecuzioni per coppia
            
        Returns:
            Dizionario gateway -> Counter dei tipi di istanza
        """
        try:
            gateway_type_instances = {}
            
            for node, details in self.branches.items():
                total_counter = Counter()
                
                for source in details["source"]:
                    for destination in details["destination"]:
                        pair = (source, destination)
                        if pair in results:
                            total_counter.update(results[pair])
                
                gateway_type_instances[node] = total_counter
            
            print(f"✓ Calcolati tipi istanza per {len(gateway_type_instances)} gateway")
            return gateway_type_instances
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo dei tipi istanza per gateway: {str(e)}")
    