import subprocess 
import json
from bpmn_python import bpmn_diagram_rep as diagram
import xml.etree.ElementTree as ET
import os

ET.register_namespace('', 'http://www.omg.org/spec/BPMN/20100524/MODEL')
ET.register_namespace('bpmndi', 'http://www.omg.org/spec/BPMN/20100524/DI')
ET.register_namespace('dc', 'http://www.omg.org/spec/DD/20100524/DC')
ET.register_namespace('di', 'http://www.omg.org/spec/DD/20100524/DI')

TAG_NAME = "diagbp"
DOWNLOAD_FOLDER="download"

class BpmnParser:
    def __init__(self):
        pass


    def generate_json_from_bpmn(self, simulation_path, file_bpmn_no_ext, bpmn_filename):
        try:
            bpmnGraph = diagram.BpmnDiagramGraph()
            bpmnGraph.create_new_diagram_graph(diagram_name="diagram1")
            bpmnGraph.load_diagram_from_xml_file(simulation_path + "/" + bpmn_filename)


            # Manually construct a dictionary from the bpmnGraph
            bpmnDictionary = {
                'diagram_attributes': bpmnGraph.diagram_attributes,
                'plane_attributes': bpmnGraph.plane_attributes,
                'sequence_flows': bpmnGraph.sequence_flows,
                'collaboration': bpmnGraph.collaboration,
            }
            pool_names = {}
            if bpmnDictionary["collaboration"]:
                for participant_id, participant in bpmnDictionary['collaboration']['participants'].items():
                    pool_names[participant['processRef']] = participant['name']

            process_elements = {}
            for process_id, process_element in bpmnGraph.process_elements.items():
                node_details = {}
                for node_id in process_element['node_ids']:
                    node_info = bpmnGraph.diagram_graph._node[node_id]
                    node_type = node_info.get('type', 'Unknown')
                    node_subtype = None
                    attached_to_id = None
                    if node_type == 'intermediateCatchEvent' or node_type == 'boundaryEvent' or node_type == 'endEvent':
                        # Get the specific type of the intermediate catch event
                        event_definitions = node_info.get('event_definitions', [])
                        for event_definition in event_definitions:
                            node_subtype = event_definition.get('definition_type', 'Unknown')
                    if node_type == 'boundaryEvent':
                        attached_to_id = node_info.get('attachedToRef')
                    node_details[node_id] = {
                        'name': node_info.get('node_name', 'Unnamed'),
                        'type': node_type,
                        'subtype': node_subtype,
                        'attached_to': attached_to_id,
                    }
                    if node_info.get('type', 'Unknown') == 'subProcess':
                        # Add subprocess details
                        subprocess_details = {}
                        for child_node_id in node_info.get('node_ids', []):
                            child_node_info = bpmnGraph.diagram_graph._node[child_node_id]
                            child_node_type = child_node_info.get('type', 'Unknown')
                            child_node_subtype = None
                            if child_node_type == 'intermediateCatchEvent' or child_node_type == 'boundaryEvent' or child_node_type == 'endEvent':
                                # Get the specific type of the intermediate catch event
                                child_event_definitions = child_node_info.get('event_definitions', [])
                                for child_event_definition in child_event_definitions:
                                    child_node_subtype = child_event_definition.get('definition_type', 'Unknown')
                            subprocess_details[child_node_id] = {
                                'name': child_node_info.get('node_name', 'Unnamed'),
                                'type': child_node_type,
                                'subtype': child_node_subtype,
                            }
                        node_details[node_id]['subprocess_details'] = subprocess_details

                process_elements[process_id] = {
                    'name': pool_names.get(process_id, 'Unnamed'),
                    'isClosed': process_element.get('isClosed', 'false'),
                    'isExecutable': process_element.get('isExecutable', 'false'),
                    'processType': process_element.get('processType', 'None'),
                    'node_ids': process_element.get('node_ids', []),
                    'node_details': node_details,
                }
            bpmnDictionary['process_elements'] = process_elements

            with open(simulation_path+"/"+file_bpmn_no_ext+".json", "w") as outfile:
                json.dump(bpmnDictionary, outfile, indent=4)
            return True
        except Exception as e:
            print(f"An error occurred: {e}")
            return False
        

    def generate_json_from_bpmn_diag(self, simulation_path, file_bpmn_no_ext, bpmn_filename):
        try:
            tree = ET.parse(simulation_path+"/"+bpmn_filename)
            root = tree.getroot()
            diagbp_tag = root.find('.//' + TAG_NAME)

            
            extra_str = ET.tostring(diagbp_tag, encoding='unicode')
            extra_str = extra_str.replace('<'+TAG_NAME+'>', '').replace('</'+TAG_NAME+'>', '')
            with open(simulation_path+"/extra.json", "w") as outfile:
                outfile.write(extra_str)
            self.generate_json_from_bpmn(simulation_path, file_bpmn_no_ext, bpmn_filename)
            return True
            
        except FileNotFoundError as e:
            print(f"-----ERROR-----: bpmn file not found: {simulation_path}/{bpmn_filename}")
            print(f"Detailed Error: {e}") 
            print(f"Current Working Directory: {os.getcwd()}")
            return False
        except ET.ParseError as e:
            os.remove(simulation_path+"/"+bpmn_filename)
            print(f"-----ERROR-----: bpmn file bad syntax in bpmnParsing.py")
            print(f"Detailed Error: {e}") 
            #sys.exit()
            return False
        except Exception as e:
            os.remove(simulation_path+"/"+bpmn_filename)
            print(f"An error occurred: {e}")
            #sys.exit()
            return False