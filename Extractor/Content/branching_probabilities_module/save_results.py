import os
from typing import Dict
import json


def save_results(self, flow_probabilities: Dict) -> str:
    """
    Salva le probabilità di branching su file.
    
    Args:
        flow_probabilities: Probabilità di flusso da salvare
        
    Returns:
        Percorso del file salvato
    """
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        # Nome file basato su tipo di modello
        if self.intermediate_model:
            filename = f'branch_prob_{self.name}_interm_points.json'
        else:
            filename = f'branch_prob_{self.name}.json'
        
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w') as file:
            file.write(json.dumps(flow_probabilities, indent=4))
        
        print(f"✓ Probabilità di branching salvate: {file_path}")
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio delle probabilità: {str(e)}")