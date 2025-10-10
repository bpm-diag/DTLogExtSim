# Functions to parse the XES file and extract data in a list of dictionaries format in order to be visualized in the frontend,
# which will be then converted and analyzed in a Pandas DataFrame.
import xmltodict
from json import dumps,loads
import pandas as pd
import xml.etree.ElementTree as ET
from typing import List, Dict, Iterable, Tuple
import statistics as _stats
from collections import defaultdict

# ------------- funzioni per leggere i file xes e convertirli in un formato che poi viene convertito in un dataframe -----------------
def get_one_event_dict(one_event, case_name, data_types):

    one_event_attri = list(one_event.keys())

    one_event_dict = {}
    for i in data_types:
        if i in one_event_attri:
            if type(one_event[i]) == list:
                for j in one_event[i]:
                    if isinstance(j, dict) and '@key' in j and '@value' in j:
                        one_event_dict[j['@key']] = j['@value']
            elif isinstance(one_event[i], dict):
                if '@key' in one_event[i] and '@value' in one_event[i]:
                    one_event_dict[one_event[i]['@key']] = one_event[i]['@value']
    one_event_dict['case_name'] = case_name
    return one_event_dict

def gain_one_trace_info(one_trace,data_types):
    # for the attributer
    one_trace_attri = list(one_trace.keys())
    one_trace_attri_dict = {}

    for i in data_types:
        if i in one_trace_attri:
            if type(one_trace[i]) == list:
                for j in one_trace[i]:
                    one_trace_attri_dict[j['@key']] = j['@value']
            else:
                one_trace_attri_dict[one_trace[i]['@key']] = one_trace[i]['@value']

    # for event seq
    one_trace_events = []
    if type(one_trace['event']) == dict:
        one_trace['event'] = [one_trace['event']]

    for i in one_trace['event']:
        inter_event = get_one_event_dict(i, one_trace_attri_dict['concept:name'],data_types)
        one_trace_events.append(inter_event)

    return one_trace_attri_dict,one_trace_events

def gain_log_info_table(xml_string):
    data_types = ['string', 'int', 'date', 'float', 'boolean', 'id']

    log_is = xmltodict.parse(xml_string)
    log_is = loads(dumps(log_is))

    traces = log_is['log']['trace']

    # Normalizza: se c'è solo una trace, rendila lista
    if isinstance(traces, dict):
        traces = [traces]
        
    trace_attri = []
    trace_event = []
    j = 0
    for i in traces:
        inter = gain_one_trace_info(i,data_types)
        trace_attri.append(inter[0])
        trace_event = trace_event + inter[1]
        j = j +1
        #print(j)
    return trace_attri, trace_event
# ---------------------------------------------------------------------------------------------------------------------------------
# ---------- function to clean and extract meaningful data from the log in a dataframe ---------------------------------------
def parse_and_clean_dataframe(xml_string: str) -> pd.DataFrame:
    trace_attri, trace_events = gain_log_info_table(xml_string)
    df = pd.DataFrame(trace_events)

    # convertire i timestamp in datetime
    # df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce', utc=True)
    df['timestamp'] = pd.to_datetime(df['timestamp'], format='ISO8601')#, errors='coerce')
    df['timestamp'] = df['timestamp'].dt.floor('s')
    df['timestamp'] = df['timestamp'].dt.tz_convert(None)
        # convertire i timestamp in datetime
    
   
  
    df = df.dropna(subset=['timestamp'])
    # drop duplicate columns
    df = df.drop(columns=['case_name', 'concept:name', 'time:timestamp'], axis=1)

    return df
# -------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------------ function to compute the simulation summary -----------------------------------------------------
def compute_simulation_summary(df) -> dict:
    """
    Ritorna:
    - numero totale di traceId
    - insieme dei poolName distinti
    """
    total_traces = df['traceId'].nunique()
    unique_pools = sorted(set(df['poolName'].dropna()))

    return {
        "total_traces": total_traces,
        "unique_pools": unique_pools
    }
