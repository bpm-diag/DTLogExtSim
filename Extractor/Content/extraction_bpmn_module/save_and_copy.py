import os
import pm4py
import pandas as pd
import shutil

from support_modules.constants import *

def save_discovery_log(self, processed_log: pd.DataFrame) -> str:
    """
    Salva il log preprocessato per il discovery.
    
    Args:
        processed_log: Log preprocessato
        
    Returns:
        Percorso del file salvato
    """
    try:
        # Crea directory se non esiste
        os.makedirs(self.input_dir, exist_ok=True)
        
        # Percorso file discovery
        discovery_file = os.path.join(self.input_dir, f"{self.name}_discovery.xes")
        
        # Salva file XES
        pm4py.write_xes(processed_log, discovery_file, case_id_key=TAG_TRACE_ID)
        
        print(f"✓ Log per discovery salvato: {discovery_file}")
        return discovery_file
        
    except Exception as e:
        raise Exception(f"Errore nel salvataggio del log discovery: {str(e)}")

def copy_to_output_file(self, bpmn_file: str) -> str:
    """
    Copia il file BPMN nella directory output_file.
    
    Args:
        bpmn_file: Percorso del file BPMN da copiare
        
    Returns:
        Percorso del file BPMN copiato
    """
    try:
        # Crea directory output_file
        os.makedirs(self.output_file_dir, exist_ok=True)
        
        # Percorso destinazione
        final_bpmn = os.path.join(self.output_file_dir, f"{self.name}_pm4py.bpmn")
        
        print("QUESTO DIO",bpmn_file)
        # Carica e salva con pm4py per standardizzazione
        # bpmn_model = pm4py.read_bpmn(bpmn_file)
        # pm4py.write_bpmn(bpmn_model, final_bpmn)
        shutil.copy(bpmn_file, final_bpmn)
        
        print(f"✓ File BPMN copiato: {final_bpmn}")
        return final_bpmn
        
    except Exception as e:
        raise Exception(f"Errore nella copia del file BPMN: {str(e)}")