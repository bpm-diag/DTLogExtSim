
<script>
const extraData = {% if flag_extra == 1 %}{{ extra | tojson | safe }}{% else %}null{% endif %};
console.log('Loaded extra data:', extraData);
</script>
<script>
// ========================================
// AUTO-LOAD PARAMETERS FROM EXTRA.JSON
// ========================================
// Questo script carica automaticamente i parametri dall'oggetto extraData
// quando flag_extra è attivo (BPMN con <diagbp> o extra.json caricato)
// IMPORTANTE: Rispetta i counter globali per mantenere la coerenza

document.addEventListener('DOMContentLoaded', function() {
console.log('=== Starting auto-load parameters ===');

// Verifica se extraData è disponibile (definito nel template Jinja)
if (typeof extraData === 'undefined' || !extraData) {
console.log('No extra data to load - using empty form');
return;
}

console.log('Extra data found:', extraData);

// ========================================
// 1. CARICA INTER-ARRIVAL TIME
// ========================================
if (extraData.arrivalRateDistribution) {
const arrival = extraData.arrivalRateDistribution;

// Tipo di distribuzione
const typeSelect = document.getElementById('inter_arrival_time_type');
if (typeSelect && arrival.type) {
    typeSelect.value = arrival.type;
    // Trigger change event per aggiornare i campi visibili
    typeSelect.dispatchEvent(new Event('change'));
}

// Attendi che l'evento change abbia aggiornato l'interfaccia
setTimeout(() => {
    // Mean
    if (arrival.mean) {
        const meanInput = document.getElementById('inter_arrival_time_mean');
        if (meanInput) meanInput.value = arrival.mean;
    }
    
    // Arg1
    if (arrival.arg1) {
        const arg1Input = document.getElementById('inter_arrival_time_arg1');
        if (arg1Input) arg1Input.value = arrival.arg1;
    }
    
    // Arg2
    if (arrival.arg2) {
        const arg2Input = document.getElementById('inter_arrival_time_arg2');
        if (arg2Input) arg2Input.value = arrival.arg2;
    }
}, 50);

// Time Unit
if (arrival.timeUnit) {
    const timeUnitSelect = document.getElementById('inter_arrival_time_time_unit');
    if (timeUnitSelect) timeUnitSelect.value = arrival.timeUnit;
}

console.log('✓ Arrival rate distribution loaded');
}

// ========================================
// 2. CARICA START DATE
// ========================================
if (extraData.startDateTime) {
const startDateInput = document.getElementById('start_date');
if (startDateInput) {
    // Convert from "YYYY-MM-DD HH:MM:SS" to "YYYY-MM-DDTHH:MM" (datetime-local format)
    const dateStr = extraData.startDateTime.replace(' ', 'T').slice(0, 16);
    startDateInput.value = dateStr;
}
console.log('✓ Start date loaded');
}

// ========================================
// 3. CARICA PROCESS INSTANCES
// ========================================
if (extraData.processInstances && extraData.processInstances.length > 0) {
console.log('Loading process instances:', extraData.processInstances.length);

extraData.processInstances.forEach((instance, index) => {
    // Aggiungi un nuovo gruppo di istanza usando la funzione esistente
    addInstanceGroup(); // Questo incrementa automaticamente instanceGroupCounter
    
    // Popola i campi con il counter AGGIORNATO
    const typeInput = document.getElementById(`instance_type_${instanceGroupCounter}`);
    const countInput = document.getElementById(`instance_count_${instanceGroupCounter}`);
    
    if (typeInput) {
        typeInput.value = instance.type || '';
        // Trigger input event per aggiornare i select dei gateway
        typeInput.dispatchEvent(new Event('input'));
    }
    if (countInput) countInput.value = instance.count || '';
});

console.log('✓ Process instances loaded (instanceGroupCounter=' + instanceGroupCounter + ')');
}

// ========================================
// 4. CARICA TIMETABLES
// ========================================
if (extraData.timetables && extraData.timetables.length > 0) {
console.log('Loading timetables:', extraData.timetables.length);

extraData.timetables.forEach((timetable, index) => {
    // Aggiungi un nuovo timetable (incrementa timetableCounter e inizializza ruleCounter)
    addTimetable();
    
    const currentTimetableCounter = timetableCounter; // Salva il valore corrente
    
    // Popola il nome
    const nameInput = document.getElementById(`timetable_name_${currentTimetableCounter}`);
    if (nameInput) {
        nameInput.value = timetable.name || '';
        // Trigger input event per aggiornare i select delle risorse
        nameInput.dispatchEvent(new Event('input'));
    }
    
    // Carica le regole
    if (timetable.rules && timetable.rules.length > 0) {
        timetable.rules.forEach((rule, ruleIndex) => {
            // addRule incrementa il counter PRIMA di creare la regola
            addRule(currentTimetableCounter);
            
            // Ora ruleCounter[currentTimetableCounter] è il valore corretto
            const currentRuleIndex = ruleCounter[currentTimetableCounter];
            
            // Popola i campi della regola
            // IMPORTANTE: L'HTML usa rule_from_day e rule_to_day (non rule_from_week_day)
            const fromTimeInput = document.getElementById(`rule_from_time_${currentTimetableCounter}_${currentRuleIndex}`);
            const toTimeInput = document.getElementById(`rule_to_time_${currentTimetableCounter}_${currentRuleIndex}`);
            const fromDaySelect = document.getElementById(`rule_from_day_${currentTimetableCounter}_${currentRuleIndex}`);
            const toDaySelect = document.getElementById(`rule_to_day_${currentTimetableCounter}_${currentRuleIndex}`);
            
            if (fromTimeInput) {
                // Rimuovi i secondi se presenti (formato HH:MM:SS -> HH:MM)
                const timeValue = rule.fromTime ? rule.fromTime.slice(0, 5) : '';
                fromTimeInput.value = timeValue;
            }
            if (toTimeInput) {
                const timeValue = rule.toTime ? rule.toTime.slice(0, 5) : '';
                toTimeInput.value = timeValue;
            }
            if (fromDaySelect) fromDaySelect.value = rule.fromWeekDay || 'MONDAY';
            if (toDaySelect) toDaySelect.value = rule.toWeekDay || 'FRIDAY';
        });
    }
});

console.log('✓ Timetables loaded (timetableCounter=' + timetableCounter + ')');
}

// ========================================
// 5. CARICA RESOURCES
// ========================================
if (extraData.resources && extraData.resources.length > 0) {
console.log('Loading resources:', extraData.resources.length);

extraData.resources.forEach((resource, index) => {
    // Aggiungi una nuova risorsa (incrementa resourceCounter e crea entry in resourcesData)
    addResource();
    
    const currentResourceCounter = resourceCounter;
    const resourceId = `resource_${currentResourceCounter}`;
    
    // Popola i campi base
    const nameInput = document.getElementById(`${resourceId}_name`);
    const amountInput = document.getElementById(`${resourceId}_amount`);
    const costInput = document.getElementById(`${resourceId}_cost`);
    const timetableSelect = document.getElementById(`${resourceId}_timetable`);
    
    if (nameInput) {
        nameInput.value = resource.name || '';
        // Trigger input event per aggiornare resourcesData e i select degli elementi
        nameInput.dispatchEvent(new Event('input'));
    }
    if (amountInput) {
        amountInput.value = resource.totalAmount || '';
        amountInput.dispatchEvent(new Event('input'));
    }
    if (costInput) {
        costInput.value = resource.costPerHour || '';
        costInput.dispatchEvent(new Event('input'));
    }
    
    // Il timetable select viene popolato dopo che i timetables sono stati aggiunti
    // Usa setTimeout per dare tempo all'aggiornamento
    if (resource.timetableId) {
        setTimeout(() => {
            if (timetableSelect) {
                timetableSelect.value = resource.timetableId;
                timetableSelect.dispatchEvent(new Event('change'));
            }
        }, 100);
    }
    
    // Setup Time (opzionale)
    if (resource.setupTime) {
        const setupTime = resource.setupTime;
        
        const setupTypeSelect = document.getElementById(`${resourceId}_setupTimeType`);
        const setupMeanInput = document.getElementById(`${resourceId}_setupTimeMean`);
        const setupArg1Input = document.getElementById(`${resourceId}_setupTimeArg1`);
        const setupArg2Input = document.getElementById(`${resourceId}_setupTimeArg2`);
        const setupTimeUnitSelect = document.getElementById(`${resourceId}_setupTimeUnit`);
        
        if (setupTypeSelect) {
            setupTypeSelect.value = setupTime.type || 'FIXED';
            // Trigger change event per mostrare/nascondere i campi corretti
            setupTypeSelect.dispatchEvent(new Event('change'));
            
            // Popola i valori dopo che i campi sono stati mostrati
            setTimeout(() => {
                if (setupMeanInput) {
                    setupMeanInput.value = setupTime.mean || '';
                    setupMeanInput.dispatchEvent(new Event('input'));
                }
                if (setupArg1Input) {
                    setupArg1Input.value = setupTime.arg1 || '';
                    setupArg1Input.dispatchEvent(new Event('input'));
                }
                if (setupArg2Input) {
                    setupArg2Input.value = setupTime.arg2 || '';
                    setupArg2Input.dispatchEvent(new Event('input'));
                }
            }, 50);
        }
        if (setupTimeUnitSelect) {
            setupTimeUnitSelect.value = setupTime.timeUnit || 'seconds';
            setupTimeUnitSelect.dispatchEvent(new Event('change'));
        }
    }
    
    // Max Usage (opzionale)
    if (resource.maxUsage) {
        const maxUsageInput = document.getElementById(`${resourceId}_maxUsage`);
        if (maxUsageInput) {
            maxUsageInput.value = resource.maxUsage;
            maxUsageInput.dispatchEvent(new Event('input'));
        }
    }
});

console.log('✓ Resources loaded (resourceCounter=' + resourceCounter + ')');
}

// ========================================
// 6. CARICA ELEMENTS (Task parameters)
// ========================================
// Attendi che le risorse siano state create prima di caricare gli elementi
setTimeout(() => {
if (extraData.elements && extraData.elements.length > 0) {
    console.log('Loading elements:', extraData.elements.length);
    
    extraData.elements.forEach((element, index) => {
        const elementId = element.elementId;
        
        // Fixed Cost
        if (element.fixedCost !== undefined) {
            const fixedCostInput = document.getElementById(`fixedCost_${elementId}`);
            if (fixedCostInput) fixedCostInput.value = element.fixedCost;
        }
        
        // Worklist ID
        if (element.worklistId) {
            const worklistInput = document.getElementById(`worklistId_${elementId}`);
            if (worklistInput) worklistInput.value = element.worklistId;
        }
        
        // Duration Distribution
        if (element.durationDistribution) {
            const duration = element.durationDistribution;
            
            const typeSelect = document.getElementById(`durationType_${elementId}`);
            const meanInput = document.getElementById(`durationMean_${elementId}`);
            const arg1Input = document.getElementById(`durationArg1_${elementId}`);
            const arg2Input = document.getElementById(`durationArg2_${elementId}`);
            const timeUnitSelect = document.getElementById(`durationTimeUnit_${elementId}`);
            
            if (typeSelect) {
                typeSelect.value = duration.type || 'FIXED';
                // Trigger change event per mostrare/nascondere i campi corretti
                typeSelect.dispatchEvent(new Event('change'));
                
                // Popola i valori dopo che i campi sono stati mostrati
                setTimeout(() => {
                    if (meanInput) meanInput.value = duration.mean || '';
                    if (arg1Input) arg1Input.value = duration.arg1 || '';
                    if (arg2Input) arg2Input.value = duration.arg2 || '';
                }, 50);
            }
            if (timeUnitSelect) timeUnitSelect.value = duration.timeUnit || 'seconds';
        }
        
        // Duration Threshold
        if (element.durationThreshold) {
            const thresholdInput = document.getElementById(`durationThreshold_${elementId}`);
            if (thresholdInput) thresholdInput.value = element.durationThreshold;
        }
        if (element.durationThresholdTimeUnit) {
            const thresholdUnitSelect = document.getElementById(`durationThresholdTimeUnit_${elementId}`);
            if (thresholdUnitSelect) thresholdUnitSelect.value = element.durationThresholdTimeUnit;
        }
        
        // Resources per questo elemento
        if (element.resourceIds && element.resourceIds.length > 0) {
            const resourcesContainer = document.querySelector(`.resources-container[data-element-id="${elementId}"]`);
            
            if (resourcesContainer) {
                // Rimuovi la risorsa vuota di default se presente
                const existingResources = resourcesContainer.querySelectorAll('.resource-input');
                existingResources.forEach(res => res.remove());
                
                element.resourceIds.forEach((resourceAssignment, resIndex) => {
                    // Aggiungi risorsa per questo elemento
                    addResourceInput(elementId);
                    
                    const resourceIndex = resIndex + 1;
                    const resourceNameSelect = document.getElementById(`resourceName_${resourceIndex}_${elementId}`);
                    const amountNeededInput = document.getElementById(`amountNeeded_${resourceIndex}_${elementId}`);
                    const groupIdInput = document.getElementById(`groupId_${resourceIndex}_${elementId}`);
                    
                    // Attendi che updateResourceOptions() abbia popolato le opzioni
                    setTimeout(() => {
                        if (resourceNameSelect) resourceNameSelect.value = resourceAssignment.resourceName || '';
                        if (amountNeededInput) amountNeededInput.value = resourceAssignment.amountNeeded || '';
                        if (groupIdInput) groupIdInput.value = resourceAssignment.groupId || '1';
                    }, 200);
                });
            }
        }
    });
    
    console.log('✓ Elements loaded');
}
}, 300); // Attendi che le risorse siano completamente caricate

// ========================================
// 7. CARICA CATCH EVENTS
// ========================================
setTimeout(() => {
if (extraData.catchEvents) {
    console.log('Loading catch events:', Object.keys(extraData.catchEvents).length);
    
    Object.keys(extraData.catchEvents).forEach(eventId => {
        const eventData = extraData.catchEvents[eventId];
        
        const typeSelect = document.getElementById(`catchEventDurationType_${eventId}`);
        const meanInput = document.getElementById(`catchEventDurationMean_${eventId}`);
        const arg1Input = document.getElementById(`catchEventDurationArg1_${eventId}`);
        const arg2Input = document.getElementById(`catchEventDurationArg2_${eventId}`);
        const timeUnitSelect = document.getElementById(`catchEventDurationTimeUnit_${eventId}`);
        
        if (typeSelect) {
            typeSelect.value = eventData.type || 'FIXED';
            // Trigger change event
            typeSelect.dispatchEvent(new Event('change'));
            
            setTimeout(() => {
                if (meanInput) meanInput.value = eventData.mean || '';
                if (arg1Input) arg1Input.value = eventData.arg1 || '';
                if (arg2Input) arg2Input.value = eventData.arg2 || '';
            }, 50);
        }
        if (timeUnitSelect) timeUnitSelect.value = eventData.timeUnit || 'seconds';
    });
    
    console.log('✓ Catch events loaded');
}
}, 400);

// ========================================
// 8. CARICA SEQUENCE FLOWS (Gateway probabilities)
// ========================================
setTimeout(() => {
if (extraData.sequenceFlows && extraData.sequenceFlows.length > 0) {
    console.log('Loading sequence flows:', extraData.sequenceFlows.length);
    
    extraData.sequenceFlows.forEach((flow, index) => {
        const flowId = flow.elementId;
        
        // Execution Probability
        const probInput = document.getElementById(`executionProbability_${flowId}`);
        if (probInput) probInput.value = flow.executionProbability || '';
        
        // Forced Instance Types
        if (flow.types && flow.types.length > 0) {
            const instanceTypesContainer = document.querySelector(`#instance-types-container-${flowId}`);
            
            if (instanceTypesContainer) {
                // Rimuovi le istanze vuote di default se presenti
                const existingInstances = instanceTypesContainer.querySelectorAll('.instance-type-input');
                existingInstances.forEach(inst => inst.remove());
                
                flow.types.forEach((typeObj, typeIndex) => {
                    // Aggiungi forced instance type
                    addInstanceTypeInput(flowId);
                    
                    const typeIndex1Based = instanceTypesContainer.querySelectorAll('.instance-type-input').length;
                    const typeSelect = document.getElementById(`forcedInstanceType_${flowId}_${typeIndex1Based}`);
                    
                    // Attendi che updateInstanceTypeSelects() abbia popolato le opzioni
                    setTimeout(() => {
                        if (typeSelect) typeSelect.value = typeObj.type || '';
                    }, 100);
                });
            }
        }
    });
    
    console.log('✓ Sequence flows loaded');
}
}, 500);

// ========================================
// 9. CARICA LOGGING OPTION
// ========================================
if (extraData.logging_opt !== undefined) {
const loggingCheckbox = document.getElementById('logging_opt');
if (loggingCheckbox) {
    // logging_opt può essere "1" (string), 1 (number), o true (boolean)
    loggingCheckbox.checked = (extraData.logging_opt === "1" || extraData.logging_opt === 1 || extraData.logging_opt === true);
}
console.log('✓ Logging option loaded');
}

console.log('=== Auto-load parameters completed successfully ===');
console.log('Final counters - instanceGroupCounter:', instanceGroupCounter, 
        'timetableCounter:', timetableCounter, 
        'resourceCounter:', resourceCounter);
});
