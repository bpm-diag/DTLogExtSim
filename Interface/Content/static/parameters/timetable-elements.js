
/**
 * Aggiunge un timetable a uno scenario
 */
function addTimetable(scenarioIndex) {
    const container = document.getElementById(`timetables-container-${scenarioIndex}`);
    if (!container) {
        console.error(`Container timetables-container-${scenarioIndex} not found`);
        return;
    }
    
    const timetableIndex = timetableCounters[scenarioIndex];
    timetableCounters[scenarioIndex]++;
    
    // Inizializza il contatore delle regole per questo timetable
    if (!window.ruleCounters) window.ruleCounters = {};
    if (!window.ruleCounters[scenarioIndex]) window.ruleCounters[scenarioIndex] = {};
    window.ruleCounters[scenarioIndex][timetableIndex] = 0;
    
    const timetableDiv = document.createElement('div');
    timetableDiv.className = 'timetable-group mb-3 box';
    timetableDiv.innerHTML = `
        <div class="row">
            <div class="form-group col-md-12 mb-3">
                <label for="scenario_${scenarioIndex}_timetable_name_${timetableIndex}">Name:</label>
                <input type="text" class="form-control" 
                       id="scenario_${scenarioIndex}_timetable_name_${timetableIndex}" 
                       name="scenario_${scenarioIndex}_timetable_name_${timetableIndex}" required>
            </div>
        </div>
        <div id="scenario_${scenarioIndex}_rules-container-${timetableIndex}"></div>
        <div class="row"> 
            <div class="col-10"> 
                <button type="button" class="btn btn-secondary btn-block my-3" 
                        onclick="addRule(${scenarioIndex}, ${timetableIndex})">Add Rule</button>
            </div>
            <div class="col-2 d-flex align-items-center justify-content-end">
                <button type="button" class="btn btn-danger btn-block" 
                        onclick="removeTimetable(this, ${scenarioIndex})">Remove Timetable</button>
            </div>
        </div>
    `;
    container.appendChild(timetableDiv);
    
    // Add event listener per aggiornare i select delle risorse
    const timetableNameInput = document.getElementById(`scenario_${scenarioIndex}_timetable_name_${timetableIndex}`);
    timetableNameInput.addEventListener('input', () => updateTimetableOptions(scenarioIndex));
}

function removeTimetable(button, scenarioIndex) {
    const timetableDiv = button.closest('.timetable-group');
    timetableDiv.remove();
    
    // Rinumera tutti i timetable rimasti
    renumberTimetables(scenarioIndex);
    
    updateTimetableOptions(scenarioIndex);
}