def compute_cost_summary_by_item(df) -> list[dict]:
    df = df.copy()

    def parse_costs(row):
        rc = row.get('resourceCost')
        try:
            rc_list = eval(rc) if isinstance(rc, str) else []
            rc_sum = sum(float(x) for x in rc_list)
        except:
            rc_sum = 0.0

        try:
            fixed_raw = row.get('fixedCost', 0)
            fixed = float(fixed_raw) if fixed_raw not in [None, '', 'nan'] else 0.0
        except:
            fixed = 0.0

        return rc_sum + fixed
    
    df['totalCost'] = df.apply(parse_costs, axis=1)

    trace_totals = df.groupby(['traceId', 'instanceType'])['totalCost'].sum().reset_index()
    summary = trace_totals.groupby('instanceType')['totalCost'].agg(['mean', 'sum']).reset_index()
    summary = summary.rename(columns={'mean': 'avg_item_cost', 'sum': 'total_item_cost'})

    return summary.to_dict(orient="records")

def compute_execution_duration_by_instance(df) -> list[dict]:
    """
    Calcola la durata totale (in minuti) di esecuzione per ogni instanceType,
    come differenza tra ultimo e primo timestamp per traceId.
    """
    df = df.copy()

    if 'timestamp' not in df.columns or 'instanceType' not in df.columns or 'traceId' not in df.columns:
        return []

    # Calcolo inizio e fine per ogni trace
    durations = (
        df.groupby(['traceId', 'instanceType'])['timestamp']
        .agg(['min', 'max'])
        .reset_index()
    )

    durations['duration_minutes'] = (durations['max'] - durations['min']).dt.total_seconds() / 60

    # Somma totale per instanceType
    result = (
        durations.groupby('instanceType')['duration_minutes']
        .sum()
        .reset_index()
        .rename(columns={'duration_minutes': 'total_execution_minutes'})
    )

    return result.to_dict(orient='records')

# -------------------------------------------------------------------------------------------------------------------------------------
# --------------function to extract the CYCLE TIME of each activity in the log---------------------------------------------------------------
def compute_activity_durations(df) -> list[dict] | None:
    """
    Calcola durata media, minima, massima (in ore) delle attività basate su assign/complete per ogni traceId.

    Args:
        df (pd.DataFrame): DataFrame con colonne 'activity', 'traceId', 'lifecycle:transition', 'timestamp'
        top_n (int): Numero massimo di attività da restituire

    Returns:
        list[dict]: Lista di dizionari per ogni attività (media, min, max, traceId min/max)
    """
    required_transitions = {'assign', 'complete'}
    present_transitions = set(df['lifecycle:transition'].unique())

    if not required_transitions.issubset(present_transitions):
        return None  
    # raggruppare il dataframe per attività, lifecycle:transition e traceId
    activities = df.groupby(['activity', 'lifecycle:transition', 'traceId'])[['timestamp', 'org:resource', 'fixedCost',	'resourceCost', 'instanceType']].first().reset_index()

    # selezionare solo le righe con transition 'assign' o 'complete'
    df_filtered = activities[activities['lifecycle:transition'].isin(['assign', 'complete'])]

    #pivot: una riga per ogni (activity, traceId), con due colonne: assign e complete
    df_pivot = df_filtered.pivot_table(
        index=['activity', 'traceId'],
        columns='lifecycle:transition',
        values='timestamp',
        aggfunc='first'  # oppure 'min' se ci sono più valori
    ).reset_index()

    # calcolare la durata della singola attività per ogni traceId
    df_pivot['duration'] = (df_pivot['complete'] - df_pivot['assign']).dt.total_seconds()/(60*60) # in ore

    # calcolare durata media, min, max per ogni attività
    agg_stats = df_pivot.groupby('activity').agg(
        avg_duration=('duration', 'mean'),
        min_duration=('duration', 'min'),
        max_duration=('duration', 'max')
    ).reset_index()

    # Filtrare righe valide (dove la duration è definita)
    valid_rows = df_pivot[df_pivot['duration'].notna()]
    # Trovare traceId per cui la durata è min e max
    min_trace = valid_rows.loc[valid_rows.groupby('activity')['duration'].idxmin()][['activity', 'traceId']].rename(columns={'traceId': 'min_traceId'})
    max_trace = valid_rows.loc[valid_rows.groupby('activity')['duration'].idxmax()][['activity', 'traceId']].rename(columns={'traceId': 'max_traceId'})

    agg_stats = agg_stats.merge(min_trace, on='activity').merge(max_trace, on='activity')

    return agg_stats.to_dict(orient='records')
