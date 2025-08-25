from typing import List, Tuple, Dict, Any

def create_pair_totals_mapping(self) -> Dict[Tuple[str, str], int]:
    """
    Crea mapping tra coppie e totali esecuzioni.
    
    Returns:
        Dizionario coppia -> totale esecuzioni
    """
    try:
        pair_tot = {}
        
        for node, details in self.branches.items():
            if node in self.tot_execute_per_branch:
                number = self.tot_execute_per_branch[node]
                
                for source in details["source"]:
                    for destination in details["destination"]:
                        pair_tot[(source, destination)] = number
        
        print(f"✓ Creato mapping totali per {len(pair_tot)} coppie")
        return pair_tot
        
    except Exception as e:
        raise Exception(f"Errore nella creazione del mapping totali: {str(e)}")
    
def create_pair_gateway_mapping(self, branches_pairs: List[Tuple[str, str]]) -> Dict[Tuple[str, str], Any]:
    """
    Crea mapping tra coppie e gateway associati.
    
    Args:
        branches_pairs: Lista delle coppie di branch
        
    Returns:
        Dizionario mapping coppia -> gateway
    """
    try:
        pair_gateway_associated = {}
        
        for node, details in self.branches.items():
            sources = details["source"]
            destinations = details["destination"]
            
            for pair in branches_pairs:
                source, destination = pair
                if source in sources and destination in destinations:
                    pair_gateway_associated[pair] = node
        
        print(f"✓ Creato mapping per {len(pair_gateway_associated)} coppie")
        return pair_gateway_associated
        
    except Exception as e:
        raise Exception(f"Errore nella creazione del mapping coppie-gateway: {str(e)}")
