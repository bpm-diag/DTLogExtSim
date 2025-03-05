import pm4py
import pandas as pd
import os
import platform as pl
import subprocess
import xml.etree.ElementTree as ET


tag_to_identify_activities = 'concept:name'
tag_to_identify_resources = 'org:resource'
tag_to_identify_trace = 'case:concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_node_lifecycle = 'lifecycle:transition'
tag_to_identify_pool = 'poolName'
tag_to_identify_cost_hour = 'resourceCost'
tag_to_identify_fixed_cost = 'fixedCost'
tag_to_identify_node_type = 'nodeType'

class ExtractionBPMN():

    def __init__(self, log, settings, with_start_end_act):
        self._log = log.copy()
        self._settings = settings
        self._path = settings[0]['path']
        self._name = settings[0]['namefile']
        self._diag_log = settings[0]['diag_log']
        self._num_timestamp = settings[0]['num_timestamp']
        self._with_start_end_act = with_start_end_act
        self._eta = settings[0]['eta']
        self._eps = settings[0]['eps']

        self._log.loc[self._log[tag_to_identify_resources].isna(), tag_to_identify_resources] = None
        if self._settings[0]['cost_hour']:
            self._log.loc[self._log[tag_to_identify_cost_hour].isna(), tag_to_identify_cost_hour] = None
        if self._settings[0]['fixed_cost']:
            self._log.loc[self._log[tag_to_identify_fixed_cost].isna(), tag_to_identify_fixed_cost] = None
        if self._settings[0]['setup_time']:
            self._log = self._log[~self._log[tag_to_identify_node_lifecycle].isin(['startSetupTime', 'endSetupTime'])].reset_index(drop=True)
        if self._settings[0]['fixed_cost']:
            self._log = self._log.drop(columns=[tag_to_identify_fixed_cost])
        if self._diag_log:
            pattern1 = r'Gateway'
            pattern4 = r'Event'
            self._log = self._log[~self._log[tag_to_identify_activities].str.contains(pattern1, case=False, na=False)]
            self._log = self._log[~self._log[tag_to_identify_activities].str.contains(pattern4, case=False, na=False)]
            self._log = self._log[~self._log[tag_to_identify_node_lifecycle].str.contains(pattern1, case=False, na=False)]
            self._log = self._log[~self._log[tag_to_identify_node_type].str.contains(pattern1, case=False, na=False)]
            self._log = self._log.drop(columns=[tag_to_identify_pool])
            self._log[tag_to_identify_node_lifecycle] = self._log[tag_to_identify_node_lifecycle].replace({
                'assign': 'start',
                'start': 'assign'
                })

        self._log = self._log.where(pd.notna(self._log), None)

        log_1 = self._log[self._log[tag_to_identify_node_lifecycle].isin(['start', 'complete'])].reset_index(drop=True)

        if self._diag_log and not self._with_start_end_act:
            log_1 = log_1[~log_1[tag_to_identify_node_type].isin(['startEvent', 'endEvent'])].reset_index(drop=True)
        
        if not self._diag_log and not self._with_start_end_act:
            pattern2 = r'START'
            pattern3 = r'END'
            log_1 = log_1[~log_1[tag_to_identify_activities].str.contains(pattern2, case=False, na=False)]
            log_1 = log_1[~log_1[tag_to_identify_activities].str.contains(pattern3, case=False, na=False)]

        directory = os.path.join(self._path, 'input_data')
        os.makedirs(directory, exist_ok=True)
        pm4py.write_xes(log_1, os.path.join(directory, self._name + '_discovery.xes'), case_id_key=tag_to_identify_trace) 

        self.spliminer()
        
        self.adapt_bpmn_model_format()  

    def spliminer(self):
        print(" -- SplitMiner Execution --")
        directory = os.path.join(self._path, 'output_data')
        os.makedirs(directory, exist_ok=True)
        file_name = os.path.join(directory, self._name + "_sm2")

        input_route = self._path + "input_data/" + self._name + "_discovery.xes"

        sep = ';' if pl.system().lower() == 'windows' else ':'
        # Mining structure definition
        args = ['java']
        if not pl.system().lower() == 'windows':
            args.append('-Xmx2G')

        sm2_path = "external_tools/splitminer2/sm2.jar"
        args.extend(['-cp',
                        (sm2_path+sep+os.path.join(
                            'external_tools','splitminer2','lib','*')),
                        'au.edu.unimelb.services.ServiceProvider',
                        'SMD',
                        self._eta, self._eps, #eta value and epsilon value
                        'false', 'false', 'false',
                        input_route,
                        file_name])
        
        
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        print("Output:\n", stdout) 
        print("Error:\n", stderr)

        bpmn_model = pm4py.read_bpmn(file_name + ".bpmn")

        directory = os.path.join(self._path + 'output_data/', 'output_file')
        os.makedirs(directory, exist_ok=True)
        pm4py.write_bpmn(bpmn_model, os.path.join(directory, self._name + '_pm4py.bpmn'))

        

    def adapt_bpmn_model_format(self):
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
            tree.write(self._path + 'output_data/output_file/' + self._name + '_pm4py.bpmn', encoding='utf-8', xml_declaration=True)

        bpmn_file_path = self._path + 'output_data/output_file/' + self._name + '_pm4py.bpmn'
        process_id = extract_process_id(bpmn_file_path)

        collaboration_id = "Collaboration_diag"
        participant_id = "Participant_diag"
        pool_name = "main"
        add_collaboration_to_bpmn(bpmn_file_path, process_id, collaboration_id, participant_id, pool_name)