# -------------------------------------------------------------------------------------------------------------------------------------
# ---------------------------- function to confront the cycle time and the waiting time of each activity in the log-----------------------------------
def compute_time_breakdown(df) -> list[dict] | None:
    required_transitions = {'assign', 'complete', 'start'}
    present_transitions = set(df['lifecycle:transition'].unique())

    if not required_transitions.issubset(present_transitions):
        return None  

    filtered = df[df['lifecycle:transition'].isin(['start', 'complete', 'assign'])]

    pivoted = filtered.pivot_table(
        index=['activity', 'traceId'],
        columns='lifecycle:transition',
        values='timestamp',
        aggfunc='first'
    ).reset_index()

    pivoted.columns.name = None

    pivoted['cycle_time'] = (pivoted['complete'] - pivoted['assign']).dt.total_seconds() / 3600
    pivoted['waiting_time'] = (pivoted['start'] - pivoted['assign']).dt.total_seconds() / 3600
    pivoted['processing_time'] = (pivoted['complete'] - pivoted['start']).dt.total_seconds() / 3600

    valid_rows = pivoted.dropna(subset=['cycle_time', 'waiting_time', 'processing_time'])

    agg = valid_rows.groupby('activity').agg(
        avg_cycle_time=('cycle_time', 'mean'),
        avg_waiting_time=('waiting_time', 'mean'),
        avg_processing_time=('processing_time', 'mean')
    ).reset_index()

    agg = agg.sort_values(by='avg_cycle_time', ascending=False)

    return agg.to_dict(orient='records')
# ------------------------------ function to analyze bottlenecks in the simulation-----------------------------------------------------
def compute_bottleneck_heatmap(df) -> list[dict] | None:

    if df is None or df.empty:
        return []

    # serve almeno 'complete' per definire l'uscita da A
    present = set(df['lifecycle:transition'].unique())
    if 'complete' not in present:
        return None

    KEEP = {'assign', 'start', 'complete'}
    df2 = df[df['lifecycle:transition'].isin(KEEP)].copy()

    # Timestamp robusti: se non sono datetime, parse + normalizzazione
    if not pd.api.types.is_datetime64_any_dtype(df2['timestamp']):
        df2['timestamp'] = pd.to_datetime(df2['timestamp'], errors='coerce', utc=True)
        df2 = df2.dropna(subset=['timestamp'])
        df2['timestamp'] = df2['timestamp'].dt.tz_convert(None)

    # Ordine stabile dentro la trace (risolve pareggi di timestamp)
    df2 = df2.sort_values(['traceId', 'timestamp', 'activity', 'lifecycle:transition'])

    rows = []
    for trace_id, g in df2.groupby('traceId', sort=False):
        evs = g[['activity', 'lifecycle:transition', 'timestamp']].to_numpy()
        n = len(evs)
        for i in range(n):
            a_i, tr_i, t_i = evs[i]
            if tr_i != 'complete':
                continue  # usciamo da A quando completa
            # cerca il PRIMO evento della prossima attività B (diversa da A)
            to_act, to_ts = None, None
            for j in range(i + 1, n):
                a_j, tr_j, t_j = evs[j]
                if a_j == a_i:
                    continue
                if tr_j in KEEP:
                    to_act, to_ts = a_j, t_j
                    break
            if to_act is None:
                continue

            wait_min = (pd.Timestamp(to_ts) - pd.Timestamp(t_i)).total_seconds() / 60.0
            if wait_min >= 0:
                rows.append((str(a_i), str(to_act), float(wait_min)))

    if not rows:
        return []

    # Media per coppia A→B su tutte le trace (ordinamento decrescente per attese)
    res = (
        pd.DataFrame(rows, columns=['activity', 'next_activity', 'wait_time'])
          .groupby(['activity', 'next_activity'], as_index=False)['wait_time']
          .mean()
          .sort_values('wait_time', ascending=False)
    )

    return res.to_dict(orient='records')

