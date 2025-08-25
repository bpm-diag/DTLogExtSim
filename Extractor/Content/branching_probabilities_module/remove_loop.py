import pandas as pd

from support_modules.constants import *

def remove_self_loops(self, log: pd.DataFrame) -> pd.DataFrame:
    """
    Rimuove i self-loop dal log.
    
    Args:
        log: Log da pulire
        
    Returns:
        Log senza self-loop
    """
    print("Rimuovendo self-loop dal log...")
    
    try:
        prev_row = None
        self_loops_activities = {}
        self_loops_count = {}
        log_no_loop_list = []
        index = 0
        
        for _, row in log.iterrows():
            if prev_row is not None:
                # Stessa traccia
                if prev_row[TAG_TRACE_ID] == row[TAG_TRACE_ID]:
                    # Stessa attività (self-loop)
                    if prev_row[TAG_ACTIVITY_NAME] == row[TAG_ACTIVITY_NAME]:
                        if index in self_loops_count:
                            self_loops_activities[index] = [
                                [row[TAG_TRACE_ID]], 
                                [row[TAG_ACTIVITY_NAME]]
                            ]
                            self_loops_count[index] += 1
                        else:
                            self_loops_count[index] = 1
                            self_loops_activities[index] = [
                                [row[TAG_TRACE_ID]], 
                                [row[TAG_ACTIVITY_NAME]]
                            ]
                    else:
                        # Attività diversa, aggiungi al log pulito
                        prev_row = row
                        index += 1
                        log_no_loop_list.append(row)
                else:
                    # Traccia diversa
                    prev_row = row
                    index += 1
                    log_no_loop_list.append(row)
            else:
                # Prima riga
                prev_row = row
                log_no_loop_list.append(row)
        
        # Crea DataFrame pulito
        if not self_loops_activities:
            log_no_loop = log
        else:
            log_no_loop = pd.DataFrame(log_no_loop_list)
            log_no_loop = log_no_loop.reset_index(drop=True)
        
        print(f"✓ Rimossi self-loop: {len(log) - len(log_no_loop)} eventi")
        return log_no_loop
        
    except Exception as e:
        raise Exception(f"Errore nella rimozione dei self-loop: {str(e)}")
