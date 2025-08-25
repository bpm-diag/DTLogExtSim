import pm4py
import pandas as pd
import numpy as np
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime


class XESLogNormalizer:
    """
    Classe per normalizzare qualsiasi log XES al formato interpretabile dal tuo sistema.
    
    Converte automaticamente log XES con strutture diverse al formato standard
    richiesto dai tuoi script di estrazione parametri.
    """
    
    def __init__(self):
        """Inizializza il normalizzatore XES."""
        # Mapping per normalizzazione colonne
        self.standard_columns = {
            'case_id': 'case:concept:name',
            'activity': 'concept:name', 
            'timestamp': 'time:timestamp',
            'lifecycle': 'lifecycle:transition',
            'resource': 'org:resource',
            'node_type': 'nodeType',
            'pool_name': 'poolName',
            'instance_type': 'instanceType',
            'cost_hour': 'resourceCost',
            'fixed_cost': 'fixedCost'
        }
        
        # Pattern comuni per identificare colonne
        self.column_patterns = {
            'case_id': [r'case', r'trace', r'process', r'instance'],
            'activity': [r'activity', r'task', r'concept', r'name'],
            'timestamp': [r'time', r'date', r'timestamp'],
            'lifecycle': [r'lifecycle', r'transition', r'state'],
            'resource': [r'resource', r'user', r'person', r'actor'],
            'node_type': [r'type', r'node', r'element'],
            'cost': [r'cost', r'price', r'expense']
        }
        
        # Valori standard per lifecycle
        self.lifecycle_mapping = {
            'complete': ['complete', 'end', 'finish', 'done'],
            'start': ['start', 'begin', 'initiate'],
            'assign': ['assign', 'allocate', 'schedule']
        }
        
        print("XESLogNormalizer inizializzato")
    
    def normalize_xes_log(self, input_path: str, output_path: str = None) -> str:
        """
        Normalizza un log XES al formato interpretabile dal sistema.
        
        Args:
            input_path: Percorso del file XES di input
            output_path: Percorso del file XES normalizzato (opzionale)
            
        Returns:
            Percorso del file normalizzato
        """
        try:
            print(f"Iniziando normalizzazione di: {input_path}")
            
            # 1. Carica il log
            log = pm4py.read_xes(input_path)
            
            # 2. Analizza la struttura
            structure_info = self._analyze_log_structure(log)
            
            # 3. Normalizza le colonne
            normalized_log = self._normalize_columns(log, structure_info)
            
            # 4. Standardizza i valori
            normalized_log = self._standardize_values(normalized_log)
            
            # 5. Aggiungi colonne mancanti essenziali
            normalized_log = self._add_missing_columns(normalized_log)
            
            # 6. Identifica e normalizza start/end events
            normalized_log = self._normalize_start_end_events(normalized_log)
            
            # 7. Pulisci e valida
            normalized_log = self._clean_and_validate(normalized_log)
            
            # 8. Salva il log normalizzato
            if output_path is None:
                base_name = os.path.splitext(input_path)[0]
                output_path = f"{base_name}_normalized.xes"
            
            pm4py.write_xes(normalized_log, output_path, case_id_key='case:concept:name')
            
            print(f"✓ Log normalizzato salvato: {output_path}")
            return output_path
            
        except Exception as e:
            raise Exception(f"Errore nella normalizzazione: {str(e)}")
    
    def _analyze_log_structure(self, log: pd.DataFrame) -> Dict[str, Any]:
        """
        Analizza la struttura del log per identificare le colonne e i pattern.
        
        Args:
            log: DataFrame del log
            
        Returns:
            Dizionario con informazioni sulla struttura
        """
        print("Analizzando struttura del log...")
        
        structure_info = {
            'columns': list(log.columns),
            'column_mapping': {},
            'is_diagnostic_log': False,
            'has_resources': False,
            'has_costs': False,
            'activity_patterns': set(),
            'unique_activities': set(log.get('concept:name', pd.Series()).dropna().unique()),
            'unique_lifecycles': set(log.get('lifecycle:transition', pd.Series()).dropna().unique())
        }
        
        # Identifica mapping colonne automaticamente
        for standard_col, patterns in self.column_patterns.items():
            best_match = self._find_best_column_match(log.columns, patterns, standard_col)
            if best_match:
                structure_info['column_mapping'][standard_col] = best_match
        
        # Verifica se è un log diagnostico
        structure_info['is_diagnostic_log'] = any(
            'nodeType' in col or 'poolName' in col for col in log.columns
        )
        
        # Verifica presenza risorse
        structure_info['has_resources'] = any(
            'resource' in col.lower() for col in log.columns
        )
        
        # Verifica presenza costi
        structure_info['has_costs'] = any(
            'cost' in col.lower() for col in log.columns
        )
        
        # Identifica pattern attività (start, end, gateway)
        for activity in structure_info['unique_activities']:
            if activity and isinstance(activity, str):
                activity_lower = activity.lower()
                if any(pattern in activity_lower for pattern in ['start', 'begin', 'initial']):
                    structure_info['activity_patterns'].add('start')
                elif any(pattern in activity_lower for pattern in ['end', 'finish', 'final', 'terminate']):
                    structure_info['activity_patterns'].add('end')
                elif any(pattern in activity_lower for pattern in ['gateway', 'split', 'merge', 'decision']):
                    structure_info['activity_patterns'].add('gateway')
        
        print(f"✓ Struttura analizzata: {len(structure_info['columns'])} colonne, "
              f"{'DIAG' if structure_info['is_diagnostic_log'] else 'STANDARD'} log")
        
        return structure_info
    
    def _find_best_column_match(self, columns: List[str], patterns: List[str], 
                               target_type: str) -> Optional[str]:
        """
        Trova la colonna che meglio corrisponde ai pattern.
        
        Args:
            columns: Lista delle colonne disponibili
            patterns: Pattern da cercare
            target_type: Tipo di colonna target
            
        Returns:
            Nome della colonna migliore o None
        """
        scores = {}
        
        for col in columns:
            score = 0
            col_lower = col.lower()
            
            # Punteggio per match esatti
            for pattern in patterns:
                if pattern in col_lower:
                    # Match esatto vale di più
                    if col_lower == pattern:
                        score += 10
                    elif col_lower.endswith(pattern) or col_lower.startswith(pattern):
                        score += 5
                    else:
                        score += 2
            
            # Bonus per colonne standard XES
            if col in self.standard_columns.values():
                score += 8
            
            # Penalità per colonne troppo generiche
            if len(col) <= 2:
                score -= 2
                
            if score > 0:
                scores[col] = score
        
        # Restituisci la colonna con punteggio maggiore
        if scores:
            return max(scores, key=scores.get)
        
        return None
    
    def _normalize_columns(self, log: pd.DataFrame, structure_info: Dict) -> pd.DataFrame:
        """
        Normalizza i nomi delle colonne al formato standard.
        
        Args:
            log: DataFrame del log
            structure_info: Informazioni sulla struttura
            
        Returns:
            DataFrame con colonne normalizzate
        """
        print("Normalizzando nomi colonne...")
        
        normalized_log = log.copy()
        column_mapping = structure_info['column_mapping']
        
        # Rinomina colonne identificate automaticamente
        rename_map = {}
        
        if 'case_id' in column_mapping:
            rename_map[column_mapping['case_id']] = self.standard_columns['case_id']
        
        if 'activity' in column_mapping:
            rename_map[column_mapping['activity']] = self.standard_columns['activity']
        
        if 'timestamp' in column_mapping:
            rename_map[column_mapping['timestamp']] = self.standard_columns['timestamp']
        
        if 'lifecycle' in column_mapping:
            rename_map[column_mapping['lifecycle']] = self.standard_columns['lifecycle']
        
        if 'resource' in column_mapping:
            rename_map[column_mapping['resource']] = self.standard_columns['resource']
        
        # Gestione speciale per colonne multiple di costo
        cost_columns = [col for col in log.columns if 'cost' in col.lower()]
        if cost_columns:
            # Prendi la prima colonna costo come resourceCost
            if cost_columns[0] not in rename_map.values():
                rename_map[cost_columns[0]] = self.standard_columns['cost_hour']
        
        # Applica rinominazione
        if rename_map:
            normalized_log = normalized_log.rename(columns=rename_map)
            print(f"✓ Rinominate {len(rename_map)} colonne")
        
        return normalized_log
    
    def _standardize_values(self, log: pd.DataFrame) -> pd.DataFrame:
        """
        Standardizza i valori nelle colonne normalizzate.
        
        Args:
            log: DataFrame del log
            
        Returns:
            DataFrame con valori standardizzati
        """
        print("Standardizzando valori...")
        
        normalized_log = log.copy()
        
        # Standardizza lifecycle transitions
        if self.standard_columns['lifecycle'] in normalized_log.columns:
            normalized_log = self._standardize_lifecycle_values(normalized_log)
        
        # Standardizza timestamp
        if self.standard_columns['timestamp'] in normalized_log.columns:
            normalized_log = self._standardize_timestamps(normalized_log)
        
        # Standardizza risorse
        if self.standard_columns['resource'] in normalized_log.columns:
            normalized_log = self._standardize_resources(normalized_log)
        
        return normalized_log
    
    def _standardize_lifecycle_values(self, log: pd.DataFrame) -> pd.DataFrame:
        """Standardizza i valori del lifecycle."""
        lifecycle_col = self.standard_columns['lifecycle']
        
        if lifecycle_col not in log.columns:
            return log
        
        # Mappa valori al formato standard
        value_mapping = {}
        
        for standard_value, variations in self.lifecycle_mapping.items():
            for variation in variations:
                value_mapping[variation] = standard_value
                value_mapping[variation.upper()] = standard_value
                value_mapping[variation.capitalize()] = standard_value
        
        # Applica mapping
        log[lifecycle_col] = log[lifecycle_col].map(value_mapping).fillna(log[lifecycle_col])
        
        # Se non ci sono lifecycle, assume complete
        log[lifecycle_col] = log[lifecycle_col].fillna('complete')
        
        return log
    
    def _standardize_timestamps(self, log: pd.DataFrame) -> pd.DataFrame:
        """Standardizza i timestamp."""
        timestamp_col = self.standard_columns['timestamp']
        
        if timestamp_col not in log.columns:
            return log
        
        # Converti timestamp se necessario
        log[timestamp_col] = pd.to_datetime(log[timestamp_col], errors='coerce')
        
        # Se ci sono timestamp mancanti, crea sequenza temporale fittizia
        if log[timestamp_col].isna().any():
            print("⚠ Timestamp mancanti rilevati, creando sequenza fittizia...")
            base_time = datetime.now()
            
            for i, idx in enumerate(log[log[timestamp_col].isna()].index):
                log.loc[idx, timestamp_col] = base_time + pd.Timedelta(seconds=i)
        
        return log
    
    def _standardize_resources(self, log: pd.DataFrame) -> pd.DataFrame:
        """Standardizza le risorse."""
        resource_col = self.standard_columns['resource']
        
        if resource_col not in log.columns:
            return log
        
        # Se la colonna resource contiene NaN o valori invalidi, sostituisci con default
        mask = log[resource_col].isna() | (log[resource_col] == 'nan')
        log.loc[mask, resource_col] = 'default_resource'
        
        return log
    
    def _add_missing_columns(self, log: pd.DataFrame) -> pd.DataFrame:
        """
        Aggiunge colonne essenziali mancanti.
        
        Args:
            log: DataFrame del log
            
        Returns:
            DataFrame con colonne mancanti aggiunte
        """
        print("Aggiungendo colonne mancanti...")
        
        # Verifica e aggiungi colonne essenziali
        essential_columns = [
            self.standard_columns['case_id'],
            self.standard_columns['activity'],
            self.standard_columns['timestamp'],
            self.standard_columns['lifecycle']
        ]
        
        for col in essential_columns:
            if col not in log.columns:
                if col == self.standard_columns['case_id']:
                    # Crea case ID sequenziali
                    log[col] = range(1, len(log) + 1)
                elif col == self.standard_columns['activity']:
                    # Usa activity generica
                    log[col] = 'GenericActivity'
                elif col == self.standard_columns['timestamp']:
                    # Crea timestamp sequenziali
                    base_time = datetime.now()
                    log[col] = [base_time + pd.Timedelta(seconds=i) for i in range(len(log))]
                elif col == self.standard_columns['lifecycle']:
                    # Default a complete
                    log[col] = 'complete'
        
        # Aggiungi colonne opzionali se mancanti
        optional_columns = {
            self.standard_columns['resource']: 'default_resource',
            self.standard_columns['node_type']: 'task'
        }
        
        for col, default_value in optional_columns.items():
            if col not in log.columns:
                log[col] = default_value
        
        return log
    
    def _normalize_start_end_events(self, log: pd.DataFrame) -> pd.DataFrame:
        """
        Identifica e normalizza eventi di start e end.
        
        Args:
            log: DataFrame del log
            
        Returns:
            DataFrame con eventi start/end normalizzati
        """
        print("Normalizzando eventi start/end...")
        
        activity_col = self.standard_columns['activity']
        
        if activity_col not in log.columns:
            return log
        
        # Pattern per identificare start events
        start_patterns = [
            r'start', r'begin', r'initial', r'first', r'entry', r'open',
            r'startevent', r'startEvent', r'Start'
        ]
        
        # Pattern per identificare end events
        end_patterns = [
            r'end', r'finish', r'final', r'last', r'exit', r'close', r'complete',
            r'endevent', r'endEvent', r'End', r'terminate', r'stop'
        ]
        
        # Normalizza start events
        start_mask = log[activity_col].str.contains('|'.join(start_patterns), case=False, na=False)
        if start_mask.any():
            log.loc[start_mask, activity_col] = 'Start'
            if self.standard_columns['node_type'] in log.columns:
                log.loc[start_mask, self.standard_columns['node_type']] = 'startEvent'
        
        # Normalizza end events  
        end_mask = log[activity_col].str.contains('|'.join(end_patterns), case=False, na=False)
        if end_mask.any():
            log.loc[end_mask, activity_col] = 'End'
            if self.standard_columns['node_type'] in log.columns:
                log.loc[end_mask, self.standard_columns['node_type']] = 'endEvent'
        
        # Identifica gateway
        gateway_patterns = [r'gateway', r'split', r'merge', r'decision', r'choice']
        gateway_mask = log[activity_col].str.contains('|'.join(gateway_patterns), case=False, na=False)
        if gateway_mask.any() and self.standard_columns['node_type'] in log.columns:
            log.loc[gateway_mask, self.standard_columns['node_type']] = 'exclusiveGateway'
        
        return log
    
    def _clean_and_validate(self, log: pd.DataFrame) -> pd.DataFrame:
        """
        Pulisce e valida il log normalizzato.
        
        Args:
            log: DataFrame del log
            
        Returns:
            DataFrame pulito e validato
        """
        print("Pulizia e validazione finale...")
        
        # Rimuovi righe con valori critici mancanti
        essential_cols = [
            self.standard_columns['case_id'],
            self.standard_columns['activity'], 
            self.standard_columns['timestamp']
        ]
        
        before_count = len(log)
        log = log.dropna(subset=essential_cols)
        after_count = len(log)
        
        if before_count != after_count:
            print(f"⚠ Rimosse {before_count - after_count} righe con valori critici mancanti")
        
        # Ordina per case ID e timestamp
        log = log.sort_values([
            self.standard_columns['case_id'], 
            self.standard_columns['timestamp']
        ]).reset_index(drop=True)
        
        # Validazione finale
        validation_results = self._validate_normalized_log(log)
        if not validation_results['is_valid']:
            print(f"⚠ Avvisi di validazione: {validation_results['warnings']}")
        
        return log
    
    def _validate_normalized_log(self, log: pd.DataFrame) -> Dict[str, Any]:
        """
        Valida il log normalizzato.
        
        Args:
            log: DataFrame del log normalizzato
            
        Returns:
            Dizionario con risultati validazione
        """
        warnings = []
        
        # Verifica colonne essenziali
        essential_columns = [
            self.standard_columns['case_id'],
            self.standard_columns['activity'],
            self.standard_columns['timestamp'],
            self.standard_columns['lifecycle']
        ]
        
        missing_essential = [col for col in essential_columns if col not in log.columns]
        if missing_essential:
            warnings.append(f"Colonne essenziali mancanti: {missing_essential}")
        
        # Verifica unicità case IDs
        if self.standard_columns['case_id'] in log.columns:
            case_ids = log[self.standard_columns['case_id']].nunique()
            if case_ids < 2:
                warnings.append("Log contiene meno di 2 case ID unici")
        
        # Verifica timestamp
        if self.standard_columns['timestamp'] in log.columns:
            if log[self.standard_columns['timestamp']].isna().any():
                warnings.append("Timestamp mancanti rilevati")
        
        return {
            'is_valid': len(warnings) == 0,
            'warnings': warnings,
            'log_stats': {
                'total_events': len(log),
                'unique_cases': log[self.standard_columns['case_id']].nunique() if self.standard_columns['case_id'] in log.columns else 0,
                'unique_activities': log[self.standard_columns['activity']].nunique() if self.standard_columns['activity'] in log.columns else 0,
                'columns': list(log.columns)
            }
        }
    
    def get_normalization_report(self, original_path: str, normalized_path: str) -> Dict[str, Any]:
        """
        Genera un report sulla normalizzazione effettuata.
        
        Args:
            original_path: Percorso log originale
            normalized_path: Percorso log normalizzato
            
        Returns:
            Dizionario con il report
        """
        try:
            original_log = pm4py.read_xes(original_path)
            normalized_log = pm4py.read_xes(normalized_path)
            
            report = {
                'original_file': original_path,
                'normalized_file': normalized_path,
                'transformation_summary': {
                    'original_columns': list(original_log.columns),
                    'normalized_columns': list(normalized_log.columns),
                    'original_events': len(original_log),
                    'normalized_events': len(normalized_log),
                    'original_cases': original_log.iloc[:, 0].nunique() if len(original_log) > 0 else 0,
                    'normalized_cases': normalized_log[self.standard_columns['case_id']].nunique(),
                    'original_activities': original_log.iloc[:, 1].nunique() if len(original_log.columns) > 1 else 0,
                    'normalized_activities': normalized_log[self.standard_columns['activity']].nunique()
                },
                'compatibility_check': self._check_system_compatibility(normalized_log)
            }
            
            return report
            
        except Exception as e:
            return {'error': f"Errore nella generazione report: {str(e)}"}
    
    def _check_system_compatibility(self, log: pd.DataFrame) -> Dict[str, bool]:
        """Verifica compatibilità con il tuo sistema."""
        checks = {
            'has_case_id': self.standard_columns['case_id'] in log.columns,
            'has_activity': self.standard_columns['activity'] in log.columns,
            'has_timestamp': self.standard_columns['timestamp'] in log.columns,
            'has_lifecycle': self.standard_columns['lifecycle'] in log.columns,
            'has_start_events': 'Start' in log[self.standard_columns['activity']].values,
            'has_end_events': 'End' in log[self.standard_columns['activity']].values,
            'has_resources': self.standard_columns['resource'] in log.columns,
            'valid_lifecycles': all(lc in ['assign', 'start', 'complete'] 
                                  for lc in log[self.standard_columns['lifecycle']].dropna().unique()),
            'no_missing_critical_data': not log[[
                self.standard_columns['case_id'],
                self.standard_columns['activity'],
                self.standard_columns['timestamp']
            ]].isna().any().any()
        }
        
        return checks


