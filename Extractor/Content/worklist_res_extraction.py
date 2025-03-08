from collections import Counter

tag_to_identify_activities = 'concept:name'
tag_to_identify_resources = 'org:resource'
#tag_to_identify_resources = 'org:group'
tag_to_identify_trace = 'case:concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_group = 'group'

#rule: binding(T1, T2) iff start(of T1 by :p) and start(of T2) implies start(of T2 by p). r: A -> B
# A: start(of T1 by :p) and start(of T2); B: start(of T2 by p)


class WorklistCalculation():

    def __init__(self, log, settings, res_group, model_activities, res_act):
        print("----Result of worklist ( or Retain Familiar or binding od duty rules)----")
        print("binding(T1, T2) iff start(of T1 by :p) and start(of T2) implies start(of T2 by p)\n")
        self._log = log.copy()
        self._log = self._log[self._log['lifecycle:transition'] == 'complete'] # same log, without duplicate events (start, end, assign)
        self._settings = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        self._sim_threshold = settings[0]['sim_threshold']
        self._res_group = res_group
        self._model_activities = model_activities
        self._res_act = res_act

        self._threshold_minSupp = 0.1
        self._threshold_minConf = 0.8
        #self._threshold_minInt = 1.0
        self._threshold_minInt = 0.98

        self._binding_rules = self.extract_binding_rules(self._log)
        self._num_trace_binding = self.num_trace_for_binding(self._binding_rules)
        self._activity_pairs = self.act_pairs(self._log, self._num_trace_binding)

        self._total_num_trace = self.tot_trace(log)

        self._suppr_list = self.compute_suppr_list(self._num_trace_binding)
        self._suppA_list = self.compute_suppA_list(self._activity_pairs)
        self._confr_list = self.compute_confr_list(self._suppr_list, self._suppA_list)

        self._sigmaB_list = self.compute_sigmaB_list(self._log, self._activity_pairs)
        self._suppB_list = self.compute_suppB_list(self._sigmaB_list)
        self._intr_list = self.compute_intr_list(self._suppr_list, self._suppA_list, self._suppB_list)
        
    def tot_trace(self, log):
        grouped_log = log.groupby(tag_to_identify_trace)
        total_num_trace = len(grouped_log)
        return total_num_trace

    def extract_binding_rules(self, df): #extract Retain Familiar (aka Binding of Duties)
        binding_rules = []

        df_sorted = df.sort_values(by=[tag_to_identify_trace, tag_to_identify_timestamp])
        for trace_id, group in df_sorted.groupby(tag_to_identify_trace):
            activities = group[[tag_to_identify_activities, tag_to_identify_group]].values.tolist()
            for i in range(len(activities)):
                T1_activity, T1_resource = activities[i]

                for j in range(i + 1, len(activities)):
                    T2_activity, T2_resource = activities[j]

                    if T1_activity != T2_activity:
                        if Counter(T1_resource) == Counter(T2_resource):
                            binding_rule = {
                                'T1': T1_activity,
                                'T2': T2_activity,
                                'resource': T1_resource,
                                'trace': trace_id
                            }
                            binding_rules.append(binding_rule)

        return binding_rules
    
    def num_trace_for_binding(self, binding_rules):
        pair_traces = {}
        for entry in binding_rules:
            t1 = entry['T1']
            t2 = entry['T2']
            trace = entry['trace']
            
            pair_key = (t1, t2)
            
            if pair_key not in pair_traces:
                pair_traces[pair_key] = set()
            pair_traces[pair_key].add(trace)

        result = {pair: len(traces) for pair, traces in pair_traces.items()}

        return result

    def act_pairs(self, log, num_trace_binding):
        trace_activities = log.groupby(tag_to_identify_trace)[tag_to_identify_activities].apply(set)
        activity_pairs = num_trace_binding.copy()
        for (activity1, activity2) in activity_pairs.keys():
            count = trace_activities.apply(lambda activities: activity1 in activities and activity2 in activities).sum()
            activity_pairs[(activity1, activity2)] = count

        return activity_pairs

    def compute_suppr_list(self, num_trace_binding):
        suppr_list = {}
        for pair, res_value in num_trace_binding.items():
            suppr = res_value / self._total_num_trace
            suppr_list[pair] = suppr

        return suppr_list

    def compute_suppA_list(self, activity_pairs):
        suppA_list = {}
        for pair, res_value in activity_pairs.items():
            suppA = res_value / self._total_num_trace
            suppA_list[pair] = suppA

        return suppA_list

    def compute_confr_list(self, suppr_list, suppA_list):
        confr_list = {}
        for pair, suppr in suppr_list.items():
            if pair in suppA_list:
                suppA = suppA_list[pair]
                confr = suppr / suppA
                confr_list[pair] = confr

        return confr_list

    def compute_sigmaB_list(self, log, activity_pairs):
        sigmaB_list = {pair: 0 for pair in activity_pairs.keys()}
        for trace_id, trace_data in log.groupby(tag_to_identify_trace):
            trace_data = trace_data.sort_values(by=tag_to_identify_timestamp)
            
            for (activity_A, activity_B) in activity_pairs.keys():
                events_B = trace_data[trace_data[tag_to_identify_activities] == activity_B]
                found = False
                for _, event_B in events_B.iterrows():
                    previous_resources = set(
                        res
                        for resources_list in trace_data[trace_data[tag_to_identify_timestamp] < event_B[tag_to_identify_timestamp]][tag_to_identify_resources]
                        for res in resources_list
                    )
                    if any(res in previous_resources for res in event_B[tag_to_identify_resources]):
                        found = True
                        break

                if found:
                    sigmaB_list[(activity_A, activity_B)] += 1

        return sigmaB_list

    def compute_suppB_list(self, sigmaB_list):
        suppB_list = {}
        for pair, sigmaB in sigmaB_list.items():
            suppB = sigmaB / self._total_num_trace  
            suppB_list[pair] = suppB

        return suppB_list

    def compute_intr_list(self, suppr_list, suppA_list, suppB_list):
        intr_list = {}
        for pair, suppr in suppr_list.items():
            if pair in suppA_list and pair in suppB_list:
                suppA = suppA_list[pair]
                suppB = suppB_list[pair]
                p = suppA * suppB
                if p != 0:
                    intr = suppr / p  
                else:
                    intr = 0
                intr_list[pair] = intr

        return intr_list

    # remove from the list of pair activities the pair in which the two activities have associated only one set of resources, because there is no point in having a worklist
    # since the two activities in any circumstance are executed only by that resource/resources.
    def delete_pair_with_single_resource(self, app_list, list_act_res):
        filtered_pairs = []
        for (activity1, activity2) in app_list:
            resources1 = list_act_res.get(activity1, [])
            resources2 = list_act_res.get(activity2, [])
            if not (len(resources1) == 1 and len(resources2) == 1 and Counter(resources1[0]) == Counter(resources2[0])):
                filtered_pairs.append((activity1, activity2))

        return filtered_pairs

    def pair_with_max_value(self, app_list):
        max_pairs = {}
        for pair, value in app_list.items():
            elements = set(pair)
            existing_pairs = [
                key for key in max_pairs if not elements.isdisjoint(set(key))
            ]
            if existing_pairs:
                for existing_pair in existing_pairs:
                    if value > max_pairs[existing_pair]:
                        del max_pairs[existing_pair]
                        max_pairs[pair] = value
                    elif pair not in max_pairs:
                        max_pairs[existing_pair] = max(max_pairs[existing_pair], value)
            else:
                max_pairs[pair] = value
        return max_pairs

    #def compute_worlist_without_intr_value(self, suppr_list, confr_list, res_act):
    def compute_worlist_without_intr_value(self):
        valid_pairs_without_intr = []
        pairs_value = {}
        for pair, suppr in self._suppr_list.items():
            if suppr >= self._threshold_minSupp:
                if pair in self._confr_list:
                    confr = self._confr_list[pair]
                    if confr >= self._threshold_minConf:
                        valid_pairs_without_intr.append(pair)
                        pairs_value[pair] = suppr + confr

        valid_pairs_without_intr = self.delete_pair_with_single_resource(valid_pairs_without_intr, self._res_act)

        max_pairs = self.pair_with_max_value(pairs_value)

        final_valid_pairs_without_intr = []
        for pair in valid_pairs_without_intr:
            if pair in max_pairs:
                final_valid_pairs_without_intr.append(pair)
        
        return final_valid_pairs_without_intr

    #def compute_worklist_with_intr_value(self, suppr_list, confr_list, intr_list, act_res):
    def compute_worklist_with_intr_value(self):
        valid_pairs_with_intr = []
        pairs_value = {}
        for pair, suppr in self._suppr_list.items():
            if suppr >= self._threshold_minSupp:
                if pair in self._confr_list:
                    confr = self._confr_list[pair]
                    if confr >= self._threshold_minConf:
                        if pair in self._intr_list:
                            intr = self._intr_list[pair]
                            if intr >= self._threshold_minInt:
                                valid_pairs_with_intr.append(pair)
                                pairs_value[pair] = suppr + confr + intr

        valid_pairs_with_intr = self.delete_pair_with_single_resource(valid_pairs_with_intr, self._res_act)

        max_pairs = self.pair_with_max_value(pairs_value)
        
        final_valid_pairs_with_intr = []
        for pair in valid_pairs_with_intr:
            if pair in max_pairs:
                final_valid_pairs_with_intr.append(pair)

        return final_valid_pairs_with_intr
