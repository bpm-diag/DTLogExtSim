import os
import json

def save_results(self) -> str:
    """
    Salva i risultati su file.
    
    Returns:
        Percorso del file salvato
    """
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path_instance_types = os.path.join(output_dir, f'instancetypes{self.name}.json')
        
        with open(file_path_instance_types, 'w') as file:
            json.dump(self._instance_types.to_dict(), file, indent=4)
        
        if self._num_types_instance > 1 and self._forced_instance_types:
            file_path_forced_instance_types = os.path.join(output_dir, f'forcedinstancetypes{self.name}.json')
            
            for node, list_of_pairs in self._forced_instance_types.copy().items():
                list_temp = []
                for pair in list_of_pairs:
                    list_temp.append([[pair[0][0], pair[0][1]], pair[1]])
                
                self._forced_instance_types.pop(node)
                self._forced_instance_types[str(node)] = list_temp
            
            with open(file_path_forced_instance_types, 'w') as file:
                json.dump(self._forced_instance_types, file, indent=4)
        
        print(f"✓ Risultati salvati: {file_path_instance_types}")
        return file_path_instance_types
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio dei risultati: {str(e)}")