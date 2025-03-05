import pandas as pd
from collections import Counter


tag_to_identify_activities = 'concept:name'
tag_to_identify_resources = 'org:resource'
tag_to_identify_trace = 'case:concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_intancetype = 'instanceType'
tag_to_identify_node_type = 'nodeType'
tag_to_identify_node_lifecycle = 'lifecycle:transition'


class InstanceTypesCalculation():
        
    def __init__(self, log, settings, branches, tot_execute_per_branch):
        self._log = log.copy()
        self._settings = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        self._diag_log = settings[0]['diag_log']
        self._branches = branches 
        self._tot_execute_per_branch = tot_execute_per_branch

        print("--- Extract Instance types ---")
        self._instance_types = self.extract_instance_types(self._log)
        self._num_types_instance = len(self._instance_types[tag_to_identify_intancetype])

        self._forced_instance_types = None
        if self._num_types_instance > 1:
            self._forced_instance_types = self.extract_forced_instance_type_gateway(self._log, self._branches, self._tot_execute_per_branch)
        
        self.save_on_file_instancetypes()

    def save_on_file_instancetypes(self):
        with open(self._path + 'output_data/output_file/instancetypes' + self._name + '.txt', 'w') as file:
            file.write("Instance Types\n")
            file.write(f"{self._instance_types}\n")
            if self._num_types_instance > 1:
                file.write("\nForced Instance Types Gateway\n")
                file.write(f"{self._forced_instance_types}")


    def extract_instance_types(self, log):
        instance_types = None
        if self._diag_log:
            unique_cases = log[[tag_to_identify_trace, tag_to_identify_intancetype]].drop_duplicates()
            instance_types = unique_cases.groupby(tag_to_identify_intancetype).size().reset_index(name='number_of_traces')
        else:
            grouped_log = self._log.groupby(tag_to_identify_trace)
            total_num_trace = len(grouped_log)
            data = {tag_to_identify_intancetype: ['A'], 'number_of_traces': [total_num_trace]}
            instance_types = pd.DataFrame(data)
        return instance_types
    
    def tot_trace(self, log):
        grouped_log = log.groupby(tag_to_identify_trace)
        total_num_trace = len(grouped_log)
        return total_num_trace
    
    def extract_forced_instance_type_gateway(self, log1, branches, tot_execute_per_branch):
        self._total_num_trace = self.tot_trace(log1)
        log = log1[log1[tag_to_identify_node_lifecycle] == 'complete'].reset_index(drop=True)
        pattern1 = r'Gateway'
        pattern2 = r'Start'
        pattern3 = r'End'
        pattern4 = r'Event'
        temp_log_1 = (log[~log[tag_to_identify_activities].isin(['Start', 'End', 'start', 'end', 'Gateway'])].reset_index(drop=True))
        temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern1, case=False, na=False)]
        temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern2, case=False, na=False)]
        temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern3, case=False, na=False)]
        temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern4, case=False, na=False)]
        temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_node_type].str.contains(pattern1, case=False, na=False)]

        #Extract all the pairs (source, destination) from branches individually
        branches_pairs = []
        node_mapping = {}
        for node, paths in branches.items():
            for source in paths['source']:
                for destination in paths['destination']:
                    pair = (source, destination)
                    branches_pairs.append(pair)
                    node_mapping[pair] = node

        #For each pair store the gateway they belong to
        pair_gateway_associated = {}
        for node, details in branches.items():
            sources = details["source"]
            destinations = details["destination"]
            for pair in branches_pairs:
                source, destination = pair
                if source in sources and destination in destinations:
                    pair_gateway_associated[pair] = node

        #Store for each pair the instance types they execute and the number of times they execute them.
        results = {pair: Counter() for pair in branches_pairs}
        for trace_id, group in temp_log_1.groupby(tag_to_identify_trace):
            sorted_events = group.sort_values(tag_to_identify_timestamp).reset_index(drop=True)
            for i in range(len(sorted_events) - 1):
                source_row = sorted_events.iloc[i]
                dest_row = sorted_events.iloc[i + 1]
                source_activity = source_row[tag_to_identify_activities]
                destination_activity = dest_row[tag_to_identify_activities]
                if (source_activity, destination_activity) in branches_pairs:
                    results[(source_activity, destination_activity)][dest_row[tag_to_identify_intancetype]] += 1

        #For each pair of branches associate the total number of executions of the gateway to which they belong
        pair_tot = {}
        for node, details in branches.items():
            if node in tot_execute_per_branch:
                number = tot_execute_per_branch[node]
                for source in details["source"]:
                    for destination in details["destination"]:
                        pair_tot[(source, destination)] = number

        #For each gateway the instance types with the repetition number for each
        gateway_type_instances = {}
        for node, details in branches.items():
            total_counter = Counter()
            for source in details["source"]:
                for destination in details["destination"]:
                    pair = (source, destination)
                    if pair in results:
                        total_counter.update(results[pair])

            gateway_type_instances[node] = total_counter

        # Check for each pair if it is possible that it has a forced instance type
        # Extract for each pair the forced instance types if there is otherwise none
        forced_instance_types = {}
        for pair, counter in results.items():
            ratio_gateway_execution = pair_tot[pair] / self._total_num_trace
            if ratio_gateway_execution > 0.3: #if the gateway is executed in 30% of the traces it is a good case to analyze
                if len(counter) > 1: #if pass more than one instance type for that branch then there can't be forced
                    forced_instance_types[pair] = None
                else:
                    if len(counter) != 0: #if there is exactly one instance type that traverses that branch then it can be analyzed
                        num_instance = counter.most_common(1)[0][1]
                        instance_type_name = counter.most_common(1)[0][0]
                        gateway = pair_gateway_associated[pair]
                        tot_rep_of_that_instance_for_that_gateway = gateway_type_instances[gateway].get(instance_type_name, 0)
                        ratio = num_instance / tot_rep_of_that_instance_for_that_gateway
                        if ratio == 1: #if that instance type always passes on that branch and never passes on other branches
                            forced_instance_types[pair] = instance_type_name
                        else:
                            forced_instance_types[pair] = None  # No forced instanceType
                    else:
                        forced_instance_types[pair] = None
            else:
                forced_instance_types[pair] = None

        # For each gateway, the pairs and for each pair the forced instance types if any
        gateway_forced_instance_types = {}
        for pair, instance_type in forced_instance_types.items():
            node = node_mapping.get(pair)
            if node:
                if node not in gateway_forced_instance_types:
                    gateway_forced_instance_types[node] = []
                gateway_forced_instance_types[node].append((pair, instance_type))

        return gateway_forced_instance_types

