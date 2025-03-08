import pm4py
import ast
import argparse
import os

from activity_param_extraction import ActivityDistributionCalculation as adcalc
from bpmn_extraction import ExtractionBPMN as exbpmn
from branching_probabilities import BranchProbCalculation as bpcalc
from instance_types_extraction import InstanceTypesCalculation as itcalc
from interarrival_rate_extraction import InterArrivalCalculation as iacalc
from intermediate_start_points_extraction import IntermediateStartPoint as isp
from other_parameters_extraction import OtherParametersCalculation as opcalc
from resource_extraction import ResourceParameterCalculation as rpcalc
from support_modules.preprocessing_analysis import PreProcessing as preproc
from support_modules.generate_parameters_file import ParamsFile as pf

tag_to_identify_activities = 'concept:name'
tag_to_identify_resources = 'org:resource'
tag_to_identify_trace = 'case:concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_node_lifecycle = 'lifecycle:transition'
tag_to_identify_node_type = 'nodeType'
#tag added by me
tag_to_identify_moment_of_day = 'moment_of_day'
tag_to_identify_group = 'group'

class SimulationInputExtraction():

    def __init__(self, log, settings, with_start_end_act):
        self._log = log
        self._settings = settings
        self._with_start_end_act = with_start_end_act

        self.extract_bpmn_model(self._log)

        self.calculate_branching_probabilities(self._log)

        self.instance_types(self._log)

        self.interarrival_rate(self._log)

        self.activity_param(self._log)

        self.resource_parameters(self._log)

        self.other_parameters(self._log)

        #self.generate_params_file()

    def extract_bpmn_model(self, log):
        self._ExtractBPMN = exbpmn(log, self._settings, self._with_start_end_act)

    def calculate_branching_probabilities(self, log, new_model_with_intermediate_poits=None, intermediate_model=False):
        pattern1 = r'Gateway'
        temp_log_1 = log

        if self._settings[0]['diag_log']:
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern1, case=False, na=False)]
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_node_type].str.contains(pattern1, case=False, na=False)]
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_node_lifecycle].str.contains(pattern1, case=False, na=False)]
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_node_type].str.contains(pattern1, case=False, na=False)]

        if intermediate_model:
            bpmn_model = new_model_with_intermediate_poits
        else:
            bpmn_model = pm4py.read_bpmn(self._settings[0]['path'] + 'output_data/output_file/' + self._settings[0]['namefile'] + '_pm4py.bpmn') 
        
        if self._with_start_end_act:
            self._id_name_act_match = self.match_id_name(bpmn_model, temp_log_1)

        if self._settings[0]['diag_log']:
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_node_type].isin(['startEvent', 'endEvent'])].reset_index(drop=True)
        
        self._BranchProb = bpcalc(temp_log_1, bpmn_model, self._settings, intermediate_model)

        if not self._with_start_end_act:
            self._id_name_act_match = self.match_id_name(bpmn_model, temp_log_1)

        
    def match_id_name(self, model, log):
        matching = []
        explode_activities = log[tag_to_identify_activities].explode()
        unique_activities = explode_activities.drop_duplicates()
        unique_activities = unique_activities[unique_activities.notna()]
        model_activities = unique_activities.tolist()
        for node in model.get_nodes():
            if node.get_name() in model_activities:
                matching.append((node.get_name(), node.get_id()))
        return matching

    def instance_types(self, log):
        branches = self._BranchProb._branches
        tot_execute_per_branch = self._BranchProb._tot
        self._InstanceTypes = itcalc(log, self._settings, branches, tot_execute_per_branch)

    def interarrival_rate(self, log):
        self._InterArrivalRate = iacalc(log, self._settings)

    def activity_param(self, log):
        self._ActivityParam = adcalc(log, self._settings)

    def resource_parameters(self, log):
        def safe_literal_eval(x):
            try:
                evaluated = ast.literal_eval(x)
                return evaluated if isinstance(evaluated, (list, dict)) else [x]
            except (ValueError, SyntaxError):
                return [x]
            
        pattern1 = r'Gateway'
        pattern2 = r'Start'
        pattern3 = r'End'
        pattern4 = r'Event'
        temp_log_1 = (log[~log[tag_to_identify_activities].isin(['Start', 'End', 'start', 'end', 'Gateway'])].reset_index(drop=True))
        temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern1, case=False, na=False)]
        temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern2, case=False, na=False)]
        temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern3, case=False, na=False)]
        temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_activities].str.contains(pattern4, case=False, na=False)]
        if self._settings[0]['diag_log']:
            temp_log_1 = temp_log_1[~temp_log_1[tag_to_identify_node_type].str.contains(pattern1, case=False, na=False)]
        temp_log_1[tag_to_identify_resources] = temp_log_1[tag_to_identify_resources].apply(safe_literal_eval) #trasform resources in list of res

        self._ResourceParam = rpcalc(temp_log_1, self._settings)

    def other_parameters(self, log):
        roles = self._ResourceParam._roles

        self._OtherParams = opcalc(log, self._settings, roles)

        if self._settings[0]['cost_hour']:
            self._OtherParams.cost_hour_parameter(log)
        
        if self._settings[0]['fixed_cost']:
            self._OtherParams.fixed_activity_cost(log)

        if self._settings[0]['diag_log'] and self._settings[0]['setup_time']:
            self._OtherParams.setup_time_act(log)

    def generate_params_file(self, start_end_act_bool = False, start_act=None, end_act=None, new_flow=None, new_forced_instance=None, cut_log_bool=False):
        fixed_cost_act = None
        if self._settings[0]['fixed_cost']:
            fixed_cost_act = self._OtherParams._fixed_cost_avg_per_activity
        setup_time_distr = None
        setup_time_max = None
        if self._settings[0]['diag_log'] and self._settings[0]['setup_time']:
            setup_time_distr = self._OtherParams._duration_distr_setup_time
            setup_time_max = self._OtherParams._max_usage_before_setup_time_per_resource
        cost_hour = None
        if self._settings[0]['cost_hour']:
            cost_hour = self._OtherParams._group_average_cost_hour
        
        pf(self._InstanceTypes._instance_types, self._InterArrivalRate._distribution_params, self._ResourceParam._working_timetables,
           self._ResourceParam._group_act, self._ActivityParam._duration_distr, self._ResourceParam._worklist, fixed_cost_act,
           self._BranchProb._flow_prob, self._InstanceTypes._forced_instance_types, self._ResourceParam._group_timetables_association, 
           self._ResourceParam._roles, setup_time_distr, setup_time_max, cost_hour, self._settings, self._id_name_act_match, 
           start_end_act_bool, start_act, end_act, new_flow, new_forced_instance, cut_log_bool)



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Input")
    parser.add_argument("--file", type=str, required=True, help="Log file name (with extension)")
    parser.add_argument("--output", type=str, default="output/", help="output folder")
    parser.add_argument("--eta", type=str, default="0.01", help="Eta value for slit miner")
    parser.add_argument("--eps", type=str, default="0.001", help="Epsilon value for slit miner")
    parser.add_argument("--simthreshold", type=str, default="0.9", help="sim_threshold for groups")
    args = parser.parse_args()

    name = os.path.splitext(args.file)[0]
    path = args.output
    eta = args.eta
    eps = args.eps
    sim_threshold = float(args.simthreshold)

    log = pm4py.read_xes(args.file)
   

    len_starting_log = len(log)

    PreProc = preproc(log.copy())

    diag_log = PreProc._diaglog
    if sim_threshold == 0.9:
        sim_threshold = PreProc._sim_threshold
    num_timestamp = PreProc._num_timestamp  # 1=only complete activities; 2=start,complete activities; 3=assign,start,complete activites
    cost_hour_bool = PreProc._cost_hour
    fixed_cost_bool = PreProc._fixed_cost
    if diag_log:
        setup_time_bool = PreProc._setup_time
    else:
        setup_time_bool = False

    settings = list()
    
    cut_log_bool = PreProc._cut_log_bool # True: log with not end traces; False: log with all traces ended
    
    if cut_log_bool: # there are traces not end, so extract also intermediate starting points 
        log_entire_trace = PreProc._log_entire_trace
        len_log_with_only_entire_trace = len(log_entire_trace)
        log_cut_traces = PreProc._log_cut_trace
        len_log_with_only_cut_trace = len(log_cut_traces)

        settings.append({'path': path, 'namefile': name, 'diag_log': diag_log, 'sim_threshold': sim_threshold, 'num_timestamp': num_timestamp, 'cost_hour': cost_hour_bool, 'fixed_cost': fixed_cost_bool, 'setup_time': setup_time_bool, 'eta': eta, 'eps': eps})
        Sim = SimulationInputExtraction(log, settings, True)
        Sim.generate_params_file()
        model_name = name + '_pm4py.bpmn'

        #extract intermediate starting points 
        new_name1 = name + '_only_cut_trace.xes'
        pm4py.write_xes(log_cut_traces, path + 'input_data/' + new_name1, case_id_key=tag_to_identify_trace)
        settings1 = list()
        settings1.append({'path': path, 'namefile': new_name1, 'model_name': model_name, 'output_name': name, 'diag_log': diag_log, 'sim_threshold': sim_threshold, 'num_timestamp': num_timestamp, 'cost_hour': cost_hour_bool, 'fixed_cost': fixed_cost_bool, 'setup_time': setup_time_bool, 'eta': eta, 'eps': eps})
        new_log1 = pm4py.read_xes(path + 'input_data/' + new_name1)
        
        model = pm4py.read_bpmn(path + 'output_data/output_file/' + model_name)

        InStartPoint = isp(new_log1, model, settings1)
        new_forced_instance = InStartPoint._forced_instance_types
        new_flow_prob = InStartPoint._flow_probabilities

        if diag_log:
            start_act_log = log[log[tag_to_identify_node_type].isin(['startEvent'])].reset_index(drop=True)
            start_activity = start_act_log[tag_to_identify_activities].unique()[0]
            end_act_log = log[log[tag_to_identify_node_type].isin(['endEvent'])].reset_index(drop=True)
            end_activity = end_act_log[tag_to_identify_activities].unique()[0]
        else:
            pattern1 = r'Start'
            pattern2 = r'End'
            start_act_log = log[log[tag_to_identify_activities].str.contains(pattern1, case=False, na=False)]
            start_activity = start_act_log[tag_to_identify_activities].unique()[0]
            end_act_log = log[log[tag_to_identify_activities].str.contains(pattern2, case=False, na=False)]
            end_activity = end_act_log[tag_to_identify_activities].unique()[0]

        Sim.generate_params_file(True, start_activity, end_activity, new_flow_prob, new_forced_instance, True)

    else:
        settings.append({'path': path, 'namefile': name, 'diag_log': diag_log, 'sim_threshold': sim_threshold, 'num_timestamp': num_timestamp, 'cost_hour': cost_hour_bool, 'fixed_cost': fixed_cost_bool, 'setup_time': setup_time_bool, 'eta': eta, 'eps': eps})
        Sim = SimulationInputExtraction(log, settings, False)
        Sim.generate_params_file()



