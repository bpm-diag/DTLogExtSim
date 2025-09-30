import sys
from bpmn_processing_module.bpmn_handler import BPMNHandler
from simulator_engine_module.simulator_engine import SimulatorEngine
from support_modules.constants import CSV_FIELDS
import simpy
import parsingAgain
import timeCalculator
import pandas as pd
import pm4py
import os
import csv
import threading


def main(loader, csv_log_path):
    print("Starting Simulator Processing")

    logging_opt = loader.extra_data['logging_opt']
    logging_opt = (logging_opt == "1")

    num_instances = sum(int(instance['count']) for instance in loader.extra_data['processInstances'])
    print("NUM_INSTANCES: "+ str(num_instances))
    instance_types = loader.extra_data['processInstances']
    xor_probabilities = {flow['elementId']: float(flow['executionProbability']) for flow in loader.extra_data['sequenceFlows']}
    resources = loader.extra_data['resources']


    # Generate the delays, calling them delay is kinda wrong because delays is in fact an array of starting times, so like 0, 5, 10...
    delay_between_instances = loader.extra_data['arrivalRateDistribution'] #array contains: type, mean, arg1, arg2
    delays = [0]
    total_delay = 0
    for _ in range(num_instances-1):
        delay = timeCalculator.convert_to_seconds(delay_between_instances)
        total_delay += delay #each delay is therefore equal to itself + the previous delay
        delays.append(total_delay)
    
    env = simpy.Environment()

    def timeout_proc(simpy_resource,env,time):
        req = simpy_resource.request()
        yield req
        yield env.timeout(time)
        req.resource.release(req)
        print(f"Initial setup completed for resource {simpy_resource} at time {env.now}")
        # You can add more actions here if needed, such as updating resource state

    #resource_tuple is: simpyRes, cost, timetableName, lastInstanceType, setupTime, maxUsage, actualUsage, lock. Starts with actualUsage=MaxUsage so that it setups on first usage.
    global_resources = {}
    for res in resources:
        resource_list = []
        for _ in range(int(res['totalAmount'])):
            simpy_resource = simpy.Resource(env, capacity=1)
            if res["maxUsage"]=="":
                lastElement=""
            else:
                lastElement=simpy.Container(env, init=0, capacity=int(res['maxUsage']))
            resource_tuple = (
                simpy_resource, 
                res['costPerHour'], 
                res['timetableName'], 
                "", 
                res['setupTime'], 
                res['maxUsage'], 
                lastElement,
                threading.Lock()
            )
            resource_list.append(resource_tuple)

            # Create and start a timeout event for each individual resource
            if res['setupTime']['type']:
                time=timeCalculator.convert_to_seconds(res['setupTime'])
                env.process(timeout_proc(simpy_resource,env,time))

        global_resources[res['name']] = resource_list

    if not resources:
        global_resources = {}


    totalCost = {}
    timeUsedPerResource = {}
    extraLog = {}
    rows = []

    def simulate_bpmn(bpmn_dict):
        instance_index = 0
        instance_count = 0

        for i in range(num_instances):
            instance_type = instance_types[instance_index]['type']

            for participant_id, participant in bpmn_dict['collaboration']['participants'].items():
                process_details = bpmn_dict['process_elements'][participant['processRef']]

                print("PROCESS_DETAILS: ", process_details)
                print("NODE")
                for node_id, node in process_details['node_details'].items():
                    print(node_id)
                    print(node)
                    print("---")
                    
                # for each instance a class Process is created:
                SimulatorEngine(env, participant['name'], process_details,i+1, loader, global_resources, logging_opt,
                 totalCost, timeUsedPerResource, extraLog, rows, delays[i], instance_type)

            instance_count += 1
            if instance_count >= int(instance_types[instance_index]['count']):
                instance_index += 1
                instance_count = 0
        env.run()

    simulate_bpmn(loader.process_data)

    taskCosts={}
    resourcesPercentageUsage={}
    resourceCosts={}

    for key, value in totalCost.items():
        taskCosts[key]=value

    for name, time in timeUsedPerResource.items():
        total_amount = len(global_resources[name])  # Get the total number of individual resources for this type
        resourcesPercentageUsage[name] = f"{((time*100)/env.now)/total_amount:.1f}"


    for resource in resources:
        total_amount = float(resource["totalAmount"])
        cost_per_hour = float(resource["costPerHour"])
        time_in_hours = env.now / 3600  # Convert time to hours
        resource_cost = total_amount * cost_per_hour * time_in_hours
        name=resource['name']
        resourceCosts[name]=f"{resource_cost:.1f}"


    with open(csv_log_path, 'w') as f:
        writer = csv.writer(f)
        writer.writerow(CSV_FIELDS)
        writer.writerows(rows)

    dataframe = pd.read_csv(csv_log_path, sep=',')
    dataframe = dataframe.rename(columns={'status': 'lifecycle:transition'})
    dataframe = pm4py.format_dataframe(dataframe, case_id='traceId', activity_key='activity', timestamp_key='timestamp')
    event_log = pm4py.convert_to_event_log(dataframe)

    csv_file_extra = loader.simulation_path + "/logExtra.csv"
    combined_dict = {}
    for k, v in taskCosts.items():
        combined_dict[f'cost of the tasks of instance ({k})'] = v
    for k, v in resourceCosts.items():
        combined_dict[f'Total costs of resource ({k})'] = v
    for k, v in resourcesPercentageUsage.items():
        combined_dict[f'total usage of resource ({k}) in percentage'] = v

    if bool(extraLog):
        combined_dict.update(extraLog)

    all_keys = set(combined_dict.keys())

    # Write the combined dictionary to the CSV file
    with open(csv_file_extra, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=all_keys)
        writer.writeheader()
        writer.writerow(combined_dict)


    original_stdout = sys.stdout
    try:
        # Redirect sys.stdout to /dev/null to suppress the output
        sys.stdout = open(os.devnull, 'w')    
        # Call the pm4py.write_xes function
        pm4py.write_xes(event_log, loader.simulation_path + "/log.xes")
    finally:
        # Close the temporary file and restore the original stdout
        sys.stdout.close()
        sys.stdout = original_stdout

    print("Simulation completed")
    
    


if __name__ == "__main__":
    sys.setrecursionlimit(100000)

    simulation_path = sys.argv[1]
    simulation_no_ext = sys.argv[2]
    extra_path=simulation_path + "/extra.json"
    process_path=simulation_path + "/" + simulation_no_ext + ".json"
    csv_log_path=simulation_path + "/log.csv"

    parsingAgain.parse_again(process_path)

    loader = BPMNHandler(simulation_path, simulation_no_ext, extra_path, process_path)
    try:
        loader.load_configuration_files()
    except ValueError as e:
        print(f"-----ERROR-----: {e}")
        raise ValueError(e)
    try:
        main(loader, csv_log_path)
    except ValueError as e:
        print(f"-----ERROR-----: {e}")
        raise ValueError(e)

    