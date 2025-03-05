from datetime import datetime, timedelta
import json
from collections import Counter

class ParamsFile():

    def __init__(self, instance, interarrival, timetables, group_act, act_duration_distr, worklist, fixed_cost_act, flow_prob, forced_instance_type, 
                 group_timetables_association, roles, setup_time_distr, setup_time_max, cost_hour, settings, id_name_act_match, 
                 start_end_act_bool=False, start_act=None, end_act=None, new_flow_prob=None, new_forced_instance=None, cut_log_bool=False):
        self._instance = instance
        self._start_date = None
        self._interarrival = interarrival
        self._timetables = timetables
        self._group_act = group_act
        self._act_duration_distr = act_duration_distr
        self._worklist = worklist
        self._fixed_cost_act = fixed_cost_act
        self._flow_prob = flow_prob
        self._forced_instance_type = forced_instance_type
        self._group_timetables_association = group_timetables_association
        self._roles = roles
        self._setup_time_distr = setup_time_distr
        self._setup_time_max = setup_time_max
        self._cost_hour = cost_hour
        self._settings = settings
        self._id_name_act_match = id_name_act_match

        self._start_end_act_bool = start_end_act_bool
        self._start_act = start_act
        self._end_act = end_act

        # parameters of model with intermediate states
        self._cut_log_bool = cut_log_bool
        self._new_flow_prob = new_flow_prob
        self._new_forced_instance = new_forced_instance

        self.generate_json()
    
    def generate_json(self):
        process_instace = self.adapt_instace()
        arrival_rate = self.adapt_interarrival()
        timetables = self.adapt_timetables()
        resources = self.adapt_resources()
        activities_id = self.adapt_activities(True)
        activities_name = self.adapt_activities(False)
        flow = self.adapt_flow_prob()

        now = datetime.now()
        current_weekday = now.weekday()
        days_until_monday = (7 - current_weekday) % 7
        if days_until_monday == 0:
            days_until_monday = 7
        next_monday = now + timedelta(days=days_until_monday)
        next_monday_at_6am = next_monday.replace(hour=6, minute=0, second=0, microsecond=0)
        startDateTime = next_monday_at_6am.strftime('%Y-%m-%dT%H:%M:%S')

        catch_events = {}
        logging_opt = "1"

        data_json = {
            "processInstances": process_instace,
            "startDateTime": startDateTime,
            "arrivalRateDistribution": arrival_rate,
            "timetables": timetables,
            "resources": resources,
            "elements": activities_id,
            "sequenceFlows": flow,
            "catchEvents": catch_events,
            "logging_opt":logging_opt
        }

        if self._start_end_act_bool:
            with open(self._settings[0]['path'] + 'output_data/output_file/parameters_' + self._settings[0]['namefile'] + '_intermediate_points.json', 'w') as f:
                json.dump(data_json, f)
        else:
            with open(self._settings[0]['path'] + 'output_data/output_file/parameters_' + self._settings[0]['namefile'] + '.json', 'w') as f:
                json.dump(data_json, f)

        data_txt = {
            "processInstances": process_instace,
            "startDateTime": startDateTime,
            "arrivalRateDistribution": arrival_rate,
            "timetables": timetables,
            "resources": resources,
            "elements": activities_name,
            "sequenceFlows": flow,
            "catchEvents": catch_events,
            "logging_opt":logging_opt
        }

        if self._start_end_act_bool:
            with open(self._settings[0]['path'] + 'output_data/output_file/parameters_' + self._settings[0]['namefile'] + '_intermediate_points.txt', 'w') as output_file:
                json.dump(data_txt, output_file, indent=4)
        else:
            with open(self._settings[0]['path'] + 'output_data/output_file/parameters_' + self._settings[0]['namefile'] + '.txt', 'w') as output_file:
                json.dump(data_txt, output_file, indent=4)
        
    def adapt_resources(self):
        resource_max = {}
        if self._settings[0]['diag_log']:
            for activity, group_lists in self._group_act.items():
                for group_list in group_lists:
                    group_counts = Counter(group_list)
                    for group_name, count in group_counts.items():
                        if group_name not in resource_max:
                            resource_max[group_name] = count
                        else:
                            resource_max[group_name] = max(resource_max[group_name], count)

        resources = []
        bool_system_resource = False
        for timetable in self._group_timetables_association:
            for group_name in timetable['groups']:
                if group_name == "system_resource":
                    bool_system_resource = True
                group_info = next(item for item in self._roles if item['group'] == group_name)
                if self._settings[0]['diag_log']:
                    group_quantity = resource_max[group_name]
                else:
                    group_quantity = group_info['quantity']
                group_members_list = group_info['members']

                setup_time = ""
                max_usage_value = ""
                if self._setup_time_distr != None:
                    for res, setup, params, group in self._setup_time_distr:
                        if group == group_name:
                            setup_time = {
                                "type": self.type_distr(setup),
                                "mean": params['mean'],
                                "arg1": "" if params['arg1'] == 0 else str(params['arg1']),
                                "arg2": "" if params['arg2'] == 0 else str(params['arg2']),
                                "timeUnit": "seconds"
                            }
                
                    max_usage_value = next((usage for g, usage in self._setup_time_max if g == group_name), "")
                
                cost_per_hour = "1"
                if self._cost_hour != None:
                    cost_per_hour = self._cost_hour.get(group_name, "")
                
                resources.append({
                    "name": group_name,
                    "totalAmount": str(group_quantity),
                    "costPerHour": str(cost_per_hour),
                    "timetableName": timetable['timetable'],
                    "setupTime": setup_time if setup_time else {
                        "type": "",
                        "mean": "",
                        "arg1": "",
                        "arg2": "",
                        "timeUnit": ""
                    },
                    "maxUsage": str(max_usage_value)
                })
        
        if self._start_end_act_bool:
            resources.append({
                    "name": "system_res_start_end",
                    "totalAmount": "1",
                    "costPerHour": "1",
                    "timetableName": "tm_system",
                    "setupTime": {
                        "type": "",
                        "mean": "",
                        "arg1": "",
                        "arg2": "",
                        "timeUnit": ""
                    },
                    "maxUsage": ""
                })
        
        #add always a system resource if there is not
        if not bool_system_resource:
            resources.append({
                    "name": "system_resource",
                    "totalAmount": "1",
                    "costPerHour": "1",
                    "timetableName": "tm_system",
                    "setupTime": {
                        "type": "",
                        "mean": "",
                        "arg1": "",
                        "arg2": "",
                        "timeUnit": ""
                    },
                    "maxUsage": ""
                })

        return resources

    def adapt_flow_prob(self):
        output = []
        for node, node_flows in self._flow_prob.items():
            # Retrieve the forced types for the node
            if self._forced_instance_type != None:
                node_forced_types = self._forced_instance_type.get(node, [])
            
            for flow_data in node_flows:
                flow_id = flow_data['flow']
                probability = flow_data['total_probability']
                source = next(iter(flow_data['source']))
                destinations = flow_data['destination']
                
                # Collect all instance types for this flow
                instance_types = []
                if self._forced_instance_type != None:
                    for destination in destinations:
                        for (pair, f_type) in node_forced_types:
                            if pair == (source, destination) and f_type is not None:
                                if {"type": f_type} not in instance_types:
                                    instance_types.append({"type": f_type})
                
                # Add the flow data to the output
                if self._cut_log_bool:
                    output.append({
                        "elementId": "id" + flow_id,
                        "executionProbability": f"{probability:.2f}",
                        "types": instance_types
                    })
                else:
                    output.append({
                        "elementId": flow_id,
                        "executionProbability": f"{probability:.2f}",
                        "types": instance_types
                    })
            
        if self._cut_log_bool:
            new_flow_prob_dict = dict(self._new_flow_prob)
            for index, row in self._new_forced_instance.iterrows():
                instance_types = []
                instance_types.append({"type": f"{row['Instance Type']}"})
                output.append({
                    "elementId": f"id{row['Flow']}",
                    "executionProbability": f"{new_flow_prob_dict[row['Flow']]}",
                    "types": instance_types
                })

            for f, p in self._new_flow_prob:
                if p == 0.9:
                    output.append({
                    "elementId": f"id{f}",
                    "executionProbability": f"{p}",
                    "types": []
                })


        return output

    def adapt_instace(self):
        process_instances = []
        if self._cut_log_bool:
            for index, row in self._new_forced_instance.iterrows():
                process_instances.append({
                'type': f"{row['Instance Type']}",
                'count': str(row['Repetition Instance Type'])
            })
        for index, row in self._instance.iterrows():
            process_instances.append({
                'type': row['instanceType'],
                'count': str(row['number_of_traces'])
            })
        
        return process_instances

    def adapt_interarrival(self):
        '''time = None
        time_unit = None
        if seconds < 60:
            return f"{seconds} secondi"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} minuti"
        else:
            hours = seconds // 3600
            return f"{hours} ore"'''
        arrival_rate_data = {
            "type": self.type_distr(self._interarrival[0]), 
            "mean": str(self._interarrival[1]['mean']),
            "arg1": "" if self._interarrival[1]['arg1'] == 0 else str(self._interarrival[1]['arg1']),
            "arg2": "" if self._interarrival[1]['arg2'] == 0 else str(self._interarrival[1]['arg2']),
            "timeUnit": "seconds"
        }
        return arrival_rate_data
    
    def adapt_timetables(self):
        #print(self._timetables)
        timetables = []
        bool_tm_system = False
        for timetable_name, schedule in self._timetables.items():
            if timetable_name == "tm_system":
                bool_tm_system = True
            rules = []
            for day, hours in schedule.items():
                time_intervals = hours.split(', ')
                for interval in time_intervals:
                    from_time, to_time = interval.split(' - ')
                    rules.append({
                        "fromTime": f"{from_time.strip()}:00",
                        "toTime": f"{to_time.strip()}:00",
                        "fromWeekDay": day.upper(),
                        "toWeekDay": day.upper()
                    })
            
            timetables.append({
                "name": timetable_name,
                "rules": rules
            })

        #add a system timetables if there is not
        if not bool_tm_system: 
            rule = []
            rule.append({
                        "fromTime": f"00:00:00",
                        "toTime": f"23:59:00",
                        "fromWeekDay": f"MONDAY",
                        "toWeekDay": f"SUNDAY"
                    })
            timetables.append({
                "name": "tm_system",
                "rules": rule
            })
        return timetables
    
    def adapt_activities(self, id_bool):
        def generate_resource_ids(resource_lists):
            resource_ids = []
            for group_index, group_list in enumerate(resource_lists, start=1):
                group_counts = Counter(group_list)
                for group_name, count in group_counts.items():
                    resource_ids.append({
                        "resourceName": group_name,
                        "amountNeeded": str(count),
                        "groupId": str(group_index)
                    })
            return resource_ids
        
        def get_node_for_activity(activity_name):
            for activity, node in self._id_name_act_match:
                if activity == activity_name:
                    return node

        worklist_map = {}
        for i, (act1, act2) in enumerate(self._worklist, start=1):
            worklist_map[act1] = str(i)
            worklist_map[act2] = str(i)

        elements = []
        resource_system = []
        resource_system.append({
                    "resourceName": "system_resource",
                    "amountNeeded": "1",
                    "groupId": "1"
                })
        for activity, dist_type, params in self._act_duration_distr:
            element = {
                "elementId": activity if not id_bool else get_node_for_activity(activity),
                "worklistId": worklist_map.get(activity, "") if worklist_map else "", 
                "fixedCost": str(self._fixed_cost_act.get(activity, "")) if self._fixed_cost_act is not None and not self._fixed_cost_act.empty else "",
                "costThreshold": "",
                "durationDistribution": {
                    "type": self.type_distr(dist_type),
                    "mean": str(params["mean"]),
                    "arg1": "" if params["arg1"] == 0 else str(params["arg1"]),
                    "arg2": "" if params["arg2"] == 0 else str(params["arg2"]),
                    "timeUnit": "seconds"
                },
                "durationThreshold": "",
                "durationThresholdTimeUnit": "",
                "resourceIds": generate_resource_ids(self._group_act.get(activity, [])) if self._group_act.get(activity, []) else resource_system
            }
            elements.append(element)
        
        if self._start_end_act_bool:
            resource_s_e = []
            resource_s_e.append({
                        "resourceName": "system_res_start_end",
                        "amountNeeded": "1",
                        "groupId": "1"
                    })
            element_start = {
                "elementId": self._start_act if not id_bool else get_node_for_activity(self._start_act),
                "worklistId": "", 
                "fixedCost": "",
                "costThreshold": "",
                "durationDistribution": {
                    "type": "FIXED",
                    "mean": "1",
                    "arg1": "",
                    "arg2": "",
                    "timeUnit": "seconds"
                },
                "durationThreshold": "",
                "durationThresholdTimeUnit": "",
                "resourceIds": resource_s_e
            }
            element_end = {
                "elementId": self._end_act if not id_bool else get_node_for_activity(self._end_act),
                "worklistId": "", 
                "fixedCost": "",
                "costThreshold": "",
                "durationDistribution": {
                    "type": "FIXED",
                    "mean": "1",
                    "arg1": "",
                    "arg2": "",
                    "timeUnit": "seconds"
                },
                "durationThreshold": "",
                "durationThresholdTimeUnit": "",
                "resourceIds": resource_s_e
            }
            elements.append(element_start)
            elements.append(element_end)
        return elements
        
    def type_distr(self, val):
        type_distr = None
        if val == 'expon':
            type_distr = 'EXPONENTIAL'
        elif val == 'norm':
            type_distr = 'NORMAL'
        elif val == 'uniform':
            type_distr = 'UNIFORM'
        elif val == 'triang':
            type_distr = 'TRIANGULAR'
        elif val == 'lognorm':
            type_distr = 'LOGNORMAL'
        elif val == 'gamma':
            type_distr = 'GAMMA'
        else:
              type_distr = 'FIXED'
        return type_distr
    