# ============== BPMN parsing per coppie ammesse (e mapping sequenceFlow) ==============
_BPMN_NS = {
    'bpmn': 'http://www.omg.org/spec/BPMN/20100524/MODEL',
    'bpmndi': 'http://www.omg.org/spec/BPMN/20100524/DI',
    'di': 'http://www.omg.org/spec/DD/20100524/DI',
    'dc': 'http://www.omg.org/spec/DD/20100524/DC'
}

def compute_activity_pairs_from_bpmn_xml(xml_string: str) -> Tuple[List[Dict], Dict[Tuple[str, str], List[str]]]:
    """
    Ritorna:
      - allowed_pairs: [{'activity': <label sorgente>, 'next_activity': <label destinazione>}]
      - flow_ids_map:  { (label_src, label_tgt): [sequenceFlowId, ...], ... }
    Usa il name se presente, altrimenti l'ID dell'elemento.
    """
    root = ET.fromstring(xml_string)

    # Mappa id -> label leggibile
    label_by_id: Dict[str, str] = {}
    node_tags = [
        'task','userTask','serviceTask','scriptTask','manualTask','receiveTask','sendTask','businessRuleTask',
        'startEvent','endEvent','intermediateThrowEvent','intermediateCatchEvent',
        'exclusiveGateway','inclusiveGateway','parallelGateway','eventBasedGateway','complexGateway',
        'subProcess','callActivity'
    ]
    for tag in node_tags:
        for el in root.findall(f'.//bpmn:{tag}', _BPMN_NS):
            _id = el.get('id')
            label_by_id[_id] = el.get('name') or _id

    allowed_pairs: List[Dict] = []
    flow_ids_map: Dict[Tuple[str, str], List[str]] = {}

    # Estrai tutte le sequenceFlow
    for sf in root.findall('.//bpmn:sequenceFlow', _BPMN_NS):
        src_id = sf.get('sourceRef')
        tgt_id = sf.get('targetRef')
        sf_id  = sf.get('id')
        if not src_id or not tgt_id or not sf_id:
            continue

        src_label = label_by_id.get(src_id, src_id)
        tgt_label = label_by_id.get(tgt_id, tgt_id)

        allowed_pairs.append({'activity': src_label, 'next_activity': tgt_label})

        key = (src_label, tgt_label)
        flow_ids_map.setdefault(key, []).append(sf_id)

    # Dedup preservando ordine
    seen = set()
    dedup_pairs = []
    for p in allowed_pairs:
        t = (p['activity'], p['next_activity'])
        if t in seen: 
            continue
        seen.add(t)
        dedup_pairs.append(p)

    return dedup_pairs, flow_ids_map

