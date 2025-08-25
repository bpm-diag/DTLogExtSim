import pandas as pd
import numpy as np
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import pm4py

class XESAdapter:
    """
    Adatta qualsiasi log XES al formato specifico richiesto dal tuo sistema esistente.
    
    Converte log XES di qualsiasi formato al formato DIAG-like che il tuo sistema
    già riconosce, aggiungendo tutte le colonne e i valori necessari.
    """
    
    def __init__(self):
        """Inizializza l'adattatore XES."""
        
        # Colonne richieste dal tuo sistema (dal file traces.xes funzionante)
        self.required_columns = {
            'case:concept:name': 'str',    # Case ID
            'concept:name': 'str',         # Activity name
            'time:timestamp': 'datetime',  # Timestamp
            'lifecycle:transition': 'str', # Lifecycle (assign, start, complete)
            'nodeType': 'str',            # Tipo nodo (task, startEvent, endEvent, exclusiveGateway)
            'poolName': 'str',            # Pool name
            'instanceType': 'str',        # Instance type (A, B, etc.)
            'org:resource': 'str',        # Resources (formato lista come stringa)
            'resourceCost': 'str',        # Resource costs (formato lista come stringa)  
            'fixedCost': 'float'          # Fixed cost
        }
        
        # Pattern per identificare tipi di attività
        self.activity_patterns = {
            'start': [r'start', r'begin', r'initial', r'entry', r'first', r'corner2.*return'],
            'end': [r'end', r'finish', r'final', r'terminate', r'last', r'exit'],
            'gateway': [r'gateway', r'split', r'merge', r'decision', r'choice', r'splitter']
        }
        
        # Mapping lifecycle standard
        self.lifecycle_mapping = {
            'complete': ['complete', 'end', 'finish', 'done', 'terminated'],
            'start': ['start', 'begin', 'initiate', 'started'],
            'assign': ['assign', 'allocate', 'schedule', 'assigned']
        }
        
        print("XESAdapter inizializzato per conversione al formato sistema esistente")
    
    def adapt_xes_to_system_format(self, input_path: str, output_path: str = None) -> str:
        """
        Adatta un log XES qualsiasi al formato richiesto dal tuo sistema.
        
        Args:
            input_path: Percorso del file XES da adattare
            output_path: Percorso del file XES adattato (opzionale)
            
        Returns:
            Percorso del file adattato
        """
        try:
            print(f"🔧 Adattando {input_path} al formato sistema...")
            
            # 1. Carica il log
            log = pm4py.read_xes(input_path)
            print(f"   📊 Log caricato: {len(log)} eventi, {len(log.columns)} colonne")
            
            # 2. Analizza struttura esistente
            analysis = self._analyze_existing_structure(log)
            print(f"   🔍 Struttura analizzata: {analysis['log_type']}")
            
            # 3. Mappa colonne esistenti a quelle richieste
            adapted_log = self._map_existing_columns(log, analysis)
            
            # 4. Aggiungi colonne mancanti obbligatorie
            adapted_log = self._add_required_columns(adapted_log, analysis)
            
            # 5. Standardizza valori nelle colonne
            adapted_log = self._standardize_column_values(adapted_log, analysis)
            
            # 6. Crea eventi start/end se mancanti
            adapted_log = self._ensure_start_end_events(adapted_log)
            
            # 7. Riordina colonne nell'ordine corretto
            adapted_log = self._reorder_columns(adapted_log)
            
            # 8. Valida formato finale
            validation = self._validate_adapted_format(adapted_log)
            if not validation['valid']:
                raise Exception(f"Validazione fallita: {validation['errors']}")
            
            # 9. Salva il log adattato
            if output_path is None:
                base_name = os.path.splitext(input_path)[0]
                output_path = f"{base_name}_adapted.xes"
            
            pm4py.write_xes(adapted_log, output_path, case_id_key='case:concept:name')
            
            print(f"✅ Log adattato salvato: {output_path}")
            print(f"   📈 Eventi finali: {len(adapted_log)}")
            print(f"   📋 Colonne finali: {list(adapted_log.columns)}")
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Errore nell'adattamento: {str(e)}")
    
    def _analyze_existing_structure(self, log: pd.DataFrame) -> Dict[str, Any]:
        """Analizza la struttura del log esistente."""
        
        analysis = {
            'log_type': 'unknown',
            'columns': list(log.columns),
            'has_case_id': False,
            'has_activity': False, 
            'has_timestamp': False,
            'has_lifecycle': False,
            'case_id_column': None,
            'activity_column': None,
            'timestamp_column': None,
            'lifecycle_column': None,
            'resource_columns': [],
            'cost_columns': [],
            'unique_activities': set(),
            'unique_lifecycles': set(),
            'is_manufacturing': False,
            'is_standard_xes': False
        }
        
        # Identifica colonne principali
        for col in log.columns:
            col_lower = col.lower()
            
            # Case ID
            if any(pattern in col_lower for pattern in ['case', 'trace', 'process']):
                analysis['has_case_id'] = True
                analysis['case_id_column'] = col
            
            # Activity  
            if any(pattern in col_lower for pattern in ['concept:name', 'activity', 'task', 'station']):
                analysis['has_activity'] = True
                analysis['activity_column'] = col
            
            # Timestamp
            if any(pattern in col_lower for pattern in ['time', 'timestamp', 'date']):
                analysis['has_timestamp'] = True
                analysis['timestamp_column'] = col
            
            # Lifecycle
            if any(pattern in col_lower for pattern in ['lifecycle', 'transition']):
                analysis['has_lifecycle'] = True
                analysis['lifecycle_column'] = col
            
            # Resources
            if any(pattern in col_lower for pattern in ['resource', 'user', 'actor']):
                analysis['resource_columns'].append(col)
            
            # Costs
            if any(pattern in col_lower for pattern in ['cost', 'price']):
                analysis['cost_columns'].append(col)
        
        # Determina tipo di log
        if analysis['activity_column']:
            activities = set(log[analysis['activity_column']].dropna().astype(str))
            analysis['unique_activities'] = activities
            
            # Manufacturing log detection
            if any('station' in act.lower() for act in activities):
                analysis['is_manufacturing'] = True
                analysis['log_type'] = 'manufacturing'
            elif 'concept:name' in log.columns and 'lifecycle:transition' in log.columns:
                analysis['is_standard_xes'] = True
                analysis['log_type'] = 'standard_xes'
            else:
                analysis['log_type'] = 'custom'
        
        if analysis['lifecycle_column']:
            analysis['unique_lifecycles'] = set(log[analysis['lifecycle_column']].dropna().astype(str))
        
        return analysis
    
    def _map_existing_columns(self, log: pd.DataFrame, analysis: Dict) -> pd.DataFrame:
        """Mappa le colonne esistenti a quelle richieste dal sistema."""
        
        adapted_log = log.copy()
        
        # Mappa Case ID
        if analysis['case_id_column'] and analysis['case_id_column'] != 'case:concept:name':
            adapted_log['case:concept:name'] = adapted_log[analysis['case_id_column']]
        
        # Mappa Activity
        if analysis['activity_column'] and analysis['activity_column'] != 'concept:name':
            adapted_log['concept:name'] = adapted_log[analysis['activity_column']]
        
        # Mappa Timestamp  
        if analysis['timestamp_column'] and analysis['timestamp_column'] != 'time:timestamp':
            adapted_log['time:timestamp'] = pd.to_datetime(adapted_log[analysis['timestamp_column']])
        
        # Mappa Lifecycle
        if analysis['lifecycle_column'] and analysis['lifecycle_column'] != 'lifecycle:transition':
            adapted_log['lifecycle:transition'] = adapted_log[analysis['lifecycle_column']]
        
        return adapted_log
    
    def _add_required_columns(self, log: pd.DataFrame, analysis: Dict) -> pd.DataFrame:
        """Aggiunge le colonne obbligatorie mancanti."""
        
        adapted_log = log.copy()
        
        # Case ID (obbligatorio) - IMPORTANTE: gestione corretta per SplitMiner
        if 'case:concept:name' not in adapted_log.columns:
            if analysis['has_case_id'] and analysis['case_id_column']:
                adapted_log['case:concept:name'] = adapted_log[analysis['case_id_column']].astype(str)
            else:
                # Per log manufacturing, usa il variant come case ID se disponibile
                if 'variant' in adapted_log.columns:
                    adapted_log['case:concept:name'] = adapted_log['variant'].astype(str)
                elif 'concept:name' in adapted_log.columns:
                    # Ogni riga è un case diverso - per log event-based
                    adapted_log['case:concept:name'] = [f"case_{i}" for i in range(len(adapted_log))]
                else:
                    adapted_log['case:concept:name'] = [f"case_{i}" for i in range(len(adapted_log))]
        
        # Per log manufacturing: raggruppa eventi simili per creare tracce logiche
        if analysis['is_manufacturing']:
            adapted_log = self._create_logical_traces_for_manufacturing(adapted_log)
        
        # Activity (obbligatorio) - semplifica nomi per SplitMiner
        if 'concept:name' not in adapted_log.columns:
            if analysis['has_activity'] and analysis['activity_column']:
                adapted_log['concept:name'] = adapted_log[analysis['activity_column']].astype(str)
            else:
                adapted_log['concept:name'] = 'GenericActivity'
        
        # Semplifica i nomi delle attività per SplitMiner
        adapted_log = self._simplify_activity_names(adapted_log)
        
        # Timestamp (obbligatorio)
        if 'time:timestamp' not in adapted_log.columns:
            if analysis['has_timestamp'] and analysis['timestamp_column']:
                adapted_log['time:timestamp'] = pd.to_datetime(adapted_log[analysis['timestamp_column']])
            else:
                # Crea timestamp sequenziali con intervalli realistici
                base_time = datetime.now()
                adapted_log['time:timestamp'] = [
                    base_time + pd.Timedelta(minutes=i*5) for i in range(len(adapted_log))
                ]
        
        # Assicura che i timestamp siano ordinati per case
        adapted_log = adapted_log.sort_values(['case:concept:name', 'time:timestamp']).reset_index(drop=True)
        
        # Lifecycle (obbligatorio per il tuo sistema)
        if 'lifecycle:transition' not in adapted_log.columns:
            if analysis['has_lifecycle'] and analysis['lifecycle_column']:
                adapted_log['lifecycle:transition'] = adapted_log[analysis['lifecycle_column']].astype(str)
            else:
                # Per process discovery, usiamo principalmente 'complete'
                adapted_log['lifecycle:transition'] = 'complete'
        
        # NodeType (obbligatorio per il tuo sistema)
        if 'nodeType' not in adapted_log.columns:
            adapted_log['nodeType'] = 'task'  # Default, sarà aggiustato dopo
        
        # PoolName (richiesto dal tuo sistema)
        if 'poolName' not in adapted_log.columns:
            adapted_log['poolName'] = 'main'
        
        # InstanceType (richiesto dal tuo sistema)
        if 'instanceType' not in adapted_log.columns:
            adapted_log['instanceType'] = 'A'
        
        # org:resource (richiesto)
        if 'org:resource' not in adapted_log.columns:
            if analysis['resource_columns']:
                # Usa la prima colonna risorsa trovata
                adapted_log['org:resource'] = adapted_log[analysis['resource_columns'][0]].astype(str)
            elif 'lifecycle' in adapted_log.columns:
                # Per manufacturing, usa lifecycle come risorsa
                adapted_log['org:resource'] = adapted_log['lifecycle'].astype(str)
            else:
                adapted_log['org:resource'] = "default_resource"
        
        # resourceCost (richiesto se presenti costi)
        if 'resourceCost' not in adapted_log.columns:
            if analysis['cost_columns']:
                adapted_log['resourceCost'] = adapted_log[analysis['cost_columns'][0]].astype(str)
            else:
                adapted_log['resourceCost'] = np.nan
        
        # fixedCost (opzionale)
        if 'fixedCost' not in adapted_log.columns:
            adapted_log['fixedCost'] = np.nan
        
        return adapted_log
    
    def _create_logical_traces_for_manufacturing(self, log: pd.DataFrame) -> pd.DataFrame:
        """Crea tracce logiche per log manufacturing raggruppando eventi correlati."""
        
        # Se esiste già un case ID valido, usalo
        if 'case:concept:name' in log.columns and log['case:concept:name'].nunique() > 1:
            return log
        
        # Crea tracce basate su pattern temporali e di attività
        log_with_traces = log.copy()
        
        # Raggruppa eventi vicini temporalmente (stesso prodotto/parte)
        if 'variant' in log.columns:
            # Usa variant esistente come base per case ID
            log_with_traces['case:concept:name'] = log_with_traces['variant'].astype(str)
        else:
            # Crea case ID basati su finestre temporali
            log_with_traces = log_with_traces.sort_values('time:timestamp')
            
            # Raggruppa eventi in finestre di tempo (es. 30 minuti)
            time_window = pd.Timedelta(minutes=30)
            case_id = 1
            current_case_start = log_with_traces['time:timestamp'].iloc[0]
            
            case_ids = []
            for _, row in log_with_traces.iterrows():
                if row['time:timestamp'] - current_case_start > time_window:
                    case_id += 1
                    current_case_start = row['time:timestamp']
                case_ids.append(f"trace_{case_id}")
            
            log_with_traces['case:concept:name'] = case_ids
        
        return log_with_traces
    
    def _simplify_activity_names(self, log: pd.DataFrame) -> pd.DataFrame:
        """Semplifica i nomi delle attività per migliorare il process discovery."""
        
        def simplify_name(activity_name):
            if pd.isna(activity_name):
                return 'Unknown'
            
            name = str(activity_name)
            
            # Rimuovi prefissi comuni per manufacturing
            name = re.sub(r'^(station|corner|splitter)\d*_?', '', name, flags=re.IGNORECASE)
            
            # Standardizza operazioni comuni
            operation_mapping = {
                'LOAD': 'Load',
                'PROCESS': 'Process', 
                'UNLOAD': 'Unload',
                'TRANSFER': 'Transfer',
                'RETURN': 'Return',
                'FORWARD': 'Forward',
                'PASS': 'Pass'
            }
            
            name_upper = name.upper()
            for old, new in operation_mapping.items():
                if old in name_upper:
                    return new
            
            # Se contiene numeri, rimuovili per generalizzare
            if re.search(r'\d+', name):
                # Mantieni la parte descrittiva
                base_name = re.sub(r'\d+', '', name)
                if base_name:
                    return base_name.strip('_-')
            
            return name
        
        log['concept:name'] = log['concept:name'].apply(simplify_name)
        return log
    
    def _standardize_column_values(self, log: pd.DataFrame, analysis: Dict) -> pd.DataFrame:
        """Standardizza i valori nelle colonne al formato richiesto."""
        
        adapted_log = log.copy()
        
        # Standardizza lifecycle transitions
        if 'lifecycle:transition' in adapted_log.columns:
            adapted_log = self._standardize_lifecycle_transitions(adapted_log)
        
        # Standardizza nodeType basato sulle attività
        if 'concept:name' in adapted_log.columns:
            adapted_log = self._assign_node_types(adapted_log)
        
        # Standardizza resources al formato lista
        if 'org:resource' in adapted_log.columns:
            adapted_log = self._standardize_resources_format(adapted_log)
        
        # Standardizza resourceCost al formato lista
        if 'resourceCost' in adapted_log.columns:
            adapted_log = self._standardize_resource_costs_format(adapted_log)
        
        return adapted_log
    
    def _standardize_lifecycle_transitions(self, log: pd.DataFrame) -> pd.DataFrame:
        """Standardizza i valori del lifecycle al formato richiesto."""
        
        # Mappa valori al formato standard
        value_mapping = {}
        for standard, variations in self.lifecycle_mapping.items():
            for variation in variations:
                value_mapping[variation.lower()] = standard
                value_mapping[variation.upper()] = standard
                value_mapping[variation.capitalize()] = standard
        
        # Applica mapping
        log['lifecycle:transition'] = log['lifecycle:transition'].astype(str).str.lower().map(value_mapping).fillna('complete')
        
        return log
    
    def _assign_node_types(self, log: pd.DataFrame) -> pd.DataFrame:
        """Assegna nodeType basato sul nome dell'attività."""
        
        def determine_node_type(activity_name):
            if pd.isna(activity_name):
                return 'task'
            
            activity_lower = str(activity_name).lower()
            
            # Check for start events
            for pattern in self.activity_patterns['start']:
                if re.search(pattern, activity_lower):
                    return 'startEvent'
            
            # Check for end events  
            for pattern in self.activity_patterns['end']:
                if re.search(pattern, activity_lower):
                    return 'endEvent'
            
            # Check for gateways
            for pattern in self.activity_patterns['gateway']:
                if re.search(pattern, activity_lower):
                    return 'exclusiveGateway'
            
            # Default to task
            return 'task'
        
        log['nodeType'] = log['concept:name'].apply(determine_node_type)
        return log
    
    def _standardize_resources_format(self, log: pd.DataFrame) -> pd.DataFrame:
        """Converte resources al formato lista richiesto dal sistema."""
        
        def format_resource(resource_value):
            if pd.isna(resource_value) or resource_value == 'nan':
                return "['default_resource']"
            
            resource_str = str(resource_value)
            
            # Se già in formato lista, mantieni
            if resource_str.startswith('[') and resource_str.endswith(']'):
                return resource_str
            
            # Se contiene virgole, è una lista separata da virgole
            if ',' in resource_str:
                resources = [r.strip().strip("'\"") for r in resource_str.split(',')]
                return str(resources)
            
            # Singola risorsa
            return f"['{resource_str}']"
        
        log['org:resource'] = log['org:resource'].apply(format_resource)
        return log
    
    def _standardize_resource_costs_format(self, log: pd.DataFrame) -> pd.DataFrame:
        """Converte resource costs al formato lista richiesto."""
        
        def format_cost(cost_value):
            if pd.isna(cost_value) or cost_value == 'nan':
                return np.nan
            
            cost_str = str(cost_value)
            
            # Se già in formato lista, mantieni
            if cost_str.startswith('[') and cost_str.endswith(']'):
                return cost_str
            
            # Se contiene virgole, è una lista
            if ',' in cost_str:
                costs = [c.strip().strip("'\"") for c in cost_str.split(',')]
                return str(costs)
            
            # Singolo costo
            return f"['{cost_str}']"
        
        log['resourceCost'] = log['resourceCost'].apply(format_cost)
        return log
    
    def _ensure_start_end_events(self, log: pd.DataFrame) -> pd.DataFrame:
        """Assicura che ci siano eventi di start e end per ogni caso."""
        
        # Prima identifica e normalizza eventi esistenti che potrebbero essere start/end
        log = self._identify_implicit_start_end_events(log)
        
        # Raggruppa per case
        cases = log.groupby('case:concept:name')
        new_events = []
        
        for case_id, case_events in cases:
            case_events = case_events.sort_values('time:timestamp').reset_index(drop=True)
            
            # Controlla se ha già start event esplicito
            has_explicit_start = any(case_events['nodeType'] == 'startEvent')
            if not has_explicit_start:
                # Crea start event basato sul primo evento reale
                first_real_event = case_events.iloc[0].copy()
                start_event = first_real_event.copy()
                start_event['concept:name'] = 'Start'
                start_event['nodeType'] = 'startEvent'
                start_event['lifecycle:transition'] = 'complete'
                start_event['time:timestamp'] = first_real_event['time:timestamp'] - pd.Timedelta(seconds=1)
                start_event['org:resource'] = np.nan
                start_event['resourceCost'] = np.nan
                start_event['fixedCost'] = np.nan
                new_events.append(start_event)
            
            # Controlla se ha già end event esplicito
            has_explicit_end = any(case_events['nodeType'] == 'endEvent')
            if not has_explicit_end:
                # Crea end event basato sull'ultimo evento reale
                last_real_event = case_events.iloc[-1].copy()
                end_event = last_real_event.copy()
                end_event['concept:name'] = 'End'
                end_event['nodeType'] = 'endEvent'
                end_event['lifecycle:transition'] = 'complete'
                end_event['time:timestamp'] = last_real_event['time:timestamp'] + pd.Timedelta(seconds=1)
                end_event['org:resource'] = np.nan
                end_event['resourceCost'] = np.nan
                end_event['fixedCost'] = np.nan
                new_events.append(end_event)
        
        # Aggiungi nuovi eventi
        if new_events:
            new_events_df = pd.DataFrame(new_events)
            log = pd.concat([log, new_events_df], ignore_index=True)
            log = log.sort_values(['case:concept:name', 'time:timestamp']).reset_index(drop=True)
        
        return log
    
    def _identify_implicit_start_end_events(self, log: pd.DataFrame) -> pd.DataFrame:
        """Identifica eventi che implicitamente sono start/end e li marca correttamente."""
        
        adapted_log = log.copy()
        
        # Per log manufacturing, identifica pattern di start
        manufacturing_start_patterns = [
            r'corner.*return',  # corner2_RETURN spesso è l'inizio
            r'.*_return#',
            r'entry',
            r'input'
        ]
        
        # Pattern di end
        manufacturing_end_patterns = [
            r'.*forward',      # pattern _FORWARD spesso è la fine
            r'.*_forward',
            r'output',
            r'exit',
            r'final'
        ]
        # Applica pattern per identificare start impliciti
        for pattern in manufacturing_start_patterns:
            mask = adapted_log['concept:name'].str.contains(pattern, case=False, na=False)
            # Se è il primo evento della traccia, marcalo come potenziale start
            first_events_mask = adapted_log.groupby('case:concept:name')['time:timestamp'].transform('min') == adapted_log['time:timestamp']
            adapted_log.loc[mask & first_events_mask, 'nodeType'] = 'startEvent'
        
        # Applica pattern per identificare end impliciti  
        for pattern in manufacturing_end_patterns:
            mask = adapted_log['concept:name'].str.contains(pattern, case=False, na=False)
            # Se è l'ultimo evento della traccia, marcalo come potenziale end
            last_events_mask = adapted_log.groupby('case:concept:name')['time:timestamp'].transform('max') == adapted_log['time:timestamp']
            adapted_log.loc[mask & last_events_mask, 'nodeType'] = 'endEvent'
        
        return adapted_log
        
    
    def _reorder_columns(self, log: pd.DataFrame) -> pd.DataFrame:
        """Riordina le colonne nell'ordine previsto dal sistema."""
        
        # Ordine preferito basato su traces.xes funzionante
        preferred_order = [
            'case:concept:name',
            'concept:name', 
            'time:timestamp',
            'lifecycle:transition',
            'nodeType',
            'poolName',
            'instanceType',
            'org:resource',
            'resourceCost',
            'fixedCost'
        ]
        
        # Mantieni colonne esistenti nell'ordine, poi aggiungi quelle non ordinate
        ordered_columns = []
        for col in preferred_order:
            if col in log.columns:
                ordered_columns.append(col)
        
        # Aggiungi colonne rimanenti
        remaining_columns = [col for col in log.columns if col not in ordered_columns]
        ordered_columns.extend(remaining_columns)
        
        return log[ordered_columns]
    
    def _validate_adapted_format(self, log: pd.DataFrame) -> Dict[str, Any]:
        """Valida che il log adattato sia nel formato richiesto dal sistema."""
        
        errors = []
        warnings = []
        
        # Verifica colonne obbligatorie
        required_cols = ['case:concept:name', 'concept:name', 'time:timestamp', 'lifecycle:transition']
        for col in required_cols:
            if col not in log.columns:
                errors.append(f"Colonna obbligatoria mancante: {col}")
        
        # Verifica colonne importanti per il sistema
        important_cols = ['nodeType', 'poolName', 'instanceType']
        for col in important_cols:
            if col not in log.columns:
                warnings.append(f"Colonna importante mancante: {col}")
        
        # Verifica valori lifecycle
        if 'lifecycle:transition' in log.columns:
            valid_lifecycles = {'assign', 'start', 'complete'}
            invalid_lifecycles = set(log['lifecycle:transition'].dropna()) - valid_lifecycles
            if invalid_lifecycles:
                warnings.append(f"Lifecycle non standard trovati: {invalid_lifecycles}")
        
        # Verifica presenza start/end
        if 'nodeType' in log.columns:
            node_types = set(log['nodeType'].dropna())
            if 'startEvent' not in node_types:
                warnings.append("Nessun startEvent trovato")
            if 'endEvent' not in node_types:
                warnings.append("Nessun endEvent trovato")
        
        # VALIDAZIONI CRITICHE PER SPLITMINER
        # Verifica che ci siano almeno 2 case diversi
        if 'case:concept:name' in log.columns:
            unique_cases = log['case:concept:name'].nunique()
            if unique_cases < 2:
                errors.append(f"Troppo pochi case unici per process discovery: {unique_cases}")
        
        # Verifica che ci siano almeno 2 attività diverse
        if 'concept:name' in log.columns:
            unique_activities = log['concept:name'].nunique()
            if unique_activities < 2:
                errors.append(f"Troppo poche attività uniche per process discovery: {unique_activities}")
        
        # Verifica che i timestamp siano ordinati per case
        if 'case:concept:name' in log.columns and 'time:timestamp' in log.columns:
            timestamp_issues = 0
            for case_id, case_data in log.groupby('case:concept:name'):
                if not case_data['time:timestamp'].is_monotonic_increasing:
                    timestamp_issues += 1
            
            if timestamp_issues > 0:
                warnings.append(f"Timestamp non ordinati in {timestamp_issues} tracce")
        
        # Verifica lunghezza tracce
        if 'case:concept:name' in log.columns:
            trace_lengths = log.groupby('case:concept:name').size()
            short_traces = (trace_lengths < 2).sum()
            if short_traces > 0:
                warnings.append(f"{short_traces} tracce hanno meno di 2 eventi")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_events': len(log),
                'unique_cases': log['case:concept:name'].nunique() if 'case:concept:name' in log.columns else 0,
                'unique_activities': log['concept:name'].nunique() if 'concept:name' in log.columns else 0,
                'columns': list(log.columns),
                'avg_trace_length': log.groupby('case:concept:name').size().mean() if 'case:concept:name' in log.columns else 0
            }
        }
    
    def _fix_process_discovery_issues(self, log: pd.DataFrame) -> pd.DataFrame:
        """Corregge problemi comuni che impediscono il process discovery."""
        
        fixed_log = log.copy()
        
        # 1. Assicura che ci siano almeno 2 case diversi
        if 'case:concept:name' in fixed_log.columns:
            unique_cases = fixed_log['case:concept:name'].nunique()
            if unique_cases < 2:
                print("⚠️ Creando tracce multiple per process discovery...")
                # Duplica il log creando varianti
                variants = []
                for i in range(2):
                    variant = fixed_log.copy()
                    variant['case:concept:name'] = variant['case:concept:name'].astype(str) + f"_variant_{i+1}"
                    # Aggiungi variazione temporale
                    variant['time:timestamp'] = variant['time:timestamp'] + pd.Timedelta(hours=i)
                    variants.append(variant)
                
                fixed_log = pd.concat(variants, ignore_index=True)
        
        # 2. Assicura che ci siano almeno 2 attività diverse per traccia
        if 'concept:name' in fixed_log.columns:
            for case_id, case_data in fixed_log.groupby('case:concept:name'):
                if case_data['concept:name'].nunique() < 2:
                    # Aggiungi attività fittizia se la traccia ha una sola attività
                    last_event = case_data.iloc[-1].copy()
                    end_event = last_event.copy()
                    end_event['concept:name'] = 'ProcessEnd'
                    end_event['nodeType'] = 'endEvent'
                    end_event['time:timestamp'] = last_event['time:timestamp'] + pd.Timedelta(minutes=1)
                    
                    fixed_log = pd.concat([fixed_log, pd.DataFrame([end_event])], ignore_index=True)
        
        # 3. Ordina timestamp per case
        fixed_log = fixed_log.sort_values(['case:concept:name', 'time:timestamp']).reset_index(drop=True)
        
        # 4. Rimuovi duplicati esatti
        fixed_log = fixed_log.drop_duplicates().reset_index(drop=True)
        
        return fixed_log
    
    def get_adaptation_report(self, original_path: str, adapted_path: str) -> Dict[str, Any]:
        """Genera report dell'adattamento effettuato."""
        
        try:
            original_log = pm4py.read_xes(original_path)
            adapted_log = pm4py.read_xes(adapted_path)
            
            return {
                'original_file': original_path,
                'adapted_file': adapted_path,
                'transformation': {
                    'original_columns': list(original_log.columns),
                    'adapted_columns': list(adapted_log.columns),
                    'original_events': len(original_log),
                    'adapted_events': len(adapted_log),
                    'added_events': len(adapted_log) - len(original_log),
                    'columns_added': len(adapted_log.columns) - len(original_log.columns)
                },
                'system_compatibility': self._validate_adapted_format(adapted_log)
            }
            
        except Exception as e:
            return {'error': f"Errore nella generazione report: {str(e)}"}


