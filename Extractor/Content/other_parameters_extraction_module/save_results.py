import os
import pandas as pd
from typing import Dict, List
import json

def save_group_cost_hour(self, group_cost_hour: Dict[str, float]) -> str:
    """Salva costi orari per gruppo."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'res_cost_{self.name}.json')
        
        with open(file_path, 'w') as file:
            json.dump(group_cost_hour, file, indent=4)
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio costi orari: {str(e)}")

def save_fixed_activity_cost(self, fixed_act_costs: pd.Series) -> str:
    """Salva costi fissi per attività."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'fixed_act_cost_{self.name}.json')
        
        with open(file_path, 'w') as file:
            json.dump(fixed_act_costs.to_dict(), file, indent=4)
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio costi fissi: {str(e)}")

def save_setup_time_params(self, duration_distr: List, max_usage: List) -> str:
    """Salva parametri setup time."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'setup_time_params_{self.name}.json')


        final_duration_distr = []
        for i in duration_distr:
            temp = []
            temp.append(i[0])
            temp.append(i[1])
            i[2]["mean"] = int(i[2]["mean"])
            i[2]["arg1"] = int(i[2]["arg1"])
            i[2]["arg2"] = int(i[2]["arg2"])
            temp.append(i[2])
            temp.append(i[3])
            final_duration_distr.append(temp)
            
        final_max_usage = []
        for i in max_usage:
            temp = []
            temp.append(i[0])
            temp.append(int(i[1]))
            final_max_usage.append(temp)
        
        with open(file_path, 'w') as file:
            json.dump({
                'duration_distr': final_duration_distr,
                'max_usage': final_max_usage
            }, file, indent=4)
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio setup time: {str(e)}")