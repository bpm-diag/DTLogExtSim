import pm4py
import pandas as pd
import xml.etree.ElementTree as ET

from branching_probabilities import BranchProbCalculation as bpcalc

tag_to_identify_activities = 'concept:name'
tag_to_identify_resources = 'org:resource'
tag_to_identify_trace = 'case:concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_node_lifecycle = 'lifecycle:transition'
tag_to_identify_node_type = 'nodeType'

class IntermediateStartPoint():
    
    def __init__(self, log, model_bpmn, settings):
        self._log = log.copy()
        self._model = model_bpmn
        self._setting = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        self._num_timestamp = settings[0]['num_timestamp']
        self._diaglog = settings[0]['diag_log']
        self._model_name = settings[0]['model_name']
        self._output_name = settings[0]['output_name']

        self._correct_order_diag_log = False
        first_trace = self._log[self._log[tag_to_identify_trace] == self._log[tag_to_identify_trace].iloc[0]]
        second_element = first_trace.iloc[1]
        if second_element[tag_to_identify_node_lifecycle] == "assign":
            self._correct_order_diag_log = True

        #TO-DO: cosidera anche quando ci sono parallelismi (mettere un parallelo per eseguire le attività che non erano terminate)
        self._final_activities_interrupted, self._final_activities_ended = self.final_activities_per_trace(self._log.copy())
        self._forced_flow_intermediate_states = self.crete_new_model_and_return_forced_flow(self._log.copy(), self._model, self._final_activities_interrupted, self._final_activities_ended) 

        self._forced_instance_types = self.extract_repetition_for_each_forced_traces(self._forced_flow_intermediate_states, self._final_activities_interrupted, self._final_activities_ended)
        
        self._flow_probabilities = self.generate_gateway_pair()

        self.save_on_file(self._forced_flow_intermediate_states, self._forced_instance_types, self._flow_probabilities)

    def branch_prob(self, log):
        pattern1 = r'Gateway'
        temp_log_1 = log

        if self._diaglog:
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern1, case=False, na=False)]
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_node_type].str.contains(pattern1, case=False, na=False)]
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_node_lifecycle].str.contains(pattern1, case=False, na=False)]
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_node_type].str.contains(pattern1, case=False, na=False)]

        bpmn_model = pm4py.read_bpmn(self._path + "output_data/" + self._output_name + "_intermediate_start_points.bpmn") 

        self._BranchProb = bpcalc(temp_log_1, bpmn_model, self._setting, True)

        return self._BranchProb._flow_prob

    def generate_gateway_pair(self):
        flow_new = self._forced_instance_types['Flow'].tolist()
        flow_numbers = self._forced_instance_types['Flow'].str.extract(r'_(\d+)$')[0].astype(int).tolist()
        flow_numbers.sort()

        flow_prob = []
        for f_n in flow_numbers:
            if f_n == flow_numbers[-1]:
                flow_id = f"flow_g_t_{f_n}"
            else:
                flow_id = f"flow_g_g_{f_n + 1}"
            flow_prob.append((flow_id, 0.9))

        for f in flow_new:
            flow_prob.append((f, 0.1))

        return flow_prob

    def extract_repetition_for_each_forced_traces(self, forced_flow_intermediate_states, final_activities_interrupted, final_activities_ended):
        rep_interrupted = self._final_activities_interrupted.groupby('task').size()
        rep_ended = self._final_activities_ended.groupby('task').size()

        i = 0
        result = []
        for flow, (status, source, activity_target) in forced_flow_intermediate_states.items():
            if status == 'interrupted' and activity_target in rep_interrupted:
                value = rep_interrupted[activity_target]
                result.append({
                'Flow': flow,
                'Status': status,
                'Instance Type': 'A' + str(i),
                'Repetition Instance Type': value
                })
            if status == 'ended' and activity_target in rep_ended:
                value = rep_ended[activity_target]
                result.append({
                'Flow': flow,
                'Status': status,
                'Instance Type': 'A' + str(i),
                'Repetition Instance Type': value
                })
            i += 1
            
        df_result = pd.DataFrame(result)
        return df_result

    def crete_new_model_and_return_forced_flow(self, log, model, final_activities_interrupted, final_activities_ended):

        app_model = pm4py.read_bpmn(self._path + 'output_data/output_file/' + self._model_name)

        pattern1 = r'Start'
        start_act_log = log[log[tag_to_identify_activities].str.contains(pattern1, case=False, na=False)]
        start_activity = start_act_log[tag_to_identify_activities].unique()[0]

        flow_start_source = None
        flow_start_target = None
        flow_start_to_delete = None
        for f in app_model.get_flows():
            if f.get_source().get_name() == start_activity:
                for f1 in model.get_flows():
                    if f1.get_id() == f.get_id():
                        flow_start_to_delete = f1
                        break
                flow_start_source = flow_start_to_delete.get_source()
                flow_start_target = flow_start_to_delete.get_target()

        final_activities = [('interrupted', element) for element in final_activities_interrupted['task'].unique()] + [('ended', element) for element in final_activities_ended['task'].unique()]

        forced_flow_intermediate_states = dict()
        start_gateway = []
        i = 0
        num_final_act= len(final_activities)
        for type, final_act in final_activities:
            for f in app_model.get_flows():
                flow_to_check = None
                if type == 'interrupted': #put gateway before interrupted activity
                    flow_to_check = f.get_target()
                else: # 'ended' put gateway after interrupted activity
                    flow_to_check = f.get_source()


                if flow_to_check.get_name() == final_act:
                    flow_to_delete = None
                    for f1 in model.get_flows():
                        if f1.get_id() == f.get_id():
                            flow_to_delete = f1
                            break
                    
                    source_flow = flow_to_delete.get_source()
                    target_flow = flow_to_delete.get_target()
                    process_id = target_flow.get_process()
                    app_in_arcs = target_flow.get_in_arcs()

                    # new gateway before the last activities stopped in the cut log
                    new_gateway = pm4py.BPMN.ExclusiveGateway(id="id_" + str(i), gateway_direction=pm4py.BPMN.Gateway.Direction.DIVERGING, process=process_id)
                    if type == "interrupted":
                        new_flow = pm4py.BPMN.Flow(source_flow, new_gateway, id=f.get_id(), name=f.get_id(), process=process_id)
                        new_flow1 = pm4py.BPMN.Flow(new_gateway, target_flow, id="flow_b_" + str(i), name="flow_b_" + str(i), process=process_id)
                    else:
                        new_flow = pm4py.BPMN.Flow(source_flow, new_gateway, id="flow_a_" + str(i), name="flow_a_" + str(i), process=process_id)
                        new_flow1 = pm4py.BPMN.Flow(new_gateway, target_flow, id="flow_b_" + str(i), name="flow_b_" + str(i), process=process_id)
                    new_gateway.add_in_arc(new_flow)
                    new_gateway.add_out_arc(new_flow1)

                    # delete flow
                    model.remove_flow(flow_to_delete)

                    target_flow.remove_in_arc(app_in_arcs[0])
                    target_flow.add_in_arc(new_flow1)
                    source_flow.add_out_arc(new_flow)

                    # new gateway at start of model to jump to the intermediate gateway
                    new_start_gateway = pm4py.BPMN.ExclusiveGateway(id="id_start_" + str(i), gateway_direction=pm4py.BPMN.Gateway.Direction.DIVERGING, process=process_id)
                    flow_start_intermediate_gateway = pm4py.BPMN.Flow(new_start_gateway, new_gateway, id="flow_s_i_a_" + str(i), name="flow_s_i_a_" + str(i), process=process_id)
                    new_gateway.add_in_arc(flow_start_intermediate_gateway)
                    new_start_gateway.add_out_arc(flow_start_intermediate_gateway)

                    forced_flow_intermediate_states[flow_start_intermediate_gateway.get_id()] = (type, new_start_gateway.get_id(), final_act)

                    if start_gateway:
                        prec_gateway = start_gateway[-1]
                        new_flow_g_g = pm4py.BPMN.Flow(prec_gateway, new_start_gateway, id="flow_g_g_" + str(i), name="flow_g_g_" + str(i), process=process_id)
                        new_start_gateway.add_in_arc(new_flow_g_g)
                        prec_gateway.add_out_arc(new_flow_g_g)
                        model.add_flow(new_flow_g_g)
                        if i + 1 == num_final_act:
                            new_flow_end = pm4py.BPMN.Flow(new_start_gateway, flow_start_target, id="flow_g_t_" + str(i), name="flow_g_t_" + str(i), process=process_id)
                            new_start_gateway.add_out_arc(new_flow_end)
                            flow_start_target.add_in_arc(new_flow_end)
                            model.add_flow(new_flow_end)
                    else:
                        new_flow_start = pm4py.BPMN.Flow(flow_start_source, new_start_gateway, id="flow_s_g_" + str(i), name="flow_s_g_" + str(i), process=process_id)
                        new_start_gateway.add_in_arc(new_flow_start)
                        flow_start_source.add_out_arc(new_flow_start)
                        model.add_flow(new_flow_start)    
                        if i + 1 == num_final_act:
                            new_flow_end = pm4py.BPMN.Flow(new_start_gateway, flow_start_target, id="flow_g_t_" + str(i), name="flow_g_t_" + str(i), process=process_id)
                            new_start_gateway.add_out_arc(new_flow_end)
                            flow_start_target.add_in_arc(new_flow_end)
                            model.add_flow(new_flow_end)
                    
                    start_gateway.append(new_start_gateway)

                    model.add_node(new_gateway)
                    model.add_flow(new_flow)
                    model.add_flow(new_flow1)  
                    model.add_node(new_start_gateway)     
                    model.add_flow(flow_start_intermediate_gateway)
                    break    
            i+=1

        f_app_to_delete = None
        for f_app in model.get_flows():
            if f_app.get_id() == flow_start_to_delete.get_id():
                f_app_to_delete = f_app
        if f_app_to_delete != None:
            model.remove_flow(f_app_to_delete)

        bpmn_file_path = self._path + "output_data/" + self._output_name + "_intermediate_start_points.bpmn"
        pm4py.write_bpmn(model, bpmn_file_path)
        self.adapt_bpmn_model_format(bpmn_file_path)

        return forced_flow_intermediate_states

    def final_activities_per_trace(self, log):
        log.rename(columns={
                tag_to_identify_trace: 'caseid',
                tag_to_identify_activities: 'task',
                tag_to_identify_node_lifecycle: 'event_type',
                tag_to_identify_timestamp: 'timestamp'}, inplace=True)
        
        log = (log[~log.task.isin(['Start', 'End', 'start', 'end'])].reset_index(drop=True))
        log = self.reorder_xes(log)
        log = pd.DataFrame(log)

        final_activities_interrupted = log[
            (log['assign_timestamp'] == "nan") |
            (log['start_timestamp'] == "nan") |
            (log['end_timestamp'] == "nan")]
        
        #final activities of tracks that were interrupted at a point where the last activities were not finished, restart from the end of the previous activity
        trace_id_interrupted_activities = final_activities_interrupted['caseid'].unique()

        log_filter = log[~log['caseid'].isin(trace_id_interrupted_activities)]

        # final activities of tracks that were interrupted at a point where the last activities had ended, start again from there
        final_activities_ended = log_filter.loc[log_filter.groupby('caseid')['end_timestamp'].idxmax()]

        return final_activities_interrupted, final_activities_ended


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
                for i in range(0, len(trace)):
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
                for i in range(0, len(trace)):
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
                        'end_timestamp': "nan"})
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
                    'start_timestamp': "nan",
                    'end_timestamp': complete_event['timestamp']})
            elif start_event:
                temp_trace.append(
                    {'caseid': caseid,
                    'task': trace[i]['task'],
                    'assign_timestamp': trace[i]['timestamp'],
                    'start_timestamp': start_event['timestamp'],
                    'end_timestamp': "nan"})
            else:
                temp_trace.append(
                    {'caseid': caseid,
                    'task': trace[i]['task'],
                    'assign_timestamp': trace[i]['timestamp'],
                    'start_timestamp': "nan",  
                    'end_timestamp': "nan"})
                
    def adapt_bpmn_model_format(self, bpmn_file_path):
        def extract_process_id(bpmn_file_path):
            tree = ET.parse(bpmn_file_path)
            root = tree.getroot()

            process_id = None
            for process in root.findall(".//{*}process"):
                process_id = process.get("id")
                if process_id:
                    break

            return process_id
        
        def add_collaboration_to_bpmn(bpmn_file_path, process_id, collaboration_id, participant_id, pool_name):
            namespaces = {
                'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
                'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
                'omgdc': 'http://www.omg.org/spec/DD/20100524/DC',
                'omgdi': 'http://www.omg.org/spec/DD/20100524/DI',
                'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                'xsd': 'http://www.w3.org/2001/XMLSchema'
            }

            for prefix, uri in namespaces.items():
                ET.register_namespace(prefix, uri)

            tree = ET.parse(bpmn_file_path)
            root = tree.getroot()

            collaboration = ET.Element('{http://www.omg.org/spec/BPMN/20100524/MODEL}collaboration', attrib={'id': 'Collaboration_0idnrdl'})
            participant = ET.SubElement(collaboration, '{http://www.omg.org/spec/BPMN/20100524/MODEL}participant', attrib={
                'id': participant_id,
                'name': pool_name,
                'processRef': process_id
            })

            root.insert(1, collaboration)
            tree.write(self._path + "output_data/output_file/" + self._output_name + "_intermediate_start_points_out.bpmn", encoding='utf-8', xml_declaration=True)

        process_id = extract_process_id(bpmn_file_path)

        collaboration_id = "Collaboration_diag"
        participant_id = "Participant_diag"
        pool_name = "main"
        add_collaboration_to_bpmn(bpmn_file_path, process_id, collaboration_id, participant_id, pool_name)


    def save_on_file(self, forced_flow_intermediate_states, forced_instance_types, flow_probabilities):
        with open(self._path + 'output_data/output_file/intermediate_states_sim_data' + self._output_name + '.txt', 'w') as file:
            file.write("Information to execute a simulation starting by intermediate states based on unfinished log traces\n")
            file.write("\nFlow to start from intermedate state\n")
            file.write(f"{forced_flow_intermediate_states}\n")    
            file.write("\nIntermediate Forced Instance Types\n")
            file.write(f"{forced_instance_types}")
            file.write("\Flow Probabilities\n")
            file.write(f"{flow_probabilities}")