# Funzione di utilità per uso diretto
def adapt_xes_for_system(input_path: str, output_path: str = None) -> Tuple[str, Dict]:
    """
    Adatta un file XES al formato richiesto dal sistema esistente.
    
    Args:
        input_path: Percorso del file XES da adattare
        output_path: Percorso del file adattato (opzionale)
        
    Returns:
        Tupla (percorso_file_adattato, report)
    """
    adapter = XESAdapter()
    
    # Adatta il file
    adapted_path = adapter.adapt_xes_to_system_format(input_path, output_path)
    
    # Genera report
    report = adapter.get_adaptation_report(input_path, adapted_path)
    
    return adapted_path, report


if __name__ == "__main__":
    # Test con il file problematico
    try:
        print("🧪 Test adattamento event_log_processed.xes")
        adapted_file, report = adapt_xes_for_system("event_log_processed.xes")
        
        print("\n📊 REPORT ADATTAMENTO:")
        print(f"File originale: {report['original_file']}")
        print(f"File adattato: {report['adapted_file']}")
        print(f"Eventi: {report['transformation']['original_events']} → {report['transformation']['adapted_events']}")
        print(f"Colonne: {len(report['transformation']['original_columns'])} → {len(report['transformation']['adapted_columns'])}")
        print(f"Eventi aggiunti: {report['transformation']['added_events']}")
        
        compatibility = report['system_compatibility']
        print(f"\n✅ Compatibilità sistema: {'OK' if compatibility['valid'] else 'ERRORI'}")
        
        if compatibility['warnings']:
            print("⚠️ Avvisi:")
            for warning in compatibility['warnings']:
                print(f"   - {warning}")
        
        if compatibility['errors']:
            print("❌ Errori:")
            for error in compatibility['errors']:
                print(f"   - {error}")
        
        print(f"\n🎯 File adattato pronto: {adapted_file}")
        print("   Ora può essere processato dal tuo sistema esistente!")
        
    except Exception as e:
        print(f"❌ Errore nel test: {e}")
  
    
    def _reorder_columns(self, log: pd.DataFrame) -> pd.DataFrame:
        """Riordina le colonne nell'ordine previsto dal sistema."""
        
        # Ordine preferito basato su traces.xes funzionante
        preferred_order = [
            'case:concept:name',
            'concept:name', 
            'time:timestamp',
            'lifecycle:transition',
            'nodeType',
            'poolName',
            'instanceType',
            'org:resource',
            'resourceCost',
            'fixedCost'
        ]
        
        # Mantieni colonne esistenti nell'ordine, poi aggiungi quelle non ordinate
        ordered_columns = []
        for col in preferred_order:
            if col in log.columns:
                ordered_columns.append(col)
        
        # Aggiungi colonne rimanenti
        remaining_columns = [col for col in log.columns if col not in ordered_columns]
        ordered_columns.extend(remaining_columns)
        
        return log[ordered_columns]
    
    def _validate_adapted_format(self, log: pd.DataFrame) -> Dict[str, Any]:
        """Valida che il log adattato sia nel formato richiesto dal sistema."""
        
        errors = []
        warnings = []
        
        # Verifica colonne obbligatorie
        required_cols = ['case:concept:name', 'concept:name', 'time:timestamp', 'lifecycle:transition']
        for col in required_cols:
            if col not in log.columns:
                errors.append(f"Colonna obbligatoria mancante: {col}")
        
        # Verifica colonne importanti per il sistema
        important_cols = ['nodeType', 'poolName', 'instanceType']
        for col in important_cols:
            if col not in log.columns:
                warnings.append(f"Colonna importante mancante: {col}")
        
        # Verifica valori lifecycle
        if 'lifecycle:transition' in log.columns:
            valid_lifecycles = {'assign', 'start', 'complete'}
            invalid_lifecycles = set(log['lifecycle:transition'].dropna()) - valid_lifecycles
            if invalid_lifecycles:
                warnings.append(f"Lifecycle non standard trovati: {invalid_lifecycles}")
        
        # Verifica presenza start/end
        if 'nodeType' in log.columns:
            node_types = set(log['nodeType'].dropna())
            if 'startEvent' not in node_types:
                warnings.append("Nessun startEvent trovato")
            if 'endEvent' not in node_types:
                warnings.append("Nessun endEvent trovato")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_events': len(log),
                'unique_cases': log['case:concept:name'].nunique() if 'case:concept:name' in log.columns else 0,
                'unique_activities': log['concept:name'].nunique() if 'concept:name' in log.columns else 0,
                'columns': list(log.columns)
            }
        }
    
    def get_adaptation_report(self, original_path: str, adapted_path: str) -> Dict[str, Any]:
        """Genera report dell'adattamento effettuato."""
        
        try:
            original_log = pm4py.read_xes(original_path)
            adapted_log = pm4py.read_xes(adapted_path)
            
            return {
                'original_file': original_path,
                'adapted_file': adapted_path,
                'transformation': {
                    'original_columns': list(original_log.columns),
                    'adapted_columns': list(adapted_log.columns),
                    'original_events': len(original_log),
                    'adapted_events': len(adapted_log),
                    'added_events': len(adapted_log) - len(original_log),
                    'columns_added': len(adapted_log.columns) - len(original_log.columns)
                },
                'system_compatibility': self._validate_adapted_format(adapted_log)
            }
            
        except Exception as e:
            return {'error': f"Errore nella generazione report: {str(e)}"}