def compute_bottleneck_heatmap_bpmn_only(
    df: pd.DataFrame,
    allowed_pairs: Iterable[Dict[str, str]],
    *,
    transitions_considered: Tuple[str, ...] = ('assign', 'start', 'complete'),
    fill_missing_with_zero: bool = True
) -> List[Dict]:
    """
    Calcola il tempo medio di attraversamento A→B SOLO per coppie presenti nel BPMN.
    - Tempo per trace: dal 'complete' di A al primo evento di B successivo (tra transitions_considered).
    - Media su trace dove A→B è osservata.
    - Se fill_missing_with_zero=True, include TUTTE le coppie ammesse con wait_time=0.0 se mai osservate.
    Output: [{'activity','next_activity','wait_time'}]
    """
    if df is None or df.empty:
        return ([{'activity': p['activity'], 'next_activity': p['next_activity'], 'wait_time': 0.0}
                 for p in allowed_pairs] if fill_missing_with_zero else [])

    if 'lifecycle:transition' not in df.columns or 'complete' not in set(df['lifecycle:transition'].unique()):
        return ([{'activity': p['activity'], 'next_activity': p['next_activity'], 'wait_time': 0.0}
                 for p in allowed_pairs] if fill_missing_with_zero else [])

    KEEP = set(transitions_considered)
    df2 = df[df['lifecycle:transition'].isin(KEEP)].copy()

    if not pd.api.types.is_datetime64_any_dtype(df2['timestamp']):
        df2['timestamp'] = pd.to_datetime(df2['timestamp'], errors='coerce', utc=True)
        df2 = df2.dropna(subset=['timestamp'])
        df2['timestamp'] = df2['timestamp'].dt.tz_convert(None)

    df2 = df2.sort_values(['traceId', 'timestamp', 'activity', 'lifecycle:transition'])

    allowed_set = {(str(p['activity']), str(p['next_activity'])) for p in allowed_pairs}

    rows = []
    for trace_id, g in df2.groupby('traceId', sort=False):
        evs = g[['activity', 'lifecycle:transition', 'timestamp']].to_numpy()
        n = len(evs)
        for i in range(n):
            a_i, tr_i, t_i = evs[i]
            if tr_i != 'complete':
                continue
            to_act, to_ts = None, None
            for j in range(i + 1, n):
                a_j, tr_j, t_j = evs[j]
                if a_j == a_i:
                    continue
                if tr_j in KEEP and (str(a_i), str(a_j)) in allowed_set:
                    to_act, to_ts = a_j, t_j
                    break
            if to_act is None:
                continue

            wait_min = (pd.Timestamp(to_ts) - pd.Timestamp(t_i)).total_seconds() / 60.0
            if wait_min >= 0:
                rows.append((str(a_i), str(to_act), float(wait_min)))

    if not rows:
        return (
            [{'activity': a, 'next_activity': b, 'wait_time': 0.0}
             for (a, b) in allowed_set]
            if fill_missing_with_zero else []
        )

    res = (
        pd.DataFrame(rows, columns=['activity', 'next_activity', 'wait_time'])
          .groupby(['activity', 'next_activity'], as_index=False)['wait_time']
          .mean()
    )

    if fill_missing_with_zero:
        full = pd.DataFrame(list(allowed_set), columns=['activity', 'next_activity'])
        res = full.merge(res, on=['activity', 'next_activity'], how='left')
        res['wait_time'] = res['wait_time'].fillna(0.0)

    res = res.sort_values('wait_time', ascending=False, kind='mergesort')

    return res.to_dict(orient='records')

# -------------------------------------------------------------------------------------------------------------------------------------
# ------------------- Function to compute fixed, variable and average costs by activity  ------------------------
def compute_activity_costs_stacked(df) -> list[dict]:
    """
    Calcola i costi medi fissi, variabili e totali per ogni attività.
    Ritorna: lista di dizionari con chiavi: activity, avg_fixed_cost, avg_variable_cost, avg_total_cost.
    """
    df = df.copy()

    def parse_costs(row):
        # Costi variabili (da lista di stringhe in float)
        resource_costs = row.get('resourceCost')
        if isinstance(resource_costs, str):
            try:
                resource_costs = eval(resource_costs)
            except:
                resource_costs = []
        if isinstance(resource_costs, list):
            try:
                resource_costs = [float(x) for x in resource_costs]
            except:
                resource_costs = []
        var_cost = sum(resource_costs)

        # Costi fissi
        try:
            fixed = float(row.get('fixedCost', 0))
        except:
            fixed = 0.0

        return pd.Series({'fixedCostFloat': fixed, 'variableCost': var_cost})

    df[['fixedCostFloat', 'variableCost']] = df.apply(parse_costs, axis=1)

    # Raggruppare per attività e traceId -> somma dei costi totali
    grouped = df.groupby(['activity', 'traceId'])[['fixedCostFloat', 'variableCost']].sum().reset_index()

    # Conversione esplicita per sicurezza
    grouped['fixedCostFloat'] = pd.to_numeric(grouped['fixedCostFloat'], errors='coerce')
    grouped['variableCost'] = pd.to_numeric(grouped['variableCost'], errors='coerce')

    # Media dei costi per attività
    summary = grouped.groupby('activity')[['fixedCostFloat', 'variableCost']].mean().reset_index()
    summary['avg_total_cost'] = summary['fixedCostFloat'] + summary['variableCost']

    return summary.rename(columns={
        'fixedCostFloat': 'avg_fixed_cost',
        'variableCost': 'avg_variable_cost'
    }).to_dict(orient='records')
