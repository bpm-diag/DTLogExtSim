import os
from typing import Dict, List, Any, Tuple
import json

def save_group_schedule(self, group_schedule: Dict, roles: List[Dict[str, Any]]) -> str:
        """Salva schedule dei gruppi su file."""
        try:
            output_dir = os.path.join(self.path, 'output_data', 'output_file')
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, f'groups_{self.name}.json')

            final_group_schedule = {}
            for group, days in group_schedule.items():
                final_group_schedule[group] = {}
                role_info = next((role for role in roles if role['group'] == group), None)
                if role_info:
                    members = role_info['members']
                    final_group_schedule[group]['num_resources'] = len(members)
                    final_group_schedule[group]['members'] = members
                    for day, times in days.items():
                        sorted_times = sorted(list(times))
                        final_group_schedule[group][day] = sorted_times
            
            with open(file_path, 'w') as file:
                json.dump(final_group_schedule, file, indent=4)
            
            return file_path
            
        except Exception as e:
            raise Exception(f"Errore nel salvataggio schedule gruppi: {str(e)}")
    
def save_timetables(self, timetables: Dict[str, Dict[str, str]]) -> str:
    """Salva timetables su file."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'timetables_{self.name}.json')
        
        final_timetables = {}
        for timetable, schedule in timetables.items():
            final_timetables[timetable] = {}
            for day, interval_str in schedule.items():
                final_timetables[timetable][day] = interval_str

        with open(file_path, 'w') as file:
            json.dump(final_timetables, file, indent=4)

        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio timetables: {str(e)}")

def save_worklists(self, worklists: List[Tuple[str, str]]) -> str:
    """Salva worklist su file."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'worklist_{self.name}.json')

        final_worklist = {}
        for i, (task1, task2) in enumerate(worklists, start=1):
            final_worklist[i] = [task1, task2]

        with open(file_path, 'w') as file:
            json.dump(final_worklist, file, indent=4)
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio worklist: {str(e)}")

def save_resources_of_activities(self, group_act: Dict[str, List[List[str]]]) -> str:
    """Salva associazioni gruppi-attività su file."""
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'resources_of_activities_{self.name}.json')

        final_group_act = {}
        for activity, groups in group_act.items():
            final_group_act[str(activity)] = groups
        
        with open(file_path, 'w') as file:
            json.dump(final_group_act, file, indent=4)
        
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio risorse attività: {str(e)}")