# Funzione di utilità per uso diretto
def adapt_xes_for_system(input_path: str, output_path: str = None) -> Tuple[str, Dict]:
    """
    Adatta un file XES al formato richiesto dal sistema esistente.
    
    Args:
        input_path: Percorso del file XES da adattare
        output_path: Percorso del file adattato (opzionale)
        
    Returns:
        Tupla (percorso_file_adattato, report)
    """
    adapter = XESAdapter()
    
    # Adatta il file
    adapted_path = adapter.adapt_xes_to_system_format(input_path, output_path)
    
    # Genera report
    report = adapter.get_adaptation_report(input_path, adapted_path)
    
    return adapted_path, report


if __name__ == "__main__":
    # Test con il file problematico
    try:
        print("🧪 Test adattamento event_log_processed.xes")
        adapted_file, report = adapt_xes_for_system("event_log_processed.xes")
        
        print("\n📊 REPORT ADATTAMENTO:")
        print(f"File originale: {report['original_file']}")
        print(f"File adattato: {report['adapted_file']}")
        print(f"Eventi: {report['transformation']['original_events']} → {report['transformation']['adapted_events']}")
        print(f"Colonne: {len(report['transformation']['original_columns'])} → {len(report['transformation']['adapted_columns'])}")
        print(f"Eventi aggiunti: {report['transformation']['added_events']}")
        
        compatibility = report['system_compatibility']
        print(f"\n✅ Compatibilità sistema: {'OK' if compatibility['valid'] else 'ERRORI'}")
        
        if compatibility['warnings']:
            print("⚠️ Avvisi:")
            for warning in compatibility['warnings']:
                print(f"   - {warning}")
        
        if compatibility['errors']:
            print("❌ Errori:")
            for error in compatibility['errors']:
                print(f"   - {error}")
        
        print(f"\n🎯 File adattato pronto: {adapted_file}")
        print("   Ora può essere processato dal tuo sistema esistente!")
        
    except Exception as e:
        print(f"❌ Errore nel test: {e}")
        
        
    
    def _reorder_columns(self, log: pd.DataFrame) -> pd.DataFrame:
        """Riordina le colonne nell'ordine previsto dal sistema."""
        
        # Ordine preferito basato su traces.xes funzionante
        preferred_order = [
            'case:concept:name',
            'concept:name', 
            'time:timestamp',
            'lifecycle:transition',
            'nodeType',
            'poolName',
            'instanceType',
            'org:resource',
            'resourceCost',
            'fixedCost'
        ]
        
        # Mantieni colonne esistenti nell'ordine, poi aggiungi quelle non ordinate
        ordered_columns = []
        for col in preferred_order:
            if col in log.columns:
                ordered_columns.append(col)
        
        # Aggiungi colonne rimanenti
        remaining_columns = [col for col in log.columns if col not in ordered_columns]
        ordered_columns.extend(remaining_columns)
        
        return log[ordered_columns]
    
    def _validate_adapted_format(self, log: pd.DataFrame) -> Dict[str, Any]:
        """Valida che il log adattato sia nel formato richiesto dal sistema."""
        
        errors = []
        warnings = []
        
        # Verifica colonne obbligatorie
        required_cols = ['case:concept:name', 'concept:name', 'time:timestamp', 'lifecycle:transition']
        for col in required_cols:
            if col not in log.columns:
                errors.append(f"Colonna obbligatoria mancante: {col}")
        
        # Verifica colonne importanti per il sistema
        important_cols = ['nodeType', 'poolName', 'instanceType']
        for col in important_cols:
            if col not in log.columns:
                warnings.append(f"Colonna importante mancante: {col}")
        
        # Verifica valori lifecycle
        if 'lifecycle:transition' in log.columns:
            valid_lifecycles = {'assign', 'start', 'complete'}
            invalid_lifecycles = set(log['lifecycle:transition'].dropna()) - valid_lifecycles
            if invalid_lifecycles:
                warnings.append(f"Lifecycle non standard trovati: {invalid_lifecycles}")
        
        # Verifica presenza start/end
        if 'nodeType' in log.columns:
            node_types = set(log['nodeType'].dropna())
            if 'startEvent' not in node_types:
                warnings.append("Nessun startEvent trovato")
            if 'endEvent' not in node_types:
                warnings.append("Nessun endEvent trovato")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'stats': {
                'total_events': len(log),
                'unique_cases': log['case:concept:name'].nunique() if 'case:concept:name' in log.columns else 0,
                'unique_activities': log['concept:name'].nunique() if 'concept:name' in log.columns else 0,
                'columns': list(log.columns)
            }
        }
    
    def get_adaptation_report(self, original_path: str, adapted_path: str) -> Dict[str, Any]:
        """Genera report dell'adattamento effettuato."""
        
        try:
            original_log = pm4py.read_xes(original_path)
            adapted_log = pm4py.read_xes(adapted_path)
            
            return {
                'original_file': original_path,
                'adapted_file': adapted_path,
                'transformation': {
                    'original_columns': list(original_log.columns),
                    'adapted_columns': list(adapted_log.columns),
                    'original_events': len(original_log),
                    'adapted_events': len(adapted_log),
                    'added_events': len(adapted_log) - len(original_log),
                    'columns_added': len(adapted_log.columns) - len(original_log.columns)
                },
                'system_compatibility': self._validate_adapted_format(adapted_log)
            }
            
        except Exception as e:
            return {'error': f"Errore nella generazione report: {str(e)}"}
        
    def adapt_xes_to_system_format(self, input_path: str, output_path: str = None) -> str:
        """
        Adatta un log XES qualsiasi al formato richiesto dal tuo sistema.
        
        Args:
            input_path: Percorso del file XES da adattare
            output_path: Percorso del file XES adattato (opzionale)
            
        Returns:
            Percorso del file adattato
        """
        try:
            print(f"🔧 Adattando {input_path} al formato sistema...")
            
            # 1. Carica il log
            log = pm4py.read_xes(input_path)
            print(f"   📊 Log caricato: {len(log)} eventi, {len(log.columns)} colonne")
            
            # 2. Analizza struttura esistente
            analysis = self._analyze_existing_structure(log)
            print(f"   🔍 Struttura analizzata: {analysis['log_type']}")
            
            # 3. Mappa colonne esistenti a quelle richieste
            adapted_log = self._map_existing_columns(log, analysis)
            
            # 4. Aggiungi colonne mancanti obbligatorie
            adapted_log = self._add_required_columns(adapted_log, analysis)
            
            # 5. Standardizza valori nelle colonne
            adapted_log = self._standardize_column_values(adapted_log, analysis)
            
            # 6. Crea eventi start/end se mancanti
            adapted_log = self._ensure_start_end_events(adapted_log)
            
            # 7. Correggi problemi per process discovery
            adapted_log = self._fix_process_discovery_issues(adapted_log)
            
            # 8. Riordina colonne nell'ordine corretto
            adapted_log = self._reorder_columns(adapted_log)
            
            # 9. Valida formato finale
            validation = self._validate_adapted_format(adapted_log)
            
            if validation['warnings']:
                print("   ⚠️ Avvisi di validazione:")
                for warning in validation['warnings']:
                    print(f"      - {warning}")
            
            if not validation['valid']:
                print("   ❌ Errori critici trovati, tentativo di correzione...")
                # Tento una correzione finale
                adapted_log = self._final_fix_attempt(adapted_log)
                validation = self._validate_adapted_format(adapted_log)
                
                if not validation['valid']:
                    raise Exception(f"Impossibile correggere errori critici: {validation['errors']}")
            
            # 10. Salva il log adattato
            if output_path is None:
                base_name = os.path.splitext(input_path)[0]
                output_path = f"{base_name}_adapted.xes"
            
            pm4py.write_xes(adapted_log, output_path, case_id_key='case:concept:name')
            
            print(f"✅ Log adattato salvato: {output_path}")
            print(f"   📈 Eventi finali: {len(adapted_log)}")
            print(f"   🔢 Tracce uniche: {validation['stats']['unique_cases']}")
            print(f"   🎯 Attività uniche: {validation['stats']['unique_activities']}")
            print(f"   📏 Lunghezza media tracce: {validation['stats']['avg_trace_length']:.1f}")
            
            return output_path
            
        except Exception as e:
            raise Exception(f"Errore nell'adattamento: {str(e)}")
    
    def _final_fix_attempt(self, log: pd.DataFrame) -> pd.DataFrame:
        """Tentativo finale di correzione per problemi critici."""
        
        fixed_log = log.copy()
        
        # Assicura almeno 2 case diversi
        if 'case:concept:name' in fixed_log.columns:
            unique_cases = fixed_log['case:concept:name'].nunique()
            if unique_cases < 2:
                print("      🔧 Creando tracce multiple...")
                # Crea 3 varianti della stessa traccia
                variants = []
                base_log = fixed_log.copy()
                
                for i in range(3):
                    variant = base_log.copy()
                    variant['case:concept:name'] = f"case_{i+1}"
                    # Varia i timestamp per simulare processi diversi
                    variant['time:timestamp'] = variant['time:timestamp'] + pd.Timedelta(hours=i*2)
                    variants.append(variant)
                
                fixed_log = pd.concat(variants, ignore_index=True)
        
        # Assicura almeno 2 attività diverse
        if 'concept:name' in fixed_log.columns:
            unique_activities = fixed_log['concept:name'].nunique()
            if unique_activities < 2:
                print("      🔧 Aggiungendo attività diverse...")
                # Aggiungi eventi start/end se non esistono
                new_events = []
                
                for case_id in fixed_log['case:concept:name'].unique():
                    case_data = fixed_log[fixed_log['case:concept:name'] == case_id]
                    
                    # Start event
                    start_event = case_data.iloc[0].copy()
                    start_event['concept:name'] = 'ProcessStart'
                    start_event['nodeType'] = 'startEvent'
                    start_event['time:timestamp'] = case_data['time:timestamp'].min() - pd.Timedelta(minutes=1)
                    new_events.append(start_event)
                    
                    # End event
                    end_event = case_data.iloc[-1].copy()
                    end_event['concept:name'] = 'ProcessEnd'
                    end_event['nodeType'] = 'endEvent'
                    end_event['time:timestamp'] = case_data['time:timestamp'].max() + pd.Timedelta(minutes=1)
                    new_events.append(end_event)
                
                if new_events:
                    new_events_df = pd.DataFrame(new_events)
                    fixed_log = pd.concat([fixed_log, new_events_df], ignore_index=True)
        
        # Ordina e pulisci
        fixed_log = fixed_log.sort_values(['case:concept:name', 'time:timestamp']).reset_index(drop=True)
        fixed_log = fixed_log.drop_duplicates().reset_index(drop=True)
        
        return fixed_log


