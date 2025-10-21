import pandas as pd
import numpy as np
from typing import List
import os
import json

def extract_waiting_distribution(self, processed_log: pd.DataFrame) -> List[List]:
        """
        Estrae le distribuzioni di tempo di attesa delle attività.
        
        Args:
            processed_log: Log preprocessato e riordinato
            
        Returns:
            Lista di distribuzioni [attività, tipo_distribuzione, parametri]
        """
        print("Calcolando distribuzioni di tempo di attesa...")
        
        if self.num_timestamp != 3:
            raise ValueError("Tempo di attesa disponibile solo con 3 timestamp (assign, start, complete)")
        
        try:
            activity_waiting_times = {}
            
            # Raccolta tempi di attesa per attività
            for _, row in processed_log.iterrows():
                task = row['task']
                if task not in activity_waiting_times:
                    activity_waiting_times[task] = []
                
                # Calcola tempo di attesa (start - assign)
                if ('start_timestamp' in row and 'assign_timestamp' in row and
                    pd.notna(row['start_timestamp']) and pd.notna(row['assign_timestamp'])):
                    
                    waiting_time = row['start_timestamp'] - row['assign_timestamp']
                    waiting_seconds = float(waiting_time.total_seconds())
                    
                    if not np.isnan(waiting_seconds) and waiting_seconds > 0:
                        # Evita tempi zero per problemi di calcolo distribuzione
                        if waiting_seconds == 0:
                            waiting_seconds = 0.00001
                        activity_waiting_times[task].append(waiting_seconds)
            
            # Calcolo distribuzioni
            waiting_distributions = []
            for activity, waiting_times in activity_waiting_times.items():
                if waiting_times:  # Solo se ci sono tempi validi
                    cleaned_waiting_times = self._clean_outliers(waiting_times)
                    distribution = self._fit_distribution(cleaned_waiting_times)
                    waiting_distributions.append([activity, distribution[0], distribution[1]])
            
            print(f"✓ Distribuzioni tempo di attesa calcolate per {len(waiting_distributions)} attività")
            return waiting_distributions
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo delle distribuzioni di attesa: {str(e)}")
        

def save_waiting_distributions(self, waiting_distributions: List[List]) -> str:
        """
        Salva le distribuzioni di tempo di attesa su file.
        
        Args:
            waiting_distributions: Lista delle distribuzioni di tempo di attesa
            
        Returns:
            Percorso del file salvato
        """
        try:
            output_dir = os.path.join(self.path, 'output_data', 'output_file')
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, f'act_distr_wait_time_{self.name}.json')
            dict = {}
            for d in waiting_distributions:
                dict[d[0]] = d
            
            with open(file_path, 'w') as file:
                json.dump(dict, file)
            
            print(f"✓ Distribuzioni tempo di attesa salvate: {file_path}")
            return file_path
            
        except Exception as e:
            raise Exception(f"Errore nel salvataggio distribuzioni attesa: {str(e)}")
    