import pandas as pd
import numpy as np
from fitter import Fitter
from collections import Counter

tag_to_identify_activities = 'concept:name'
tag_to_identify_resources = 'org:resource'
tag_to_identify_trace = 'case:concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_node_lifecycle = 'lifecycle:transition'
tag_to_identify_node_type = 'nodeType'


class ActivityDistributionCalculation():

    ''' This class is responsible for calculating the processing and waiting time distribution and parameters '''

    def __init__(self, log, settings = 0):
        self._log = log.copy()
        self._settings = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        self._num_timestamp = settings[0]['num_timestamp']
        self._diaglog = settings[0]['diag_log']

        if not self._diaglog:
            pattern2 = r'Start'
            pattern3 = r'End'
            self._log = self._log[~self._log[tag_to_identify_activities].str.contains(pattern2, case=False, na=False)]
            self._log = self._log[~self._log[tag_to_identify_activities].str.contains(pattern3, case=False, na=False)]

        unique_abort_event = None
        if self._diaglog: #check if there are abort event
            pattern = r'endEvent/terminateEventDefinition'
            abort_event = self._log[self._log[tag_to_identify_node_type].str.contains(pattern, case=False, na=False)]
            unique_abort_event = abort_event[tag_to_identify_activities].unique().tolist()
            print(unique_abort_event)

        self._log.rename(columns={
                tag_to_identify_trace: 'caseid',
                tag_to_identify_activities: 'task',
                tag_to_identify_node_lifecycle: 'event_type',
                tag_to_identify_timestamp: 'timestamp'}, inplace=True)
        
    
        self._correct_order_diag_log = False
        first_trace = self._log[self._log['caseid'] == self._log['caseid'].iloc[0]]
        second_element = first_trace.iloc[1]
        if second_element['event_type'] == "assign":
            self._correct_order_diag_log = True

        self._log = self._log[self._log.event_type.isin(['assign', 'start', 'complete'])].reset_index(drop=True)
        self._log = self.reorder_xes(self._log)
        self._log = pd.DataFrame(self._log)

        self._duration_distr = self.extract_duration_distribution(self._log)

        if unique_abort_event:
            for err in unique_abort_event:
                self._duration_distr.append([err, 'fixed', {'mean': 1.0, 'arg1': 0, 'arg2': 0}])

        self.save_on_file_duration()

        if self._num_timestamp == 3:
            self._waiting_distr = self.extract_waiting_distribution()
            self.save_on_file_waiting()

    def extract_duration_distribution(self, log):
        print("--- Compute process time distribution ---")
        act_duration = {}
        for index, row in log.iterrows():
            if row['task'] not in act_duration:
                act_duration[row['task']] = []
            duration = row['end_timestamp'] - row['start_timestamp']
            duration_in_s = float(duration.total_seconds())
            if duration_in_s is not np.nan:
                if duration_in_s == 0: #to avoid problem with distribution calculation
                    duration_in_s = 0.00001
                if duration_in_s > 0:
                    act_duration[row['task']].append(duration_in_s)

        activity_distribution = []
        for activity, duration_list in act_duration.items():
            #eliminates high time values ​​that also contain times when no one works between one day and another
            median_value = np.median(duration_list)
            median_value_2 = 5 * median_value
            new_duration_list = []
            for d in duration_list:
                if d <= median_value_2:
                    new_duration_list.append(d)
            distribution_params = self.extract_distribution([x for x in new_duration_list])
            activity_distribution.append([activity, distribution_params[0], distribution_params[1]])

        return activity_distribution

    def save_on_file_duration(self):
        with open(self._path + 'output_data/output_file/activity_distr_' + self._name + '.txt', 'w') as file:
            for a in self._duration_distr:
                file.write(f"{a}\n")

    def extract_waiting_distribution(self):
        print("--- Compute waiting time distribution ---")
        act_waiting = {}
        for index, row in self._log.iterrows():
            if row['task'] not in act_waiting:
                act_waiting[row['task']] = []
            duration = row['start_timestamp'] - row['assign_timestamp']
            duration_in_s = float(duration.total_seconds())
            if duration_in_s is not np.nan:
                if duration_in_s == 0: #to avoid problem with distribution calculation
                    duration_in_s = 0.00001
                if duration_in_s > 0:
                    act_waiting[row['task']].append(duration_in_s)

        activity_distribution_waiting = []
        for activity, duration_list in act_waiting.items():
            #eliminates high time values ​​that also contain times when no one works between one day and another
            median_value = np.median(duration_list)
            median_value_2 = 5 * median_value
            new_duration_list = []
            for d in duration_list:
                if d <= median_value_2:
                    new_duration_list.append(d)
            distribution_params = self.extract_distribution([x for x in new_duration_list])
            activity_distribution_waiting.append([activity, distribution_params[0], distribution_params[1]])

        return activity_distribution_waiting
    
    def save_on_file_waiting(self):
        with open(self._path + 'output_data/output_file/act_distr_wait_time_' + self._name + '.txt', 'w') as file:
            for a in self._waiting_distr:
                file.write(f"{a}\n")


    def reorder_xes(self, temp_data):
        temp_data = pd.DataFrame(temp_data)
        ordered_event_log = list()

        if self._num_timestamp == 1:
            temp_data = temp_data[temp_data.event_type == 'complete']
            ordered_event_log = temp_data.rename(
                columns={'timestamp': 'end_timestamp'})
            ordered_event_log = ordered_event_log.drop(columns='event_type')
            ordered_event_log = ordered_event_log[['caseid', 'task', 'end_timestamp']]
            ordered_event_log = ordered_event_log.to_dict('records')
        elif self._num_timestamp == 3:
            for caseid, group in temp_data.groupby('caseid'):
                trace = group.to_dict('records')
                temp_trace = list()
                for i in range(0, len(trace) - 1):
                    if self._diaglog and not self._correct_order_diag_log:
                        if trace[i]['event_type'] == 'start':
                            self.reorder_event(caseid, i, temp_trace, trace)
                    else:
                        if trace[i]['event_type'] == 'assign':
                            self.reorder_event(caseid, i, temp_trace, trace)
                
                ordered_event_log.extend(temp_trace)
        else:
            for caseid, group in temp_data.groupby('caseid'):
                trace = group.to_dict('records')
                temp_trace = list()
                for i in range(0, len(trace) - 1):
                    if self._diaglog and not self._correct_order_diag_log:
                        if trace[i]['event_type'] == 'assign':
                            self.reorder_event(caseid, i, temp_trace, trace)
                    else:
                        if trace[i]['event_type'] == 'start':
                            self.reorder_event(caseid, i, temp_trace, trace)
                ordered_event_log.extend(temp_trace)

        return ordered_event_log
    
    def reorder_event(self, caseid, i, temp_trace, trace):
        c_task_name = trace[i]['task']
        remaining = trace[i + 1:]

        if self._num_timestamp == 2:
            complete_event = next((event for event in remaining if
                                    (event['task'] == c_task_name and event['event_type'] == 'complete')),
                                    None)
            if complete_event:
                temp_trace.append(
                    {'caseid': caseid,
                        'task': trace[i]['task'],
                        'start_timestamp': trace[i]['timestamp'],
                        'end_timestamp': complete_event['timestamp']})
            else:
                temp_trace.append(
                    {'caseid': caseid,
                        'task': trace[i]['task'],
                        'start_timestamp': trace[i]['timestamp'],
                        'end_timestamp': trace[i]['timestamp']})
        else:
            if self._diaglog and not self._correct_order_diag_log:
                start_event = next((event for event in remaining if
                            (event['task'] == c_task_name and event['event_type'] == 'assign')),
                            None)
            else:
                start_event = next((event for event in remaining if
                            (event['task'] == c_task_name and event['event_type'] == 'start')),
                            None)
            complete_event = next((event for event in remaining if
                                (event['task'] == c_task_name and event['event_type'] == 'complete')),
                                None)

            if start_event and complete_event:
                temp_trace.append(
                    {'caseid': caseid,
                    'task': trace[i]['task'],
                    'assign_timestamp': trace[i]['timestamp'],
                    'start_timestamp': start_event['timestamp'],
                    'end_timestamp': complete_event['timestamp']})
            elif complete_event:
                temp_trace.append(
                    {'caseid': caseid,
                    'task': trace[i]['task'],
                    'assign_timestamp': trace[i]['timestamp'],
                    'start_timestamp': None,
                    'end_timestamp': complete_event['timestamp']})
            elif start_event:
                temp_trace.append(
                    {'caseid': caseid,
                    'task': trace[i]['task'],
                    'assign_timestamp': trace[i]['timestamp'],
                    'start_timestamp': start_event['timestamp'],
                    'end_timestamp': None})
            else:
                temp_trace.append(
                    {'caseid': caseid,
                    'task': trace[i]['task'],
                    'assign_timestamp': trace[i]['timestamp'],
                    'start_timestamp': None,  
                    'end_timestamp': None})

    def extract_distribution(self, X):
            d = None
            most_common_elem, count = Counter(X).most_common(1)[0]
            if count > 0.9 * len(X):
                d = 'fixed'
                mean = 1
                if count == len(X):
                    mean = 1 if X[0] == 0.00001 else X[0]
                else:
                    mean = round(most_common_elem, 2)
                params = {'mean': mean, 'arg1': 0, 'arg2': 0}
                return [d, params]
            f = Fitter(X, distributions=['norm', 'expon', 'uniform', 'triang', 'lognorm', 'gamma'])
            #f = Fitter(X, distributions=['norm', 'expon', 'uniform'])
            f.fit()
            f.summary()
            d = list(f.get_best(method='sumsquare_error').keys())[0]
            params = self.extract_params(X, d)
            return [d, params]
        
    def extract_params(self, X, dtype):
        params = None
        if dtype == 'fixed':
            mean = 0 if X[0] == 0.00001 else X[0]
            params = {'mean': round(mean, 2), 'arg1': 0, 'arg2': 0}
        elif dtype == 'norm':
            mean = np.mean(X)
            arg1 = np.std(X)
            params = {'mean': round(mean, 2), 'arg1': round(arg1, 2), 'arg2': 0}
        elif dtype == 'expon':
            mean = np.mean(X)
            params = {'mean': round(mean, 2), 'arg1': 0, 'arg2': 0}
        elif dtype == 'uniform':
            mean = np.mean(X)
            arg1 = np.min(X)
            arg2 = np.max(X)
            params = {'mean': round(mean, 2), 'arg1': round(arg1, 2), 'arg2': round(arg2, 2)}
        elif dtype == 'triang':
            mean = np.mean(X)
            arg1 = np.min(X)
            arg2 = np.max(X)
            params = {'mean': round(mean, 2), 'arg1': 0, 'arg2': 0}
        elif dtype in ['lognorm', 'gamma']:
            mean = np.mean(X)
            arg1 = np.var(X)
            params = {'mean': round(mean, 2), 'arg1': round(arg1, 2), 'arg2': 0}
        return params