# -------------------------------------------------------------------------------------------------------------------------------------
# ---------------- function to compare the production cost of each instance Type in average for each traceId by summing the cost of each activity --------------
def compute_item_costs(df) -> list[dict]:
    """
    Calcola il costo totale per ogni traceId (somma dei costi attività),
    poi la media per ogni instanceType (item).
    """
    df = df.copy()

    def parse_costs(row):
        rc = row.get('resourceCost')
        try:
            rc_list = eval(rc) if isinstance(rc, str) else []
            rc_sum = sum(float(x) for x in rc_list)
        except:
            rc_sum = 0.0

        try:
            fixed_raw = row.get('fixedCost', 0)
            fixed = float(fixed_raw) if fixed_raw not in [None, '', 'nan'] else 0.0
        except:
            fixed = 0.0

        return rc_sum + fixed

    df['totalCost'] = df.apply(parse_costs, axis=1)

    # Somma totale per traceId
    trace_totals = df.groupby(['traceId', 'instanceType'])['totalCost'].sum().reset_index()

    # Media per instanceType
    item_costs = trace_totals.groupby('instanceType')['totalCost'].agg(['mean', 'sum']).reset_index()
    item_costs = item_costs.rename(columns={'mean': 'avg_item_cost', 'sum': 'total_item_cost'})

    return item_costs.to_dict(orient='records')
# -------------------------------------------------------------------------------------------------------------------------------------
# function to compute the duration of each instance type in average for each traceId by summing the duration of each activity
def compute_avg_duration_per_item(df) -> list[dict]:
    """
    Calcola la durata media per ogni instanceType (item),
    come differenza tra primo e ultimo timestamp per ogni traceId.
    """
    df = df.copy()

    if 'timestamp' not in df.columns or 'instanceType' not in df.columns or 'traceId' not in df.columns:
        return []

    # Calcolo inizio/fine per ogni trace
    durations = (
        df.groupby(['traceId', 'instanceType'])['timestamp']
        .agg(['min', 'max'])
        .reset_index()
    )

    durations['duration_minutes'] = (durations['max'] - durations['min']).dt.total_seconds() / 60

    # Media per instanceType
    result = (
        durations.groupby('instanceType')['duration_minutes']
        .mean()
        .reset_index()
        .rename(columns={'duration_minutes': 'avg_duration_minutes'})
    )

    return result.to_dict(orient='records')
# -------------------------------------------------------------------------------------------------------------------------------------
# ------------------------------ function to count the resource count and cost ------------------------------------
def compute_resource_bubble_data(df) -> list[dict]:
    """
    Restituisce per ogni risorsa:
    - total_usage: numero totale di utilizzi (su tutti i traceId)
    - avg_cost: costo medio per utilizzo
    """
    import ast
    from collections import defaultdict

    resource_usage = defaultdict(int)
    resource_costs = defaultdict(list)

    for _, row in df.iterrows():
        res_raw = row.get('org:resource')
        cost_raw = row.get('resourceCost')

        if pd.isna(res_raw) or pd.isna(cost_raw):
            continue

        try:
            resources = ast.literal_eval(res_raw)
            costs = ast.literal_eval(cost_raw)
            if not isinstance(resources, list) or not isinstance(costs, list):
                continue
        except:
            continue

        for i, res in enumerate(resources):
            if i >= len(costs): continue
            try:
                cost = float(costs[i])
            except:
                continue
            resource_usage[res] += 1
            resource_costs[res].append(cost)

    result = []
    for res in resource_usage:
        avg_cost = sum(resource_costs[res]) / len(resource_costs[res]) if resource_costs[res] else 0
        result.append({
            "resource": res,
            "usage_count": resource_usage[res],
            "avg_cost": avg_cost
        })

    return result
# -------------------------------------------------------------------------------------------------------------------------------------
# === WHAT-IF HELPERS: calcolo KPI per run singola e media su N run ==================

