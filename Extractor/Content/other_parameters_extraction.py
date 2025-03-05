import pandas as pd
from collections import Counter
import numpy as np
import ast
from fitter import Fitter

tag_to_identify_resources = 'org:resource' 
tag_to_identify_activities = 'concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_cost_hour = 'resourceCost'
tag_to_identify_node_lifecycle = 'lifecycle:transition'
tag_to_identify_fixed_cost = 'fixedCost'
tag_to_identify_trace = 'case:concept:name'
#tag added by me
tag_to_identify_moment_of_day = 'moment_of_day'
tag_to_identify_group = 'group'

class OtherParametersCalculation():

    def __init__(self, log, settings, group):
        self._log = log.copy()
        self._settings = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        self._diag_log = settings[0]['diag_log']

        self._group = group

        
    '''Extract cost/hour for each resources, if there is in the log'''
    def cost_hour_parameter(self, log):
        def safe_literal_eval(x):
            try:
                evaluated = ast.literal_eval(x)
                return evaluated if isinstance(evaluated, (list, dict)) else [x]
            except (ValueError, SyntaxError):
                return [x]
            
        local_log = log.copy()
        self._group_average_cost_hour = None
        
        if self._diag_log:
            local_log[tag_to_identify_resources] = local_log[tag_to_identify_resources].apply(safe_literal_eval) #trasform resources in list of res
            local_log[tag_to_identify_cost_hour] = local_log[tag_to_identify_cost_hour].apply(safe_literal_eval) #trasform resources cost in list of res cost
            temp_log_1 = local_log[local_log[tag_to_identify_node_lifecycle] == 'complete'].reset_index(drop=True)
            pattern1 = r'Gateway'

            pattern4 = r'Event'
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern1, case=False, na=False)]
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern4, case=False, na=False)]

            df_expanded = temp_log_1.explode([tag_to_identify_resources, tag_to_identify_cost_hour])
            df_expanded[tag_to_identify_cost_hour] = df_expanded[tag_to_identify_cost_hour].apply(lambda x: x[0] if isinstance(x, list) else x)
            df_expanded[tag_to_identify_cost_hour] = pd.to_numeric(df_expanded[tag_to_identify_cost_hour])

            resource_cost_df = df_expanded.groupby(tag_to_identify_resources)[tag_to_identify_cost_hour].agg(list).reset_index()
            resource_to_costs = resource_cost_df.set_index(tag_to_identify_resources)[tag_to_identify_cost_hour].to_dict()

            group_costs = {}
            for group_info in self._group:
                group_name = group_info['group']
                members = group_info['members']
                combined_costs = []
                for member in members:
                    combined_costs.extend(resource_to_costs.get(member, []))
                group_costs[group_name] = combined_costs

            group_average_cost = {}
            for group, costs in group_costs.items():
                if costs:
                    group_average_cost[group] = sum(costs) / len(costs)
                else:
                    group_average_cost[group] = 0 
            self._group_average_cost_hour = group_average_cost
        else:
            local_log = local_log[local_log[tag_to_identify_node_lifecycle].isin(['start', 'complete'])].reset_index(drop=True)
            reorder_log = self.reorder_xes_task(local_log)
            reorder_log = pd.DataFrame(reorder_log)
            self._group_average_cost_hour = self.extract_cost_hour_per_group(reorder_log)
        
        self.save_group_cost_hour(self._group_average_cost_hour)

    def reorder_xes_task(self, temp_data):
        temp_data = pd.DataFrame(temp_data)
        ordered_event_log = list()
        for caseid, group in temp_data.groupby(tag_to_identify_trace):
            trace = group.to_dict('records')
            temp_trace = list()
            for i in range(0, len(trace) - 1):
                if trace[i][tag_to_identify_node_lifecycle] == 'start':
                    self.reorder_event_task(caseid, i, temp_trace, trace)
            ordered_event_log.extend(temp_trace)
        return ordered_event_log
    
    def reorder_event_task(self, caseid, i, temp_trace, trace):
        c_task_name = trace[i][tag_to_identify_activities]
        remaining = trace[i + 1:]

        complete_event = next((event for event in remaining if
                                    (event[tag_to_identify_activities] == c_task_name and event[tag_to_identify_node_lifecycle] == 'complete')),
                                    None)
        if complete_event:
            temp_trace.append(
                {tag_to_identify_trace: caseid,
                    tag_to_identify_activities: trace[i][tag_to_identify_activities],
                    tag_to_identify_resources: trace[i][tag_to_identify_resources],
                    tag_to_identify_cost_hour: complete_event[tag_to_identify_cost_hour],
                    'start_timestamp': trace[i][tag_to_identify_timestamp],
                    'end_timestamp': complete_event[tag_to_identify_timestamp]})
        else: 
            temp_trace.append(
                {tag_to_identify_trace: caseid,
                    tag_to_identify_activities: trace[i][tag_to_identify_activities],
                    tag_to_identify_resources: trace[i][tag_to_identify_resources],
                    tag_to_identify_cost_hour: trace[i][tag_to_identify_cost_hour],
                    'start_timestamp': trace[i][tag_to_identify_timestamp],
                    'end_timestamp': trace[i][tag_to_identify_timestamp]})
           
    def extract_cost_hour_per_group(self, log):
        cost_hour_res = {}
        for index, row in log.iterrows():
            if row[tag_to_identify_resources] not in cost_hour_res:
                cost_hour_res[row[tag_to_identify_resources]] = []
            cost = float(row[tag_to_identify_cost_hour])
            duration = row['end_timestamp'] - row['start_timestamp']
            duration_in_s = float(duration.total_seconds())
            #if duration_in_s == 0: #to avoid problem with distribution calculation
            #    duration_in_s = 0.00001
            if duration_in_s != 0:
                cost_hour = cost / (duration_in_s / 3600) # costo orario
                cost_hour_res[row[tag_to_identify_resources]].append(cost_hour)

        resource_to_group = {}
        for group_info in self._group:
            group_name = group_info['group']
            for member in group_info['members']:
                resource_to_group[member] = group_name

        group_costs = {group_info['group']: [] for group_info in self._group}

        for resource, cost_hours in cost_hour_res.items():
            group = resource_to_group.get(resource)
            if group:  
                group_costs[group].extend(cost_hours)

        group_average_cost = {}
        for group, costs in group_costs.items():
            if costs:
                group_average_cost[group] = sum(costs) / len(costs)
            else:
                group_average_cost[group] = 0 

        return group_average_cost

    '''Extract fixed cost for each activity, if there is in the log'''
    def fixed_activity_cost(self, log):
        local_log = log.copy()
        pattern1 = r'Gateway'
        pattern4 = r'Event'
        local_log = local_log[~local_log[tag_to_identify_activities].str.contains(pattern1, case=False, na=False)]
        local_log = local_log[~local_log[tag_to_identify_activities].str.contains(pattern4, case=False, na=False)]
        local_log = local_log[local_log[tag_to_identify_node_lifecycle] == 'complete'].reset_index(drop=True)
        local_log[tag_to_identify_fixed_cost] = pd.to_numeric(local_log[tag_to_identify_fixed_cost], errors='coerce')
        local_log = local_log.dropna(subset=[tag_to_identify_fixed_cost])
        self._fixed_cost_avg_per_activity = local_log.groupby(tag_to_identify_activities)[tag_to_identify_fixed_cost].mean()
        self.save_fixed_activity_cost(self._fixed_cost_avg_per_activity)

    '''Extract setup time act for reasource, if there is in the log'''
    def setup_time_act(self, log):
        def safe_literal_eval(x):
            try:
                evaluated = ast.literal_eval(x)
                return evaluated if isinstance(evaluated, (list, dict)) else [x]
            except (ValueError, SyntaxError):
                return [x]
        local_log = log.copy()
        local_log = local_log[local_log[tag_to_identify_node_lifecycle].isin(['startSetupTime', 'endSetupTime'])].reset_index(drop=True)
        local_log[tag_to_identify_resources] = local_log[tag_to_identify_resources].apply(safe_literal_eval)
        local_log = self.reorder_xes(local_log)
        local_log = pd.DataFrame(local_log)
        duration_distr_setup_time_app = self.extract_duration_distribution(local_log)
        member_to_group = {member: group['group'] for group in self._group for member in group['members']}
        self._duration_distr_setup_time = []
        for item in duration_distr_setup_time_app:
            member = item[0]
            group = member_to_group.get(member, None)
            enriched_item = item + [group]
            self._duration_distr_setup_time.append(enriched_item)
        
        max_usage = local_log.groupby(tag_to_identify_resources)['max_usage_before_setup_time'].unique()
        app = list(max_usage.items())
        self._max_usage_before_setup_time_per_resource = [(member_to_group.get(resource, resource), usage[0]) for resource, usage in app]
        self.save_setup_time_params(self._duration_distr_setup_time, self._max_usage_before_setup_time_per_resource)

    def reorder_xes(self, temp_data):
        temp_data = pd.DataFrame(temp_data)
        ordered_event_log = list()
        for caseid, group in temp_data.groupby(tag_to_identify_trace):
            trace = group.to_dict('records')
            temp_trace = list()
            for i in range(0, len(trace) - 1):
                if trace[i][tag_to_identify_node_lifecycle] == 'startSetupTime':
                    self.reorder_event(caseid, i, temp_trace, trace)
            ordered_event_log.extend(temp_trace)
        return ordered_event_log
    
    def reorder_event(self, caseid, i, temp_trace, trace):
        c_task_name = trace[i][tag_to_identify_activities]
        remaining = trace[i + 1:]

        complete_event = next((event for event in remaining if
                                    (event[tag_to_identify_activities] == c_task_name and event[tag_to_identify_node_lifecycle] == 'endSetupTime')),
                                    None)
        if complete_event:
            temp_trace.append(
                {tag_to_identify_trace: caseid,
                    tag_to_identify_activities: trace[i][tag_to_identify_activities],
                    tag_to_identify_resources: trace[i][tag_to_identify_resources][0][0],
                    'max_usage_before_setup_time': trace[i][tag_to_identify_resources][0][1],
                    'start_timestamp': trace[i][tag_to_identify_timestamp],
                    'end_timestamp': complete_event[tag_to_identify_timestamp]})
        else: 
            temp_trace.append(
                {tag_to_identify_trace: caseid,
                    tag_to_identify_activities: trace[i][tag_to_identify_activities],
                    tag_to_identify_resources: trace[i][tag_to_identify_resources][0][0],
                    'max_usage_before_setup_time': trace[i][tag_to_identify_resources][0][1],
                    'start_timestamp': trace[i][tag_to_identify_timestamp],
                    'end_timestamp': trace[i][tag_to_identify_timestamp]})
            
    def extract_duration_distribution(self, log):
        setup_time_duration = {}
        for index, row in log.iterrows():
            if row[tag_to_identify_resources] not in setup_time_duration:
                setup_time_duration[row[tag_to_identify_resources]] = []
            duration = row['end_timestamp'] - row['start_timestamp']
            duration_in_s = float(duration.total_seconds())
            #if duration_in_s == 0: #to avoid problem with distribution calculation
            #    duration_in_s = 0.00001
            if duration_in_s != 0:
                setup_time_duration[row[tag_to_identify_resources]].append(duration_in_s)

        setup_time_distribution = []
        for res, duration_list in setup_time_duration.items():
            distribution_params = self.extract_distribution([x for x in duration_list])
            setup_time_distribution.append([res, distribution_params[0], distribution_params[1]])

        return setup_time_distribution

    def extract_distribution(self, X):
            d = None
            most_common_elem, count = Counter(X).most_common(1)[0]
            if count > 0.9 * len(X):
                d = 'fixed'
                mean = 0
                if count == len(X):
                    mean = 0 if X[0] == 0.00001 else X[0]
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

    def save_group_cost_hour(self, group_cost_hour):
        with open(self._path + 'output_data/output_file/res_cost_' + self._name + '.txt', 'w') as file:
            file.write(f'{group_cost_hour}')

    def save_fixed_activity_cost(self, fixed_act_costs):
        with open(self._path + 'output_data/output_file/fixed_act_cost_' + self._name + '.txt', 'w') as file:
            file.write(f'{fixed_act_costs}')

    def save_setup_time_params(self, duration_distr_setup_time, max_usage_before_setup_time_per_resource):
        with open(self._path + 'output_data/output_file/setup_time_params_' + self._name + '.txt', 'w') as file:
            file.write(f'Setup Time Duration DIstribution: \n')
            file.write(f'{duration_distr_setup_time}\n')
            file.write(f'\nMax Usage before setup time is needed:\n')
            file.write(f'{max_usage_before_setup_time_per_resource}\n')

            