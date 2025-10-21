import os
import subprocess
import platform as pl
from typing import List

def execute_splitminer(self, discovery_file: str) -> str:
    """
    Esegue SplitMiner2 per generare il modello BPMN.
    
    Args:
        discovery_file: Percorso del file XES per discovery
        
    Returns:
        Percorso del file BPMN generato
    """
    print("Eseguendo SplitMiner2...")
    
    try:
        # Crea directory output
        os.makedirs(self.output_dir, exist_ok=True)
        
        # Percorso output SplitMiner
        output_file = os.path.join(self.output_dir, f"{self.name}_sm2")
        
        # Verifica esistenza SplitMiner
        sm2_jar = "external_tools/splitminer2/sm2.jar"
        if not os.path.exists(sm2_jar):
            raise FileNotFoundError(f"SplitMiner2 non trovato: {sm2_jar}")
        
        # Costruzione comando
        args = self._build_splitminer_command(discovery_file, output_file, sm2_jar)
        
        # Esecuzione SplitMiner
        process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        
        # Controllo risultato
        if process.returncode != 0:
            print(f"SplitMiner stdout: {stdout}")
            print(f"SplitMiner stderr: {stderr}")
            raise Exception(f"SplitMiner2 fallito con codice {process.returncode}")
        
        bpmn_file = f"{output_file}.bpmn"
        if not os.path.exists(bpmn_file):
            raise FileNotFoundError(f"File BPMN non generato: {bpmn_file}")
        
        print(f"✓ SplitMiner2 completato: {bpmn_file}")
        return bpmn_file
        
    except Exception as e:
        raise Exception(f"Errore nell'esecuzione di SplitMiner2: {str(e)}")

def build_splitminer_command(self, input_file: str, output_file: str, sm2_jar: str) -> List[str]:
    """Costruisce il comando per SplitMiner2."""
    # Separatore classpath
    sep = ';' if pl.system().lower() == 'windows' else ':'
    
    # Comando base
    args = []
    
    # xvfb-run per sistemi non-Windows (display virtuale)
    if pl.system().lower() != 'windows':
        args.append('xvfb-run')
    
    args.append('java')
    
    # Memoria JVM per sistemi non-Windows
    if pl.system().lower() != 'windows':
        args.append('-Xmx2G')
    
    # Classpath e classe principale
    classpath = f"{sm2_jar}{sep}{os.path.join('external_tools', 'splitminer2', 'lib', '*')}"
    args.extend([
        '-cp', classpath,
        'au.edu.unimelb.services.ServiceProvider',
        'SMD',
        self.eta, self.eps,  # Parametri eta e epsilon
        'false', 'false', 'false',  # Altri parametri SplitMiner
        input_file,
        output_file
    ])
    
    return args