def _compute_metrics_for_df(df: pd.DataFrame, *, bpmn_xml: str | None = None):
    """
    Calcola le KPI di UNA run (un singolo file XES) riutilizzando le funzioni esistenti.
    Ritorna un dict compatibile con /all-graphs/.
    """
    allowed_pairs = None
    flow_ids_map = {}
    if bpmn_xml:
        allowed_pairs, flow_ids_map = compute_activity_pairs_from_bpmn_xml(bpmn_xml)

    durations = compute_activity_durations(df)
    breakdown = compute_time_breakdown(df)

    if allowed_pairs:
        bottleneck = compute_bottleneck_heatmap_bpmn_only(df, allowed_pairs)
        # sequenceFlowIds (se mapping presente)
        for row in bottleneck:
            key = (str(row['activity']), str(row['next_activity']))
            row['sequenceFlowIds'] = flow_ids_map.get(key, [])
    else:
        bottleneck = compute_bottleneck_heatmap(df)

    costs = compute_activity_costs_stacked(df)
    item_costs = compute_item_costs(df)
    item_duration = compute_avg_duration_per_item(df)
    res_bubble = compute_resource_bubble_data(df)

    return {
        "simulation_summary": {
            **compute_simulation_summary(df),
            "costs_by_item": compute_cost_summary_by_item(df),
            "execution_by_item": compute_execution_duration_by_instance(df)
        },
        "durations": durations or [],
        "breakdown": breakdown or [],
        "bottleneck": bottleneck or [],
        "costs": costs or [],
        "itemCosts": item_costs or [],
        "itemDurations": item_duration or [],
        "resource_bubble": res_bubble or [],
    }

def _mean_over_dict_list(list_of_dicts, key_fields, mean_fields, *, fill_missing_zero=True):
    """
    Media per-chiave su liste di dizionari.
    - key_fields: tuple di chiavi (es. ('activity',) oppure ('activity','next_activity'))
    - mean_fields: campi numerici da mediare (es. ['avg_duration','min_duration','max_duration'])
    - fill_missing_zero: se una chiave manca in alcune run, considera 0 per quei campi (utile per bottleneck).
    """
    buckets = defaultdict(lambda: defaultdict(list))

    # raccoglie valori per ciascuna chiave
    for rows in list_of_dicts:
        # mappa rapida chiave -> record per questa run
        index = {tuple(str(r[k]) for k in key_fields): r for r in rows}
        # chiavi globali: unione di tutte le chiavi viste finora e in questa run
        all_keys = set(buckets.keys()) | set(index.keys())
        for k in all_keys:
            rec = index.get(k)
            for f in mean_fields:
                if rec is not None and f in rec and rec[f] is not None:
                    try:
                        val = float(rec[f])
                    except:
                        val = 0.0
                    buckets[k][f].append(val)
                else:
                    if fill_missing_zero:
                        buckets[k][f].append(0.0)

    # calcola media
    out = []
    for k, field_lists in buckets.items():
        new_rec = {}
        for i, key_name in enumerate(key_fields):
            new_rec[key_name] = k[i]
        for f, values in field_lists.items():
            new_rec[f] = float(_stats.mean(values)) if values else 0.0
        out.append(new_rec)
    return out

