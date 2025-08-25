import pandas as pd
from pandas import DataFrame
import networkx as nx
import numpy as np
import os
from datetime import datetime, timedelta
from collections import defaultdict
from sklearn.metrics import jaccard_score
from typing import Dict, List, Any, Optional, Tuple

from support_modules.constants import *


class TimeTablesCalculation:
    """
    Classe per il calcolo delle timetables (orari di lavoro) dei gruppi di risorse.
    
    Analizza i pattern temporali dei gruppi per identificare timetables simili
    e raggrupparli, calcolando gli intervalli di lavoro per ogni timetable.
    """
    
    def __init__(self, log: pd.DataFrame, settings: List[Dict[str, Any]], 
                 res_group: Dict[str, List[str]], group_schedule: Dict[str, Dict[str, set]]):
        """
        Inizializza il calcolatore di timetables.
        
        Args:
            log: DataFrame contenente il log XES
            settings: Lista di configurazioni
            res_group: Dizionario gruppo -> lista risorse
            group_schedule: Schedule per ogni gruppo
        """
        self.log = log.copy()
        self.settings = settings
        self.res_groups = res_group
        self.group_schedule = group_schedule
        
        # Validazione input
        self._validate_inputs()
        
        # Configurazione primaria
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        self.sim_threshold_timetables = 0.8
        
        # Risultati (inizializzati come None)
        self._timetables_def = None
        self._processed_log = None
        
        print(f"TimeTablesCalculation inizializzato per {len(self.log)} eventi")
    
    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.log is None or self.log.empty:
            raise ValueError("Log non può essere vuoto")
            
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
            
        if not self.res_groups:
            raise ValueError("Gruppi risorse non può essere vuoto")
            
        if not self.group_schedule:
            raise ValueError("Schedule gruppi non può essere vuoto")
            
        # Verifica colonne necessarie
        required_columns = [TAG_ACTIVITY_NAME, TAG_RESOURCE, TAG_TIMESTAMP, TAG_GROUP]
        missing_columns = [col for col in required_columns if col not in self.log.columns]
        if missing_columns:
            raise ValueError(f"Colonne mancanti nel log: {missing_columns}")
    
    def _initialize_calculation(self) -> None:
        """Inizializza il calcolo delle timetables."""
        # Aggiungi colonna time_slot al log
        self._processed_log = self.log.copy()
        self._processed_log[TAG_TIME_SLOT] = self._processed_log[TAG_TIMESTAMP].apply(self._calculate_time_slot)
        
        # Definisci timetables
        self._timetables_def = self._define_timetables(self._processed_log)
    
    def _calculate_time_slot(self, timestamp: pd.Timestamp) -> str:
        """
        Calcola il time slot per un timestamp (giorno + fascia oraria).
        
        Args:
            timestamp: Timestamp da convertire
            
        Returns:
            Stringa formato 'giornoX' dove X è fascia oraria 1-12
        """
        try:
            day_week = self._get_day_of_week(timestamp)
            hour = timestamp.hour
            
            # Fasce orarie di 2 ore ciascuna
            time_slots = [
                (2, 4, '1'), (4, 6, '2'), (6, 8, '3'), (8, 10, '4'),
                (10, 12, '5'), (12, 14, '6'), (14, 16, '7'), (16, 18, '8'),
                (18, 20, '9'), (20, 22, '10'), (22, 24, '11')
            ]
            
            for start_hour, end_hour, slot_num in time_slots:
                if start_hour <= hour < end_hour:
                    return f"{day_week}{slot_num}"
            
            # Default per ore 0-2 (notte)
            return f"{day_week}12"
            
        except Exception as e:
            print(f"Errore nel calcolo time slot per {timestamp}: {e}")
            return "unknown12"
    
    def _get_day_of_week(self, timestamp: pd.Timestamp) -> str:
        """Ottiene il giorno della settimana da un timestamp."""
        day_of_week = timestamp.weekday()  # 0=lunedì, 6=domenica
        days_of_week = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
        return days_of_week[day_of_week % 7]  # Protezione overflow
    
    def _define_timetables(self, log: pd.DataFrame) -> List[Dict[str, Any]]:
        """
        Definisce le timetables raggruppando gruppi con pattern simili.
        
        Args:
            log: Log con colonna time_slot
            
        Returns:
            Lista di definizioni timetable
        """
        print("Definendo timetables...")
        
        try:
            # Costruisci matrice conoscenze per gruppo
            group_knowledge_dict = defaultdict(lambda: defaultdict(int))
            
            for _, event in log.iterrows():
                groups = event[TAG_GROUP]
                time_slot = event[TAG_TIME_SLOT]
                
                # Gestisci sia liste che singoli valori
                if isinstance(groups, list):
                    for group in groups:
                        group_knowledge_dict[group][time_slot] = 1
                else:
                    group_knowledge_dict[groups][time_slot] = 1
            
            # Crea DataFrame per analisi similarità
            df = DataFrame.from_dict(group_knowledge_dict, orient='index').fillna(0)
            
            if df.empty:
                print("⚠ Nessun dato per calcolo timetables")
                return [{'timetable': 'Tm1', 'groups': list(self.res_groups.keys())}]
            
            # Calcola matrice correlazioni
            correlation_matrix = self._calculate_correlation_matrix(df)
            
            # Crea grafo e trova cluster
            graph = self._create_similarity_graph(correlation_matrix)
            subgraphs = list(graph.subgraph(c) for c in nx.connected_components(graph))
            
            # Definisci timetables dai cluster
            timetables_definitions = self._create_timetables_from_clusters(subgraphs)
            
            print(f"✓ Definite {len(timetables_definitions)} timetables")
            return timetables_definitions
            
        except Exception as e:
            raise Exception(f"Errore nella definizione delle timetables: {str(e)}")
    
    def _calculate_correlation_matrix(self, profiles: DataFrame) -> List[Dict[str, Any]]:
        """
        Calcola la matrice di correlazione usando coefficiente Dice.
        
        Args:
            profiles: DataFrame con profili temporali dei gruppi
            
        Returns:
            Lista di correlazioni
        """
        print("Calcolando matrice correlazione per timetables...")
        
        try:
            correlation_matrix = []
            
            for user_id_x, row_x in profiles.iterrows():
                for user_id_y, row_y in profiles.iterrows():
                    x = np.array(row_x.values, dtype=int)
                    y = np.array(row_y.values, dtype=int)
                    
                    try:
                        # Calcola Jaccard score
                        jaccard = jaccard_score(x, y, average='binary')
                        
                        # Converti in coefficiente Dice
                        if jaccard > 0:
                            dice_coefficient = (2 * jaccard) / (1 + jaccard)
                        else:
                            dice_coefficient = 0.0
                        
                    except Exception as e:
                        print(f"Errore nel calcolo Dice per {user_id_x}-{user_id_y}: {e}")
                        dice_coefficient = 0.0
                    
                    correlation_matrix.append({
                        'x': user_id_x,
                        'y': user_id_y,
                        'distance': dice_coefficient
                    })
            
            print(f"✓ Calcolate {len(correlation_matrix)} correlazioni")
            return correlation_matrix
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo matrice correlazione: {str(e)}")
    
    def _create_similarity_graph(self, correlation_matrix: List[Dict[str, Any]]) -> nx.Graph:
        """
        Crea grafo di similarità per clustering.
        
        Args:
            correlation_matrix: Matrice delle correlazioni
            
        Returns:
            Grafo NetworkX
        """
        try:
            graph = nx.Graph()
            
            # Aggiungi nodi (gruppi)
            for group in self.res_groups.keys():
                graph.add_node(group)
            
            # Aggiungi archi per correlazioni significative
            for correlation in correlation_matrix:
                distance = abs(correlation['distance'])
                if (distance >= self.sim_threshold_timetables and 
                    correlation['x'] != correlation['y']):
                    
                    graph.add_edge(
                        correlation['x'],
                        correlation['y'],
                        weight=distance
                    )
            
            print(f"✓ Creato grafo con {graph.number_of_nodes()} nodi e {graph.number_of_edges()} archi")
            return graph
            
        except Exception as e:
            raise Exception(f"Errore nella creazione del grafo: {str(e)}")
    
    def _create_timetables_from_clusters(self, subgraphs: List[nx.Graph]) -> List[Dict[str, Any]]:
        """
        Crea definizioni timetable dai cluster di gruppi.
        
        Args:
            subgraphs: Lista di sottografi (cluster)
            
        Returns:
            Lista di definizioni timetable
        """
        try:
            records = []
            
            for i, subgraph in enumerate(subgraphs):
                # Trova gruppi nel cluster
                group_names = [
                    group for group in self.res_groups.keys() 
                    if group in subgraph
                ]
                
                if group_names:  # Solo se ci sono gruppi validi
                    records.append({
                        'timetable': f'Tm{i + 1}',
                        'groups': group_names
                    })
            
            # Se nessun cluster valido, crea timetable singola
            if not records:
                records.append({
                    'timetable': 'Tm1',
                    'groups': list(self.res_groups.keys())
                })
            
            return records
            
        except Exception as e:
            raise Exception(f"Errore nella creazione timetables da cluster: {str(e)}")
    
    def compute_timetables(self) -> Dict[str, Dict[str, List]]:
        """
        Calcola le timetables effettive combinando schedule dei gruppi.
        
        Returns:
            Dizionario timetable -> giorno -> lista intervalli
        """
        print("Calcolando timetables effettive...")
        
        try:
            if not self._timetables_def:
                raise ValueError("Timetables non definite. Chiamare prima _define_timetables()")
            
            # Raccogli tutti gli orari per timetable
            timetable_times = defaultdict(lambda: defaultdict(set))
            
            for entry in self._timetables_def:
                timetable = entry['timetable']
                groups = entry['groups']
                
                for group in groups:
                    if group in self.group_schedule:
                        role_schedule = self.group_schedule[group]
                        for day, times in role_schedule.items():
                            timetable_times[timetable][day].update(times)
            
            # Processa schedule per creare intervalli
            final_schedule = self._process_schedule(timetable_times)
            
            print(f"✓ Calcolate {len(final_schedule)} timetables")
            return final_schedule
            
        except Exception as e:
            raise Exception(f"Errore nel calcolo delle timetables: {str(e)}")
    
    def _process_schedule(self, timetable_schedule: Dict) -> Dict[str, Dict[str, List]]:
        """
        Processa gli schedule per creare intervalli temporali continui.
        
        Args:
            timetable_schedule: Schedule grezzi per timetable
            
        Returns:
            Schedule processati con intervalli
        """
        try:
            final_schedule = defaultdict(lambda: defaultdict(list))
            
            for timetable, schedule in timetable_schedule.items():
                for day, times in schedule.items():
                    if times:  # Solo se ci sono orari
                        # Converti stringhe in oggetti time e ordina
                        times_list = sorted([self._time_from_string(time) for time in times])
                        
                        # Genera intervalli continui
                        intervals = self._generate_time_intervals(times_list)
                        final_schedule[timetable][day] = intervals
            
            return dict(final_schedule)
            
        except Exception as e:
            raise Exception(f"Errore nel processamento degli schedule: {str(e)}")
    
    def _time_from_string(self, time_str: str) -> datetime.time:
        """Converte stringa tempo in oggetto time."""
        try:
            return datetime.strptime(time_str, '%H:%M').time()
        except ValueError as e:
            print(f"Errore nella conversione tempo '{time_str}': {e}")
            return datetime.strptime('00:00', '%H:%M').time()
    
    def _time_difference(self, t1: datetime.time, t2: datetime.time) -> timedelta:
        """Calcola la differenza tra due orari."""
        dt1 = datetime.combine(datetime.today(), t1)
        dt2 = datetime.combine(datetime.today(), t2)
        return dt2 - dt1
    
    def _generate_time_intervals(self, times: List[datetime.time]) -> List[List[datetime.time]]:
        """
        Genera intervalli temporali continui da una lista di orari.
        
        Raggruppa orari consecutivi (con gap < 4 ore) in intervalli.
        
        Args:
            times: Lista ordinata di orari
            
        Returns:
            Lista di intervalli [inizio, fine]
        """
        if not times:
            return []
        
        try:
            intervals = []
            current_interval = [times[0]]
            max_gap = timedelta(hours=4)
            
            for i in range(1, len(times)):
                previous_time = times[i - 1]
                current_time = times[i]
                
                diff = self._time_difference(previous_time, current_time)
                
                if diff > max_gap:
                    # Gap troppo grande, chiudi intervallo corrente
                    current_interval.append(previous_time)
                    intervals.append(current_interval)
                    current_interval = [current_time]
                else:
                    # Continua intervallo
                    current_interval.append(current_time)
            
            # Chiudi ultimo intervallo
            if current_interval:
                if len(current_interval) == 1:
                    # Singolo orario, duplica per creare intervallo
                    intervals.append([current_interval[0], current_interval[0]])
                else:
                    # Intervallo con inizio e fine
                    intervals.append([current_interval[0], current_interval[-1]])
            
            return intervals
            
        except Exception as e:
            print(f"Errore nella generazione intervalli: {e}")
            return [[times[0], times[-1]]] if times else []
    
    def save_timetables_definition(self) -> str:
        """
        Salva le definizioni delle timetables su file.
        
        Returns:
            Percorso del file salvato
        """
        try:
            if not self._timetables_def:
                raise ValueError("Nessuna definizione timetable da salvare")
            
            output_dir = os.path.join(self.path, 'output_data', 'output_file')
            os.makedirs(output_dir, exist_ok=True)
            
            file_path = os.path.join(output_dir, f'timetables_definition_{self.name}.txt')
            
            with open(file_path, 'w') as file:
                file.write("Timetables Definition:\n")
                for definition in self._timetables_def:
                    file.write(f"Timetable: {definition['timetable']}\n")
                    file.write(f"Groups: {definition['groups']}\n")
                    file.write("---\n")
            
            print(f"✓ Definizioni timetables salvate: {file_path}")
            return file_path
            
        except Exception as e:
            raise Exception(f"Errore nel salvataggio definizioni timetables: {str(e)}")
    
    def get_calculation_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto del calcolo delle timetables.
        
        Returns:
            Dizionario con informazioni sul calcolo
        """
        return {
            'input_events': len(self.log),
            'groups_count': len(self.res_groups),
            'timetables_count': len(self._timetables_def) if self._timetables_def else 0,
            'sim_threshold': self.sim_threshold_timetables,
            'has_timetables_def': self._timetables_def is not None,
            'processed_log_events': len(self._processed_log) if self._processed_log is not None else 0,
            'schedule_days_count': sum(len(schedule) for schedule in self.group_schedule.values()),
            'model_name': self.name
        }
    
    # Properties per accesso ai risultati
    @property
    def timetables_def(self) -> Optional[List[Dict[str, Any]]]:
        """Definizioni delle timetables."""
        return self._timetables_def
    
    @property
    def processed_log(self) -> Optional[pd.DataFrame]:
        """Log processato con time_slot."""
        return self._processed_log
    
    @property 
    def sim_threshold(self) -> float:
        """Soglia di similarità per timetables."""
        return self.sim_threshold_timetables