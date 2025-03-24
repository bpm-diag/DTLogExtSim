import pm4py
import pandas as pd
import numpy as np

input_file = '1.5-Hour Dataset.csv'
output_file = "1.5-Hour_lego_log"

data = pd.read_csv(input_file)

data = data[data["activity"] != "BLOCK"]
data = data[data["activity"] != "FAIL"]

data["trace_id"] = 0

last_trace_id = 0
for i in range (0, 12):
    current_trace_ids = {}
    for idx, row in data.iterrows():
        part_id = row["part_id"]
        if part_id == i+1:
            activity = row["activity"]
            station_id = row["station_id"]

            if activity == "LOAD" and station_id == 1:
                if part_id not in current_trace_ids:
                    current_trace_ids[part_id] = last_trace_id + 1
                    
                else:
                    current_trace_ids[part_id] += 1
                    last_trace_id = current_trace_ids[part_id]

            data.at[idx, "trace_id"] = current_trace_ids[part_id]
            
data["activity"] = data["activity"].replace({
    "LOAD": "assign",
    "PROCESS": "start",
    "UNLOAD": "complete"
})

data["time"] = pd.to_datetime(data["time"])
data["trace_id"] = data["trace_id"].astype(str)
data["station_id"] = data["station_id"].astype(str)
data["part_id"] = data["part_id"].astype(str)
data["org:resource"] = data.apply(
    lambda row: f"['res_{row['station_id']}']" if row['activity'] == 'complete' else np.nan, 
    axis=1
)
data["resourceCost"] = data.apply(
    lambda row: f"['1']" if row['activity'] == 'complete' else np.nan, 
    axis=1
)
data["nodeType"] = "task"
data["poolName"] = "main"
data["fixedCost"] = np.nan

data.rename(columns={
    "time": "time:timestamp",
    "station_id": "concept:name",
    "part_id": "instanceType",
    "activity": "lifecycle:transition",
    "trace_id": "case:concept:name"
}, inplace=True)


activity_order = {
    "assign": 0,
    "start": 1,
    "complete": 2
}
data["activity_order"] = data["lifecycle:transition"].map(activity_order)
data = data.sort_values(by=["case:concept:name", "time:timestamp", "concept:name", "activity_order"])

data = data.drop(columns=["activity_order"])

start_events = []
for trace_id in data["case:concept:name"].unique():
    trace_data = data[data["case:concept:name"] == trace_id]
    if not trace_data.empty:
        start_event = {
            "time:timestamp": trace_data["time:timestamp"].min(),
            "concept:name": "Start",
            "instanceType": trace_data["instanceType"].iloc[0],
            "lifecycle:transition": "complete",
            "case:concept:name": trace_id,
            "org:resource": np.nan,
            "nodeType": "startEvent",
            "resourceCost": np.nan,
            "poolName": "main",
            "fixedCost": np.nan
        }
        start_events.append(start_event)

data = pd.concat([pd.DataFrame(start_events), data], ignore_index=True)

end_events = []
for trace_id in data["case:concept:name"].unique():
    trace_data = data[data["case:concept:name"] == trace_id]
    if not trace_data.empty:
        last_row = trace_data.iloc[-1]
        if last_row["concept:name"] == "5" and last_row["lifecycle:transition"] == "complete":
            end_event = {
                "time:timestamp": trace_data["time:timestamp"].max(),
                "concept:name": "End",
                "instanceType": trace_data["instanceType"].iloc[0],
                "lifecycle:transition": "complete",
                "case:concept:name": trace_id,
                "org:resource": np.nan,
                "nodeType": "endEvent",
                "resourceCost": np.nan,
                "poolName": "main",
                "fixedCost": np.nan
            }
            end_events.append(end_event)

data = pd.concat([data, pd.DataFrame(end_events)], ignore_index=True)

pm4py.write_xes(data, output_file, case_id_key='case:concept:name')
        