# Funzione di utilità per uso diretto
def adapt_xes_for_system(input_path: str, output_path: str = None) -> Tuple[str, Dict]:
    """
    Adatta un file XES al formato richiesto dal sistema esistente.
    
    Args:
        input_path: Percorso del file XES da adattare
        output_path: Percorso del file adattato (opzionale)
        
    Returns:
        Tupla (percorso_file_adattato, report)
    """
    adapter = XESAdapter()
    
    # Adatta il file
    adapted_path = adapter.adapt_xes_to_system_format(input_path, output_path)
    
    # Genera report
    report = adapter.get_adaptation_report(input_path, adapted_path)
    
    return adapted_path, report





if __name__ == "__main__":
    # Test con il file problematico
    try:
        print("🧪 Test adattamento event_log_processed.xes")
        adapted_file, report = adapt_xes_for_system("event_log_processed.xes")
        
        print("\n📊 REPORT ADATTAMENTO:")
        print(f"File originale: {report['original_file']}")
        print(f"File adattato: {report['adapted_file']}")
        print(f"Eventi: {report['transformation']['original_events']} → {report['transformation']['adapted_events']}")
        print(f"Colonne: {len(report['transformation']['original_columns'])} → {len(report['transformation']['adapted_columns'])}")
        print(f"Eventi aggiunti: {report['transformation']['added_events']}")
        
        compatibility = report['system_compatibility']
        print(f"\n✅ Compatibilità sistema: {'OK' if compatibility['valid'] else 'ERRORI'}")
        
        if compatibility['warnings']:
            print("⚠️ Avvisi:")
            for warning in compatibility['warnings']:
                print(f"   - {warning}")
        
        if compatibility['errors']:
            print("❌ Errori:")
            for error in compatibility['errors']:
                print(f"   - {error}")
        
        print(f"\n🎯 File adattato pronto: {adapted_file}")
        print("   Ora può essere processato dal tuo sistema esistente!")
        
    except Exception as e:
        print(f"❌ Errore nel test: {e}")

    