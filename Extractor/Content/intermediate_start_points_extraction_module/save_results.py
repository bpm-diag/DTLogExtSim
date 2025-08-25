import pm4py
import os
import pandas as pd
from typing import Dict, Tuple, List, Any

def save_results(self, forced_flows: Dict[str, Tuple[str, str, str]], 
                    forced_instance_types: pd.DataFrame,
                    flow_probabilities: List[Tuple[str, float]]) -> str:
    """
    Salva i risultati dell'estrazione su file.
    
    Args:
        forced_flows: Flussi forzati per stati intermedi
        forced_instance_types: Tipi di istanza forzati
        flow_probabilities: Probabilità di flusso
        
    Returns:
        Percorso del file salvato
    """
    try:
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        file_path = os.path.join(output_dir, f'intermediate_states_sim_data{self.output_name}.txt')
        
        with open(file_path, 'w') as file:
            file.write("Information to execute a simulation starting by intermediate states based on unfinished log traces\n")
            file.write("\nFlow to start from intermediate state\n")
            file.write(f"{forced_flows}\n")
            file.write("\nIntermediate Forced Instance Types\n")
            file.write(f"{forced_instance_types.to_string()}\n")
            file.write("\nFlow Probabilities\n")
            file.write(f"{flow_probabilities}\n")
        
        print(f"✓ Risultati salvati: {file_path}")
        return file_path
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio dei risultati: {str(e)}")

def save_modified_model(self, model: Any) -> str:
    """Salva il modello BPMN modificato."""
    output_dir = os.path.join(self.path, "output_data")
    os.makedirs(output_dir, exist_ok=True)
    
    bpmn_file_path = os.path.join(output_dir, f"{self.output_name}_intermediate_start_points.bpmn")
    pm4py.write_bpmn(model, bpmn_file_path)
    
    # Adatta formato BPMN
    self._adapt_bpmn_format(bpmn_file_path)
    
    return bpmn_file_path

def add_collaboration_to_bpmn(self, bpmn_file_path: str, process_id: str,
                                collaboration_id: str, participant_id: str, pool_name: str) -> None:
    """Aggiunge collaboration al file BPMN."""
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
    
    collaboration = ET.Element(
        '{http://www.omg.org/spec/BPMN/20100524/MODEL}collaboration',
        attrib={'id': 'Collaboration_0idnrdl'}
    )
    participant = ET.SubElement(
        collaboration,
        '{http://www.omg.org/spec/BPMN/20100524/MODEL}participant',
        attrib={
            'id': participant_id,
            'name': pool_name,
            'processRef': process_id
        }
    )
    
    root.insert(1, collaboration)
    
    # Salva con nome diverso
    output_path = os.path.join(
        self.path, "output_data", "output_file", 
        f"{self.output_name}_intermediate_start_points_out.bpmn"
    )
    
    tree.write(output_path, encoding='utf-8', xml_declaration=True)
    

def adapt_bpmn_format(self, bpmn_file_path: str) -> None:
    """Adatta il formato BPMN con collaboration."""
    try:
        # Estrai process ID
        process_id = self._extract_process_id(bpmn_file_path)
        if not process_id:
            raise ValueError("Process ID non trovato")
        
        # Aggiungi collaboration
        self._add_collaboration_to_bpmn(
            bpmn_file_path, process_id,
            "Collaboration_diag", "Participant_diag", "main"
        )
        
    except Exception as e:
        raise Exception(f"Errore nell'adattamento formato BPMN: {str(e)}")