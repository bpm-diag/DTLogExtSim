import json
import os
import pandas as pd
from datetime import datetime, timedelta
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple

from support_modules.constants import *


class ParamsFile:
    """
    Classe per la generazione del file parametri di simulazione.
    
    Converte tutti i parametri estratti dal log in formato JSON
    compatibile con il simulatore di processi business.
    """
    
    def __init__(self, instance: pd.DataFrame, interarrival: List, timetables: Dict, 
                 group_act: Dict, act_duration_distr: List, worklist: List, 
                 fixed_cost_act: Optional[pd.Series], flow_prob: Dict, 
                 forced_instance_type: Optional[Dict], group_timetables_association: List, 
                 roles: List, setup_time_distr: Optional[List], setup_time_max: Optional[List], 
                 cost_hour: Optional[Dict], settings: List, id_name_act_match: List,
                 start_end_act_bool: bool = False, start_act: Optional[str] = None, 
                 end_act: Optional[str] = None, new_flow_prob: Optional[List] = None, 
                 new_forced_instance: Optional[pd.DataFrame] = None, cut_log_bool: bool = False):
        """
        Inizializza il generatore di file parametri.
        
        Args:
            instance: DataFrame tipi di istanza
            interarrival: Distribuzione inter-arrivo
            timetables: Timetables di lavoro
            group_act: Gruppi per attività
            act_duration_distr: Distribuzioni durata attività
            worklist: Lista worklist
            fixed_cost_act: Costi fissi per attività
            flow_prob: Probabilità di flusso
            forced_instance_type: Tipi istanza forzati
            group_timetables_association: Associazioni gruppo-timetable
            roles: Ruoli/gruppi identificati
            setup_time_distr: Distribuzioni setup time
            setup_time_max: Max usage setup time
            cost_hour: Costi orari
            settings: Configurazioni
            id_name_act_match: Mapping ID-nome attività
            start_end_act_bool: Se includere attività start/end
            start_act: Attività di start
            end_act: Attività di end
            new_flow_prob: Nuove probabilità flusso (per punti intermedi)
            new_forced_instance: Nuovi tipi forzati (per punti intermedi)
            cut_log_bool: Se il log ha tracce tagliate
        """
        # Input principali
        self.instance = instance
        self.interarrival = interarrival
        self.timetables = timetables
        self.group_act = group_act
        self.act_duration_distr = act_duration_distr
        self.worklist = worklist
        self.fixed_cost_act = fixed_cost_act
        self.flow_prob = flow_prob
        self.forced_instance_type = forced_instance_type
        self.group_timetables_association = group_timetables_association
        self.roles = roles
        self.setup_time_distr = setup_time_distr
        self.setup_time_max = setup_time_max
        self.cost_hour = cost_hour
        self.settings = settings
        self.id_name_act_match = id_name_act_match
        
        # Parametri opzionali
        self.start_end_act_bool = start_end_act_bool
        self.start_act = start_act
        self.end_act = end_act
        self.cut_log_bool = cut_log_bool
        self.new_flow_prob = new_flow_prob
        self.new_forced_instance = new_forced_instance
        
        # Validazione e configurazione
        self._validate_inputs()
        self.config = self.settings[0]
        self.path = self.config['path']
        self.name = self.config['namefile']
        self.diag_log = self.config['diag_log']
        
        print(f"ParamsFile inizializzato per {self.name}")
        
        # Genera automaticamente i file
        try:
            self.generate_json()
        except Exception as e:
            raise Exception(f"Errore nella generazione file parametri: {str(e)}")
    
    def _validate_inputs(self) -> None:
        """Valida gli input forniti."""
        if self.instance is None or self.instance.empty:
            raise ValueError("Instance types non può essere vuoto")
        
        if not self.interarrival:
            raise ValueError("Interarrival non può essere vuoto")
        
        if not self.timetables:
            raise ValueError("Timetables non può essere vuoto")
        
        print("ACT_DUR_DISTR", self.act_duration_distr)
        if not self.act_duration_distr:
            raise ValueError("Activity duration distributions non può essere vuoto")
        
        if not self.settings:
            raise ValueError("Settings non può essere vuoto")
    
    def generate_json(self) -> Tuple[str, str]:
        """
        Genera i file JSON e TXT con i parametri.
        
        Returns:
            Tupla (percorso_json, percorso_txt)
        """
        print("Generando file parametri...")
        
        try:
            # Adatta tutti i componenti
            process_instances = self._adapt_instances()
            arrival_rate = self._adapt_interarrival()
            timetables = self._adapt_timetables()
            resources = self._adapt_resources()
            activities_id = self._adapt_activities(use_id=True)
            activities_name = self._adapt_activities(use_id=False)
            flow = self._adapt_flow_probabilities()
            
            # Calcola data/ora di inizio
            start_datetime = self._calculate_start_datetime()
            
            # Struttura dati finale per JSON (con ID)
            data_json = {
                "processInstances": process_instances,
                "startDateTime": start_datetime,
                "arrivalRateDistribution": arrival_rate,
                "timetables": timetables,
                "resources": resources,
                "elements": activities_id,
                "sequenceFlows": flow,
                "catchEvents": {},
                "logging_opt": "1"
            }
            
            # Struttura dati finale per TXT (con nomi)
            data_txt = {
                "processInstances": process_instances,
                "startDateTime": start_datetime,
                "arrivalRateDistribution": arrival_rate,
                "timetables": timetables,
                "resources": resources,
                "elements": activities_name,
                "sequenceFlows": flow,
                "catchEvents": {},
                "logging_opt": "1"
            }
            
            # Salva file
            json_path = self._save_json_file(data_json)
            txt_path = self._save_txt_file(data_txt)
            
            print(f"✓ File parametri generati: {json_path}, {txt_path}")
            return json_path, txt_path
            
        except Exception as e:
            raise Exception(f"Errore nella generazione JSON: {str(e)}")
    
    def _calculate_start_datetime(self) -> str:
        """
        Calcola la data/ora di inizio per la simulazione (prossimo lunedì alle 6:00).
        
        Returns:
            Stringa data/ora in formato ISO
        """
        try:
            now = datetime.now()
            current_weekday = now.weekday()  # 0=lunedì, 6=domenica
            
            # Calcola giorni fino al prossimo lunedì
            days_until_monday = (7 - current_weekday) % 7
            if days_until_monday == 0:
                days_until_monday = 7  # Se è già lunedì, vai al prossimo
            
            # Prossimo lunedì alle 6:00
            next_monday = now + timedelta(days=days_until_monday)
            next_monday_at_6am = next_monday.replace(hour=6, minute=0, second=0, microsecond=0)
            
            return next_monday_at_6am.strftime('%Y-%m-%dT%H:%M:%S')
            
        except Exception as e:
            print(f"Errore nel calcolo start datetime: {e}")
            return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
    
    def _adapt_instances(self) -> List[Dict[str, str]]:
        """
        Adatta i tipi di istanza per il formato di output.
        
        Returns:
            Lista dei tipi di istanza formattati
        """
        try:
            process_instances = []
            
            # Aggiungi nuovi tipi forzati se presenti
            if self.cut_log_bool and self.new_forced_instance is not None:
                for _, row in self.new_forced_instance.iterrows():
                    process_instances.append({
                        'type': str(row['Instance Type']),
                        'count': str(row['Repetition Instance Type'])
                    })
            
            # Aggiungi tipi di istanza base
            for _, row in self.instance.iterrows():
                process_instances.append({
                    'type': row[TAG_INSTANCE_TYPE],
                    'count': str(row['number_of_traces'])
                })
            
            print(f"✓ Adattati {len(process_instances)} tipi di istanza")
            return process_instances
            
        except Exception as e:
            raise Exception(f"Errore nell'adattamento istanze: {str(e)}")
    
    def _adapt_interarrival(self) -> Dict[str, str]:
        """
        Adatta la distribuzione di inter-arrivo.
        
        Returns:
            Dizionario con distribuzione formattata
        """
        try:
            distribution_type = self.interarrival[0]
            params = self.interarrival[1]
            
            arrival_rate_data = {
                "type": self._convert_distribution_type(distribution_type),
                "mean": str(params['mean']),
                "arg1": "" if params['arg1'] == 0 else str(params['arg1']),
                "arg2": "" if params['arg2'] == 0 else str(params['arg2']),
                "timeUnit": "seconds"
            }
            
            print("✓ Adattata distribuzione inter-arrivo")
            return arrival_rate_data
            
        except Exception as e:
            raise Exception(f"Errore nell'adattamento inter-arrivo: {str(e)}")
    
    def _adapt_timetables(self) -> List[Dict[str, Any]]:
        """
        Adatta le timetables per il formato di output.
        
        Returns:
            Lista delle timetables formattate
        """
        try:
            timetables = []
            has_tm_system = False
            
            for timetable_name, schedule in self.timetables.items():
                if timetable_name == "tm_system":
                    has_tm_system = True
                
                rules = []
                for day, hours in schedule.items():
                    if hours:  # Solo se ci sono orari
                        time_intervals = hours.split(', ')
                        for interval in time_intervals:
                            if ' - ' in interval:
                                from_time, to_time = interval.split(' - ')
                                rules.append({
                                    "fromTime": f"{from_time.strip()}:00",
                                    "toTime": f"{to_time.strip()}:00",
                                    "fromWeekDay": day.upper(),
                                    "toWeekDay": day.upper()
                                })
                
                timetables.append({
                    "name": timetable_name,
                    "rules": rules
                })
            
            # Aggiungi timetable di sistema se mancante
            if not has_tm_system:
                system_rule = [{
                    "fromTime": "00:00:00",
                    "toTime": "23:59:00",
                    "fromWeekDay": "MONDAY",
                    "toWeekDay": "SUNDAY"
                }]
                
                timetables.append({
                    "name": "tm_system",
                    "rules": system_rule
                })
            
            print(f"✓ Adattate {len(timetables)} timetables")
            return timetables
            
        except Exception as e:
            raise Exception(f"Errore nell'adattamento timetables: {str(e)}")
    
    def _adapt_resources(self) -> List[Dict[str, Any]]:
        """
        Adatta le risorse per il formato di output.
        
        Returns:
            Lista delle risorse formattate
        """
        try:
            resources = []
            has_system_resource = False
            
            # Calcola quantità massime per log diagnostici
            resource_max = {}
            if self.diag_log:
                resource_max = self._calculate_max_resources()
            
            # Processa ogni timetable
            for timetable in self.group_timetables_association:
                for group_name in timetable['groups']:
                    if group_name == "system_resource":
                        has_system_resource = True
                    
                    # Trova info gruppo
                    group_info = next(
                        (item for item in self.roles if item['group'] == group_name), 
                        None
                    )
                    
                    if group_info:
                        # Calcola quantità
                        if self.diag_log:
                            group_quantity = resource_max.get(group_name, group_info['quantity'])
                        else:
                            group_quantity = group_info['quantity']
                        
                        # Setup time
                        setup_time = self._get_setup_time_for_group(group_name)
                        
                        # Max usage
                        max_usage_value = self._get_max_usage_for_group(group_name)
                        
                        # Costo orario
                        cost_per_hour = "1"
                        if self.cost_hour:
                            cost_per_hour = str(self.cost_hour.get(group_name, "1"))
                        
                        resources.append({
                            "name": group_name,
                            "totalAmount": str(group_quantity),
                            "costPerHour": cost_per_hour,
                            "timetableName": timetable['timetable'],
                            "setupTime": setup_time,
                            "maxUsage": str(max_usage_value)
                        })
            
            # Aggiungi risorsa per start/end se necessario
            if self.start_end_act_bool:
                resources.append(self._create_start_end_resource())
            
            # Aggiungi risorsa di sistema se mancante
            if not has_system_resource:
                resources.append(self._create_system_resource())
            
            print(f"✓ Adattate {len(resources)} risorse")
            return resources
            
        except Exception as e:
            raise Exception(f"Errore nell'adattamento risorse: {str(e)}")
    
    def _calculate_max_resources(self) -> Dict[str, int]:
        """Calcola quantità massime di risorse per log diagnostici."""
        resource_max = {}
        
        for activity, group_lists in self.group_act.items():
            for group_list in group_lists:
                group_counts = Counter(group_list)
                for group_name, count in group_counts.items():
                    if group_name not in resource_max:
                        resource_max[group_name] = count
                    else:
                        resource_max[group_name] = max(resource_max[group_name], count)
        
        return resource_max
    
    def _get_setup_time_for_group(self, group_name: str) -> Dict[str, str]:
        """Ottiene setup time per un gruppo."""
        if self.setup_time_distr:
            for res, setup_type, params, group in self.setup_time_distr:
                if group == group_name:
                    return {
                        "type": self._convert_distribution_type(setup_type),
                        "mean": str(params['mean']),
                        "arg1": "" if params['arg1'] == 0 else str(params['arg1']),
                        "arg2": "" if params['arg2'] == 0 else str(params['arg2']),
                        "timeUnit": "seconds"
                    }
        
        # Default vuoto
        return {
            "type": "",
            "mean": "",
            "arg1": "",
            "arg2": "",
            "timeUnit": ""
        }
    
    def _get_max_usage_for_group(self, group_name: str) -> str:
        """Ottiene max usage per un gruppo."""
        if self.setup_time_max:
            for group, usage in self.setup_time_max:
                if group == group_name:
                    return str(usage)
        return ""
    
    def _create_start_end_resource(self) -> Dict[str, Any]:
        """Crea risorsa per attività start/end."""
        return {
            "name": "system_res_start_end",
            "totalAmount": "1",
            "costPerHour": "1",
            "timetableName": "tm_system",
            "setupTime": {
                "type": "",
                "mean": "",
                "arg1": "",
                "arg2": "",
                "timeUnit": ""
            },
            "maxUsage": ""
        }
    
    def _create_system_resource(self) -> Dict[str, Any]:
        """Crea risorsa di sistema."""
        return {
            "name": "system_resource",
            "totalAmount": "1",
            "costPerHour": "1",
            "timetableName": "tm_system",
            "setupTime": {
                "type": "",
                "mean": "",
                "arg1": "",
                "arg2": "",
                "timeUnit": ""
            },
            "maxUsage": ""
        }
    
    def _adapt_activities(self, use_id: bool) -> List[Dict[str, Any]]:
        """
        Adatta le attività per il formato di output.
        
        Args:
            use_id: Se usare ID invece di nomi
            
        Returns:
            Lista delle attività formattate
        """
        try:
            elements = []
            
            # Crea mappa worklist
            worklist_map = {}
            if self.worklist:
                for i, (act1, act2) in enumerate(self.worklist, start=1):
                    worklist_map[act1] = str(i)
                    worklist_map[act2] = str(i)
            
            # Risorsa di sistema di default
            default_resource = [{
                "resourceName": "system_resource",
                "amountNeeded": "1",
                "groupId": "1"
            }]
            
            # Processa ogni attività
            for activity, dist_type, params in self.act_duration_distr:
                element = {
                    "elementId": self._get_activity_identifier(activity, use_id),
                    "worklistId": worklist_map.get(activity, ""),
                    "fixedCost": self._get_fixed_cost_for_activity(activity),
                    "costThreshold": "",
                    "durationDistribution": {
                        "type": self._convert_distribution_type(dist_type),
                        "mean": str(params["mean"]),
                        "arg1": "" if params["arg1"] == 0 else str(params["arg1"]),
                        "arg2": "" if params["arg2"] == 0 else str(params["arg2"]),
                        "timeUnit": "seconds"
                    },
                    "durationThreshold": "",
                    "durationThresholdTimeUnit": "",
                    "resourceIds": self._generate_resource_ids_for_activity(activity, default_resource)
                }
                elements.append(element)
            
            # Aggiungi attività start/end se necessario
            if self.start_end_act_bool:
                elements.extend(self._create_start_end_activities(use_id))
            
            print(f"✓ Adattate {len(elements)} attività")
            return elements
            
        except Exception as e:
            raise Exception(f"Errore nell'adattamento attività: {str(e)}")
    
    def _get_activity_identifier(self, activity: str, use_id: bool) -> str:
        """Ottiene identificatore attività (ID o nome)."""
        if use_id:
            for act_name, node_id in self.id_name_act_match:
                if act_name == activity:
                    return node_id
        return activity
    
    def _get_fixed_cost_for_activity(self, activity: str) -> str:
        """Ottiene costo fisso per un'attività."""
        if self.fixed_cost_act is not None and not self.fixed_cost_act.empty:
            return str(self.fixed_cost_act.get(activity, ""))
        return ""
    
    def _generate_resource_ids_for_activity(self, activity: str, default_resource: List) -> List[Dict[str, str]]:
        """Genera ID risorse per un'attività."""
        if activity in self.group_act and self.group_act[activity]:
            return self._generate_resource_ids(self.group_act[activity])
        return default_resource
    
    def _generate_resource_ids(self, resource_lists: List[List[str]]) -> List[Dict[str, str]]:
        """
        Genera ID risorse da liste di gruppi.
        
        Args:
            resource_lists: Liste di gruppi risorse
            
        Returns:
            Lista di ID risorse formattati
        """
        resource_ids = []
        
        for group_index, group_list in enumerate(resource_lists, start=1):
            group_counts = Counter(group_list)
            for group_name, count in group_counts.items():
                resource_ids.append({
                    "resourceName": group_name,
                    "amountNeeded": str(count),
                    "groupId": str(group_index)
                })
        
        return resource_ids
    
    def _create_start_end_activities(self, use_id: bool) -> List[Dict[str, Any]]:
        """Crea attività start e end."""
        start_end_resource = [{
            "resourceName": "system_res_start_end",
            "amountNeeded": "1",
            "groupId": "1"
        }]
        
        fixed_duration = {
            "type": "FIXED",
            "mean": "1",
            "arg1": "",
            "arg2": "",
            "timeUnit": "seconds"
        }
        
        activities = []
        
        # Attività start
        if self.start_act:
            activities.append({
                "elementId": self._get_activity_identifier(self.start_act, use_id),
                "worklistId": "",
                "fixedCost": "",
                "costThreshold": "",
                "durationDistribution": fixed_duration,
                "durationThreshold": "",
                "durationThresholdTimeUnit": "",
                "resourceIds": start_end_resource
            })
        
        # Attività end
        if self.end_act:
            activities.append({
                "elementId": self._get_activity_identifier(self.end_act, use_id),
                "worklistId": "",
                "fixedCost": "",
                "costThreshold": "",
                "durationDistribution": fixed_duration,
                "durationThreshold": "",
                "durationThresholdTimeUnit": "",
                "resourceIds": start_end_resource
            })
        
        return activities
    
    def _adapt_flow_probabilities(self) -> List[Dict[str, Any]]:
        """
        Adatta le probabilità di flusso per il formato di output.
        
        Returns:
            Lista delle probabilità di flusso formattate
        """
        try:
            output = []
            
            # Processa probabilità di flusso esistenti
            for node, node_flows in self.flow_prob.items():
                # Ottieni tipi forzati per il nodo
                node_forced_types = []
                if self.forced_instance_type:
                    node_forced_types = self.forced_instance_type.get(node, [])
                
                for flow_data in node_flows:
                    flow_id = flow_data['flow']
                    probability = flow_data['total_probability']
                    source = next(iter(flow_data['source']))
                    destinations = flow_data['destination']
                    
                    # Raccogli tipi di istanza per questo flusso
                    instance_types = []
                    for destination in destinations:
                        for (pair, f_type) in node_forced_types:
                            if pair == (source, destination) and f_type is not None:
                                type_entry = {"type": f_type}
                                if type_entry not in instance_types:
                                    instance_types.append(type_entry)
                    
                    # Aggiungi entry flusso
                    element_id = f"id{flow_id}" if self.cut_log_bool else flow_id
                    output.append({
                        "elementId": element_id,
                        "executionProbability": f"{probability:.2f}",
                        "types": instance_types
                    })
            
            # Aggiungi nuove probabilità per punti intermedi
            if self.cut_log_bool and self.new_flow_prob and self.new_forced_instance is not None:
                output.extend(self._add_intermediate_flow_probabilities())
            
            print(f"✓ Adattate {len(output)} probabilità di flusso")
            return output
            
        except Exception as e:
            raise Exception(f"Errore nell'adattamento probabilità flusso: {str(e)}")
    
    def _add_intermediate_flow_probabilities(self) -> List[Dict[str, Any]]:
        """Aggiunge probabilità per punti intermedi."""
        intermediate_flows = []
        
        # Converti in dizionario per lookup
        new_flow_prob_dict = dict(self.new_flow_prob) if self.new_flow_prob else {}
        
        # Aggiungi flussi con tipi forzati
        for _, row in self.new_forced_instance.iterrows():
            flow_id = row['Flow']
            probability = new_flow_prob_dict.get(flow_id, 0.0)
            
            intermediate_flows.append({
                "elementId": f"id{flow_id}",
                "executionProbability": f"{probability}",
                "types": [{"type": str(row['Instance Type'])}]
            })
        
        # Aggiungi flussi con probabilità 0.9 (gateway principali)
        if self.new_flow_prob:
            for flow_id, probability in self.new_flow_prob:
                if probability == 0.9:
                    intermediate_flows.append({
                        "elementId": f"id{flow_id}",
                        "executionProbability": f"{probability}",
                        "types": []
                    })
        
        return intermediate_flows
    
    def _convert_distribution_type(self, dist_type: str) -> str:
        """
        Converte tipo distribuzione al formato simulator.
        
        Args:
            dist_type: Tipo distribuzione originale
            
        Returns:
            Tipo convertito
        """
        conversion_map = {
            'expon': 'EXPONENTIAL',
            'norm': 'NORMAL',
            'uniform': 'UNIFORM',
            'triang': 'TRIANGULAR',
            'lognorm': 'LOGNORMAL',
            'gamma': 'GAMMA'
        }
        
        return conversion_map.get(dist_type, 'FIXED')
    
    def _save_json_file(self, data: Dict) -> str:
        """Salva file JSON."""
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        if self.start_end_act_bool:
            filename = f'parameters_{self.name}_intermediate_points.json'
        else:
            filename = f'parameters_{self.name}.json'
        
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w') as f:
            json.dump(data, f)
        
        return file_path
    
    def _save_txt_file(self, data: Dict) -> str:
        """Salva file TXT."""
        output_dir = os.path.join(self.path, 'output_data', 'output_file')
        os.makedirs(output_dir, exist_ok=True)
        
        if self.start_end_act_bool:
            filename = f'parameters_{self.name}_intermediate_points.txt'
        else:
            filename = f'parameters_{self.name}.txt'
        
        file_path = os.path.join(output_dir, filename)
        
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)
        
        return file_path
    
    def get_generation_summary(self) -> Dict[str, Any]:
        """
        Restituisce un riassunto della generazione parametri.
        
        Returns:
            Dizionario con informazioni sulla generazione
        """
        return {
            'model_name': self.name,
            'is_diag_log': self.diag_log,
            'has_start_end_activities': self.start_end_act_bool,
            'has_cut_log': self.cut_log_bool,
            'instance_types_count': len(self.instance),
            'activities_count': len(self.act_duration_distr),
            'timetables_count': len(self.timetables),
            'resources_count': len(self.group_timetables_association),
            'worklist_count': len(self.worklist) if self.worklist else 0,
            'flow_probabilities_count': len(self.flow_prob),
            'has_fixed_costs': self.fixed_cost_act is not None,
            'has_setup_time': self.setup_time_distr is not None,
            'has_cost_hour': self.cost_hour is not None
        }