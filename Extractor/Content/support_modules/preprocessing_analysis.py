import pm4py

tag_to_identify_activities = 'concept:name'
tag_to_identify_resources = 'org:resource'
tag_to_identify_trace = 'case:concept:name'
tag_to_identify_timestamp = 'time:timestamp'
tag_to_identify_node_lifecycle = 'lifecycle:transition'
tag_to_identify_node_type = 'nodeType'
tag_to_identify_pool = 'poolName'
tag_to_identify_cost_hour = 'resourceCost'
tag_to_identify_fixed_cost = 'fixedCost'
tag_to_identify_intancetype = 'instanceType'
tag_to_identify_activities_id = 'elementId'
#tag added by me
tag_to_identify_moment_of_day = 'moment_of_day'
tag_to_identify_time_slot = 'time_slot'
tag_to_identify_group = 'group'

class PreProcessing():

    def __init__(self, log):
        self._log = log.copy()

        self._diaglog = self.diaglog_checking(self._log)
        
        self.extract_tag_and_params(self._log)
        self._cut_log_bool, self._log_cut_trace, self._log_entire_trace = self.cut_log_checking(self._log)

    def diaglog_checking(self, log):
        self._column_names = list(log.columns)
        check1 = False
        check2 = False
        for c in self._column_names:
            if c == tag_to_identify_node_type:
                check1 = True
            if c == tag_to_identify_pool:
                check2 = True
        
        if check1 and check2:
            return True
        else:
            return False

    def extract_tag_and_params(self, log):
        # extract similarity threshold for groups and timetables
        if self._diaglog:
            self._sim_threshold = 0.9
        else:
            self._sim_threshold = 0.5

        # extract number of timestamp
        lifecycle_transition = list(log[tag_to_identify_node_lifecycle].unique())
        check_assign = False
        check_start = False
        check_complete = False
        check_setuptime = False
        if self._diaglog:
            for c in lifecycle_transition:
                if c == 'start':
                    check_start = True
                if c == 'assign':
                    check_assign = True
                if c == 'complete':
                    check_complete = True
                if c == 'startSetupTime' or c == 'endSetupTime':
                    check_setuptime = True

            if check_start and check_assign and check_complete:
                self._num_timestamp = 3
            elif check_assign and check_complete:
                self._num_timestamp = 2
            elif check_complete:
                self._num_timestamp = 1
            else:
                self._num_timestamp = 0
            
            if check_setuptime:
                self._setup_time = True
            else:
                self._setup_time = False
        else:
            for c in lifecycle_transition:
                if c == 'assign':
                    check_assign = True
                if c == 'start':
                    check_start = True
                if c == 'complete':
                    check_complete = True
            
            if check_start and check_assign and check_complete:
                self._num_timestamp = 3
            elif check_start and check_complete:
                self._num_timestamp = 2
            elif check_complete:
                self._num_timestamp = 1
            else:
                self._num_timestamp = 0

        # check if there are cost_hour and/or fixed_cost
        self._cost_hour = False
        self._fixed_cost = False
        for c in self._column_names:
            if c == tag_to_identify_cost_hour:
                self._cost_hour = True
            if c == tag_to_identify_fixed_cost:
                self._fixed_cost = True
        

    def cut_log_checking(self, log):
        if self._diaglog:
            traces_without_endEvent = (
                log.groupby(tag_to_identify_trace)
                .filter(lambda x: not x[tag_to_identify_node_type].str.contains("endEvent", na=False).any())
                .reset_index(drop=True) 
            )

            if not traces_without_endEvent.empty:
                traces_with_endEvent = (
                    log.groupby(tag_to_identify_trace)
                    .filter(lambda x: x[tag_to_identify_node_type].str.contains("endEvent", na=False).any())
                    .reset_index(drop=True) 
                )

                return True, traces_without_endEvent, traces_with_endEvent
            else:
                return False, traces_without_endEvent, log
        else:
            traces_without_endEvent = (
                log.groupby(tag_to_identify_trace)
                .filter(lambda x: not x[tag_to_identify_activities].str.contains(r"END|abort|End", na=False).any())
                .reset_index(drop=True) 
            )

            if not traces_without_endEvent.empty:
                traces_with_endEvent = (
                    log.groupby(tag_to_identify_trace)
                    .filter(lambda x: x[tag_to_identify_activities].str.contains(r"END|abort|End", na=False).any())
                    .reset_index(drop=True) 
                )

                return True, traces_without_endEvent, traces_with_endEvent
            else:
                return False, traces_without_endEvent, log