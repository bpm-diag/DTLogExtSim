import os
import pandas as pd
from typing import Dict, List

def save_group_cost_hour(self, group_cost_hour: Dict[str, float]) -> str:
    """Salva costi orari per gruppo."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'res_cost_{self.name}.txt')
        
        with open(file_path, 'w') as file:
            file.write(f'{group_cost_hour}')
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio costi orari: {str(e)}")

def save_fixed_activity_cost(self, fixed_act_costs: pd.Series) -> str:
    """Salva costi fissi per attività."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'fixed_act_cost_{self.name}.txt')
        
        with open(file_path, 'w') as file:
            file.write(f'{fixed_act_costs.to_dict()}')
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio costi fissi: {str(e)}")

def save_setup_time_params(self, duration_distr: List, max_usage: List) -> str:
    """Salva parametri setup time."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'setup_time_params_{self.name}.txt')
        
        with open(file_path, 'w') as file:
            file.write('Setup Time Duration Distribution: \n')
            file.write(f'{duration_distr}\n')
            file.write('\nMax Usage before setup time is needed:\n')
            file.write(f'{max_usage}\n')
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio setup time: {str(e)}")