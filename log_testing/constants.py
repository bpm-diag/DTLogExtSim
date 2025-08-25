# support_modules/constants.py
"""
Costanti per i tag utilizzati nei file XES e nel processamento dei log.
Centralizza tutti i tag per facilitare manutenzione e modifiche.
"""

# Tag principali per identificare elementi nei log XES
TAG_ACTIVITY_NAME = 'concept:name'
TAG_RESOURCE = 'org:resource'
TAG_TRACE_ID = 'case:concept:name'
TAG_TIMESTAMP = 'time:timestamp'
TAG_LIFECYCLE = 'lifecycle:transition'
TAG_NODE_TYPE = 'nodeType'
TAG_POOL = 'poolName'
TAG_COST_HOUR = 'resourceCost'
TAG_FIXED_COST = 'fixedCost'
TAG_INSTANCE_TYPE = 'instanceType'
TAG_ACTIVITY_ID = 'elementId'

# Tag aggiunti per analisi avanzate
TAG_MOMENT_OF_DAY = 'moment_of_day'
TAG_TIME_SLOT = 'time_slot'
TAG_GROUP = 'group'

# Valori del ciclo di vita delle attività
LIFECYCLE_ASSIGN = 'assign'
LIFECYCLE_START = 'start'
LIFECYCLE_COMPLETE = 'complete'
LIFECYCLE_START_SETUP = 'startSetupTime'
LIFECYCLE_END_SETUP = 'endSetupTime'

# Tipi di nodi per log diagnostici
NODE_TYPE_START = 'startEvent'
NODE_TYPE_END = 'endEvent'

# Pattern per identificare attività di start/end in log normali
PATTERN_START = r'Start|START|start'
PATTERN_END = r'End|END|end|abort|ABORT'

# Soglie di default
DEFAULT_SIM_THRESHOLD_DIAG = 0.9
DEFAULT_SIM_THRESHOLD_NORMAL = 0.5

# Configurazioni per tipi di timestamp
TIMESTAMP_CONFIG = {
    'COMPLETE_ONLY': 1,
    'START_COMPLETE': 2, 
    'ASSIGN_START_COMPLETE': 3
}

# Directory di output standard
OUTPUT_SUBDIRS = [
    'input_data',
    'output_data', 
    'output_data/output_file'  
]