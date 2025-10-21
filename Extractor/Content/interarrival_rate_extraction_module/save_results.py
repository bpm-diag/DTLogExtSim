import os
import json
from typing import Dict, Tuple

def save_results(self, distribution_params: Tuple[str, Dict[str, float]]) -> str:
        """
        Salva i risultati della distribuzione su file.
        
        Args:
            distribution_params: Tupla (distribuzione, parametri)
            
        Returns:
            Percorso del file salvato
        """
        try:
            output_dir = os.path.join(self.path, 'output_data', 'output_file')
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, f'interarrival{self.name}.json')
            
            with open(file_path, 'w') as file:
                json.dump(distribution_params, file, indent=4)
            
            print(f"✓ Risultati salvati: {file_path}")
            return file_path
            
        except Exception as e:
            raise Exception(f"Errore nel salvataggio dei risultati: {str(e)}")