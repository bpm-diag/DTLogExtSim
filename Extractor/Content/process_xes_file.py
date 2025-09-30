import os
import pm4py
from typing import Dict, List, Tuple, Optional, Any

from support_modules.constants import *
from support_modules.preprocessing_analysis import PreProcessing
from simulation_input_extraction_module.simulation_input_extraction import SimulationInputExtraction
from intermediate_start_points_extraction_module.intermediate_start_points_extraction import IntermediateStartPoint
            


class ProcessXesFile():
    """
    Classe per processare file XES ed estrarre parametri per la simulazione.
    
    Gestisce l'intero flusso di elaborazione dei log XES, inclusa l'analisi
    di preprocessing, l'estrazione dei parametri e la gestione delle tracce incomplete.
    """

    def __init__(self, file_path, output_dir_path, eta, eps, simthreshold):
        """
        Inizializza il processore XES.
        
        Args:
            file_path: Percorso del file XES
            output_dir_path: Directory di output
            eta: Parametro eta per l'algoritmo
            eps: Parametro epsilon per l'algoritmo  
            simthreshold: Soglia di similarità
        """
        self.file_path = file_path
        self.file_name = os.path.splitext(file_path)[0]
        self.output_dir_path = self._ensure_output_dir(output_dir_path)
        self.eta = float(eta)
        self.eps = float(eps)
        self.simthreshold = float(simthreshold)

        self.log = None
        self.preprocessor = None
        self.settings = []

    def _ensure_output_dir(self, output_dir_path: str) -> str:
        """Assicura che la directory di output esista."""
        if not os.path.exists(output_dir_path):
            os.makedirs(output_dir_path)
        
        # Crea sottodirectory necessarie
        subdirs = ['input_data', 'output_data', 'output_data/output_file']
        for subdir in subdirs:
            full_path = os.path.join(output_dir_path, subdir)
            if not os.path.exists(full_path):
                os.makedirs(full_path)
                
        return output_dir_path

    def load_xes_file(self) -> None:
        """Carica il file XES."""
        try:
            self.log = pm4py.read_xes(self.file_path)
            print(f"File XES caricato: {len(self.log)} eventi")
        except Exception as e:
            raise Exception(f"Errore nel caricamento del file XES: {str(e)}")

    def initialize_preprocessing(self) -> None:
        """Inizializza il preprocessing del log."""
        if self.log is None:
            raise ValueError("Log non caricato. Chiamare prima load_xes_file()")
            
        self.preprocessor = PreProcessing(self.log)
        
        # Aggiorna simthreshold se necessario
        if self.simthreshold == 0.9:
            self.simthreshold = self.preprocessor._sim_threshold

    def create_base_settings(self) -> Dict[str, Any]:
        """Crea le impostazioni base per l'elaborazione."""
        return {
            'path': self.output_dir_path,
            'namefile': self.file_name,
            'diag_log': self.preprocessor.diaglog,
            'sim_threshold': self.simthreshold,
            'num_timestamp': self.preprocessor.num_timestamp,
            'cost_hour': self.preprocessor.cost_hour,
            'fixed_cost': self.preprocessor.fixed_cost,
            'setup_time': self.preprocessor.setup_time,
            'eta': self.eta,
            'eps': self.eps
        }
    
    def process_cut_traces(self) -> None:
        """Processa tracce tagliate ed estrae punti di partenza intermedi."""
        print("Processando tracce tagliate...")
        
        # Processa log completo
        base_settings = self.create_base_settings()
        self.settings.append(base_settings)
        
        # TODO: Implementare SimulationInputExtraction
        sim_extractor = SimulationInputExtraction(self.log, self.settings, True)
        sim_extractor.process_all_extractions()
        sim_extractor.generate_params_file()
        
        # Processa tracce tagliate per punti di partenza intermedi
        self._process_intermediate_starting_points()
        
        print("✓ Processamento tracce tagliate completato")

    def _process_intermediate_starting_points(self) -> None:
        """Processa i punti di partenza intermedi dalle tracce tagliate."""
        print("Estraendo punti di partenza intermedi...")
        
        try:
            # Salva tracce tagliate in file separato
            cut_traces_filename = f"{self.file_name}_only_cut_trace.xes"
            cut_traces_path = os.path.join(self.output_dir_path, 'input_data', cut_traces_filename)
            
            pm4py.write_xes(
                self.preprocessor.log_cut_trace, 
                cut_traces_path, 
                case_id_key=TAG_TRACE_ID
            )
            
            # Carica il file delle tracce tagliate
            cut_log = pm4py.read_xes(cut_traces_path)
            
            # Carica il modello BPMN generato
            model_name = f"{self.file_name}_pm4py.bpmn"
            model_path = os.path.join(self.output_dir_path, 'output_data', 'output_file', model_name)
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Modello BPMN non trovato: {model_path}")
                
            model = pm4py.read_bpmn(model_path)
            
            # Crea settings per punti intermedi
            intermediate_settings = self.create_base_settings()
            intermediate_settings.update({
                'namefile': cut_traces_filename,
                'model_name': model_name,
                'output_name': self.file_name
            })
            
            # Estrai punti di partenza intermedi
            isp_processor = IntermediateStartPoint(cut_log, model, [intermediate_settings])
            result = isp_processor.extract_all_intermediate_points()
            
            # Ottieni risultati
            new_forced_instance = isp_processor._forced_instance_types
            new_flow_prob = isp_processor._flow_probabilities
            
            # Estrai attività di start e end
            start_activity, end_activity = self._extract_start_end_activities()
            
            # Aggiorna parametri con punti intermedi
            sim_extractor = SimulationInputExtraction(self.log, self.settings, True)
            sim_extractor.process_all_extractions()
            sim_extractor.generate_params_file(
                start_end_act_bool=True,
                start_act=start_activity,
                end_act=end_activity,
                new_flow=new_flow_prob,
                new_forced_instance=new_forced_instance,
                cut_log_bool=True
            )
            
            print("✓ Punti di partenza intermedi estratti")
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione punti intermedi: {str(e)}")
        
    def _extract_start_end_activities(self) -> Tuple[str, str]:
        """Estrae le attività di start e end dal log con logica robusta."""
        
        try:
            if self.preprocessor.diaglog:
                # Per log diagnostici, cerca eventi specifici
                start_events = self.log[self.log[TAG_NODE_TYPE] == 'startEvent']
                end_events = self.log[self.log[TAG_NODE_TYPE] == 'endEvent']
                
                # Se non trovati con nodeType, usa pattern
                if start_events.empty:
                    start_events = self.log[self.log[TAG_ACTIVITY_NAME].str.contains(r'Start', case=False, na=False)]
                if end_events.empty:
                    end_events = self.log[self.log[TAG_ACTIVITY_NAME].str.contains(r'End', case=False, na=False)]
                    
            else:
                # Per log normali, cerca pattern testuali
                start_events = self.log[self.log[TAG_ACTIVITY_NAME].str.contains(r'Start', case=False, na=False)]
                end_events = self.log[self.log[TAG_ACTIVITY_NAME].str.contains(r'End|abort', case=False, na=False)]
            
            # Fallback: usa prima e ultima attività
            if start_events.empty:
                print("⚠ Evento start non trovato, usando prima attività")
                first_activities = []
                for trace_id, trace_group in self.log.groupby(TAG_TRACE_ID):
                    trace_sorted = trace_group.sort_values(TAG_TIMESTAMP)
                    if not trace_sorted.empty:
                        first_activities.append(trace_sorted.iloc[0][TAG_ACTIVITY_NAME])
                
                if first_activities:
                    from collections import Counter
                    start_activity = Counter(first_activities).most_common(1)[0][0]
                else:
                    raise ValueError("Impossibile determinare attività di start")
            else:
                start_activity = start_events[TAG_ACTIVITY_NAME].iloc[0]
                
            if end_events.empty:
                print("⚠ Evento end non trovato, usando ultima attività")
                last_activities = []
                for trace_id, trace_group in self.log.groupby(TAG_TRACE_ID):
                    trace_sorted = trace_group.sort_values(TAG_TIMESTAMP)
                    if not trace_sorted.empty:
                        last_activities.append(trace_sorted.iloc[-1][TAG_ACTIVITY_NAME])
                
                if last_activities:
                    from collections import Counter
                    end_activity = Counter(last_activities).most_common(1)[0][0]
                else:
                    raise ValueError("Impossibile determinare attività di end")
            else:
                end_activity = end_events[TAG_ACTIVITY_NAME].iloc[0]
            
            print(f"✓ Start activity: {start_activity}")
            print(f"✓ End activity: {end_activity}")
            return start_activity, end_activity
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione start/end: {str(e)}")

    def _extract_start_end_activities_old(self) -> Tuple[str, str]:
        """Estrae le attività di start e end dal log."""
        if self.preprocessor.diaglog:
            # Per log diagnostici, cerca eventi specifici
            start_events = self.log[self.log[TAG_NODE_TYPE] == 'startEvent']
            end_events = self.log[self.log[TAG_NODE_TYPE] == 'endEvent']
            
            if start_events.empty or end_events.empty:
                raise ValueError("Eventi di start/end non trovati nel log diagnostico")
                
            start_activity = start_events[TAG_ACTIVITY_NAME].iloc[0]
            end_activity = end_events[TAG_ACTIVITY_NAME].iloc[0]
        else:
            # Per log normali, cerca pattern testuali
            start_pattern = r'Start'
            end_pattern = r'End|END|abort'
            
            start_events = self.log[
                self.log[TAG_ACTIVITY_NAME].str.contains(start_pattern, case=False, na=False)
            ]
            end_events = self.log[
                self.log[TAG_ACTIVITY_NAME].str.contains(end_pattern, case=False, na=False)
            ]
            
            if start_events.empty or end_events.empty:
                raise ValueError("Attività di start/end non trovate nel log")
                
            start_activity = start_events[TAG_ACTIVITY_NAME].iloc[0]
            end_activity = end_events[TAG_ACTIVITY_NAME].iloc[0]
        
        return start_activity, end_activity

    def process_complete_traces(self) -> None:
        """Processa tracce complete (senza tracce tagliate)."""
        print("Processando tracce complete...")
        
        settings = self.create_base_settings()
        self.settings.append(settings)
        
        # TODO: Implementare SimulationInputExtraction
        sim_extractor = SimulationInputExtraction(self.log, self.settings, False)
        sim_extractor.process_all_extractions()
        sim_extractor.generate_params_file()
        
        print("✓ Processamento tracce complete completato")

    def process(self):
        try: 
            print(f"Iniziando processamento file: {self.file_path}")

            self.load_xes_file()
            self.validate_inputs()

            self.initialize_preprocessing()

            if self.preprocessor.cut_log_bool:
                print(f"Trovate {len(self.preprocessor.log_cut_trace)} tracce incomplete")
                print(f"Trovate {len(self.preprocessor.log_entire_trace)} tracce complete")
                self.process_cut_traces()
            else:
                print("Tutte le tracce sono complete")
                self.process_complete_traces()

            # 4. Risultati
            result = {
                'success': True,
                'file_processed': self.file_name,
                'total_events': len(self.log),
                'has_cut_traces': self.preprocessor.cut_log_bool,
                'num_cut_traces': len(self.preprocessor.log_cut_trace) if self.preprocessor.cut_log_bool else 0,
                'num_complete_traces': len(self.preprocessor.log_entire_trace) if self.preprocessor.cut_log_bool else len(self.log),
                'settings_used': self.settings,
                'output_directory': self.output_dir_path
            }
            
            print(f"✓ Processamento completato con successo")
            return result
        except Exception as e:
            error_msg = f"Errore durante il processamento: {str(e)}"
            print(f"✗ {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'file_processed': self.file_name
            }

    def validate_inputs(self):
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP, TAG_LIFECYCLE]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            print(f"Colonne mancanti nel log: {missing_columns}")
            if TAG_LIFECYCLE in missing_columns:
                print("Aggiungo colonna lifecycle")
                for trace_id, trace_group in self.log.groupby(TAG_TRACE_ID):
                    self.log.loc[trace_group.index, TAG_LIFECYCLE] = "complete"