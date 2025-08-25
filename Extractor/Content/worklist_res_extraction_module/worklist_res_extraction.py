import pandas as pd
import numpy as np
import os
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple, Set

from support_modules.constants import *


class WorklistCalculation:
    """
    Classe per il calcolo delle worklist (regole di binding tra attività).
    
    Implementa l'algoritmo per identificare regole di "Retain Familiar" o "Binding of Duties"
    dove le attività T1 e T2 sono eseguite dalla stessa risorsa più frequentemente 
    di quanto ci si aspetterebbe per caso.
    
    Regola: binding(T1, T2) iff start(of T1 by :p) and start(of T2) implies start(of T2 by p)
    """
    
    def __init__(self, log: pd.DataFrame, settings: List[Dict[str, Any]], 
                 res_group: Dict[str, List[str]], model_activities: List[str], 
                 res_act: Dict[str, List[List[str]]]):
        """
        Inizializza il calcolatore di worklist.
        
        Args:
            log: DataFrame contenente il log XES
            settings: Lista di configurazioni
            res_group: Dizionario gruppo -> lista risorse
            model_activities: Lista delle attività del modello
            res_act: Dizionario attività -> lista gruppi risorse
        """
        self.original_log = log.copy()
        self.settings = settings
        self.res_group = res_group
        self.model_activities = model_activities
        self.res_act = res_act
        
        # Validazione input
        self._validate_inputs()
        
        # Configurazione primaria
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        self.sim_threshold = self.config['sim_threshold']
        
        # Soglie per l'algoritmo worklist
        self.threshold_min_supp = 0.1   # Supporto minimo
        self.threshold_min_conf = 0.8   # Confidenza minima
        self.threshold_min_intr = 0.98  # Interest minimo
        
        # Risultati (inizializzati come None)
        self._log = None
        self._binding_rules = None
        self._num_trace_binding = None
        self._activity_pairs = None
        self._total_num_trace = None
        self._suppr_list = None
        self._suppA_list = None
        self._confr_list = None
        self._sigmaB_list = None
        self._suppB_list = None
        self._intr_list = None
        
        print(f"WorklistCalculation inizializzato per {len(self.original_log)} eventi")
        print("Regola: binding(T1, T2) iff start(of T1 by :p) and start(of T2) implies start(of T2 by p)")

    
    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.original_log is None or self.original_log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        if not self.model_activities:
            raise ValueError("Model activities non può essere vuoto")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_TRACE_ID, TAG_TIMESTAMP, TAG_LIFECYCLE, TAG_GROUP]
        missing_columns = [col for col in required_columns if col not in self.original_log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    
    def _initialize_calculation(self) -> None:
        """Inizializza il calcolo delle worklist."""
        # Preprocessa log (solo eventi complete)
        self._log = self._preprocess_log()
        
        # Calcola metriche base
        self._total_num_trace = self._count_total_traces()
        self._binding_rules = self._extract_binding_rules()
        self._num_trace_binding = self._count_traces_for_binding()
        self._activity_pairs = self._count_activity_pairs()
        
        # Calcola metriche support/confidence
        self._suppr_list = self._compute_support_r()
        self._suppA_list = self._compute_support_A()
        self._confr_list = self._compute_confidence_r()
        
        # Calcola metriche interest
        self._sigmaB_list = self._compute_sigma_B()
        self._suppB_list = self._compute_support_B()
        self._intr_list = self._compute_interest()
    
    def _preprocess_log(self) -> pd.DataFrame:
        """
        Preprocessa il log filtrando solo eventi complete.
        
        Returns:
            DataFrame preprocessato
        """
        print("Preprocessing log per worklist (solo eventi complete)...")
        
        try:
            # Filtra solo eventi complete per evitare duplicati
            processed_log = self.original_log[
                self.original_log[TAG_LIFECYCLE] == LIFECYCLE_COMPLETE
            ].reset_index(drop=True)
            
            print(f"✓ Log preprocessato: {len(processed_log)} eventi complete")
            return processed_log
            
        except Exception as e:
            raise Exception(f"Errore nel preprocessing del log: {str(e)}")
    
    def _count_total_traces(self) -> int:
        """
        Conta il numero totale di tracce nel log.
        
        Returns:
            Numero totale di tracce
        """
        try:
            grouped_log = self.original_log.groupby(TAG_TRACE_ID)
            total_traces = len(grouped_log)
            
            print(f"✓ Totale tracce: {total_traces}")
            return total_traces
            
        except Exception as e:
            raise Exception(f"Errore nel conteggio tracce: {str(e)}")
    
    def _extract_binding_rules(self) -> List[Dict[str, Any]]:
        """
        Estrae le regole di binding (Retain Familiar) dal log.
        
        Una regola binding esiste quando due attività diverse T1 e T2
        sono eseguite dalle stesse risorse nella stessa traccia.
        
        Returns:
            Lista di regole binding
        """
        print("Estraendo regole di binding...")
        
        try:
            binding_rules = []
            
            # Ordina log per traccia e timestamp
            df_sorted = self._log.sort_values(by=[TAG_TRACE_ID, TAG_TIMESTAMP])
            
            for trace_id, group in df_sorted.groupby(TAG_TRACE_ID):
                # Estrai (attività, gruppo_risorse) per ogni evento nella traccia
                activities = group[[TAG_ACTIVITY_NAME, TAG_GROUP]].values.tolist()
                
                # Confronta ogni coppia di attività nella traccia
                for i in range(len(activities)):
                    T1_activity, T1_resource = activities[i]
                    
                    for j in range(i + 1, len(activities)):
                        T2_activity, T2_resource = activities[j]
                        
                        # Solo se attività diverse
                        if T1_activity != T2_activity:
                            # Confronta risorse (liste di gruppi)
                            if self._resources_match(T1_resource, T2_resource):
                                binding_rule = {
                                    'T1': T1_activity,
                                    'T2': T2_activity,
                                    'resource': T1_resource,
                                    'trace': trace_id
                                }
                                binding_rules.append(binding_rule)
            
            print(f"✓ Estratte {len(binding_rules)} regole di binding")
            return binding_rules
            
        except Exception as e:
            raise Exception(f"Errore nell'estrazione regole binding: {str(e)}")
    
    def _resources_match(self, resource1: Any, resource2: Any) -> bool:
        """
        Verifica se due set di risorse sono uguali.
        
        Args:
            resource1: Prima risorsa/gruppo
            resource2: Seconda risorsa/gruppo
            
        Returns:
            True se le risorse sono uguali
        """
        try:
            # Gestisci diversi tipi di input
            if isinstance(resource1, list) and isinstance(resource2, list):
                return Counter(resource1) == Counter(resource2)
            else:
                return resource1 == resource2
        except Exception:
            return False
    
    def _count_traces_for_binding(self) -> Dict[Tuple[str, str], int]:
        """
        Conta il numero di tracce per ogni coppia di attività con binding.
        
        Returns:
            Dizionario (T1, T2) -> numero_tracce
        """
        print("Contando tracce per binding...")
        
        try:
            pair_traces = {}
            
            for entry in self._binding_rules:
                t1 = entry['T1']
                t2 = entry['T2']
                trace = entry['trace']
                
                pair_key = (t1, t2)
                
                if pair_key not in pair_traces:
                    pair_traces[pair_key] = set()
                pair_traces[pair_key].add(trace)
            
            # Converti set in conteggi
            result = {pair: len(traces) for pair, traces in pair_traces.items()}
            
            print(f"✓ Contate tracce per {len(result)} coppie")
            return result
            
        except Exception as e:
            raise Exception(f"Errore nel conteggio tracce per binding: {str(e)}")
    
    def _count_activity_pairs(self) -> Dict[Tuple[str, str], int]:
        """
        Conta tracce contenenti entrambe le attività di ogni coppia.
        
        Returns:
            Dizionario (T1, T2) -> numero_tracce_contenenti_entrambe
        """
        print("Contando coppie di attività...")
        
        try:
            # Crea set di attività per ogni traccia
            trace_activities = self._log.groupby(TAG_TRACE_ID)[TAG_ACTIVITY_NAME].apply(set)
            
            activity_pairs = self._num_trace_binding.copy()
            
            for (activity1, activity2) in activity_pairs.keys():
                # Conta tracce contenenti entrambe le attività
                count = trace_activities.apply(
                    lambda activities: activity1 in activities and activity2 in activities
                ).sum()
                activity_pairs[(activity1, activity2)] = count
            
            print(f"✓ Contate coppie per {len(activity_pairs)} combinazioni")
            return activity_pairs
            
        except Exception as e:
            raise Exception(f"Errore nel conteggio coppie attività: {str(e)}")
    
    def _compute_support_r(self) -> Dict[Tuple[str, str], float]:
        """
        Calcola il supporto per ogni regola: Support(R) = |R| / |D|
        dove R è la regola e D è il dataset (tracce totali).
        
        Returns:
            Dizionario (T1, T2) -> supporto
        """
        try:
            support_list = {}
            
            for pair, binding_count in self._num_trace_binding.items():
                support = binding_count / self._total_num_trace
                support_list[pair] = support
            
            print(f"✓ Calcolato supporto per {len(support_list)} regole")
            return support_list
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo supporto R: {str(e)}")
    
    def _compute_support_A(self) -> Dict[Tuple[str, str], float]:
        """
        Calcola il supporto per l'antecedente: Support(A) = |A| / |D|
        dove A è "tracce contenenti entrambe le attività".
        
        Returns:
            Dizionario (T1, T2) -> supporto_A
        """
        try:
            support_A_list = {}
            
            for pair, pair_count in self._activity_pairs.items():
                support_A = pair_count / self._total_num_trace
                support_A_list[pair] = support_A
            
            print(f"✓ Calcolato supporto A per {len(support_A_list)} coppie")
            return support_A_list
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo supporto A: {str(e)}")
    
    def _compute_confidence_r(self) -> Dict[Tuple[str, str], float]:
        """
        Calcola la confidenza per ogni regola: Confidence(R) = Support(R) / Support(A)
        
        Returns:
            Dizionario (T1, T2) -> confidenza
        """
        try:
            confidence_list = {}
            
            for pair, support_r in self._suppr_list.items():
                if pair in self._suppA_list:
                    support_a = self._suppA_list[pair]
                    if support_a > 0:
                        confidence = support_r / support_a
                        confidence_list[pair] = confidence
                    else:
                        confidence_list[pair] = 0.0
            
            print(f"✓ Calcolata confidenza per {len(confidence_list)} regole")
            return confidence_list
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo confidenza: {str(e)}")
    
    def _compute_sigma_B(self) -> Dict[Tuple[str, str], int]:
        """
        Calcola sigma_B per ogni coppia: numero di tracce dove l'attività B
        è eseguita da risorse che hanno già eseguito altre attività nella traccia.
        
        Returns:
            Dizionario (T1, T2) -> sigma_B
        """
        print("Calcolando sigma B...")
        
        try:
            sigma_B_list = {pair: 0 for pair in self._activity_pairs.keys()}
            
            for trace_id, trace_data in self._log.groupby(TAG_TRACE_ID):
                # Ordina eventi per timestamp
                trace_data = trace_data.sort_values(by=TAG_TIMESTAMP)
                
                for (activity_A, activity_B) in self._activity_pairs.keys():
                    # Trova eventi dell'attività B
                    events_B = trace_data[trace_data[TAG_ACTIVITY_NAME] == activity_B]
                    
                    found = False
                    for _, event_B in events_B.iterrows():
                        # Trova risorse usate prima di questo evento B
                        previous_events = trace_data[
                            trace_data[TAG_TIMESTAMP] < event_B[TAG_TIMESTAMP]
                        ]
                        
                        # Raccogli tutte le risorse precedenti
                        previous_resources = set()
                        for resources_list in previous_events[TAG_RESOURCE]:
                            if isinstance(resources_list, list):
                                previous_resources.update(resources_list)
                            else:
                                previous_resources.add(resources_list)
                        
                        # Verifica se qualche risorsa di B era già usata
                        current_resources = event_B[TAG_RESOURCE]
                        if isinstance(current_resources, list):
                            if any(res in previous_resources for res in current_resources):
                                found = True
                                break
                        else:
                            if current_resources in previous_resources:
                                found = True
                                break
                    
                    if found:
                        sigma_B_list[(activity_A, activity_B)] += 1
            
            print(f"✓ Calcolato sigma B per {len(sigma_B_list)} coppie")
            return sigma_B_list
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo sigma B: {str(e)}")
    
    def _compute_support_B(self) -> Dict[Tuple[str, str], float]:
        """
        Calcola il supporto B: Support(B) = sigma_B / |D|
        
        Returns:
            Dizionario (T1, T2) -> supporto_B
        """
        try:
            support_B_list = {}
            
            for pair, sigma_B in self._sigmaB_list.items():
                support_B = sigma_B / self._total_num_trace
                support_B_list[pair] = support_B
            
            print(f"✓ Calcolato supporto B per {len(support_B_list)} coppie")
            return support_B_list
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo supporto B: {str(e)}")
    
    def _compute_interest(self) -> Dict[Tuple[str, str], float]:
        """
        Calcola l'interest per ogni regola: Interest = Support(R) / (Support(A) * Support(B))
        
        Misura quanto la regola è interessante rispetto alla casualità.
        
        Returns:
            Dizionario (T1, T2) -> interest
        """
        try:
            interest_list = {}
            
            for pair, support_r in self._suppr_list.items():
                if pair in self._suppA_list and pair in self._suppB_list:
                    support_a = self._suppA_list[pair]
                    support_b = self._suppB_list[pair]
                    
                    denominator = support_a * support_b
                    if denominator > 0:
                        interest = support_r / denominator
                        interest_list[pair] = interest
                    else:
                        interest_list[pair] = 0.0
            
            print(f"✓ Calcolato interest per {len(interest_list)} coppie")
            return interest_list
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo interest: {str(e)}")
    
    def _filter_single_resource_pairs(self, pairs: List[Tuple[str, str]]) -> List[Tuple[str, str]]:
        """
        Rimuove coppie dove entrambe le attività hanno una sola opzione di risorsa
        e quella risorsa è la stessa.
        
        Args:
            pairs: Lista di coppie da filtrare
            
        Returns:
            Lista filtrata
        """
        try:
            filtered_pairs = []
            
            for (activity1, activity2) in pairs:
                resources1 = self.res_act.get(activity1, [])
                resources2 = self.res_act.get(activity2, [])
                
                # Filtra se entrambe hanno una sola risorsa uguale
                single_same_resource = (
                    len(resources1) == 1 and 
                    len(resources2) == 1 and 
                    Counter(resources1[0]) == Counter(resources2[0])
                )
                
                if not single_same_resource:
                    filtered_pairs.append((activity1, activity2))
            
            print(f"✓ Filtrate {len(pairs) - len(filtered_pairs)} coppie con risorsa singola")
            return filtered_pairs
            
        except Exception as e:
            print(f"Errore nel filtro risorse singole: {e}")
            return pairs
    
    def _select_max_value_pairs(self, pairs_values: Dict[Tuple[str, str], float]) -> Dict[Tuple[str, str], float]:
        """
        Seleziona coppie con valore massimo quando ci sono sovrapposizioni di attività.
        
        Args:
            pairs_values: Dizionario coppia -> valore
            
        Returns:
            Dizionario filtrato con valori massimi
        """
        try:
            max_pairs = {}
            
            for pair, value in pairs_values.items():
                elements = set(pair)
                
                # Trova coppie esistenti che condividono attività
                existing_pairs = [
                    key for key in max_pairs 
                    if not elements.isdisjoint(set(key))
                ]
                
                if existing_pairs:
                    # Gestisci sovrapposizioni
                    for existing_pair in existing_pairs:
                        if value > max_pairs[existing_pair]:
                            # Nuovo valore più alto, sostituisci
                            del max_pairs[existing_pair]
                            max_pairs[pair] = value
                        # Se il valore esistente è più alto, mantieni quello
                else:
                    # Nessuna sovrapposizione, aggiungi
                    max_pairs[pair] = value
            
            print(f"✓ Selezionate {len(max_pairs)} coppie con valore massimo")
            return max_pairs
            
        except Exception as e:
            print(f"Errore nella selezione valori massimi: {e}")
            return pairs_values
    
    def compute_worklist_without_intr_value(self) -> List[Tuple[str, str]]:
        """
        Calcola worklist senza considerare il valore di interest.
        
        Utilizza solo supporto e confidenza per filtrare le regole.
        
        Returns:
            Lista di coppie (T1, T2) valide
        """
        print("Calcolando worklist senza interest...")
        
        try:
            valid_pairs = []
            pairs_values = {}
            
            # Filtra per supporto e confidenza
            for pair, support in self._suppr_list.items():
                if support >= self.threshold_min_supp:
                    if pair in self._confr_list:
                        confidence = self._confr_list[pair]
                        if confidence >= self.threshold_min_conf:
                            valid_pairs.append(pair)
                            pairs_values[pair] = support + confidence
            
            # Filtra coppie con risorsa singola
            valid_pairs = self._filter_single_resource_pairs(valid_pairs)
            
            # Seleziona valori massimi per coppie sovrapposte
            max_pairs = self._select_max_value_pairs(pairs_values)
            
            # Mantieni solo coppie con valore massimo
            final_pairs = [pair for pair in valid_pairs if pair in max_pairs]
            
            print(f"✓ Worklist senza interest: {len(final_pairs)} coppie")
            return final_pairs
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo worklist senza interest: {str(e)}")
    
    def compute_worklist_with_intr_value(self) -> List[Tuple[str, str]]:
        """
        Calcola worklist considerando anche il valore di interest.
        
        Utilizza supporto, confidenza e interest per filtrare le regole.
        
        Returns:
            Lista di coppie (T1, T2) valide
        """
        print("Calcolando worklist con interest...")
        
        try:
            valid_pairs = []
            pairs_values = {}
            
            # Filtra per supporto, confidenza e interest
            for pair, support in self._suppr_list.items():
                if support >= self.threshold_min_supp:
                    if pair in self._confr_list:
                        confidence = self._confr_list[pair]
                        if confidence >= self.threshold_min_conf:
                            if pair in self._intr_list:
                                interest = self._intr_list[pair]
                                if interest >= self.threshold_min_intr:
                                    valid_pairs.append(pair)
                                    pairs_values[pair] = support + confidence + interest
            
            # Filtra coppie con risorsa singola
            valid_pairs = self._filter_single_resource_pairs(valid_pairs)
            
            # Seleziona valori massimi per coppie sovrapposte
            max_pairs = self._select_max_value_pairs(pairs_values)
            
            # Mantieni solo coppie con valore massimo
            final_pairs = [pair for pair in valid_pairs if pair in max_pairs]
            
            print(f"✓ Worklist con interest: {len(final_pairs)} coppie")
            return final_pairs
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo worklist con interest: {str(e)}")
    
    def save_worklist_analysis(self, worklist: List[Tuple[str, str]]) -> str:
        """
        Salva l'analisi della worklist su file.
        
        Args:
            worklist: Lista delle coppie worklist
            
        Returns:
            Percorso del file salvato
        """
        try:
            output_dir = os.path.join(self.path, 'output_data', 'output_file')
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, f'worklist_analysis_{self.name}.txt')
            
            with open(file_path, 'w') as file:
                file.write("WORKLIST ANALYSIS - Binding of Duties Rules\n")
                file.write("=" * 50 + "\n\n")
                
                file.write("Regola: binding(T1, T2) iff start(of T1 by :p) and start(of T2) implies start(of T2 by p)\n\n")
                
                file.write(f"Soglie utilizzate:\n")
                file.write(f"- Supporto minimo: {self.threshold_min_supp}\n")
                file.write(f"- Confidenza minima: {self.threshold_min_conf}\n")
                file.write(f"- Interest minimo: {self.threshold_min_intr}\n\n")
                
                file.write(f"Statistiche:\n")
                file.write(f"- Tracce totali: {self._total_num_trace}\n")
                file.write(f"- Regole binding estratte: {len(self._binding_rules)}\n")
                file.write(f"- Coppie candidate: {len(self._num_trace_binding)}\n")
                file.write(f"- Worklist finale: {len(worklist)}\n\n")
                
                file.write("Worklist finale:\n")
                for i, (t1, t2) in enumerate(worklist, 1):
                    support = self._suppr_list.get((t1, t2), 0)
                    confidence = self._confr_list.get((t1, t2), 0)
                    interest = self._intr_list.get((t1, t2), 0)
                    
                    file.write(f"{i}. {t1} -> {t2}\n")
                    file.write(f"   Support: {support:.3f}, Confidence: {confidence:.3f}, Interest: {interest:.3f}\n\n")
            
            print(f"✓ Analisi worklist salvata: {file_path}")
            return file_path
            
        except Exception as e:
            raise Exception(f"Errore nel salvataggio analisi worklist: {str(e)}")
    
    def get_calculation_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto del calcolo della worklist.
        
        Returns:
            Dizionario con informazioni sul calcolo
        """
        return {
            'input_events': len(self.original_log),
            'complete_events': len(self._log) if self._log is not None else 0,
            'total_traces': self._total_num_trace,
            'binding_rules_count': len(self._binding_rules) if self._binding_rules else 0,
            'candidate_pairs_count': len(self._num_trace_binding) if self._num_trace_binding else 0,
            'thresholds': {
                'min_support': self.threshold_min_supp,
                'min_confidence': self.threshold_min_conf,
                'min_interest': self.threshold_min_intr
            },
            'model_name': self.name,
            'activities_count': len(self.model_activities)
        }
    
    # Properties per accesso ai risultati
    @property
    def binding_rules(self) -> Optional[List[Dict[str, Any]]]:
        """Regole di binding estratte."""
        return self._binding_rules
    
    @property
    def num_trace_binding(self) -> Optional[Dict[Tuple[str, str], int]]:
        """Numero tracce per binding."""
        return self._num_trace_binding
    
    @property
    def suppr_list(self) -> Optional[Dict[Tuple[str, str], float]]:
        """Lista supporti regole."""
        return self._suppr_list
    
    @property
    def confr_list(self) -> Optional[Dict[Tuple[str, str], float]]:
        """Lista confidenze regole."""
        return self._confr_list
    
    @property
    def intr_list(self) -> Optional[Dict[Tuple[str, str], float]]:
        """Lista interest regole."""
        return self._intr_list
    
    @property
    def total_num_trace(self) -> Optional[int]:
        """Numero totale tracce."""
        return self._total_num_trace