def aggregate_runs_metrics(metrics_list: list[dict]) -> dict:
    """
    Media le KPI su N run (ognuna è il dict prodotto da _compute_metrics_for_df).
    Politiche:
    - 'durations': media di avg/min/max per attività (average of averages).
    - 'breakdown': media di avg_* per attività.
    - 'bottleneck': media di wait_time su (activity,next_activity) con fill_missing_zero=True (grafici stabili).
    - 'costs': media di avg_fixed_cost, avg_variable_cost, avg_total_cost per attività.
    - 'itemCosts': media di avg_item_cost e total_item_cost per instanceType (average of totals inteso per run).
    - 'itemDurations': media di avg_duration_minutes per instanceType.
    - 'resource_bubble': media di usage_count e avg_cost per resource (nota: usage_count medio ha senso come “attività media”).
    - 'simulation_summary': total_traces medio e unione degli unique_pools; gli altri due campi sono combinati
      mediando per key uguale.
    """
    if not metrics_list:
        return {
            "simulation_summary": {"total_traces": 0, "unique_pools": []},
            "durations": [], "breakdown": [], "bottleneck": [], "costs": [],
            "itemCosts": [], "itemDurations": [], "resource_bubble": []
        }

    # durations
    durations = _mean_over_dict_list(
        [m.get("durations", []) for m in metrics_list],
        key_fields=("activity",),
        mean_fields=["avg_duration", "min_duration", "max_duration"]
    )

    # breakdown
    breakdown = _mean_over_dict_list(
        [m.get("breakdown", []) for m in metrics_list],
        key_fields=("activity",),
        mean_fields=["avg_cycle_time", "avg_waiting_time", "avg_processing_time"]
    )

    # bottleneck
    def _aggregate_bottleneck_with_flowids(metrics_list: list[dict]) -> list[dict]:
        from collections import defaultdict
        import statistics as _stats

        waits = defaultdict(list)         # (act,next) -> [wait_time,...]
        flowids = defaultdict(set)        # (act,next) -> set(flowId)

        for m in metrics_list:
            for row in m.get("bottleneck", []):
                a = str(row.get("activity"))
                b = str(row.get("next_activity"))
                key = (a, b)
                wt = row.get("wait_time", 0) or 0
                try:
                    wt = float(wt)
                except:
                    wt = 0.0
                waits[key].append(wt)

                # raccogli tutti i sequenceFlowIds osservati nelle run
                for fid in row.get("sequenceFlowIds", []) or []:
                    flowids[key].add(str(fid))

        out = []
        for (a, b), arr in waits.items():
            out.append({
                "activity": a,
                "next_activity": b,
                "wait_time": float(_stats.mean(arr)) if arr else 0.0,
                "sequenceFlowIds": sorted(list(flowids[(a, b)])),
            })
        return out
    bottleneck = _aggregate_bottleneck_with_flowids(metrics_list)



    # costs
    costs = _mean_over_dict_list(
        [m.get("costs", []) for m in metrics_list],
        key_fields=("activity",),
        mean_fields=["avg_fixed_cost","avg_variable_cost","avg_total_cost"]
    )

    # itemCosts (per instanceType)
    item_costs = _mean_over_dict_list(
        [m.get("itemCosts", []) for m in metrics_list],
        key_fields=("instanceType",),
        mean_fields=["avg_item_cost","total_item_cost"]
    )

    # itemDurations
    item_durations = _mean_over_dict_list(
        [m.get("itemDurations", []) for m in metrics_list],
        key_fields=("instanceType",),
        mean_fields=["avg_duration_minutes"]
    )

    # resource_bubble
    resource_bubble = _mean_over_dict_list(
        [m.get("resource_bubble", []) for m in metrics_list],
        key_fields=("resource",),
        mean_fields=["usage_count","avg_cost"]
    )

    # simulation_summary (media di total_traces, unione unique_pools; media for key on costs_by_item, execution_by_item)
    # total_traces
    tt_vals = [m["simulation_summary"].get("total_traces", 0) for m in metrics_list]
    total_traces_mean = int(round(_stats.mean(tt_vals))) if tt_vals else 0
    # unique_pools: unione
    pools = set()
    for m in metrics_list:
        pools.update(m["simulation_summary"].get("unique_pools", []))
    unique_pools = sorted(pools)
    # costs_by_item / execution_by_item
    costs_by_item = _mean_over_dict_list(
        [m["simulation_summary"].get("costs_by_item", []) for m in metrics_list],
        key_fields=("instanceType",),
        mean_fields=["avg_item_cost","total_item_cost"]
    )
    execution_by_item = _mean_over_dict_list(
        [m["simulation_summary"].get("execution_by_item", []) for m in metrics_list],
        key_fields=("instanceType",),
        mean_fields=["total_execution_minutes"]
    )

    return {
        "simulation_summary": {
            "total_traces": total_traces_mean,
            "unique_pools": unique_pools,
            "costs_by_item": costs_by_item,
            "execution_by_item": execution_by_item
        },
        "durations": durations,
        "breakdown": breakdown,
        "bottleneck": bottleneck,
        "costs": costs,
        "itemCosts": item_costs,
        "itemDurations": item_durations,
        "resource_bubble": resource_bubble
    }

# per i grafici “duration/breakdown/costi per attività” si fa la media delle medie (e delle min/max riportate da ciascuna run).