function renumberTimetables(scenarioIndex) {
    const container = document.getElementById(`timetables-container-${scenarioIndex}`);
    const allTimetables = Array.from(container.querySelectorAll('.timetable-group'));
    
    // Resetta i contatori delle regole per questo scenario
    if (!window.ruleCounters) window.ruleCounters = {};
    if (!window.ruleCounters[scenarioIndex]) window.ruleCounters[scenarioIndex] = {};
    
    allTimetables.forEach((timetableDiv, newIndex) => {
        // Aggiorna il nome del timetable
        const nameInput = timetableDiv.querySelector('input[name*="_timetable_name_"]');
        const nameLabel = timetableDiv.querySelector('label[for*="_timetable_name_"]');
        
        if (nameInput) {
            nameInput.id = `scenario_${scenarioIndex}_timetable_name_${newIndex}`;
            nameInput.name = `scenario_${scenarioIndex}_timetable_name_${newIndex}`;
            
            // Rimuovi vecchio listener e aggiungi nuovo
            const newInput = nameInput.cloneNode(true);
            newInput.value = nameInput.value; // Preserva il valore
            newInput.addEventListener('input', () => updateTimetableOptions(scenarioIndex));
            nameInput.parentNode.replaceChild(newInput, nameInput);
        }
        
        if (nameLabel) {
            nameLabel.setAttribute('for', `scenario_${scenarioIndex}_timetable_name_${newIndex}`);
        }
        
        // Aggiorna il container delle regole
        const rulesContainer = timetableDiv.querySelector('[id*="rules-container"]');
        if (rulesContainer) {
            rulesContainer.id = `scenario_${scenarioIndex}_rules-container-${newIndex}`;
            
            // Rinumera tutte le regole in questo timetable
            const allRules = Array.from(rulesContainer.querySelectorAll('.rule-group'));
            allRules.forEach((ruleDiv, ruleIndex) => {
                // Aggiorna tutti gli input/select delle regole
                const fromTimeInput = ruleDiv.querySelector('input[name*="_rule_from_time_"]');
                const toTimeInput = ruleDiv.querySelector('input[name*="_rule_to_time_"]');
                const fromDaySelect = ruleDiv.querySelector('select[name*="_rule_from_day_"]');
                const toDaySelect = ruleDiv.querySelector('select[name*="_rule_to_day_"]');
                
                if (fromTimeInput) {
                    fromTimeInput.id = `scenario_${scenarioIndex}_rule_from_time_${newIndex}_${ruleIndex + 1}`;
                    fromTimeInput.name = `scenario_${scenarioIndex}_rule_from_time_${newIndex}_${ruleIndex + 1}`;
                }
                if (toTimeInput) {
                    toTimeInput.id = `scenario_${scenarioIndex}_rule_to_time_${newIndex}_${ruleIndex + 1}`;
                    toTimeInput.name = `scenario_${scenarioIndex}_rule_to_time_${newIndex}_${ruleIndex + 1}`;
                }
                if (fromDaySelect) {
                    fromDaySelect.id = `scenario_${scenarioIndex}_rule_from_day_${newIndex}_${ruleIndex + 1}`;
                    fromDaySelect.name = `scenario_${scenarioIndex}_rule_from_day_${newIndex}_${ruleIndex + 1}`;
                }
                if (toDaySelect) {
                    toDaySelect.id = `scenario_${scenarioIndex}_rule_to_day_${newIndex}_${ruleIndex + 1}`;
                    toDaySelect.name = `scenario_${scenarioIndex}_rule_to_day_${newIndex}_${ruleIndex + 1}`;
                }
            });
            
            // Aggiorna il contatore delle regole per questo timetable
            window.ruleCounters[scenarioIndex][newIndex] = allRules.length;
        }
        
        // Aggiorna i bottoni Add Rule e Remove Timetable
        const addRuleBtn = timetableDiv.querySelector('button[onclick*="addRule"]');
        if (addRuleBtn) {
            addRuleBtn.setAttribute('onclick', `addRule(${scenarioIndex}, ${newIndex})`);
        }
        
        const removeBtn = timetableDiv.querySelector('button[onclick*="removeTimetable"]');
        if (removeBtn) {
            removeBtn.setAttribute('onclick', `removeTimetable(this, ${scenarioIndex})`);
        }
    });
    
    // Aggiorna il contatore
    timetableCounters[scenarioIndex] = allTimetables.length;
}

