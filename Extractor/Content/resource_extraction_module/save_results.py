import os
from typing import Dict, List, Any, Tuple

def save_group_schedule(self, group_schedule: Dict, roles: List[Dict[str, Any]]) -> str:
        """Salva schedule dei gruppi su file."""
        try:
            output_dir = os.path.join(self.path, 'output_data', 'output_file')
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, f'groups_{self.name}.txt')
            
            with open(file_path, 'w') as file:
                for group, days in group_schedule.items():
                    role_info = next((role for role in roles if role['group'] == group), None)
                    if role_info:
                        members = role_info['members']
                        file.write(f"GROUP {group} (# of resources = {len(members)}) {members}:\n")
                        for day, times in days.items():
                            sorted_times = sorted(list(times))
                            file.write(f"   {day}: {sorted_times}\n")
            
            return file_path
            
        except Exception as e:
            raise Exception(f"Errore nel salvataggio schedule gruppi: {str(e)}")
    
def save_timetables(self, timetables: Dict[str, Dict[str, str]]) -> str:
    """Salva timetables su file."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'timetables_{self.name}.txt')
        
        with open(file_path, 'w') as file:
            for timetable, schedule in timetables.items():
                file.write(f"Timetable: {timetable}\n")
                for day, interval_str in schedule.items():
                    file.write(f"  {day}: {interval_str}\n")
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio timetables: {str(e)}")

def save_worklists(self, worklists: List[Tuple[str, str]]) -> str:
    """Salva worklist su file."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'worklist_{self.name}.txt')
        
        with open(file_path, 'w') as file:
            for i, (task1, task2) in enumerate(worklists, start=1):
                file.write(f"Worklist {i}: ({task1}, {task2})\n")
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio worklist: {str(e)}")

def save_resources_of_activities(self, group_act: Dict[str, List[List[str]]]) -> str:
    """Salva associazioni gruppi-attività su file."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'resources_of_activities_{self.name}.txt')
        
        with open(file_path, 'w') as file:
            for activity, groups in group_act.items():
                file.write(f"{activity}: {groups}\n")
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio risorse attività: {str(e)}")