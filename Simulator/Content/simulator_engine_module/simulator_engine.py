from datetime import datetime, timedelta
from datetime import time as dt_time
import timeCalculator
import numpy as np
import math
import simpy
import functools
from collections import Counter


class SimulatorEngine:
    def __init__(self, env, name, process_details, num, loader, global_resources, logging_opt, totalCost,
     timeUsedPerResource, extraLog, rows, start_delay=0, instance_type="default", batch_state=None):
        self.env = env
        self.name = name
        self.process_details = process_details
        self.stack=[] #used to save parallel gateways closing pair
        self.stackInclusive=[] #used to save inclusive gateways closing pair
        self.start_delay = start_delay
        self.instance_type = instance_type
        self.num = num
        self.action = env.process(self.run())
        self.costThresholds = {element['elementId']: int(element['costThreshold']) if element['costThreshold'] != '' else None for element in loader.extra_data['elements']} 
        self.durationThresholds={element['elementId']: int(element['durationThreshold']) if element['durationThreshold'] != '' else None for element in loader.extra_data['elements']}
        self.durationThresholdTimeUnits={element['elementId']: element['durationThresholdTimeUnit'] for element in loader.extra_data['elements']}
        self.global_resources=global_resources
        self.logging_opt = logging_opt
        self.loader = loader
        self.extraLog = extraLog
        self.rows = rows
        self.batch_state = batch_state if batch_state is not None else {}

        self.timetables = self.loader.extra_data['timetables']
        self.catchEvents = self.loader.extra_data['catchEvents']
        self.timeConstrainedGateways = self.loader.extra_data.get('timeConstrainedGateways', {})

        self.task_durations = {element['elementId']: element['durationDistribution'] for element in loader.extra_data['elements']} #dict contains: type, mean, arg1, arg2
        self.task_resources = {element['elementId']: element['resourceIds'] for element in loader.extra_data['elements']} #array contains dicts with each: resourceName, amountNeeded, groupId
        self.task_costs = {element['elementId']: element['fixedCost'] for element in loader.extra_data['elements']} #array contains dicts with each: resourceName, amountNeeded, groupId
        self.tasks_worklists={element['elementId']: element['worklistId'] for element in loader.extra_data['elements']}

        for element_id, time_unit in self.durationThresholdTimeUnits.items(): #edit duratioThresholds multiplying by self.durationThresholdTimeUnits
            threshold = self.durationThresholds.get(element_id)
            if threshold is not None:
                if time_unit == 'minutes':
                    self.durationThresholds[element_id] = float(self.durationThresholds[element_id])*60
                elif time_unit == 'hours':
                    self.durationThresholds[element_id] = float(self.durationThresholds[element_id])*3600
                elif time_unit == 'days':
                    self.durationThresholds[element_id] = float(self.durationThresholds[element_id])*86400

        self.totalCost=totalCost
        self.totalCost[self.num]=0.0

        self.worklist_resources={} #worklist resources are summed here
        self.worklist_resources[self.num]={}

        self.executed_nodes={} #executed nodes are saved here
        self.executed_nodes[self.num]=set()
        self.executed_node_counts={} #how many times each node has executed, for cardinality conditions ("visited N times")
        self.executed_node_counts[self.num]=Counter()

        self.terminateEndEvent={} # dictionary of true or false, to tell if that process has been terminated or not
        self.terminateEndEvent[self.num] = False

        self.subprocessTerminate={} #this is used for subprocesses for terminate end events
        self.subprocessTerminate[self.num] = {}

        self.startDateTime = self.loader.extra_data['startDateTime']
        self.start_datetime_obj = datetime.strptime(self.startDateTime, "%Y-%m-%dT%H:%M:%S")

        self.sequence_flows_dict = {item['elementId']: item for item in self.loader.extra_data['sequenceFlows']}
        
        self.timetables_dict = {}
        for t in self.loader.extra_data['timetables']:
            rules = t.get('rules', [])
            parsed_rules = []
            for rule in rules:
                from_hour, from_minute, from_second = map(int, rule['fromTime'].split(':'))
                to_hour, to_minute, to_second = map(int, rule['toTime'].split(':'))
                parsed_rules.append({
                    'from_time': dt_time(from_hour, from_minute, from_second),
                    'to_time': dt_time(to_hour, to_minute, to_second),
                    'from_day_idx': ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'].index(rule['fromWeekDay'].upper()),
                    'to_day_idx': ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY'].index(rule['toWeekDay'].upper())
                })
            self.timetables_dict[t['name']] = parsed_rules

        self.task_grouped_resources = {}
        for element_id, res_list in self.task_resources.items():
            if res_list:
                grouped = {}
                for res in res_list:
                    if res['groupId'] not in grouped:
                        grouped[res['groupId']] = []
                    grouped[res['groupId']].append((res['resourceName'], int(res['amountNeeded'])))
                self.task_grouped_resources[element_id] = grouped
            else:
                self.task_grouped_resources[element_id] = {}

        # Batch config: elementId -> max/min batch size (only present when batching is enabled and valid for that node)
        self.task_batch_max_size = {}
        self.task_batch_min_size = {}
        self.task_batch_mixed_types = {}
        for element in loader.extra_data['elements']:
            element_id = element['elementId']
            raw_max_size = element.get('batchMaxSize', '')
            try:
                max_size = int(raw_max_size)
            except (TypeError, ValueError):
                max_size = None
            if max_size is None or max_size < 1:
                continue
            if self.tasks_worklists.get(element_id):
                print(f"[BATCH] Node {element_id} has both a worklistId and batching enabled — batching is unsupported in this combination, disabling batch for this node.", flush=True)
                continue

            raw_min_size = element.get('batchMinSize', '')
            try:
                min_size = int(raw_min_size)
            except (TypeError, ValueError):
                min_size = None
            if min_size is None or min_size < 1:
                min_size = 1
            if min_size > max_size:
                print(f"[BATCH] Node {element_id} has batchMinSize ({min_size}) > batchMaxSize ({max_size}) — clamping min to max.", flush=True)
                min_size = max_size

            self.task_batch_max_size[element_id] = max_size
            self.task_batch_min_size[element_id] = min_size
            self.task_batch_mixed_types[element_id] = bool(element.get('batchAllowMixedTypes', False))

            # Setup time on any resource used by this node forces homogeneous batches (single instance_type),
            # since lastInstanceType/changeover logic needs one unambiguous type to compare against.
            for resource_name, _amount in [(r['resourceName'], r['amountNeeded']) for r in self.task_resources.get(element_id, [])]:
                resource_units = self.global_resources.get(resource_name)
                if resource_units and resource_units[0][4].get('type'):
                    self.task_batch_mixed_types[element_id] = False
                    break

            # Shared queue/coordinator state for this node, created once and reused by every instance.
            self.batch_state.setdefault(element_id, {'queue': [], 'arrival_event': self.env.event(), 'coordinator_started': False})

        self.subprocessInternalError = {} #used in error end event
        self.subprocessExternalException = {}

        self.state_changed_event = {}
        self.state_changed_event[self.num] = self.env.event()


        #resources is a dict with name as key and a tuple made of simpy resource, cost and timetable.
        self.executed_nodes[self.num] = set()
        self.executed_node_counts[self.num] = Counter()
        self.timeUsedPerResource=timeUsedPerResource
        for resource_name, resource_info in self.global_resources.items():
            self.timeUsedPerResource[resource_name]=0.0
        
    def trigger_resource_release(self):
        if not hasattr(self.env, 'resource_released_event'):
            self.env.resource_released_event = self.env.event()
        if not self.env.resource_released_event.triggered:
            self.env.resource_released_event.succeed()
            self.env.resource_released_event = self.env.event()

    def mark_node_executed(self, node_id):
        self.executed_nodes[self.num].add(node_id)
        self.executed_node_counts[self.num][node_id] += 1
        if not self.state_changed_event[self.num].triggered:
            self.state_changed_event[self.num].succeed()
            self.state_changed_event[self.num] = self.env.event()

    def update_resources(self,resource_obj, mode, resource_name, node_id, instance_type=None): #this function handles setup time for resources
        #instance_type defaults to self.instance_type (the normal per-instance case); the batch coordinator
        #passes the batch's representative type explicitly, since it runs as a method on an arbitrary owner instance.
        if instance_type is None:
            instance_type = self.instance_type
        #resource_tuple is: simpyRes, cost, timetableName, lastInstanceType, setupTime, maxUsage, actualUsage, lock
        #mode can either be, increment, instanceTypeChange. First mode means that same instanceType has arrived, counter of usages needs to incremented; second mode is
        #for when the instance that comes has a different type than what the resource was previously used for, so it needs some time to prepare.
        usury=False
        instanceCambio=False
        #find the tuple where the resource obj is the one we want to update, tuple structure is in the first comment of function
        for tuple_ in self.global_resources[resource_name]:
            if tuple_[0] is resource_obj:
                resource_tuple=tuple_
        #if this resource doesn't involve setup times
        if not resource_tuple[4]["type"]:
            return

        if mode=="increment":
            #if usage limit reached put usage to 0 and flag usury, otherwise just increment by 1
            if int(resource_tuple[6].level) + 1 >= int(resource_tuple[5]):
                resource_tuple[6].get(int(resource_tuple[5])-1)
                usury=True
            else:
                resource_tuple[6].put(1)

        elif mode=="instanceTypeChange":
            instanceCambio=True
            #usage to 0
            while resource_tuple[6].level > 0:
                yield resource_tuple[6].get(1)
        
        logg=""
        if usury==True:
            logg="worn"
        elif instanceCambio==True:
            logg="instanceTypeChange"

        setup_time = timeCalculator.convert_to_seconds(resource_tuple[4])
        # Update currentUsages
        for i, res_tuple in enumerate(self.global_resources[resource_name]):

            # add by LR
            resource_setup_time_info = list()

            if res_tuple[0] is resource_tuple[0]:

                # add by LR
                resource_setup_time_info.append((resource_name, int(res_tuple[5])))
                self.xeslog(node_id,"startSetupTime",logg, resource_setup_time_info)
                #self.xeslog(node_id,"startSetupTime",logg) if usury or instanceCambio else None

                if instanceCambio or usury:
                    yield self.env.timeout(setup_time)
                    print(f"Fine cambio {resource_tuple[0]} {self.env.now}")

                # add by LR
                self.xeslog(node_id,"endSetupTime",logg, resource_setup_time_info)
                #self.xeslog(node_id,"endSetupTime",logg) if usury or instanceCambio else None

                #update resource by locking resource first
                with res_tuple[7]:
                    self.global_resources[resource_name][i] = (
                        res_tuple[0],  # simpy resource
                        res_tuple[1],  # cost
                        res_tuple[2],  # timetable
                        instance_type,  # lastInstanceType
                        res_tuple[4],  # setupTime
                        int(res_tuple[5]),  # maxUsages
                        res_tuple[6],
                        res_tuple[7]  
                    )                                                    
                break

    def _acquire_batch_group_resources(self, node_id, instance_type):
        #Standalone, simplified resource acquisition used only by the batch coordinator: acquires the
        #resources for ONE WHOLE BATCH at once (not per member). Unlike the per-instance path in run_node,
        #it doesn't need the "wait one tick to give a same-type instance priority" dance (the coordinator
        #already commits to a single representative instance_type for the whole batch up front) or worklist
        #bookkeeping (batching + worklistId is an unsupported combination, guarded against in __init__).
        grouped_resources = self.task_grouped_resources.get(node_id, {})
        if not grouped_resources:
            return []
        while True:
            for group_id, resources in grouped_resources.items():
                requests = []
                group_ok = True
                for resource_name, amount_needed in resources:
                    available = [r for r in self.global_resources[resource_name]
                                 if self.is_in_timetable(r[2]) and r[0].count < r[0].capacity]
                    if len(available) < amount_needed:
                        group_ok = False
                        break
                    for resource_tuple in available[:amount_needed]:
                        mode = "increment" if (not resource_tuple[4]['type'] or not resource_tuple[3] or resource_tuple[3] == instance_type) else "instanceTypeChange"
                        requests.append((resource_name, resource_tuple, mode))
                if group_ok:
                    acquired = []
                    for resource_name, resource_tuple, mode in requests:
                        yield from self.update_resources(resource_tuple[0], mode, resource_name, node_id, instance_type)
                        req = resource_tuple[0].request()
                        yield req
                        acquired.append((resource_name, req, resource_tuple[1]))
                    return acquired
            if not hasattr(self.env, 'resource_released_event'):
                self.env.resource_released_event = self.env.event()
            yield self.env.resource_released_event | self.env.timeout(60)

    def _run_batch_coordinator(self, node_id):
        #Started exactly once per batch-enabled node (by the first instance to reach it) and lives for the
        #whole simulation. Runs as a method on whichever instance happened to start it purely as a source of
        #shared, per-node config identical across every instance of this process (task_grouped_resources,
        #global_resources, task_durations, ...) — it does NOT represent any particular process instance.
        #Per-instance bookkeeping (cost, thresholds, xeslog rows, mark_node_executed) is always done through
        #each batch member's own `engine` reference, never through self.
        state = self.batch_state[node_id]
        while True:
            if not state['queue']:
                yield state['arrival_event']
                continue

            terminated = [t for t in state['queue'] if t['engine'].terminateEndEvent[t['engine'].num]]
            if terminated:
                state['queue'] = [t for t in state['queue'] if t not in terminated]
                for t in terminated:
                    #wake the waiting instance so it resumes and exits through the normal
                    #terminateEndEvent check in run_node, instead of staying blocked forever
                    t['done_event'].succeed()

            #a ticket whose owning TCG attempt timed out sets 'cancelled' and returns on its own
            #(see _execute_task) -- it's not waiting on anything anymore, just drop it here too.
            cancelled_in_queue = [t for t in state['queue'] if t.get('cancelled')]
            if cancelled_in_queue:
                state['queue'] = [t for t in state['queue'] if t not in cancelled_in_queue]

            if not state['queue']:
                continue

            max_size = self.task_batch_max_size[node_id]
            if self.task_batch_mixed_types.get(node_id, False):
                batch_members = state['queue'][:max_size]
            else:
                #Only take the CONTIGUOUS run of same-type tickets from the front of the queue (FIFO):
                #scanning the whole queue for matching types would let a fast-arriving type repeatedly
                #leapfrog an older, different-type ticket stuck further back, starving it indefinitely.
                leader_type = state['queue'][0]['engine'].instance_type
                batch_members = []
                for t in state['queue']:
                    if t['engine'].instance_type != leader_type or len(batch_members) >= max_size:
                        break
                    batch_members.append(t)

            min_size = self.task_batch_min_size[node_id]
            if len(batch_members) < min_size:
                #not enough queued yet to reach the configured minimum -- leave them queued (still
                #"assigned") and wait for more arrivals. Nothing to release: no resources were touched.
                #An instance stuck here forever if the minimum is never reached has no built-in escape
                #hatch of its own -- route it through a TCG gateway upstream if a bound is needed, same
                #as any other batch wait.
                yield state['arrival_event']
                continue

            state['queue'] = state['queue'][len(batch_members):]

            leader_instance_type = batch_members[0]['engine'].instance_type
            acquired = yield from self._acquire_batch_group_resources(node_id, leader_instance_type)

            #a member could have been cancelled (its own TCG attempt timed out) while we were waiting
            #for resources above -- it already exited on its own via _execute_task's interrupt handler.
            #If enough survive to still meet the minimum, drop just the cancelled ones and proceed;
            #otherwise release what we acquired and put the survivors back to retry as a fresh round
            #(possibly joined by new arrivals) instead of silently starting an under-strength batch.
            batch_members = [m for m in batch_members if not m.get('cancelled')]
            if len(batch_members) < min_size:
                for resource_name, req, cost_per_hour in acquired:
                    if req.triggered:
                        req.cancel()
                        req.resource.release(req)
                        self.trigger_resource_release()
                state['queue'] = batch_members + state['queue']
                continue

            for member in batch_members:
                member['engine'].xeslog(node_id, "start", 'task')
                if not member['started_event'].triggered:
                    member['started_event'].succeed()

            taskTime = timeCalculator.convert_to_seconds(self.task_durations[node_id])
            if not math.isfinite(taskTime):
                print(f"[ERROR] Batch at node {node_id}: non-finite duration ({taskTime}) — check distribution parameters", flush=True)
                taskTime = 0
            yield self.env.timeout(taskTime)

            batch_size = len(batch_members)
            full_cost = self.task_costs[node_id]
            cost_share = (float(full_cost) / batch_size) if full_cost != '' else None
            resourceid_for_task = [r[0] for r in acquired]
            resource_cost_hour_share = []
            for _, _, cost_per_hour in acquired:
                if cost_per_hour not in (None, ''):
                    resource_cost_hour_share.append(float(cost_per_hour) / batch_size)
                else:
                    resource_cost_hour_share.append(cost_per_hour)

            for member in batch_members:
                eng = member['engine']
                eng.mark_node_executed(node_id)
                if eng.durationThresholds.get(node_id) is not None:
                    eng.durationThresholds[node_id] -= taskTime
                if cost_share is not None:
                    eng.totalCost[eng.num] += cost_share
                    if eng.costThresholds.get(node_id) is not None:
                        eng.costThresholds[node_id] -= cost_share
                eng.xeslog(node_id, "complete", 'task', resourceid_for_task,
                           cost_share if cost_share is not None else full_cost, resource_cost_hour_share)
                member['done_event'].succeed()

            for resource_name, req, cost_per_hour in acquired:
                self.timeUsedPerResource[resource_name] += float(taskTime)
                if req.triggered:
                    req.cancel()
                    req.resource.release(req)
                    self.trigger_resource_release()

    def is_in_timetable(self, timetable_name): #this func is used when gathering resources for a task, to check if a res is in shift
        current_time = self.start_datetime_obj + timedelta(seconds=self.env.now)
        parsed_rules = self.timetables_dict.get(timetable_name, [])

        current_hour_minute_second = dt_time(current_time.hour, current_time.minute, current_time.second)
        current_day_idx = current_time.weekday()
        
        for p_rule in parsed_rules:
            timeFlag=False
            from_time = p_rule['from_time']
            to_time = p_rule['to_time']
            from_day_idx = p_rule['from_day_idx']
            to_day_idx = p_rule['to_day_idx']

            if from_time > to_time:
                if not (to_time >= current_hour_minute_second or current_hour_minute_second >= from_time):
                    continue
                timeFlag=True  
            elif not from_time <= current_hour_minute_second <= to_time:
                continue

            if (to_day_idx < from_day_idx) and timeFlag:
                if not (to_day_idx > current_day_idx or current_day_idx >= from_day_idx):
                    continue
            elif (to_day_idx < from_day_idx) and not timeFlag:
                if not (to_day_idx >= current_day_idx or current_day_idx >= from_day_idx):
                    continue
            elif (not (from_day_idx <= current_day_idx < to_day_idx)) and timeFlag:
                continue
            elif (not (from_day_idx <= current_day_idx <= to_day_idx)) and not timeFlag:
                continue

            return True

        return False
    # add by LR
    def xeslog(self, node_id, status, nodeType, resourceid=None, taskCost=None, resource_cost_hour=None):
    #def xeslog(self, node_id, status, nodeType):
        # print("-------XESLOG------")
        if nodeType=="parallelGateway":
            nodeType="parallelGatewayOpen"
        if nodeType=="inclusiveGateway":
            nodeType="inclusiveGatewayOpen"
        if not math.isfinite(self.env.now):
            print(f"[ERROR] Instance #{self.num}: non-finite simulation time ({self.env.now}) at node {node_id} — skipping log entry", flush=True)
            return None
        current_time = self.start_datetime_obj + timedelta(seconds=self.env.now)
        if self.logging_opt or status=="complete":
            # add by LR
            act_name = self.process_details['node_details'][node_id].get('name', None)
            if not act_name:
                row = [self.num, node_id, current_time, status, nodeType,self.name,self.instance_type,resourceid,taskCost,resource_cost_hour]
            else:
                row = [self.num, act_name, current_time, status, nodeType,self.name,self.instance_type,resourceid,taskCost,resource_cost_hour]
            self.rows.append(row)
            #rows.append([self.num, node_id, current_time, status, nodeType,self.name,self.instance_type],)
            return row
        return None

    def printState(self, node, node_id, inSubProcess):
        node_copy = node.copy() #to avoid changing data in node due to the first if
        if node_copy['subtype'] is not None:
            node_copy['type']=node_copy['type']+"/"+node_copy['subtype']
        if node_copy['type'] == 'subProcess':
            print(f"#{self.num}|{self.name}: {node_id} (subprocess {node_copy['name']} just started), instance_type:{self.instance_type}. time: {self.env.now}.")
        elif inSubProcess == True:
            print(f"#{self.num}|{self.name} (inside subprocess): {node_id} ({node_copy['name']}), type: {node_copy['type']}, instance_type:{self.instance_type}. time: {self.env.now}.")
        else:
            print(f"#{self.num}|{self.name}: {node_id} ({node_copy['name']}), type: {node_copy['type']}, instance_type:{self.instance_type}. time: {self.env.now}.")

    def run(self):
        yield self.env.timeout(self.start_delay) #delay start because of arrival rate.
        start_node_id = next((node_id for node_id, node in self.process_details['node_details'].items() if node['type'] == 'startEvent'), None) #find first start event
        if start_node_id is None:
            return
        yield from self.run_node(start_node_id)

        #This zone is executed after instance is over, since run_node recursively visits all nodes:
        for element_id, duration_threshold in self.durationThresholds.items():
            if self.durationThresholds[element_id] is not None and self.durationThresholds[element_id] < 0.0:
                abss=abs(self.durationThresholds[element_id])
                print(f"-------------------\n{element_id} has exceded his duration threshold by {abss}\n-------------------")
                self.extraLog[f"{element_id} has exceded his DURATION threshold in instance {self.num} by:"]= abss
        for element_id, cost_threshold in self.costThresholds.items():
            if self.costThresholds[element_id] is not None and self.costThresholds[element_id] < 0.0:
                abss=abs(self.costThresholds[element_id])
                print(f"-------------------\n{element_id} has exceded his cost threshold by {abss}\n-------------------")
                self.extraLog[f"{element_id} has exceded his COST threshold in instance {self.num} by:"]= abss

        print(f"[SIM] Instance #{self.num} ({self.name}, type={self.instance_type}) completed at sim time {self.env.now:.1f}s", flush=True)

    def _execute_task(self, node_id, subprocess_node=None):
        #Full task lifecycle for a single instance's pass through this task node: message/exception
        #pre-checks, resource acquisition (or batch-queue join), duration, cost/threshold accounting,
        #logging, resource release. Returns next_node_id (or None on any early exit) instead of
        #recursing into it, so the caller decides how/when to continue -- run_node's normal task branch
        #recurses immediately.
        #Invoked via `yield from` for normal (non-TCG) tasks, so it behaves exactly as before: `yield
        #from` is generator delegation on the same process and can never receive a simpy.Interrupt, so
        #the interrupt handling below only ever fires when a TCG gateway (possibly several `run_node`
        #levels up the call chain, through any number of intermediate nodes) has spawned the whole
        #candidate path as its own env.process(...) and later abandons/interrupts it. `env.active_process`
        #always points at that top-level Process no matter how deep the `yield from` chain got here, so
        #this discovers whether anyone is racing us without needing a parameter threaded through every
        #node type in run_node.
        started_event = getattr(self.env.active_process, 'tcg_started_event', None)
        if started_event is None:
            started_event = self.env.event()

        if subprocess_node is None:
            node = self.process_details['node_details'][node_id]
            printFlag = False
        else:
            node = self.process_details['node_details'][subprocess_node]['subprocess_details'][node_id]
            printFlag = True

        #check if external exceptions happened (if in a subprocess), if yes handle it or just return
        if subprocess_node is not None:
            idd,error_node = next(((idd,node) for idd, node in self.process_details['node_details'].items() if node['type'] == 'boundaryEvent' and node['subtype'] == 'messageEventDefinition' and node['attached_to'] == subprocess_node), (None, None))
            if idd is not None: #if there is a boundary event of type msg
                if any(prev_node in self.executed_nodes[self.num] for prev_node in error_node['previous']): #if some msg arrived to it
                    self.subprocessExternalException[subprocess_node]=True
                has_exception_been_handled = idd in self.executed_nodes[self.num]
                if self.subprocessExternalException[subprocess_node]==True and not has_exception_been_handled:
                    yield from self.run_node(idd, None)
                    return None
                elif self.subprocessExternalException[subprocess_node]==True and has_exception_been_handled:
                    return None
            if self.subprocessTerminate[self.num][subprocess_node]==True:
                return None

        #wait for previous messages to be delivered (message pointing to this task)
        if len(node['previous'])>0:
            while not all(prev_node in self.executed_nodes[self.num] for prev_node in node['previous']):
                yield self.state_changed_event[self.num]
        assign_row = self.xeslog(node_id,"assign",node['type'])

        if self.task_batch_max_size.get(node_id):
            #Batch-enabled task: join the shared queue for this node instead of acquiring resources
            #and sampling a duration individually. A per-node coordinator (started once, by whoever
            #arrives first) pulls up to the configured max batch size from the queue whenever the
            #resource is free, processes them together with one shared duration, and wakes every
            #member's ticket at once when the batch completes.
            state = self.batch_state[node_id]
            if not state['coordinator_started']:
                state['coordinator_started'] = True
                self.env.process(self._run_batch_coordinator(node_id))
            ticket = {'engine': self, 'started_event': started_event, 'done_event': self.env.event(), 'cancelled': False}
            state['queue'].append(ticket)
            if not state['arrival_event'].triggered:
                state['arrival_event'].succeed()
                state['arrival_event'] = self.env.event()
            try:
                yield ticket['done_event']
            except simpy.Interrupt:
                if started_event.triggered:
                    #the coordinator already committed this member in the same instant the interrupt
                    #was raised -- nothing to cancel anymore, just keep waiting for it to finish.
                    yield ticket['done_event']
                else:
                    ticket['cancelled'] = True
                    if assign_row is not None:
                        self.rows.remove(assign_row)
                    return None
            next_node_id = node['next'][0]
            return next_node_id

        taskTime=timeCalculator.convert_to_seconds(self.task_durations[node_id]) # task duration is used here, it is passed before to a converter that transforms the type/mean/arg1/arg2 to a value in seconds, this value the task duration is always different in each instance
        if self.durationThresholds[node_id] is not None:
            self.durationThresholds[node_id] -= taskTime
            #print(self.durationThresholds)


        #RESOURCES zone

        # add by LR
        resourceid_for_task = list()
        resource_cost_hour = list()

        taskNeededResources = self.task_resources[node_id]
        worklist_id = self.tasks_worklists[node_id]
        if taskNeededResources: #if the task needs some resources
            grouped_resources = self.task_grouped_resources.get(node_id, {})
            waited={}
            requests = []
            try:
                while True: #iterate till some resources can be allocated
                    #check if terminate end events happened
                    if self.terminateEndEvent[self.num]==True:
                        return None
                    resources_allocated = False
                    failed_due_to_timetable = False
                    i = 0
                    for group_id, resources in grouped_resources.items(): # Check each group of resources
                        timetablebreakFlag=False
                        i += 1
                        # Check if there are enough resources and within timetable for this group
                        requests = []
                        for resource_name, amount_needed in resources:
                            if worklist_id and worklist_id in self.worklist_resources[self.num]: #if this task has a worklist_id, then the set of resources is a subset of the full resources and it is taken from worklist_resources
                                available_resources = []
                                resources_in_timetable = []
                                if resource_name in self.worklist_resources[self.num][worklist_id]:  # Check if the resource exists for this worklist_id
                                    for resource_tuple in self.global_resources[resource_name]:
                                        if self.is_in_timetable(resource_tuple[2]) and resource_tuple[0].count < resource_tuple[0].capacity:
                                            available_resources.append(resource_tuple)
                                        if self.is_in_timetable(resource_tuple[2]):
                                            resources_in_timetable.append(resource_tuple)

                                timetablebreakFlag=True #this avoids a false print of timetable error later

                            else:
                                available_resources = [res for res in self.global_resources[resource_name] if self.is_in_timetable(res[2]) and res[0].count < res[0].capacity]
                                resources_in_timetable = [res for res in self.global_resources[resource_name] if self.is_in_timetable(res[2])]
                            if len(available_resources) < amount_needed:
                                if len(self.global_resources[resource_name]) < amount_needed:
                                    raise ValueError(f"ERRORE CRITICO DI LOGICA: L'istanza {self.num} nel nodo {node_id} richiede {amount_needed} '{resource_name}', ma ne esistono in totale solo {len(self.global_resources[resource_name])} nel simulatore! La simulazione non può proseguire.")
                                if len(resources_in_timetable) < amount_needed:
                                    if self.env.now > 31536000: # 1 year
                                        raise ValueError(f"ERRORE CRITICO: L'istanza {self.num} aspetta da 1 anno le risorse del nodo {node_id} (risorsa {resource_name}). Turni timetable mancanti o inarrivabili!")
                                    failed_due_to_timetable = True
                                for name, req, costPerHour, resourceSimpy,_ in requests:
                                    req.resource.release(req)
                                    req.cancel() # cancel the requests that were accumulated till now since this group is ko
                                requests = []  # avoid re-releasing these same (already-released) entries below
                                break  # Move to the next group if not enough resources
                            else:
                                #print(node_id + f"|group n.{i}| OK | {resource_name}: {len(available_resources)}/{len(global_resources[resource_name])} resources available, {amount_needed} needed")
                                appended=0
                                to_request = []  # New data structure to store resources to request later, needed due to possible setup_times

                                #resource_tuple is: simpyRes, cost, timetableName, lastInstanceType, setupTime, maxUsage, actualUsage, lock
                                for resource_tuple in available_resources:

                                    if appended == amount_needed:
                                        break
                                    # Checks if there is no setupTime or there is setupTime but no lastInstance, or there is lastInstance but it is our current instanceType
                                    if (not resource_tuple[4]['type'] or not resource_tuple[3] or resource_tuple[3]==self.instance_type):
                                        modified_tuple = resource_tuple + ("increment",)
                                        to_request.append(modified_tuple)
                                        appended += 1

                                    #case where different lastInstanceType so i wait 1 second to give opportunity to other instances of same type to use resource, if there are any.
                                    elif resource_tuple[3] and (resource_tuple[0] not in waited or waited[resource_tuple[0]]==False):
                                        waited[resource_tuple[0]]=True
                                        yield self.env.timeout(0)

                                    # Check if resource is with different lastInstanceType, so needs setupTime (after having waited)
                                    elif resource_tuple[3] and waited[resource_tuple[0]]==True:
                                        modified_tuple = resource_tuple + ("instanceTypeChange",)
                                        to_request.append(modified_tuple)
                                        appended+=1

                                    else:
                                        waited[resource_tuple[0]]=False

                                if appended == amount_needed:
                                    for resource_tuple in to_request:
                                        req = resource_tuple[0].request()
                                        requests.append((resource_name, req, resource_tuple[1], resource_tuple[0],resource_tuple[8])) #[8] is the "mode" for update_resources funct, it was appended to the tuple in previous elif

                        if len(requests) == sum(amount for _, amount in resources):
                            resources_allocated = True
                            waited={}
                            # Store acquired resources in instance-specific worklist_resources if worklist_id is not empty
                            if worklist_id:
                                if worklist_id not in self.worklist_resources[self.num]:
                                    self.worklist_resources[self.num][worklist_id] = {}
                                for resource_name, req, cost_per_hour, resourceSimpy,_ in requests:
                                    if resource_name not in self.worklist_resources[self.num][worklist_id]:
                                        self.worklist_resources[self.num][worklist_id][resource_name] = []
                                    # Find the matching resource tuple in global_resources
                                    res_tuple = next(res for res in self.global_resources[resource_name] if res[0] is req.resource)
                                    _, cost_per_hour, timetable_name, last_instance, setup_time, max_usages, current_usages,lock = res_tuple
                                    # Append to worklist_resources with all elements (IMPORTANT: actually the tuple is USELESS (except for the resource), only the resource will be used in the rest of the code, the other info will be taken from global_resources using the res as id)
                                    self.worklist_resources[self.num][worklist_id][resource_name].append(
                                        (req.resource, cost_per_hour, timetable_name, last_instance, setup_time, max_usages, current_usages,lock)
                                    )

                                    # add by LR
                                    #resourceid_for_task.append(resource_name)

                            for resource_name, req, cost_per_hour, resourceSimpy,mode in requests:  # Extract elements from the tuple
                                #update global_resources 2 cases: 1) self.instance.type is different and then throw setupTime 2) same instanceType, check usage
                                #mode can either be, increment, instanceTypeChange
                                yield from self.update_resources(req.resource, mode,resource_name, node_id)
                                yield req

                                # add by LR
                                #if not worklist_id:
                                resourceid_for_task.append(resource_name)
                                resource_cost_hour.append(cost_per_hour)

                            break  # Break the loop as resources are allocated
                        else:
                            for _,req,_,_,_ in requests:
                                if req.triggered:
                                    req.cancel()
                                    req.resource.release(req)
                            requests = []  # avoid re-releasing these same (already-released) entries later

                    if not resources_allocated:
                        if not hasattr(self.env, 'resource_released_event'):
                            self.env.resource_released_event = self.env.event()
                        if failed_due_to_timetable:
                            yield self.env.resource_released_event | self.env.timeout(60)  # Polling only off shift
                        else:
                            yield self.env.resource_released_event  # Waiting fully for capacity
                    else:
                        break  # Break the while loop as resources are allocated
            except simpy.Interrupt:
                #abandon: release anything actually granted so far in this group's attempt, and
                #withdraw the one request (if any) that was in-flight on the interrupted yield.
                for _, req, _, _, _ in requests:
                    if req.triggered:
                        req.cancel()
                        req.resource.release(req)
                    else:
                        req.cancel()
                if assign_row is not None:
                    self.rows.remove(assign_row)
                return None
        #END resources

        #started_event is fetched fresh from env.active_process on every _execute_task call (see the
        #comment above), but it's the same event object for every task a given attempt_proc visits --
        #only the first task reached should succeed it, later ones must no-op or this raises
        #"Event has already been triggered" the moment an attempt process's path crosses 2+ tasks.
        if not started_event.triggered:
            started_event.succeed()

        # add by LR
        #self.xeslog(node_id,"assign",node['type'],resourceid_for_task)
        self.xeslog(node_id,"start",node['type'])

        if not math.isfinite(taskTime):
            print(f"[ERROR] Instance #{self.num}: task {node_id} has non-finite duration ({taskTime}) — check distribution parameters", flush=True)
            taskTime = 0
        yield self.env.timeout(taskTime)

        #EXCEPTIONS check, the check was already done before but it might have happened some stuff during the timeout:
        #check if terminate end events happened
        if self.terminateEndEvent[self.num]==True:
            return None
        #check if external exceptions happened (if in a subprocess), if yes handle it or just return
        if subprocess_node is not None:
            idd,error_node = next(((idd,node) for idd, node in self.process_details['node_details'].items() if node['type'] == 'boundaryEvent' and node['subtype'] == 'messageEventDefinition' and node['attached_to'] == subprocess_node), (None, None))
            if idd is not None: #if there is a boundary event of type msg
                if any(prev_node in self.executed_nodes[self.num] for prev_node in error_node['previous']): #if some msg arrived to it
                    self.subprocessExternalException[subprocess_node]=True
                has_exception_been_handled = idd in self.executed_nodes[self.num]
                if self.subprocessExternalException[subprocess_node]==True and not has_exception_been_handled:
                    yield from self.run_node(idd, None)
                    return None
                elif self.subprocessExternalException[subprocess_node]==True and has_exception_been_handled:
                    return None
            if self.subprocessTerminate[self.num][subprocess_node]==True:
                return None


        self.mark_node_executed(node_id)
        self.printState(node,node_id,printFlag)
        next_node_id = node['next'][0]
        taskCost=self.task_costs[node_id]
        if taskCost != '':
            self.totalCost[self.num] += float(taskCost)
            if self.costThresholds[node_id] is not None:
                self.costThresholds[node_id]-=float(taskCost)

        # add by LR
        self.xeslog(node_id,"complete",node['type'],resourceid_for_task,taskCost,resource_cost_hour)
        #self.xeslog(node_id,"complete",node['type'])

        # Release resources
        if taskNeededResources:
            for name, req, costPerHour,_, _ in requests:
                self.timeUsedPerResource[name]+=float(taskTime)
                if req.triggered:
                    req.cancel()
                    req.resource.release(req)
                    self.trigger_resource_release()
        return next_node_id

    def run_node(self, node_id, subprocess_node=None):

        #if we are in a subprocess then the data is saved in a different section of bpmn.json (that has been saved to process_details)
        if subprocess_node is None:
            node = self.process_details['node_details'][node_id]
            printFlag=False
        else:
            node = self.process_details['node_details'][subprocess_node]['subprocess_details'][node_id]
            printFlag=True

        #if this instance met a terminate end event anywhere, stop execution
        if self.terminateEndEvent[self.num]==True:
            return
    
        if node['type'] == 'startEvent':
            if node['subtype']=="timerEventDefinition":
                #add by mm
                fullType = node['type'] + '/' + node['subtype'] if node['subtype'] is not None else node['type']
                
                waitTime = self.catchEvents[node_id]
                waitTimeSeconds=timeCalculator.convert_to_seconds(waitTime)
                self.xeslog(node_id,"start",fullType)
                yield self.env.timeout(waitTimeSeconds)
            next_node_id = node['next'][0]
            if len(node['previous'])>0:
                while not all(prev_node in self.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.state_changed_event[self.num]
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            self.mark_node_executed(node_id)
            yield from self.run_node(next_node_id, subprocess_node)


        elif node['type'] == 'task':
            next_node_id = yield from self._execute_task(node_id, subprocess_node)
            if next_node_id is not None:
                yield from self.run_node(next_node_id, subprocess_node)

        # add by LR , modify by LR
        elif node['type'] == 'exclusiveGateway':
            flows_from_gw = [(flow_id, flow) for flow_id, flow in self.loader.process_data['sequence_flows'].items() if flow['sourceRef'] == node_id]

            def normalize_condition_groups(diagbp_flow):
                #A branch's conditions are a list of groups; conditions inside a group combine with
                #that group's own operator (default AND). Groups combine with each other left to
                #right, each via its own 'connector' to the group right before it (group 0 has none) --
                #e.g. "G1 OR G2 AND G3" is evaluated as (G1 OR G2) AND G3, exactly as written, no
                #AND-before-OR precedence. Falls back to treating a pre-groups flat 'conditions' list
                #(saved before this feature existed) as one implicit AND-group.
                groups = diagbp_flow.get('conditionGroups')
                if groups is None:
                    legacy = diagbp_flow.get('conditions', [])
                    groups = [{'operator': 'AND', 'conditions': legacy}] if legacy else []
                else:
                    groups = list(groups)

                #Legacy 'Forced Instance Types' (pre-dates moving instance type into conditions)
                #becomes an implicit OR-group of instanceType conditions, ANDed with whatever
                #conditions already exist -- matches the old types_match gate, which applied on top
                #of any condition/timer already present.
                legacy_types = diagbp_flow.get('types')
                if legacy_types:
                    type_group = {
                        'operator': 'OR',
                        'conditions': [{'kind': 'instanceType', 'value': t.get('type')} for t in legacy_types]
                    }
                    if groups:
                        type_group['connector'] = 'AND'
                    groups = groups + [type_group]
                return groups

            def has_any_condition(diagbp_flow):
                groups = normalize_condition_groups(diagbp_flow)
                return any(g.get('conditions') for g in groups)

            def conditions_hold(diagbp_flow):
                groups = normalize_condition_groups(diagbp_flow)
                if not groups:
                    return True

                def group_holds(group):
                    results = []
                    for cond in group.get('conditions', []):
                        kind = cond.get('kind')
                        value = cond.get('value', cond.get('activityId'))
                        if kind == 'visited':
                            results.append(value in self.executed_nodes[self.num])
                        elif kind == 'notVisited':
                            results.append(value not in self.executed_nodes[self.num])
                        elif kind == 'instanceType':
                            results.append(value == self.instance_type)
                        elif kind == 'notInstanceType':
                            results.append(value != self.instance_type)
                        elif kind == 'visitedCount':
                            actual = self.executed_node_counts[self.num].get(value, 0)
                            try:
                                threshold = int(cond.get('count', 0))
                            except (TypeError, ValueError):
                                threshold = 0
                            comparator = cond.get('comparator', '>=')
                            if comparator == '<=':
                                results.append(actual <= threshold)
                            elif comparator == '=':
                                results.append(actual == threshold)
                            else:
                                results.append(actual >= threshold)
                    if not results:
                        return True
                    return all(results) if group.get('operator', 'AND') == 'AND' else any(results)

                result = group_holds(groups[0])
                for group in groups[1:]:
                    val = group_holds(group)
                    connector = group.get('connector', 'OR')
                    result = (result and val) if connector == 'AND' else (result or val)
                return result

            def pick_p_candidate(p_entries):
                #p_entries: list of (target, diagbp_flow). Instance-type forcing now happens via
                #conditions -- a branch with an instanceType condition is no longer a P entry at all
                #(see has_any_condition/normalize_condition_groups above), so this is just a plain
                #weighted random pick among the remaining probability branches.
                if not p_entries:
                    return None
                node_probabilities = {target: float(diagbp_flow['executionProbability']) for target, diagbp_flow in p_entries}
                return np.random.choice(list(node_probabilities.keys()), p=list(node_probabilities.values()))

            #Sort this gateway's outgoing flows into C / T / TC / P purely by what's configured on each --
            #no more special "isTimeoutPath" flag. A plain T branch using the gateway's default timer now
            #plays the role the old dedicated timeout branch used to.
            c_flows = []
            t_flows = []
            tc_flows = []
            p_entries = []
            for flow_id, flow in flows_from_gw:
                diagbp_flow = self.sequence_flows_dict.get(flow_id)
                if diagbp_flow is None:
                    continue
                target = flow['targetRef']
                #legacy 'isTimeoutPath' (pre-dates hasOwnTimer/conditions) is treated as "has its own
                #timer, no condition" -- keeps scenarios saved before this change working as a T branch
                #on the gateway's default timer, instead of silently falling into the P pool.
                has_timer = bool(diagbp_flow.get('hasOwnTimer')) or bool(diagbp_flow.get('isTimeoutPath'))
                has_condition = has_any_condition(diagbp_flow)
                if not has_timer and not has_condition:
                    p_entries.append((target, diagbp_flow))
                elif has_timer and has_condition:
                    tc_flows.append((target, diagbp_flow))
                elif has_timer:
                    t_flows.append((target, diagbp_flow))
                else:
                    c_flows.append((target, diagbp_flow))

            def resolve_c(c_flows):
                matched = [target for target, diagbp_flow in c_flows if conditions_hold(diagbp_flow)]
                if len(matched) > 1:
                    print(f"[GATEWAY WARNING] Instance #{self.num}: gateway {node_id} has {len(matched)} condition branches matching simultaneously — taking the first by definition order.", flush=True)
                return matched[0] if matched else None

            #Fast path: no branch on this gateway has a timer at all -- degenerates exactly to the
            #original plain-XOR mechanism, no process spawned, no race.
            if not t_flows and not tc_flows:
                next_node_id = resolve_c(c_flows)
                if next_node_id is None:
                    next_node_id = pick_p_candidate(p_entries)
                if next_node_id is None:
                    next_node_id = node['next'][0]
                self.xeslog(node_id, "complete", node['type'])
                self.printState(node, node_id, printFlag)
                yield from self.run_node(next_node_id, subprocess_node)
                return

            #At least one T/TC branch exists -- condition-only branches are still checked immediately,
            #with zero waiting, before anything else is even considered.
            matched_c = resolve_c(c_flows)
            if matched_c is not None:
                self.xeslog(node_id, "complete", node['type'])
                self.printState(node, node_id, printFlag)
                yield from self.run_node(matched_c, subprocess_node)
                return

            #Race path: at most one P attempt (spawned for real, exactly like the original TCG mechanism)
            #races against every eligible T/TC branch's own timer, all started together from now.
            candidate = pick_p_candidate(p_entries)
            started_event = None
            attempt_proc = None
            if candidate is not None:
                started_event = self.env.event()
                attempt_proc = self.env.process(self.run_node(candidate, subprocess_node))
                attempt_proc.tcg_started_event = started_event
                print(f"[GATEWAY] Instance #{self.num} at {node_id}: attempting→{candidate}", flush=True)

            pending = {}  # timeout_event -> ('T'|'TC', target, diagbp_flow)
            for target, diagbp_flow in t_flows:
                own_timer = diagbp_flow.get('ownTimer')
                timer_dist = own_timer if (own_timer and own_timer.get('mean', '') != '') else self.timeConstrainedGateways.get(node_id)
                wait = timeCalculator.convert_to_seconds(timer_dist) if timer_dist else 0
                pending[self.env.timeout(wait)] = ('T', target, None)
            for target, diagbp_flow in tc_flows:
                own_timer = diagbp_flow.get('ownTimer')
                timer_dist = own_timer if (own_timer and own_timer.get('mean', '') != '') else self.timeConstrainedGateways.get(node_id)
                wait = timeCalculator.convert_to_seconds(timer_dist) if timer_dist else 0
                pending[self.env.timeout(wait)] = ('TC', target, diagbp_flow)

            chosen_target = None
            chosen_via_p = False
            try:
                while chosen_target is None:
                    race_set = ([started_event] if started_event is not None else []) + list(pending.keys())
                    if not race_set:
                        print(f"[GATEWAY WARNING] Instance #{self.num}: gateway {node_id} ran out of eligible candidates — falling back to its first outgoing flow.", flush=True)
                        chosen_target = node['next'][0]
                        break
                    if len(race_set) == 1:
                        yield race_set[0]
                        result = {race_set[0]: race_set[0].value}
                    else:
                        result = yield functools.reduce(lambda a, b: a | b, race_set)
                    if started_event is not None and started_event in result:
                        chosen_target = candidate
                        chosen_via_p = True
                        break
                    fired = [ev for ev in list(pending.keys()) if ev in result]
                    for ev in fired:
                        kind, target, diagbp_flow = pending.pop(ev)
                        if kind == 'T' or conditions_hold(diagbp_flow):
                            chosen_target = target
                            break
                        #else: this TC's condition wasn't met at expiry -- it fizzles, keep racing the rest
            except simpy.Interrupt:
                #an OUTER TCG gave up on the attempt we're part of -- cascade the cancellation down.
                if attempt_proc is not None:
                    attempt_proc.interrupt()
                raise

            self.xeslog(node_id, "complete", node['type'])
            self.printState(node, node_id, printFlag)
            if chosen_via_p:
                print(f"[GATEWAY] Instance #{self.num}: {candidate} started in time at t={self.env.now:.1f} → letting it run to completion", flush=True)
                yield attempt_proc  # the rest of the real process flow already runs inside it
                return
            else:
                print(f"[GATEWAY] Instance #{self.num}: taking timer-resolved branch {chosen_target} at t={self.env.now:.1f}", flush=True)
                if attempt_proc is not None:
                    attempt_proc.interrupt()
                yield from self.run_node(chosen_target, subprocess_node)


        elif node['type'] == 'parallelGateway':
            # AND logic: run all paths concurrently and wait for all to finish
            events = []
            for next_node_id in node['next']:
                process = self.env.process(self.run_node(next_node_id, subprocess_node)) # a process is created for each path to ensure parallelism
                events.append(process)
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            yield self.env.all_of(events)
            # When all_of is done, proceed with the node after the close
            if self.stack:  # checks if the list is not empty
                parallel_close_id,next_node_after_parallel = self.stack.pop()
                self.xeslog(parallel_close_id,"complete",node['type'])
                yield from self.run_node(next_node_after_parallel, subprocess_node)
                # print for parallel close                      
                if not printFlag:
                    print(f"#{self.num}|{self.name}: {parallel_close_id}, Parallel gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")
                else:
                    print(f"#{self.num}|{self.name}| (inside subprocess): {parallel_close_id}, Parallel gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")

        elif node['type'] == 'parallelGateway_close':
            if (node_id, node['next'][0]) not in self.stack:
                self.stack.append((node_id, node['next'][0]))
            #print(self.stack)
            return

        elif node['type'] == 'inclusiveGateway':
            flows_from_inclusive = [(flow_id, flow) for flow_id, flow in self.loader.process_data['sequence_flows'].items() if flow['sourceRef'] == node_id]
            paths_to_take = []
            for flow_id, flow in flows_from_inclusive:
                type_matched = False
                diagbp_flow = self.sequence_flows_dict.get(flow_id)
                if diagbp_flow is not None:
                    if 'types' in diagbp_flow:
                        for type_dict in diagbp_flow['types']:
                            if type_dict['type'] == self.instance_type:
                                paths_to_take.append(flow['targetRef'])
                                type_matched = True  # Mark that a type matched
                                break 
                    # If the type didn't match, use probability 
                    if not type_matched: 
                        probability = float(diagbp_flow['executionProbability'])
                        if np.random.rand() <= probability: 
                            paths_to_take.append(flow['targetRef'])
            events = []
            for next_node_id in paths_to_take:
                process = self.env.process(self.run_node(next_node_id, subprocess_node))
                events.append(process)           
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            yield self.env.all_of(events)

            if self.stackInclusive: 
                inclusive_close_id,next_node_after_inclusive = self.stackInclusive.pop()
                self.xeslog(inclusive_close_id,"complete",node['type'])
                yield from self.run_node(next_node_after_inclusive, subprocess_node)
                if not printFlag:
                    print(f"#{self.num}|{self.name}: {inclusive_close_id}, Inclusive gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")
                else:
                    print(f"#{self.num}|{self.name}| (inside subprocess): {inclusive_close_id}, Inclusive gateway closed. instance_type:{self.instance_type}. time: {self.env.now}.")
            
            

        elif node['type'] == 'inclusiveGateway_close':
            if (node_id, node['next'][0]) not in self.stackInclusive:
                self.stackInclusive.append((node_id, node['next'][0]))
            return
            
        elif node['type'] == 'subProcess':
            #set to false all exceptions at first
            self.subprocessExternalException[node_id]=False
            self.subprocessTerminate[self.num][node_id]=False
            self.subprocessInternalError[node_id]=False
            
            #wait for msg to arrive, if any
            if len(node['previous'])>0:
                while not all(prev_node in self.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.state_changed_event[self.num]

            self.xeslog(node_id,"start",node['type'])
            start_node_id = next(sub_node_id for sub_node_id, sub_node in node['subprocess_details'].items() if sub_node['type'] == 'startEvent')
            self.printState(node,node_id,printFlag)
            yield from self.run_node(start_node_id, node_id)

            self.mark_node_executed(node_id)
            next_node_id = node['next'][0]
            self.xeslog(node_id,"complete",node['type'])

            # After the subprocess is executed, continue with the node next to the subprocess if no error end event
            if self.subprocessInternalError[node_id]==False and self.subprocessExternalException[node_id]==False and self.terminateEndEvent[self.num]==False:
                yield from self.run_node(next_node_id, None)
            elif self.subprocessInternalError[node_id]==True: #if internal error happened, deal with it
                error_node = next((idd for idd, node in self.process_details['node_details'].items() if node['type'] == 'boundaryEvent' and node['attached_to'] == node_id), None)
                yield from self.run_node(error_node, None)
            #implicit else: if external exception do nothing since it is handled inside elif node[type]==task

        elif node['type'] == 'intermediateThrowEvent':
            next_node_id = node['next'][0]
            self.mark_node_executed(node_id)
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            yield from self.run_node(next_node_id, subprocess_node)
            return

        elif node['type'] == 'intermediateCatchEvent':
            fullType = node['type'] + '/' + node['subtype'] if node['subtype'] is not None else node['type']
            if node['subtype'] == 'messageEventDefinition': #if it is an intermediate msg catch wait for the msg
                next_node_id = node['next'][0]
                if len(node['previous'])>0: #wait for msg
                    while not all(prev_node in self.executed_nodes[self.num] for prev_node in node['previous']):
                        yield self.state_changed_event[self.num]
                self.mark_node_executed(node_id)
                self.xeslog(node_id,"complete",fullType)
                self.printState(node,node_id,printFlag)
                yield from self.run_node(next_node_id, subprocess_node)
                return
            else: #otherwise treats it as a timer event, whatever subtype it is
                next_node_id = node['next'][0]
                self.mark_node_executed(node_id)
                waitTime = self.catchEvents[node_id]
                waitTimeSeconds=timeCalculator.convert_to_seconds(waitTime)
                self.xeslog(node_id,"start",fullType)
                yield self.env.timeout(waitTimeSeconds)
                self.xeslog(node_id,"complete",fullType)
                self.printState(node,node_id,printFlag)
                yield from self.run_node(next_node_id, subprocess_node)
                return
        
        elif node['type'] == 'eventBasedGateway':
            smallestTimer=None #variable where the timer that has lower time to wait (attached to the eventBasedGateway) gets saved, if any
            ready=False
            self.mark_node_executed(node_id)
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)    

            for next_node_id in node['next']:
                if subprocess_node is None:
                    nextNode = self.process_details['node_details'][next_node_id]
                    printFlag=False
                else:
                    nextNode = self.process_details['node_details'][subprocess_node]['subprocess_details'][next_node_id]
                    printFlag=True
                if not nextNode['subtype'] == 'messageEventDefinition': #after event based gateway there is for sure intermediate catch events, if not message i save smallest timer
                    timer=timeCalculator.convert_to_seconds(self.catchEvents[next_node_id])
                    if smallestTimer is None or timer < smallestTimer:
                        smallestTimer = timer
                        nextNodeToVisit=nextNode['next'][0] #sets this as next node to visit, can only be changed by a msg received later
            startTime = self.env.now
            while (not ready) and (smallestTimer is None or (self.env.now - startTime) < smallestTimer): #while no msg has been received and the smallest timer is not over yet
                for next_node_id in node['next']:
                    if subprocess_node is None:
                        nextNode = self.process_details['node_details'][next_node_id]
                        printFlag=False
                    else:
                        nextNode = self.process_details['node_details'][subprocess_node]['subprocess_details'][next_node_id]
                        printFlag=True
                    if nextNode['subtype'] == 'messageEventDefinition' and ready==False:
                        ready=any(prev_node in self.executed_nodes[self.num] for prev_node in nextNode['previous']) #this updates the ready variable to leave the while loop above
                        if ready==True:
                            nextNodeToVisit=nextNode['next'][0]
                            break
                if ready:
                    break
                
                if smallestTimer is not None:
                    remainingTime = smallestTimer - (self.env.now - startTime)
                    if remainingTime <= 0:
                        break
                    yield self.state_changed_event[self.num] | self.env.timeout(remainingTime)
                else:
                    yield self.state_changed_event[self.num]

            self.printState(nextNode,next_node_id,printFlag) # print the state of the intermediate catch event (timer or msg, whatever)
            self.xeslog(next_node_id,"complete",nextNode['type'])        
            yield from self.run_node(nextNodeToVisit, subprocess_node) # now it visits the node 2 times forward (2 times after the eventBasedGateway) because the catches have already been handled
            return

        elif node['type'] == 'boundaryEvent': 
            self.printState(node,node_id,printFlag)
            self.xeslog(node_id,"complete",node['type'])
            self.mark_node_executed(node_id)
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, subprocess_node)
            return

        elif node['type'] == 'endEvent': 
            fullType = node['type'] + '/' + node['subtype'] if node['subtype'] is not None else node['type']
            self.mark_node_executed(node_id)
            self.xeslog(node_id,"complete",fullType)           
            self.printState(node,node_id,printFlag)
            # Terminate end event
            if node['subtype'] == 'terminateEventDefinition' and subprocess_node is None:
                self.terminateEndEvent[self.num]=True
            elif node['subtype'] == 'terminateEventDefinition':
                self.subprocessTerminate[self.num][subprocess_node]=True #it stops the subprocess
            # Error end event (lightning symbol)
            elif node['subtype'] == 'errorEventDefinition' and subprocess_node is not None:
                self.subprocessInternalError[subprocess_node]=True
                return
            # standard end event
            else:
                return