function addRule(scenarioIndex, timetableNum) {
    if (!window.ruleCounters[scenarioIndex]) window.ruleCounters[scenarioIndex] = {};
    if (!window.ruleCounters[scenarioIndex][timetableNum]) {
        window.ruleCounters[scenarioIndex][timetableNum] = 0;
    }
    
    window.ruleCounters[scenarioIndex][timetableNum]++;
    const ruleIndex = window.ruleCounters[scenarioIndex][timetableNum];
    
    const rulesContainer = document.getElementById(`scenario_${scenarioIndex}_rules-container-${timetableNum}`);
    const ruleDiv = document.createElement('div');
    ruleDiv.className = 'rule-group mb-3 box';
    ruleDiv.innerHTML = `
        <div class="row my-2">
            <div class="col-10 d-flex align-items-center"></div>
            <div class="col-2 d-flex align-items-center justify-content-end">
                <button type="button" class="btn btn-danger btn-block" 
                        onclick="removeRule(this, ${scenarioIndex}, ${timetableNum})">Remove Rule</button>
            </div>
        </div>
        <div class="row">
            <div class="form-group col-3">
                <label for="scenario_${scenarioIndex}_rule_from_time_${timetableNum}_${ruleIndex}">From Time:</label>
                <input type="time" class="form-control" 
                       id="scenario_${scenarioIndex}_rule_from_time_${timetableNum}_${ruleIndex}" 
                       name="scenario_${scenarioIndex}_rule_from_time_${timetableNum}_${ruleIndex}" required>
            </div>
            <div class="form-group col-3">
                <label for="scenario_${scenarioIndex}_rule_to_time_${timetableNum}_${ruleIndex}">To Time:</label>
                <input type="time" class="form-control" 
                       id="scenario_${scenarioIndex}_rule_to_time_${timetableNum}_${ruleIndex}" 
                       name="scenario_${scenarioIndex}_rule_to_time_${timetableNum}_${ruleIndex}" required>
            </div>
            <div class="form-group col-3">
                <label for="scenario_${scenarioIndex}_rule_from_day_${timetableNum}_${ruleIndex}">From Day:</label>
                <select id="scenario_${scenarioIndex}_rule_from_day_${timetableNum}_${ruleIndex}" 
                        name="scenario_${scenarioIndex}_rule_from_day_${timetableNum}_${ruleIndex}" class="form-control">
                    <option value="MONDAY">Monday</option>
                    <option value="TUESDAY">Tuesday</option>
                    <option value="WEDNESDAY">Wednesday</option>
                    <option value="THURSDAY">Thursday</option>
                    <option value="FRIDAY">Friday</option>
                    <option value="SATURDAY">Saturday</option>
                    <option value="SUNDAY">Sunday</option>
                </select>
            </div>
            <div class="form-group col-3">
                <label for="scenario_${scenarioIndex}_rule_to_day_${timetableNum}_${ruleIndex}">To Day:</label>
                <select id="scenario_${scenarioIndex}_rule_to_day_${timetableNum}_${ruleIndex}" 
                        name="scenario_${scenarioIndex}_rule_to_day_${timetableNum}_${ruleIndex}" class="form-control">
                    <option value="MONDAY">Monday</option>
                    <option value="TUESDAY">Tuesday</option>
                    <option value="WEDNESDAY">Wednesday</option>
                    <option value="THURSDAY">Thursday</option>
                    <option value="FRIDAY">Friday</option>
                    <option value="SATURDAY">Saturday</option>
                    <option value="SUNDAY">Sunday</option>
                </select>
            </div>
        </div>
    `;
    rulesContainer.appendChild(ruleDiv);
}

function removeRule(button, scenarioIndex, timetableNum) {
    const ruleDiv = button.closest('.rule-group');
    if (ruleDiv) {
        ruleDiv.remove();
        
        // Rinumera le regole rimaste in questo timetable
        const rulesContainer = document.getElementById(`scenario_${scenarioIndex}_rules-container-${timetableNum}`);
        const allRules = Array.from(rulesContainer.querySelectorAll('.rule-group'));
        
        allRules.forEach((ruleDiv, newRuleIndex) => {
            const ruleIndex = newRuleIndex + 1; // Le regole partono da 1
            
            const fromTimeInput = ruleDiv.querySelector('input[name*="_rule_from_time_"]');
            const toTimeInput = ruleDiv.querySelector('input[name*="_rule_to_time_"]');
            const fromDaySelect = ruleDiv.querySelector('select[name*="_rule_from_day_"]');
            const toDaySelect = ruleDiv.querySelector('select[name*="_rule_to_day_"]');
            
            if (fromTimeInput) {
                fromTimeInput.id = `scenario_${scenarioIndex}_rule_from_time_${timetableNum}_${ruleIndex}`;
                fromTimeInput.name = `scenario_${scenarioIndex}_rule_from_time_${timetableNum}_${ruleIndex}`;
            }
            if (toTimeInput) {
                toTimeInput.id = `scenario_${scenarioIndex}_rule_to_time_${timetableNum}_${ruleIndex}`;
                toTimeInput.name = `scenario_${scenarioIndex}_rule_to_time_${timetableNum}_${ruleIndex}`;
            }
            if (fromDaySelect) {
                fromDaySelect.id = `scenario_${scenarioIndex}_rule_from_day_${timetableNum}_${ruleIndex}`;
                fromDaySelect.name = `scenario_${scenarioIndex}_rule_from_day_${timetableNum}_${ruleIndex}`;
            }
            if (toDaySelect) {
                toDaySelect.id = `scenario_${scenarioIndex}_rule_to_day_${timetableNum}_${ruleIndex}`;
                toDaySelect.name = `scenario_${scenarioIndex}_rule_to_day_${timetableNum}_${ruleIndex}`;
            }
        });
        
        window.ruleCounters[scenarioIndex][timetableNum] = allRules.length;
    }
}