# Funzione di utilità per uso diretto
def normalize_xes_file(input_path: str, output_path: str = None) -> Tuple[str, Dict]:
    """
    Funzione di utilità per normalizzare un file XES.
    
    Args:
        input_path: Percorso del file XES da normalizzare
        output_path: Percorso del file normalizzato (opzionale)
        
    Returns:
        Tupla (percorso_file_normalizzato, report)
    """
    normalizer = XESLogNormalizer()
    
    # Normalizza il file
    normalized_path = normalizer.normalize_xes_log(input_path, output_path)
    
    # Genera report
    report = normalizer.get_normalization_report(input_path, normalized_path)
    
    return normalized_path, report


if __name__ == "__main__":
    # Esempio di utilizzo
    input_file = "event_log_processed.xes"
    
    try:
        normalized_file, report = normalize_xes_file(input_file)
        
        print("\n" + "="*50)
        print("REPORT NORMALIZZAZIONE")
        print("="*50)
        print(f"File originale: {report['original_file']}")
        print(f"File normalizzato: {report['normalized_file']}")
        print(f"Eventi: {report['transformation_summary']['original_events']} → {report['transformation_summary']['normalized_events']}")
        print(f"Colonne: {len(report['transformation_summary']['original_columns'])} → {len(report['transformation_summary']['normalized_columns'])}")
        
        print("\nCompatibilità con il sistema:")
        for check, result in report['compatibility_check'].items():
            status = "✓" if result else "✗"
            print(f"  {status} {check.replace('_', ' ').title()}")
        
        print(f"\n✓ Normalizzazione completata: {normalized_file}")
        
    except Exception as e:
        print(f"✗ Errore: {e}")
