from datetime import datetime, timedelta
from datetime import time as dt_time
import timeCalculator
import numpy as np


class SimulatorEngine:
    def __init__(self, env, name, process_details, num, loader, global_resources, logging_opt, totalCost,
     timeUsedPerResource, extraLog, rows, start_delay=0, instance_type="default"):
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

        self.timetables = self.loader.extra_data['timetables']
        self.catchEvents = self.loader.extra_data['catchEvents']

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

        self.startDateTime = self.loader.extra_data['startDateTime']

        self.terminateEndEvent={} # dictionary of true or false, to tell if that process has been terminated or not
        self.terminateEndEvent[self.num] = False

        self.subprocessTerminate={} #this is used for subprocesses for terminate end events
        self.subprocessTerminate[self.num] = {}

        self.subprocessInternalError = {} #used in error end event
        self.subprocessExternalException = {}


        #resources is a dict with name as key and a tuple made of simpy resource, cost and timetable.
        self.executed_nodes[self.num] = set() 
        self.timeUsedPerResource=timeUsedPerResource
        for resource_name, resource_info in self.global_resources.items():
            self.timeUsedPerResource[resource_name]=0.0
        
    def update_resources(self,resource_obj, mode, resource_name, node_id): #this function handles setup time for resources
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
                        self.instance_type,  # lastInstanceType
                        res_tuple[4],  # setupTime
                        int(res_tuple[5]),  # maxUsages
                        res_tuple[6],
                        res_tuple[7]  
                    )                                                    
                break


    
    def is_in_timetable(self, timetable_name): #this func is used when gathering resources for a task, to check if a res is in shift
        start_time = self.startDateTime
        start_time = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%S")
        current_time = start_time + timedelta(seconds=self.env.now)
        # Get the timetable from the global timetables variable
        timetable = next(t for t in self.timetables if t['name'] == timetable_name)

        # Extract the current time's hour and minute
        current_hour_minute_second = dt_time(current_time.hour, current_time.minute, current_time.second)
        
        # Check if the current time falls within any of the rules in the timetable
        for rule in timetable['rules']:
            timeFlag=False
            from_hour, from_minute, from_second = map(int, rule['fromTime'].split(':'))
            to_hour, to_minute, to_second = map(int, rule['toTime'].split(':'))

            from_time = dt_time(from_hour, from_minute, from_second)
            to_time = dt_time(to_hour, to_minute, to_second)
            from_day = rule['fromWeekDay'].upper()
            to_day = rule['toWeekDay'].upper()

            # Checks for both ways, from time bigger or lower than to time
            if from_time > to_time: #ie: 22:00:00 to 04:00:00
                if not (to_time >= current_hour_minute_second or current_hour_minute_second >= from_time):
                    continue  # Skip this rule, as current time is outside the range
                # This variable is true only if current hour minute is less than midnight
                # This is to avoid a case where shift is 22 to 04 and friday to sunday (morning) and sunday 23:00 would be considered ok (which is not), while sunday 01:00 is ok
                timeFlag=True  
            elif not from_time <= current_hour_minute_second <= to_time:
                continue  # Skip this rule, as current time is outside the range

            # Check if current day is within the rule's day range

            days = ['MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY']

            # Checks for both ways as before for time
            if (days.index(to_day) < days.index(from_day)) and timeFlag:
                if not (days.index(to_day) > days.index(current_time.strftime('%A').upper()) or days.index(current_time.strftime('%A').upper()) >= days.index(from_day)):
                    continue # Skip this rule, as current day is outside the range
            elif days.index(to_day) < days.index(from_day) and not timeFlag:
                if not (days.index(to_day) >= days.index(current_time.strftime('%A').upper()) or days.index(current_time.strftime('%A').upper()) >= days.index(from_day)):
                    continue  # Skip this rule, as current day is outside the range
            elif (not (days.index(from_day) <= days.index(current_time.strftime('%A').upper()) < days.index(to_day))) and timeFlag:
                continue  # Skip this rule, as current day is outside the range
            elif (not (days.index(from_day) <= days.index(current_time.strftime('%A').upper()) <= days.index(to_day))) and not timeFlag:
                continue  # Skip this rule, as current day is outside the range


            return True

        return False
    # add by LR
    def xeslog(self, node_id, status, nodeType, resourceid=None, taskCost=None, resource_cost_hour=None):
    #def xeslog(self, node_id, status, nodeType):
        print("-------XESLOG------")
        if nodeType=="parallelGateway":
            nodeType="parallelGatewayOpen"
        if nodeType=="inclusiveGateway":
            nodeType="inclusiveGatewayOpen"
        start_time = datetime.strptime(self.startDateTime, "%Y-%m-%dT%H:%M:%S")
        current_time = start_time + timedelta(seconds=self.env.now)
        if self.logging_opt or status=="complete":
            # add by LR
            act_name = self.process_details['node_details'][node_id].get('name', None)
            if not act_name:
                self.rows.append([self.num, node_id, current_time, status, nodeType,self.name,self.instance_type,resourceid,taskCost,resource_cost_hour],)
            else:
                self.rows.append([self.num, act_name, current_time, status, nodeType,self.name,self.instance_type,resourceid,taskCost,resource_cost_hour],)
            #rows.append([self.num, node_id, current_time, status, nodeType,self.name,self.instance_type],)

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
                waitTime = self.catchEvents[node_id]
                waitTimeSeconds=timeCalculator.convert_to_seconds(waitTime)
                self.xeslog(node_id,"start",fullType)
                yield self.env.timeout(waitTimeSeconds)
            next_node_id = node['next'][0]
            if len(node['previous'])>0:
                while not all(prev_node in self.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.env.timeout(1)
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            self.executed_nodes[self.num].add(node_id)
            yield from self.run_node(next_node_id, subprocess_node)


        elif node['type'] == 'task':
            #print(Process.terminateEndEvent[self.num])
            #check if external exceptions happened (if in a subprocess), if yes handle it or just return
            if subprocess_node is not None:
                idd,error_node = next(((idd,node) for idd, node in self.process_details['node_details'].items() if node['type'] == 'boundaryEvent' and node['subtype'] == 'messageEventDefinition' and node['attached_to'] == subprocess_node), (None, None))
                if idd is not None: #if there is a boundary event of type msg
                    if any(prev_node in self.executed_nodes[self.num] for prev_node in error_node['previous']): #if some msg arrived to it
                        self.subprocessExternalException[subprocess_node]=True
                    has_exception_been_handled = idd in self.executed_nodes[self.num]
                    if self.subprocessExternalException[subprocess_node]==True and not has_exception_been_handled:
                        yield from self.run_node(idd, None)
                        return
                    elif self.subprocessExternalException[subprocess_node]==True and has_exception_been_handled:
                        return
                if self.subprocessTerminate[self.num][subprocess_node]==True: 
                    return 

            #wait for previous messages to be delivered (message pointing to this task)
            if len(node['previous'])>0:
                while not all(prev_node in self.executed_nodes[self.num] for prev_node in node['previous']):
                    yield self.env.timeout(1)
            self.xeslog(node_id,"assign",node['type'])
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
                grouped_resources = {}
                for res in taskNeededResources:
                    if res['groupId'] not in grouped_resources:
                        grouped_resources[res['groupId']] = []
                    grouped_resources[res['groupId']].append((res['resourceName'], int(res['amountNeeded'])))
                waited={}                                    
                while True: #iterate till some resources can be allocated
                    #check if terminate end events happened
                    if self.terminateEndEvent[self.num]==True:
                        return
                    resources_allocated = False
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
                                for name, req, costPerHour, resourceSimpy,_ in requests:
                                    req.resource.release(req)
                                    req.cancel() # cancel the requests that were accumulated till now since this group is ko
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
                                        yield self.env.timeout(1)

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

                    if not resources_allocated:
                        yield self.env.timeout(1)  # If no group can be allocated, wait for a timeout
                    else:
                        break  # Break the while loop as resources are allocated
            #END resources

            # add by LR
            #self.xeslog(node_id,"assign",node['type'],resourceid_for_task)
            self.xeslog(node_id,"start",node['type'])

            yield self.env.timeout(taskTime)
            
            #EXCEPTIONS check, the check was already done before but it might have happened some stuff during the timeout:
            #check if terminate end events happened
            if self.terminateEndEvent[self.num]==True:
                return
            #check if external exceptions happened (if in a subprocess), if yes handle it or just return
            if subprocess_node is not None:
                idd,error_node = next(((idd,node) for idd, node in self.process_details['node_details'].items() if node['type'] == 'boundaryEvent' and node['subtype'] == 'messageEventDefinition' and node['attached_to'] == subprocess_node), (None, None))
                if idd is not None: #if there is a boundary event of type msg
                    if any(prev_node in self.executed_nodes[self.num] for prev_node in error_node['previous']): #if some msg arrived to it
                        self.subprocessExternalException[subprocess_node]=True
                    has_exception_been_handled = idd in self.executed_nodes[self.num]
                    if self.subprocessExternalException[subprocess_node]==True and not has_exception_been_handled:
                        yield from self.run_node(idd, None)
                        return
                    elif self.subprocessExternalException[subprocess_node]==True and has_exception_been_handled:
                        return
                if self.subprocessTerminate[self.num][subprocess_node]==True: 
                    return 
                    

            self.executed_nodes[self.num].add(node_id)
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
            yield from self.run_node(next_node_id, subprocess_node)

        # add by LR , modify by LR
        elif node['type'] == 'exclusiveGateway':
            print("Gateway Code Debug")
            # Get the flows from bpmn.json that start from the current XOR
            flows_from_xor = [(flow_id, flow) for flow_id, flow in self.loader.process_data['sequence_flows'].items() if flow['sourceRef'] == node_id]
            # Create a dictionary mapping target nodes to their probabilities
            node_probabilities = {}
            
            # add by LR
            node_probabilities_to_delete = {}
            redistribute_probabilities = False
            forced_flow_target = None
            for flow_id, flow in flows_from_xor:
                # Find the corresponding flow in diagbp.json
                diagbp_flow = next((item for item in self.loader.extra_data['sequenceFlows'] if item['elementId'] == flow_id), None)
                if diagbp_flow is not None:
                    node_probabilities[flow['targetRef']] = float(diagbp_flow['executionProbability'])
                    # Check if 'types' field exists and if it matches with self.instance_type (to force the current instance into his xor based on the instance type)
                    if 'types' in diagbp_flow:
                    #if diagbp_flow['types']:

                        # add by LR
                        print("Target: ", flow['targetRef'])
                        print("Diag Flow: ", diagbp_flow['types'])
                        bool_red = False
                        for type_dict in diagbp_flow['types']:
                            bool_red = False
                            print("Type dict: ", type_dict['type'])
                            print("Instance Types: ", self.instance_type)
                            if type_dict['type'] == self.instance_type:
                                forced_flow_target = flow['targetRef']
                                redistribute_probabilities = False
                                bool_red = False
                                break
                            else:
                                bool_red = True
                        if bool_red:
                            #del node_probabilities[flow['targetRef']]
                            node_probabilities_to_delete[flow['targetRef']] = float(diagbp_flow['executionProbability'])
                            redistribute_probabilities = True
                    #else:
                    #    node_probabilities[flow['targetRef']] = float(diagbp_flow['executionProbability'])
                if forced_flow_target is not None:
                    break

            # add by LR
            print("Node Probabilities: ", node_probabilities)
            print("Forced Flow Target: ", forced_flow_target)
            if redistribute_probabilities:
                print("Redistribute Probabilities: \n")
                print(node_probabilities_to_delete)

                for key in node_probabilities_to_delete:
                    if key in node_probabilities:
                        del node_probabilities[key]

                remaining_sum = sum(node_probabilities.values())
                print("Remaining Sum: ", remaining_sum)

                for key in node_probabilities:
                    node_probabilities[key] = round(node_probabilities[key] / remaining_sum, 2)
                
                rounded_sum = sum(node_probabilities.values())
                print("Rounded Sum: ", rounded_sum)

                if rounded_sum != 1:
                    first_key = list(node_probabilities.keys())[0]
                    node_probabilities[first_key] += (1 - rounded_sum)

                print("New Node Probabilities: ", node_probabilities)
            
            # Check if node_probabilities is empty, if yes then the xor has only one next elem. else if there is a forced target use it, else pick it at random.
            if not node_probabilities:
                next_node_id = node['next'][0]
            elif forced_flow_target is not None:
                next_node_id = forced_flow_target
            else:
                next_node_id = np.random.choice(list(node_probabilities.keys()), p=list(node_probabilities.values()))
            self.xeslog(node_id,"complete",node['type'])
            self.printState(node,node_id,printFlag)
            yield from self.run_node(next_node_id, subprocess_node)


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
            flows_from_inclusive = [(flow_id, flow) for flow_id, flow in self.loader.process_data['sequenceFlows'].items() if flow['sourceRef'] == node_id]
            paths_to_take = []
            for flow_id, flow in flows_from_inclusive:
                type_matched = False
                diagbp_flow = next((item for item in self.loader.extra_data['sequenceFlows'] if item['elementId'] == flow_id), None)
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
                    yield self.env.timeout(1)

            self.xeslog(node_id,"start",node['type'])
            start_node_id = next(sub_node_id for sub_node_id, sub_node in node['subprocess_details'].items() if sub_node['type'] == 'startEvent')
            self.printState(node,node_id,printFlag)
            yield from self.run_node(start_node_id, node_id)

            self.executed_nodes[self.num].add(node_id)
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
            self.executed_nodes[self.num].add(node_id)
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
                        yield self.env.timeout(1)
                self.executed_nodes[self.num].add(node_id)
                self.xeslog(node_id,"complete",fullType)
                self.printState(node,node_id,printFlag)
                yield from self.run_node(next_node_id, subprocess_node)
                return
            else: #otherwise treats it as a timer event, whatever subtype it is
                next_node_id = node['next'][0]
                self.executed_nodes[self.num].add(node_id)
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
            waitedTimeInEventBasedGateway=0
            self.executed_nodes[self.num].add(node_id)
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
            while (not ready) and (smallestTimer is None or waitedTimeInEventBasedGateway < smallestTimer): #while no msg has been received and the smallest timer is not over yet
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
                yield self.env.timeout(1)
                waitedTimeInEventBasedGateway+=1

            self.printState(nextNode,next_node_id,printFlag) # print the state of the intermediate catch event (timer or msg, whatever)
            self.xeslog(next_node_id,"complete",nextNode['type'])        
            yield from self.run_node(nextNodeToVisit, subprocess_node) # now it visits the node 2 times forward (2 times after the eventBasedGateway) because the catches have already been handled
            return

        elif node['type'] == 'boundaryEvent': 
            self.printState(node,node_id,printFlag)
            self.xeslog(node_id,"complete",node['type'])
            self.executed_nodes[self.num].add(node_id)
            next_node_id = node['next'][0]
            yield from self.run_node(next_node_id, subprocess_node)
            return

        elif node['type'] == 'endEvent': 
            fullType = node['type'] + '/' + node['subtype'] if node['subtype'] is not None else node['type']
            self.executed_nodes[self.num].add(node_id)
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