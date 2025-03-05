import pm4py
import pandas as pd
from pandas.core.common import flatten
from collections import defaultdict

tag_to_identify_activities = 'concept:name'
tag_to_identify_resources = 'org:resource'
tag_to_identify_trace = 'case:concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_node_lifecycle = 'lifecycle:transition'
tag_to_identify_node_type = 'nodeType'


class BranchProbCalculation():
    
    def __init__(self, log, bpmn_model, settings, intermediate_model=False):
        print("---CALCULATE BRANCHING PROBABILITIES---")
        self._log = log.copy()
        self._bpmn_model = bpmn_model
        self._settings = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        self._intermediate_model = intermediate_model

        self._exclusive_diverging_gateway = self.diverging_gateway(self._bpmn_model)
        #extract the tasks/node output and input for each gateway
        self._out_task_of_gateway, self._in_task_of_gateway, self._gateway_flow = self.succ_prec_events_of_gateway(self._exclusive_diverging_gateway, self._bpmn_model)

        self._branches = self.compute_branches(self._in_task_of_gateway, self._out_task_of_gateway)

        self._branches_probabilities = self.compute_branch_probabilities(self._log, self._branches)
    
        flow_prob_app = self.extract_flow_probabilities(self._branches_probabilities, self._gateway_flow)
        self._flow_prob = {}
        for node, flows in flow_prob_app.items():
            filtered_flows = [flow for flow in flows if flow['source'] and flow['destination']]
            if filtered_flows:
                self._flow_prob[node] = filtered_flows

        self.save_on_file_branch_prob(self._flow_prob)


    def extract_flow_probabilities(self, branch_prob, flow):
        result = {}

        for node, flow_list in flow.items():
            result[node] = []
            
            for flow_id, activities in flow_list:
                if isinstance(activities, list):
                    activity_list = activities
                else:
                    activity_list = [activities]

                if node in branch_prob:
                    total_probability = 0.0
                    source = set()
                    destination = set()
                    for prob_info in branch_prob[node]:
                        act1, act2 = prob_info['pair']
                        prob = float(prob_info['probability'])

                        if act2 in activity_list:
                            source.add(act1)
                            destination.add(act2)
                            total_probability += prob

                    result[node].append({'flow': flow_id, 'total_probability': round(total_probability, 2), 'source': source, 'destination': destination})

        for node, flows in result.items():
            total_probability = sum(flow['total_probability'] for flow in flows)
            if total_probability != 1:
                difference = 1 - total_probability
                flows[0]['total_probability'] += difference

        return result


    def diverging_gateway(self, model):
        #extract the diverging gateway from model
        exclusive_gateway = {}
        i = 0
        for node in model.get_nodes():
            if isinstance(node, pm4py.BPMN.ExclusiveGateway):
                if node.get_gateway_direction() == pm4py.BPMN.Gateway.Direction.DIVERGING:
                    exclusive_gateway[i] = node
                    i += 1
        return exclusive_gateway

    def succ_prec_events_of_gateway(self, exclusive_gateway, bpmn_model):
        #find the events succesive and precedent of each gateway
        #if the succ and/or prec is another gateway, save it
        gateway_flow = {}
        gateway_path_succ = {}
        gateway_path_prec = {}
        gateway_node_target = list()
        gateway_node_source = list()
        for i in range(len(exclusive_gateway)):
            gateway = exclusive_gateway[i]
            gateway_path_succ[gateway] = []
            gateway_path_prec[gateway] = []
            gateway_flow[gateway] = []
            for f in bpmn_model.get_flows():
                if f.get_source() == gateway:
                    gateway_path_succ[gateway].append(f.get_target())
                    gateway_flow[gateway].append((f.get_id(), f.get_target()))
                    if isinstance(f.get_target(), pm4py.BPMN.Gateway):
                        gateway_node_target.append(f.get_target())
                elif f.get_target() == gateway:
                    gateway_path_prec[gateway].append(f.get_source())
                    gateway_flow[gateway].append((f.get_id(), f.get_source()))
                    if isinstance(f.get_source(), pm4py.BPMN.Gateway):
                        gateway_node_source.append(f.get_source())
            i += i

        # substitute the out gateway of each diverging gateway with the task
        if len(gateway_node_target) > 0:
            target_nodes = {}
            for n in gateway_node_target:
                target_nodes[n] = self.find_task_succ(n)
                target_nodes[n] = list(flatten(target_nodes[n]))

            for gnt in gateway_path_succ.copy():
                for n in list(gateway_path_succ[gnt].copy()):
                    if n in target_nodes:
                        gateway_path_succ[gnt].remove(n)
                        for i, (fl, act) in enumerate(gateway_flow[gnt]):
                            act = act[0] if isinstance(act, list) else act
                            n = n[0] if isinstance(n, list) else n
                            if n == act:
                                gateway_flow[gnt][i] = (fl, target_nodes[0] if isinstance(act, str) else self.extract_list_task_name(target_nodes[n]))
                            else:
                                if isinstance(act, str):
                                    gateway_flow[gnt][i] = (fl, act)
                                else:
                                    if act.get_name():
                                        gateway_flow[gnt][i] = (fl, act.get_name())

                        for elem in target_nodes[n]:
                            gateway_path_succ[gnt].append(elem)
                    else:
                        for i, (fl, act) in enumerate(gateway_flow[gnt]):
                            act = act[0] if isinstance(act, list) else act
                            n = n[0] if isinstance(n, list) else n
                            if n == act:
                                gateway_flow[gnt][i] = (fl, act if isinstance(act, str) else act.get_name())


        # substitute the in gateway of each diverging gateway with the task
        if len(gateway_node_source) > 0:
            target_nodes = {}
            for n in gateway_node_source:
                target_nodes[n] = self.find_task_prec(n)
                target_nodes[n] = list(flatten(target_nodes[n]))

            for gnt in gateway_path_prec.copy():
                for n in list(gateway_path_prec[gnt].copy()):
                    if n in target_nodes:
                        gateway_path_prec[gnt].remove(n)

                        for i, (fl, act) in enumerate(gateway_flow[gnt]):
                            act = act[0] if isinstance(act, list) else act
                            n = n[0] if isinstance(n, list) else n
                            if n == act:
                                gateway_flow[gnt][i] = (fl, target_nodes[0] if isinstance(act, str) else self.extract_list_task_name(target_nodes[n]))
                            else:
                                if isinstance(act, str):
                                    gateway_flow[gnt][i] = (fl, act)
                                else:
                                    if act.get_name():
                                        gateway_flow[gnt][i] = (fl, act.get_name())
                        
                        for elem in target_nodes[n]:
                            gateway_path_prec[gnt].append(elem)
                        
                    else:
                        for i, (fl, act) in enumerate(gateway_flow[gnt]):
                            act = act[0] if isinstance(act, list) else act
                            n = n[0] if isinstance(n, list) else n
                            if n == act:
                                gateway_flow[gnt][i] = (fl, act if isinstance(act, str) else act.get_name())

        if len(gateway_node_source) == 0 and len(gateway_node_target) == 0:
            for n in gateway_flow:
                for i, (fl, act)in enumerate(gateway_flow[n]):
                    gateway_flow[n][i] = (fl, act if isinstance(act, str) else act.get_name())

        return gateway_path_succ, gateway_path_prec, gateway_flow
        

    #function to find the succ event of gateway consider that the real succ block is a gateway
    def find_task_succ(self, node) -> list:
        tasks_list = list()
        if isinstance(node, pm4py.BPMN.Task):
            return node

        for f in self._bpmn_model.get_flows():
            if f.get_source() == node:
                tasks_list.append(self.find_task_succ(f.get_target()))
        
        return tasks_list

    #function to find the prec event of gateway consider that the real prec block is a gateway
    def find_task_prec(self, node) -> list:
        tasks_list = list()
        if isinstance(node, pm4py.BPMN.Task):
            return node

        for f in self._bpmn_model.get_flows():
            if f.get_target() == node:
                tasks_list.append(self.find_task_prec(f.get_source()))
        
        return tasks_list
    
    def extract_list_task_name(self, l):
            return [elem.get_name() if elem.get_name() != "" else "event" for elem in l]

    def compute_branches(self, gateway_path_prec, gateway_path_succ):
        #insert in list branches for each gataway the list of source tasks and the list of destination tasks
        branches = {}
        for g in gateway_path_prec:
            if g in gateway_path_succ:
                branches[g] = {
                    "source": self.extract_list_task_name(gateway_path_prec[g]),
                    "destination": self.extract_list_task_name(gateway_path_succ[g])
                }
        return branches
    
    def delete_selfloop_log(self, log):
        prec_row = None
        i = 0
        self_loops_activities = {}
        self_loops_count = {}
        log_noloop_app = []
        for index, row in log.iterrows():
            if prec_row is not None:
                if prec_row[tag_to_identify_trace] == row[tag_to_identify_trace]:
                    if prec_row[tag_to_identify_activities] == row[tag_to_identify_activities]:
                        if i in self_loops_count:
                            self_loops_activities[i] = [[row[tag_to_identify_trace]], [row[tag_to_identify_activities]]]
                            self_loops_count[i] += 1
                        else:
                            self_loops_count[i] = 0
                            self_loops_activities[i] = [[row[tag_to_identify_trace]], [row[tag_to_identify_activities]]]
                            self_loops_count[i] += 1
                    else:
                        prec_row = row
                        i+=1
                        log_noloop_app.append(row)
                else:
                    prec_row = row 
                    i+=1
                    log_noloop_app.append(row)
            else:
                prec_row = row
                log_noloop_app.append(row)

        self_loops = []
        if not self_loops_activities:
            log_noloop = log
        else:
            # log without self loops
            log_noloop = pd.DataFrame(log_noloop_app)
            log_noloop.reset_index(drop=True, inplace=True)

            for j in range(i):
                if j in self_loops_activities:
                    self_loops.append((self_loops_activities[j][0][0], self_loops_activities[j][1][0], self_loops_count[j]+1))
        return log_noloop

    def compute_branch_probabilities(self, log, branches):
        
        no_selfloop_log = self.delete_selfloop_log(log)

        # create a list of pairs (source, destination) from branches
        branches_pairs = []
        node_mapping = {}
        for node, paths in branches.items():
            for source in paths['source']:
                for destination in paths['destination']:
                    pair = (source, destination)
                    branches_pairs.append(pair)
                    node_mapping[pair] = node

        branches_group_dict = defaultdict(list)
        for f, s in branches_pairs:
            branches_group_dict[f].append(s)

        branches_group = [(first, tuple(seconds)) for first, seconds in branches_group_dict.items()]

        counts = defaultdict(int)
        for source_act, destination_act_list in branches_group:
            for trace_id, trace_activities in no_selfloop_log.groupby(tag_to_identify_trace):
                sorted_events = trace_activities.sort_values(tag_to_identify_timestamp).reset_index(drop=True)
                for i in range(len(sorted_events) - 1):
                    if source_act == sorted_events.iloc[i][tag_to_identify_activities]:
                        source_row = sorted_events.iloc[i]
                        source_activity = source_row[tag_to_identify_activities]
                        for j in range(i + 1, len(sorted_events)):
                            if source_act != sorted_events.iloc[j][tag_to_identify_activities]:
                                if sorted_events.iloc[j][tag_to_identify_activities] in destination_act_list:
                                    dest_row = sorted_events.iloc[j]
                                    destination_activity = dest_row[tag_to_identify_activities]
                                    counts[(source_activity, destination_activity)] += 1
                                    break
                            else:
                                break

        for pair, count in counts.items():
            print(f"Pair {pair} repeats {count} times")

        self._tot = {}
        for g, p in branches.items():
            self._tot[g] = 0
            for s in p['source']:
                for d in p['destination']:
                    self._tot[g] = self._tot[g] + counts[s, d]

        #compute the probabilities for each branch of gateway
        branches_probabilities = {}
        for g, p in branches.items():
            branches_probabilities[g] = []
            for s in p['source']:
                for d in p['destination']:
                    if self._tot[g] != 0:
                        branches_probabilities[g].append({
                        "pair": (s, d),
                        "probability": str(counts[(s, d)] / self._tot[g])
                    })
                    else:
                        branches_probabilities[g].append({
                        "pair": (s, d),
                        "probability": str(0)
                    })

        return branches_probabilities

    def save_on_file_branch_prob(self, flow_prob):
        if self._intermediate_model:
            with open(self._path + 'output_data/output_file/branch_prob_' + self._name + '_interm_points.txt', 'w') as file:
                file.write("Gateway probabilities: \n")
                file.write(f"{flow_prob}")
        else:
            with open(self._path + 'output_data/output_file/branch_prob_' + self._name + '.txt', 'w') as file:
                file.write("Gateway probabilities: \n")
                file.write(f"{flow_prob}")