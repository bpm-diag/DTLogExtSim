import pandas as pd
import numpy as np
from typing import List
import os

def extract_duration_distribution(self, processed_log: pd.DataFrame) -> List[List]:
        """
        Estrae le distribuzioni di durata delle attività.
        
        Args:
            processed_log: Log preprocessato e riordinato
            
        Returns:
            Lista di distribuzioni [attività, tipo_distribuzione, parametri]
        """
        print("Calcolando distribuzioni di durata delle attività...")
        
        try:
            activity_durations = {}
            
            # Raccolta durate per attività
            for _, row in processed_log.iterrows():
                task = row['task']
                if task not in activity_durations:
                    activity_durations[task] = []
                
                # Calcola durata
                if 'end_timestamp' in row and 'start_timestamp' in row:
                    if pd.notna(row['end_timestamp']) and pd.notna(row['start_timestamp']):
                        duration = row['end_timestamp'] - row['start_timestamp']
                        duration_seconds = float(duration.total_seconds())
                        
                        if not np.isnan(duration_seconds) and duration_seconds > 0:
                            # Evita durate zero per problemi di calcolo distribuzione
                            if duration_seconds == 0:
                                duration_seconds = 0.00001
                            activity_durations[task].append(duration_seconds)
            
            # Calcolo distribuzioni
            activity_distributions = []
            for activity, durations in activity_durations.items():
                if durations:  # Solo se ci sono durate valide
                    cleaned_durations = self._clean_outliers(durations)
                    distribution = self._fit_distribution(cleaned_durations)
                    activity_distributions.append([activity, distribution[0], distribution[1]])
            
            # Aggiungi eventi abort se presenti
            if self._abort_events:
                for abort_event in self._abort_events:
                    activity_distributions.append([
                        abort_event, 
                        'fixed', 
                        {'mean': 1.0, 'arg1': 0, 'arg2': 0}
                    ])
            
            print(f"✓ Distribuzioni durata calcolate per {len(activity_distributions)} attività")
            return activity_distributions
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo delle distribuzioni di durata: {str(e)}")
        

def save_duration_distributions(self, duration_distributions: List[List]) -> str:
        """
        Salva le distribuzioni di durata su file.
        
        Args:
            duration_distributions: Lista delle distribuzioni di durata
            
        Returns:
            Percorso del file salvato
        """
        try:
            output_dir = os.path.join(self.path, 'output_data', 'output_file')
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, f'activity_distr_{self.name}.txt')
            
            with open(file_path, 'w') as file:
                for distribution in duration_distributions:
                    file.write(f"{distribution}\n")
            
            print(f"✓ Distribuzioni durata salvate: {file_path}")
            return file_path
            
        except Exception as e:
            raise Exception(f"Errore nel salvataggio distribuzioni durata: {str(e)}")