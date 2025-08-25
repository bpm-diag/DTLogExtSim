import os

def save_results(self) -> str:
    """
    Salva i risultati su file.
    
    Returns:
        Percorso del file salvato
    """
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'instancetypes{self.name}.txt')
        
        with open(file_path, 'w') as file:
            file.write("Instance Types\n")
            file.write(f"{self._instance_types.to_dict()}\n")
            
            if self._num_types_instance > 1 and self._forced_instance_types:
                file.write("\nForced Instance Types Gateway\n")
                file.write(f"{self._forced_instance_types}")
        
        print(f"✓ Risultati salvati: {file_path}")
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio dei risultati: {str(e)}")