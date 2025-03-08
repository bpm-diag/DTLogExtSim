from pandas import DataFrame
import networkx as nx
from datetime import datetime, timedelta
from collections import defaultdict
import numpy as np
from sklearn.metrics import jaccard_score

tag_to_identify_resources = 'org:resource' 
tag_to_identify_activities = 'concept:name'
tag_to_identify_timestamp = 'time:timestamp'
#tag added by me
tag_to_identify_moment_of_day = 'moment_of_day'
tag_to_identify_time_slot = 'time_slot'
tag_to_identify_group = 'group'

class TimeTablesCalculation():

    def __init__(self, log, settings, res_group, group_schedule):
        self._log = log.copy()
        self._res_groups = res_group
        self._group_schedule = group_schedule
        self._settings = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        self._sim_threshold_timetables = 0.8

        self._log[tag_to_identify_time_slot] = self._log[tag_to_identify_timestamp].apply(self.time_slot)

        self._timetables_def = self.timetables_definition(self._log)

    def compute_timetables(self):
        timetable_times = defaultdict(lambda: defaultdict(set))
        for entry in self._timetables_def:
            timetable = entry['timetable']
            groups = entry['groups']
            for group in groups:
                if group in self._group_schedule:
                    role_schedule = self._group_schedule[group]
                    for day, times in role_schedule.items():
                        timetable_times[timetable][day].update(times)

        final_schedule = self.process_schedule(timetable_times)

        return final_schedule

    def time_from_string(self, time_str):
        return datetime.strptime(time_str, '%H:%M').time()

    def time_difference(self, t1, t2):
        dt1 = datetime.combine(datetime.today(), t1)
        dt2 = datetime.combine(datetime.today(), t2)
        return dt2 - dt1

    def generate_time_intervals(self, times):
        intervals = []
        current_interval = [times[0]]

        for i in range(1, len(times)):
            previous_time = times[i - 1]
            current_time = times[i]

            diff = self.time_difference(previous_time, current_time)
            
            if diff > timedelta(hours=4):
                current_interval.append(previous_time)
                intervals.append(current_interval)
                current_interval = [current_time]
            else:
                current_interval.append(current_time)

        if current_interval:
            intervals.append([current_interval[0], current_interval[-1]])

        return intervals

    def process_schedule(self, timetable_schedule):
        final_schedule = defaultdict(lambda: defaultdict(list))

        for timetable, schedule in timetable_schedule.items():
            for day, times in schedule.items():
                times_list = sorted([self.time_from_string(time) for time in times])
                intervals = self.generate_time_intervals(times_list)
                final_schedule[timetable][day] = intervals

        return final_schedule

    def timetables_definition(self, log):
        group_knowledge_dict = defaultdict(lambda: defaultdict(lambda: 0))
        
        for _, event in log.iterrows():
            groups = event[tag_to_identify_group]  
            t_slot = event[tag_to_identify_time_slot]
            for group in groups:
                group_knowledge_dict[group][t_slot] = 1

        df = DataFrame.from_dict(group_knowledge_dict, orient='index').fillna(0)
        num_columns = len(df.columns)

        co_matrix = self.det_correl_matrix(df)

        g = nx.Graph()
        for group, components in self._res_groups.items():
            g.add_node(group)
        for rel in co_matrix:
            print(rel)
            if abs(rel['distance']) >= self._sim_threshold_timetables and rel['x'] != rel['y']:
                g.add_edge(rel['x'],
                            rel['y'],
                            weight=rel['distance'])

        sub_graphs = list((g.subgraph(c) for c in nx.connected_components(g)))
        timetables_def = self.group_timetables_definition(sub_graphs)

        return timetables_def
    
    def group_timetables_definition(self, sub_graphs):
        records= list()
        for i in range(0, len(sub_graphs)):
            groups_name = [group for group, components in self._res_groups.items() if group in sub_graphs[i]]
            records.append({'timetable': 'Tm'+ str(i + 1),
                            'groups': groups_name})
        return records

    def det_correl_matrix(self, profiles):
        correl_matrix = list()
        for user_id_x, row_x in profiles.iterrows():
            for user_id_y, row_y in profiles.iterrows():
                x = np.array(row_x.values)
                x_int = x.astype(int)
                y = np.array(row_y.values)
                y_int = y.astype(int)

                # Dice Coefficient Calculation
                jaccard = jaccard_score(x_int, y_int, average='binary')
                dice_coefficient = (2 * jaccard) / (1 + jaccard)

                correl_matrix.append(({'x': user_id_x,
                                            'y': user_id_y,
                                            'distance': dice_coefficient}))
        return correl_matrix

    def get_day_of_week(self, timestamp):
        day_of_week = timestamp.weekday()  # 0=monday, 1=tuesday, ..., 6=sunday
        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        return days_of_week[day_of_week]

    def time_slot(self, timestamp):
        day_week = self.get_day_of_week(timestamp)
        hour = timestamp.hour
        if 2 <= hour < 4:
            return day_week + '1'
        elif 4 <= hour < 6:
            return day_week + '2'
        elif 6 <= hour < 8:
            return day_week + '3'
        elif 8 <= hour < 10:
            return day_week + '4'
        elif 10 <= hour < 12:
            return day_week + '5'
        elif 12 <= hour < 14:
            return day_week + '6'
        elif 14 <= hour < 16:
            return day_week + '7'
        elif 16 <= hour < 18:
            return day_week + '8'
        elif 18 <= hour < 20:
            return day_week + '9'
        elif 20 <= hour < 22:
            return day_week + '10'
        elif 22 <= hour < 24:
            return day_week + '11'
        else: #24-2
            return day_week + '12'