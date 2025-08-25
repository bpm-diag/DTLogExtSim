import pandas as pd
import xml.etree.ElementTree as ET
from typing import Optional

from support_modules.constants import *

def handle_missing_resources(self, log: pd.DataFrame) -> pd.DataFrame:
    """Gestisce i valori mancanti nelle risorse."""
    if TAG_RESOURCE in log.columns:
        log.loc[log[TAG_RESOURCE].isna(), TAG_RESOURCE] = None
    return log

def handle_costs(self, log: pd.DataFrame) -> pd.DataFrame:
    """Gestisce i valori NaN nelle colonne dei costi (senza dropparle)."""
    # Gestione cost_hour NaN
    if self.config.get('cost_hour', False) and TAG_COST_HOUR in log.columns:
        log.loc[log[TAG_COST_HOUR].isna(), TAG_COST_HOUR] = None
    
    # Gestione fixed_cost NaN (senza droppare ancora)
    if self.config.get('fixed_cost', False) and TAG_FIXED_COST in log.columns:
        log.loc[log[TAG_FIXED_COST].isna(), TAG_FIXED_COST] = None
    
    return log

def handle_setup_time(self, log: pd.DataFrame) -> pd.DataFrame:
    """Rimuove eventi di setup time se necessario."""
    if self.config.get('setup_time', False):
        setup_events = [LIFECYCLE_START_SETUP, LIFECYCLE_END_SETUP]
        log = log[~log[TAG_LIFECYCLE].isin(setup_events)].reset_index(drop=True)
    return log

def drop_fixed_cost_column(self, log: pd.DataFrame) -> pd.DataFrame:
    """Droppa la colonna fixed_cost se necessario (dopo setup_time)."""
    if self.config.get('fixed_cost', False) and TAG_FIXED_COST in log.columns:
        log = log.drop(columns=[TAG_FIXED_COST])
    return log



def filter_lifecycle_events(self, log: pd.DataFrame) -> pd.DataFrame:
    """Filtra solo eventi start e complete."""
    return log[log[TAG_LIFECYCLE].isin([LIFECYCLE_START, LIFECYCLE_COMPLETE])].reset_index(drop=True)

def remove_start_end_events(self, log: pd.DataFrame) -> pd.DataFrame:
    """Rimuove eventi di start e end se non richiesti."""
    if self.with_start_end_act:
        return log
    
    if self.diag_log:
        # Per log diag, rimuovi startEvent e endEvent
        log = log[~log[TAG_NODE_TYPE].isin([NODE_TYPE_START, NODE_TYPE_END])].reset_index(drop=True)
    else:
        # Per log normali, rimuovi pattern START/END
        log = log[~log[TAG_ACTIVITY_NAME].str.contains(r'START', case=False, na=False)]
        log = log[~log[TAG_ACTIVITY_NAME].str.contains(r'END', case=False, na=False)]
    
    return log


def adapt_bpmn_format(self, bpmn_file: str) -> None:
    """
    Adatta il formato BPMN aggiungendo collaboration e participant.
    
    Args:
        bpmn_file: Percorso del file BPMN da modificare
    """
    try:
        print("Adattando formato BPMN...")
        
        # Estrai process ID
        process_id = self._extract_process_id(bpmn_file)
        if not process_id:
            raise ValueError("Process ID non trovato nel file BPMN")
        
        # Aggiungi collaboration
        self._add_collaboration_to_bpmn(
            bpmn_file,
            process_id,
            collaboration_id="Collaboration_diag",
            participant_id="Participant_diag", 
            pool_name="main"
        )
        
        print("✓ Formato BPMN adattato con collaboration")
        
    except Exception as e:
        raise Exception(f"Errore nell'adattamento del formato BPMN: {str(e)}")
    

def extract_process_id(self, bpmn_file: str) -> Optional[str]:
    """
    Estrae l'ID del processo dal file BPMN.
    
    Args:
        bpmn_file: Percorso del file BPMN
        
    Returns:
        ID del processo o None se non trovato
    """
    try:
        tree = ET.parse(bpmn_file)
        root = tree.getroot()
        
        # Cerca il primo elemento process
        for process in root.findall(".//{*}process"):
            process_id = process.get("id")
            if process_id:
                return process_id
        
        return None
        
    except Exception as e:
        raise Exception(f"Errore nell'estrazione del process ID: {str(e)}")

def add_collaboration_to_bpmn(self, bpmn_file: str, process_id: str, 
                                collaboration_id: str, participant_id: str, pool_name: str) -> None:
    """
    Aggiunge collaboration e participant al file BPMN.
    
    Args:
        bpmn_file: Percorso del file BPMN
        process_id: ID del processo
        collaboration_id: ID della collaboration
        participant_id: ID del participant
        pool_name: Nome del pool
    """
    # Namespace BPMN
    namespaces = {
        'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
        'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
        'omgdc': 'http://www.omg.org/spec/DD/20100524/DC',
        'omgdi': 'http://www.omg.org/spec/DD/20100524/DI',
        'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'xsd': 'http://www.w3.org/2001/XMLSchema'
    }
    
    # Registra namespace
    for prefix, uri in namespaces.items():
        ET.register_namespace(prefix, uri)
    
    # Parse file
    tree = ET.parse(bpmn_file)
    root = tree.getroot()
    
    # Crea collaboration element
    collaboration = ET.Element(
        '{http://www.omg.org/spec/BPMN/20100524/MODEL}collaboration',
        attrib={'id': collaboration_id}
    )
    
    # Crea participant element
    participant = ET.SubElement(
        collaboration,
        '{http://www.omg.org/spec/BPMN/20100524/MODEL}participant',
        attrib={
            'id': participant_id,
            'name': pool_name,
            'processRef': process_id
        }
    )
    
    # Inserisci collaboration come secondo elemento (dopo definitions)
    root.insert(1, collaboration)
    
    # Salva file modificato
    tree.write(bpmn_file, encoding='utf-8', xml_declaration=True)
