import pm4py
import pandas as pd
from pandas import DataFrame
import networkx as nx
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from scipy.stats import pearsonr
from operator import itemgetter

from timetables_extraction import TimeTablesCalculation as ttcalc
from worklist_res_extraction import WorklistCalculation as wlcalc

tag_to_identify_resources = 'org:resource' 
tag_to_identify_activities = 'concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_node_lifecycle = 'lifecycle:transition'
#tag added by me
tag_to_identify_moment_of_day = 'moment_of_day'
tag_to_identify_group = 'group'

class ResourceParameterCalculation():

    def __init__(self, log, settings):
        self._log = log.copy()
        self._settings = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        self._sim_threshold = settings[0]['sim_threshold']

        self._log = self._log[self._log[tag_to_identify_node_lifecycle].isin(['assign', 'start', 'complete'])].reset_index(drop=True)

        self._activities = self.extract_activities(self._log)
        self._resources = self.extract_resources(self._log)
        self._res_act = self.extract_res_act(self._log, self._activities)
        self._act_res = self.extract_act_res(self._log, self._resources)

        self._roles, self._roles_tables = self.extract_roles(self._log)
        self._group_schedule = self.roles_time_division(self._log, self._roles)
        self.save_on_file_group_schedule(self._group_schedule, self._roles)

        self._res_groups = {item['group']: item['members'] for item in self._roles}
        self._log[tag_to_identify_group] = self._log[tag_to_identify_resources].apply(self.group_assign)
        self._working_timetables = self.timetables_compute(self._log, self._res_groups)
        self.save_on_file_timetables(self._working_timetables)

        self._group_act = self.extract_group_act(self._log, self._activities)
        self.save_on_file_res_of_activities(self._group_act)

        self._worklist = self.worklist_compute(self._log, self._res_groups, self._activities, self._res_act)
        self.save_on_file_worklists(self._worklist)
    
    def extract_activities(self, log):
        explode_activities = log[tag_to_identify_activities].explode()
        unique_activities = explode_activities.drop_duplicates()
        unique_activities = unique_activities[unique_activities.notna()]
        model_activities = unique_activities.tolist()
        num_of_activities = len(model_activities)
        print("Number of activities: ", num_of_activities)
        return model_activities

    def extract_resources(self, log):
        exploded_resources = log[tag_to_identify_resources].explode()
        unique_resources = exploded_resources.drop_duplicates()
        unique_resources = unique_resources[unique_resources.notna()]
        model_resources = unique_resources.tolist()
        num_of_resources = len(model_resources)
        print("Number of resources: ", num_of_resources)
        return model_resources
    
    def extract_group_act(self, log, model_activities): #for each activity the groups that perform it
        groups_by_act = {}
        for act in model_activities:
            filtered_log = log[log[tag_to_identify_activities] == act]
            filter_log = filtered_log[tag_to_identify_group]
            unique_lists = [list(item) for item in set(tuple(sublist) for sublist in filter_log)]
            unique_lists =  [sublist for sublist in unique_lists if sublist and not any(pd.isna(x) for x in sublist)]
            if unique_lists: 
                groups_by_act[act] = unique_lists
        return groups_by_act
    
    def extract_res_act(self, log, model_activities): #for each activity the resources that perform it
        resources_by_act = {}
        for act in model_activities:
            filtered_log = log[log[tag_to_identify_activities] == act]
            filter_log = filtered_log[tag_to_identify_resources]
            unique_lists = [list(item) for item in set(tuple(sublist) for sublist in filter_log)]
            unique_lists =  [sublist for sublist in unique_lists if sublist and not any(pd.isna(x) for x in sublist)]
            if unique_lists: 
                resources_by_act[act] = unique_lists
        return resources_by_act
    
    def extract_act_res(self, log, model_resources): #for each resources the activities that perform
        activities_by_res = {}
        for res in model_resources:
            filtered_log = log[log[tag_to_identify_resources].apply(lambda resources: res in resources)]
            activities = filtered_log[tag_to_identify_activities].drop_duplicates().tolist()
            activities_by_res[res] = activities
        return activities_by_res

    def group_assign(self, res_list):
        groups = list()
        for res in res_list:
            for g, r in self._res_groups.items():
                if res in r:
                    groups.append(g)
        return list(groups)
    
    def extract_roles(self, log):
        co_matrix = self.correlation_matrix(log)

        g = nx.Graph()
        for user in self._resources:
            g.add_node(user)
        for rel in co_matrix:
            if rel['distance'] > self._sim_threshold and rel['x'] != rel['y']:
                g.add_edge(rel['x'],
                            rel['y'],
                            weight=rel['distance'])

        sub_graphs = list((g.subgraph(c) for c in nx.connected_components(g)))
        roles, roles_table = self.role_definition(sub_graphs)
        return roles, roles_table

    def correlation_matrix(self, log):

        def part_of_day(timestamp):
            hour = timestamp.hour
            if 5 <= hour < 12:
                return 'Morning'
            elif 12 <= hour < 17:
                return 'Afternoon'
            elif 17 <= hour < 21:
                return 'Evening'
            else:
                return 'Night'

        log[tag_to_identify_moment_of_day] = log[tag_to_identify_timestamp].apply(part_of_day)

        res_knowledge_dict = defaultdict(lambda: defaultdict(int))
        
        for _, event in log.iterrows():
            activity = event[tag_to_identify_activities]
            moment_of_day = event[tag_to_identify_moment_of_day]
            resource_list = event[tag_to_identify_resources]
            if not pd.isna(resource_list[0]):
                for res in resource_list:
                    pair = (activity, moment_of_day)
                    res_knowledge_dict[res][pair] += 1

        df = DataFrame.from_dict(res_knowledge_dict, orient='index').fillna(0)
        co_matrix = self.det_correl_matrix(df)
        return co_matrix
    
    def role_definition(self, sub_graphs):
        records= list()
        for i in range(0, len(sub_graphs)):
            users_names = [resource for resource in self._resources if resource in sub_graphs[i]]
            records.append({'group': 'Group'+ str(i + 1),
                            'quantity': len(sub_graphs[i]),
                            'members': users_names})
        #Sort roles by number of resources
        records = sorted(records, key=itemgetter('quantity'), reverse=True)
        for i in range(0,len(records)):
            records[i]['group']='Group'+ str(i + 1)
        resource_table = list()
        for record in records:
            for member in record['members']:
                resource_table.append({'group': record['group'],
                                        'resource': member})
        return records, resource_table
    
    def det_correl_matrix(self, profiles):
        correl_matrix = list()
        for user_id_x, row_x in profiles.iterrows():
            for user_id_y, row_y in profiles.iterrows():
                x = np.array(row_x.values)
                x_int = x.astype(int)
                y = np.array(row_y.values)
                y_int = y.astype(int)

                r_row, p_value = pearsonr(x_int, y_int)
                correl_matrix.append(({'x': user_id_x,
                                            'y': user_id_y,
                                            'distance': r_row}))
        return correl_matrix
    
    def roles_time_division(self, log, roles):
        group_schedule = defaultdict(lambda: defaultdict(set))

        for index, row in log.iterrows():
            resource_list = row[tag_to_identify_resources]
            timestamp = row['time:timestamp']
            if not pd.isna(resource_list[0]):
                for role in roles:
                    if any(resource in role['members'] for resource in resource_list):
                        day_of_week = self.get_day_of_week(timestamp)

                        rounded_time = self.round_time_to_half_hour(timestamp)
                        rounded_time_str = rounded_time.strftime('%H:%M')
                        
                        group_schedule[role['group']][day_of_week].add(rounded_time_str)
        return group_schedule
    
    def get_day_of_week(self, timestamp):
        day_of_week = timestamp.weekday()  # 0=monday, 1=tuesday, ..., 6=sunday
        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        return days_of_week[day_of_week]

    def round_time_to_half_hour(self, timestamp): #approximating by defect
        if timestamp.minute >= 0 and timestamp.minute < 5:
            rounded_minute = 0
        elif timestamp.minute >= 5 and timestamp.minute < 10:
            rounded_minute = 5
        elif timestamp.minute >= 10 and timestamp.minute < 15:
            rounded_minute = 10
        elif timestamp.minute >= 15 and timestamp.minute < 20:
            rounded_minute = 15
        elif timestamp.minute >= 20 and timestamp.minute < 25:
            rounded_minute = 20
        elif timestamp.minute >= 25 and timestamp.minute < 30:
            rounded_minute = 25
        elif timestamp.minute >= 30 and timestamp.minute < 35:
            rounded_minute = 30
        elif timestamp.minute >= 35 and timestamp.minute < 40:
            rounded_minute = 35
        elif timestamp.minute >= 40 and timestamp.minute < 45:
            rounded_minute = 40
        elif timestamp.minute >= 45 and timestamp.minute < 50:
            rounded_minute = 45
        elif timestamp.minute >= 50 and timestamp.minute < 55:
            rounded_minute = 50
        else:
            rounded_minute = 55
        
        return timestamp.replace(minute=rounded_minute, second=0, microsecond=0)
    
    def save_on_file_group_schedule(self, group_schedule, roles):
        with open(self._path + 'output_data/output_file/groups_' + self._name + '.txt', 'w') as file:
            for group, days in group_schedule.items():
                role_info = next((role for role in roles if role['group'] == group), None)
                if role_info:  
                    members = role_info['members']
                    file.write(f"GROUP {group} (# of resources = {len(members)}) {members}:\n")
                    for day, times in days.items():
                        sorted_times = sorted(list(times))
                        file.write(f"   {day}: {sorted_times}\n")

    def timetables_compute(self, log, res_groups):
        TimeTables = ttcalc(log, self._settings, res_groups, self._group_schedule)
        self._group_timetables_association = TimeTables._timetables_def
        print(self._group_timetables_association)
        app_timetables = TimeTables.compute_timetables()
       
        timetables = {}
        for timetable, schedule in app_timetables.items():
            timetables[timetable] = {}
            for day, intervals in schedule.items():
                interval_str = ', '.join([
                    f"{min(interval).strftime('%H:%M')} - {((datetime.combine(datetime.today(), max(interval)) + timedelta(minutes=5)).time().strftime('%H:%M') if (datetime.combine(datetime.today(), max(interval)) + timedelta(minutes=5)).time() != datetime.strptime('00:00', '%H:%M').time() else '23:59')}"
                    for interval in intervals
                ])
                timetables[timetable][day.capitalize()] = interval_str

        return timetables
    
    def save_on_file_timetables(self, timetables):
        with open(self._path + 'output_data/output_file/timetables_' + self._name + '.txt', 'w') as file:
            for timetable, schedule in timetables.items():
                file.write(f"Timetable: {timetable}\n")
                for day, interval_str in schedule.items():
                    file.write(f"  {day}: {interval_str}\n")

    def worklist_compute(self, log, res_group, model_activities, res_act):
        Worklist = wlcalc(log, self._settings, res_group, model_activities, res_act)
        worklist = Worklist.compute_worklist_with_intr_value()

        return worklist

    def save_on_file_worklists(self, worklists):
        with open(self._path + 'output_data/output_file/worklist_' + self._name + '.txt', 'w') as file:
            for i, (task1, task2) in enumerate(worklists, start=1):
                file.write(f"Worklist {i}: ({task1}, {task2})\n")

    def save_on_file_res_of_activities(self, res_act):
        with open(self._path + 'output_data/output_file/resources_of_activities_' + self._name + '.txt', 'w') as file:
            for act, groups in res_act.items():
                file.write(f"{act}: {groups}\n")