import os
from typing import Dict, Any

from support_modules.constants import *

from .preprocess_log import *
from .handle_elements import *
from .splitminer import *
from .save_and_copy import *
# from .bpmn_layout_improver import *

class ExtractionBPMN():
    """
    Classe per l'estrazione del modello BPMN da log XES.
    
    Gestisce il preprocessing del log, l'esecuzione di SplitMiner2
    e l'adattamento del formato BPMN per includere collaboration e participant.
    """

    def __init__(self, log, settings, with_start_end_act):
        """
        Inizializza l'estrattore BPMN.
        
        Args:
            log: DataFrame contenente il log XES
            settings: Lista di configurazioni 
            with_start_end_act: Se includere attività di start/end
        """
        self.log = log.copy()
        self.settings = settings
        self.with_start_end_act = with_start_end_act

        # Validazione input
        self._validate_inputs()
        
        # Configurazione primaria
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        self.diag_log = self.config['diag_log']
        self.num_timestamp = self.config['num_timestamp']
        self.eta = str(self.config['eta'])
        self.eps = str(self.config['eps'])

        # Percorsi
        self.input_dir = os.path.join(self.path, 'input_data')
        self.output_dir = os.path.join(self.path, 'output_data')
        self.output_file_dir = os.path.join(self.output_dir, 'output_file')
        
        self._preprocess_diag_log = preprocess_diag_log.__get__(self)
        self.preprocess_log = preprocess_log.__get__(self)

        self._handle_missing_resources = handle_missing_resources.__get__(self)
        self._handle_costs = handle_costs.__get__(self)
        self._handle_setup_time = handle_setup_time.__get__(self)
        self._drop_fixed_cost_column = drop_fixed_cost_column.__get__(self)
        self._filter_lifecycle_events = filter_lifecycle_events.__get__(self)
        self._remove_start_end_events = remove_start_end_events.__get__(self)
        self.adapt_bpmn_format = adapt_bpmn_format.__get__(self)
        self._extract_process_id = extract_process_id.__get__(self)
        self._add_collaboration_to_bpmn = add_collaboration_to_bpmn.__get__(self)

        self.execute_splitminer = execute_splitminer.__get__(self)
        self._build_splitminer_command = build_splitminer_command.__get__(self)

        self.save_discovery_log = save_discovery_log.__get__(self)
        self.copy_to_output_file = copy_to_output_file.__get__(self)
        print(f"ExtractionBPMN inizializzato per log con {len(self.log)} eventi")


    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP, TAG_LIFECYCLE]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    

    def extract_bpmn_model(self) -> str:
        """
        Metodo principale per estrarre il modello BPMN.
        
        Returns:
            Percorso del file BPMN finale
        """
        try:
            print(f"Iniziando estrazione BPMN per: {self.name}")
            
            # 1. Preprocessing del log
            processed_log = self.preprocess_log()
            
            # 2. Salvataggio log per discovery
            discovery_file = self.save_discovery_log(processed_log)
            
            # 3. Esecuzione SplitMiner2
            bpmn_file = self.execute_splitminer(discovery_file)
            
            # 4. Copia nella directory finale
            final_bpmn = self.copy_to_output_file(bpmn_file)
            
            # 5. Adattamento formato
            self.adapt_bpmn_format(final_bpmn)
            
            print(f"✓ Estrazione BPMN completata: {final_bpmn}")
            return final_bpmn
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione del modello BPMN: {str(e)}")
    

    def get_extraction_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto dell'estrazione BPMN.
        
        Returns:
            Dizionario con informazioni sull'estrazione
        """
        return {
            'input_events': len(self.log),
            'model_name': self.name,
            'is_diag_log': self.diag_log,
            'with_start_end_act': self.with_start_end_act,
            'eta_parameter': self.eta,
            'eps_parameter': self.eps,
            'input_directory': self.input_dir,
            'output_directory': self.output_file_dir,
            'final_bpmn_path': os.path.join(self.output_file_dir, f"{self.name}_pm4py.bpmn")
        }