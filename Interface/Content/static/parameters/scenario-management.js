// scenario-management.js
// Gestione aggiunta e rimozione scenari

let scenarioCount = 1;
let instanceCounters = {0: 0};
let timetableCounters = {0: 0};
let resourceCounters = {0: 0};
let elementResourceCounters = {}; // Formato: {scenarioIdx_elementId: counter}
/**
 * Aggiunge un nuovo scenario clonando lo scenario 0
 */
function addScenario() {
    const tabsList = document.getElementById('scenarioTabs');
    const tabContent = document.getElementById('scenarioTabContent');
    const scenarioIndex = scenarioCount;
    
    // Crea nuovo tab
    const newTabLi = document.createElement('li');
    newTabLi.className = 'nav-item';
    newTabLi.setAttribute('role', 'presentation');
    newTabLi.innerHTML = `
        <button class="nav-link" id="scenario-${scenarioIndex}-tab" data-bs-toggle="tab" 
                data-bs-target="#scenario-${scenarioIndex}" type="button" role="tab">
            Scenario ${scenarioIndex}
            <span class="tab-close-btn" onclick="removeScenario(${scenarioIndex}, event)" title="Remove scenario">×</span>
        </button>
    `;
    tabsList.appendChild(newTabLi);

    // Clona il contenuto dello scenario 0
    const templateContent = document.getElementById('scenario-0').cloneNode(true);
    templateContent.id = `scenario-${scenarioIndex}`;
    templateContent.className = 'tab-pane fade';
    
    // Aggiorna tutti i nomi degli input nel contenuto clonato
    updateScenarioInputNames(templateContent, scenarioIndex);

    // Aggiorna gli attributi for delle label
    updateScenarioLabelFor(templateContent, scenarioIndex);
    
    // Aggiorna gli ID dei container
    updateContainerIds(templateContent, scenarioIndex);

    // Aggiorna i data attributes per le distribuzioni temporali
    const durationSelects = templateContent.querySelectorAll('.duration-type');
    durationSelects.forEach(select => {
        select.setAttribute('data-scenario', scenarioIndex);
    });

    const catchEventSelects = templateContent.querySelectorAll('.catch-event-duration-type');
    catchEventSelects.forEach(select => {
        select.setAttribute('data-scenario', scenarioIndex);
    });
    
    // Pulisci i container dinamici (instances, timetables, resources)
    clearDynamicContainers(templateContent, scenarioIndex);
    
    // Aggiorna gli handler onclick dei bottoni
    updateButtonHandlers(templateContent, scenarioIndex);
    
    // Aggiorna i container delle risorse degli elementi BPMN
    updateElementResourceContainers(templateContent, scenarioIndex);
    
    tabContent.appendChild(templateContent);

    setCurrentDateTime(scenarioIndex);

    updateInterArrivalTimeDistribution(scenarioIndex);

    initializeActivityDurationListeners(scenarioIndex);
    initializeCatchEventDurationListeners(scenarioIndex);
    
    // Inizializza i contatori per il nuovo scenario
    instanceCounters[scenarioIndex] = 0;
    timetableCounters[scenarioIndex] = 0;
    resourceCounters[scenarioIndex] = 0;
    
    scenarioCount++;
    updateScenarioCount();
}

/**
 * Rimuove uno scenario e rinumera tutti gli altri
 */
function removeScenario(scenarioIndex, event) {
    event.stopPropagation();
    event.preventDefault();
    
    const allTabs = Array.from(document.querySelectorAll('#scenarioTabs .nav-item'));
    
    // Non permettere di rimuovere se è l'ultimo scenario
    if (allTabs.length === 1) {
        alert('You must have at least one scenario');
        return;
    }
    
    // Rimuovi tab e contenuto
    const tabToRemove = document.getElementById(`scenario-${scenarioIndex}-tab`).closest('.nav-item');
    const contentToRemove = document.getElementById(`scenario-${scenarioIndex}`);

    tabToRemove.remove();
    contentToRemove.remove();
    
    // Elimina i contatori
    delete instanceCounters[scenarioIndex];
    delete timetableCounters[scenarioIndex];
    delete resourceCounters[scenarioIndex];
    
    // Elimina i contatori delle risorse degli elementi
    Object.keys(elementResourceCounters).forEach(key => {
        if (key.startsWith(`${scenarioIndex}_`)) {
            delete elementResourceCounters[key];
        }
    });
    
    // Rinumera tutti gli scenari
    renumberScenarios();
    
    updateScenarioCount();
}

/**
 * Rinumera tutti gli scenari per mantenere l'ordine sequenziale
 */
function renumberScenarios() {
    const tabsList = document.getElementById('scenarioTabs');
    const tabContent = document.getElementById('scenarioTabContent');
    
    const allTabs = Array.from(tabsList.querySelectorAll('.nav-item'));
    const allContents = Array.from(tabContent.querySelectorAll('.tab-pane'));
    
    // SALVA i valori dei select arrival_type PRIMA di clonare
    const arrivalTypeValues = {};
    const arrivalTimeUnitValues = {};
    const timetableRuleValues = {};
    const resourceSelectValues = {};
    allTabs.forEach((tab, index) => {
        const tabButton = tab.querySelector('.nav-link');
        const oldIndex = parseInt(tabButton.id.match(/scenario-(\d+)-tab/)[1]);
        const select = document.getElementById(`scenario_${oldIndex}_arrival_type`);
        if (select) {
            arrivalTypeValues[index] = select.value;
        }

        const timeUnitSelect = document.getElementById(`scenario_${oldIndex}_arrival_time_unit`);
        if (timeUnitSelect) {
            arrivalTimeUnitValues[index] = timeUnitSelect.value;
        }

        timetableRuleValues[index] = [];
        const allRuleSelects = document.querySelectorAll(`#scenario-${oldIndex} select[name*="_rule_from_day_"], #scenario-${oldIndex} select[name*="_rule_to_day_"]`);
        allRuleSelects.forEach(ruleSelect => {
            timetableRuleValues[index].push({
                name: ruleSelect.name,
                value: ruleSelect.value
            });
        });

        resourceSelectValues[index] = [];
        const resourceSelects = document.querySelectorAll(`#scenario-${oldIndex} .resource-group select`);
        resourceSelects.forEach(select => {
            resourceSelectValues[index].push({
                id: select.id,
                value: select.value
            });
        });

        const bpmnElementSelects = {};
        const durationTypeSelects = document.querySelectorAll(`#scenario-${oldIndex} .duration-type`);
        durationTypeSelects.forEach(select => {
            const elementId = select.dataset.elementId;
            if (elementId) {
                bpmnElementSelects[elementId] = {
                    durationType: select.value,
                    durationTimeUnit: null,
                    durationThresholdTimeUnit: null,
                    elementResources: []
                };
                
                // Salva anche time unit e threshold time unit
                const timeUnitSelect = document.getElementById(`scenario_${oldIndex}_durationTimeUnit_${elementId}`);
                if (timeUnitSelect) {
                    bpmnElementSelects[elementId].durationTimeUnit = timeUnitSelect.value;
                }
                
                const thresholdTimeUnitSelect = document.getElementById(`scenario_${oldIndex}_durationThresholdTimeUnit_${elementId}`);
                if (thresholdTimeUnitSelect) {
                    bpmnElementSelects[elementId].durationThresholdTimeUnit = thresholdTimeUnitSelect.value;
                }

                const resourceSelects = document.querySelectorAll(`.element-resources-container-${oldIndex}-${elementId} select[name*="resourceName"]`);
                resourceSelects.forEach(resSelect => {
                    bpmnElementSelects[elementId].elementResources.push(resSelect.value);
                });
            }
        });

        const gatewaySelects = document.querySelectorAll(`#gateways-container-${oldIndex} select[name*="forcedInstanceType"]`);
        if (!window.savedGatewayStates) window.savedGatewayStates = {};
        window.savedGatewayStates[index] = [];
        gatewaySelects.forEach(select => {
            window.savedGatewayStates[index].push({
                name: select.name,
                value: select.value
            });
        });

        const catchEventSelects = {};
        const catchEventTypeSelects = document.querySelectorAll(`#scenario-${oldIndex} .catch-event-duration-type`);
        catchEventTypeSelects.forEach(select => {
            const elementId = select.dataset.elementId;
            if (elementId) {
                catchEventSelects[elementId] = {
                    durationType: select.value,
                    durationTimeUnit: null
                };
                
                // Salva anche time unit
                const timeUnitSelect = document.getElementById(`scenario_${oldIndex}_catchEventDurationTimeUnit_${elementId}`);
                if (timeUnitSelect) {
                    catchEventSelects[elementId].durationTimeUnit = timeUnitSelect.value;
                }
            }
        });

        // Memorizza per questo scenario
        if (!window.savedCatchEventStates) window.savedCatchEventStates = {};
        window.savedCatchEventStates[index] = catchEventSelects;
        
        // Memorizza per questo scenario
        if (!window.savedBpmnElementStates) window.savedBpmnElementStates = {};
        window.savedBpmnElementStates[index] = bpmnElementSelects;
    });
    
    const newTabs = [];
    const newContents = [];
    
    const newCounters = {
        instances: {},
        timetables: {},
        resources: {},
        elementResources: {}
    };
    
    allTabs.forEach((tab, newIndex) => {
        const tabButton = tab.querySelector('.nav-link');
        const oldIndex = parseInt(tabButton.id.match(/scenario-(\d+)-tab/)[1]);
        const oldContent = document.getElementById(`scenario-${oldIndex}`);
        
        // Salva contatori
        newCounters.instances[newIndex] = instanceCounters[oldIndex] || 0;
        newCounters.timetables[newIndex] = timetableCounters[oldIndex] || 0;
        newCounters.resources[newIndex] = resourceCounters[oldIndex] || 0;
        
        Object.keys(elementResourceCounters).forEach(key => {
            if (key.startsWith(`${oldIndex}_`)) {
                const elementId = key.substring(key.indexOf('_') + 1);
                newCounters.elementResources[`${newIndex}_${elementId}`] = elementResourceCounters[key];
            }
        });
        
        const newTab = tab.cloneNode(true);
        const newContent = oldContent.cloneNode(true);
        
        const newTabButton = newTab.querySelector('.nav-link');
        newTabButton.id = `scenario-${newIndex}-tab`;
        newTabButton.setAttribute('data-bs-target', `#scenario-${newIndex}`);
        newTabButton.childNodes[0].textContent = `Scenario ${newIndex} `;
        newTabButton.classList.toggle('active', newIndex === 0);
        newTabButton.setAttribute('aria-selected', newIndex === 0 ? 'true' : 'false');
        
        const closeBtn = newTabButton.querySelector('.tab-close-btn');
        closeBtn.setAttribute('onclick', `removeScenario(${newIndex}, event)`);
        
        newContent.id = `scenario-${newIndex}`;
        newContent.setAttribute('aria-labelledby', `scenario-${newIndex}-tab`);
        if (newIndex === 0) {
            newContent.className = 'tab-pane fade show active';
        } else {
            newContent.className = 'tab-pane fade';
        }
        
        updateScenarioInputNames(newContent, newIndex);
        updateScenarioLabelFor(newContent, newIndex);
        updateContainerIds(newContent, newIndex);
        updateButtonHandlers(newContent, newIndex);
        updateElementResourceContainers(newContent, newIndex);
        
        newTabs.push(newTab);
        newContents.push(newContent);
    });
    
    tabsList.innerHTML = '';
    tabContent.innerHTML = '';
    
    newTabs.forEach(tab => tabsList.appendChild(tab));
    newContents.forEach(content => tabContent.appendChild(content));
    
    instanceCounters = newCounters.instances;
    timetableCounters = newCounters.timetables;
    resourceCounters = newCounters.resources;
    elementResourceCounters = newCounters.elementResources;
    
    scenarioCount = newTabs.length;

    // Aggiorna i data attributes per ogni scenario rinumerato
    newContents.forEach((content, idx) => {
        const durationSelects = content.querySelectorAll('.duration-type');
        durationSelects.forEach(select => {
            select.setAttribute('data-scenario', idx);
        });
        
        const catchEventSelects = content.querySelectorAll('.catch-event-duration-type');
        catchEventSelects.forEach(select => {
            select.setAttribute('data-scenario', idx);
        });
    });
    
    // RIPRISTINA i valori e aggiorna la UI
    for (let i = 0; i < scenarioCount; i++) {
        const select = document.getElementById(`scenario_${i}_arrival_type`);
        if (select && arrivalTypeValues[i]) {
            select.value = arrivalTypeValues[i];
            updateInterArrivalTimeDistribution(i);
        }

        const timeUnitSelect = document.getElementById(`scenario_${i}_arrival_time_unit`);
        if (timeUnitSelect && arrivalTimeUnitValues[i]) {
            timeUnitSelect.value = arrivalTimeUnitValues[i];
        }

        if (timetableRuleValues[i]) {
            timetableRuleValues[i].forEach(savedSelect => {
                // Il name è stato rinumerato, quindi cerca per pattern
                const newName = savedSelect.name.replace(/scenario_\d+/, `scenario_${i}`);
                const ruleSelect = document.querySelector(`select[name="${newName}"]`);
                if (ruleSelect) {
                    ruleSelect.value = savedSelect.value;
                }
            });
        }

        if (resourceSelectValues[i]) {
            resourceSelectValues[i].forEach(savedSelect => {
                // Trova il select con ID rinumerato
                const oldResourceMatch = savedSelect.id.match(/scenario_\d+_resource_\d+/);
                if (oldResourceMatch) {
                    const newId = savedSelect.id.replace(/scenario_\d+_resource_\d+/, 
                                  savedSelect.id.match(/scenario_\d+_resource_\d+/)[0].replace(/scenario_\d+/, `scenario_${i}`));
                    const select = document.getElementById(newId);
                    if (select) {
                        select.value = savedSelect.value;
                    }
                }
            });
        }

        if (window.savedBpmnElementStates && window.savedBpmnElementStates[i]) {
            const bpmnStates = window.savedBpmnElementStates[i];
            
            for (const elementId in bpmnStates) {
                const state = bpmnStates[elementId];
                
                // Ripristina duration type
                const durationTypeSelect = document.getElementById(`scenario_${i}_durationType_${elementId}`);
                if (durationTypeSelect && state.durationType) {
                    durationTypeSelect.value = state.durationType;
                    updateActivityTimeDistribution(elementId, i);
                }
                
                // Ripristina duration time unit
                const timeUnitSelect = document.getElementById(`scenario_${i}_durationTimeUnit_${elementId}`);
                if (timeUnitSelect && state.durationTimeUnit) {
                    timeUnitSelect.value = state.durationTimeUnit;
                }
                
                // Ripristina threshold time unit
                const thresholdTimeUnitSelect = document.getElementById(`scenario_${i}_durationThresholdTimeUnit_${elementId}`);
                if (thresholdTimeUnitSelect && state.durationThresholdTimeUnit) {
                    thresholdTimeUnitSelect.value = state.durationThresholdTimeUnit;
                }

                if (state.elementResources && state.elementResources.length > 0) {
                    const resourceSelects = document.querySelectorAll(`.element-resources-container-${i}-${elementId} select[name*="resourceName"]`);
                    resourceSelects.forEach((resSelect, index) => {
                        if (state.elementResources[index]) {
                            resSelect.value = state.elementResources[index];
                        }
                    });
                }
            }
        }

        if (window.savedGatewayStates && window.savedGatewayStates[i]) {
            window.savedGatewayStates[i].forEach(savedSelect => {
                const newName = savedSelect.name.replace(/scenario_\d+/, `scenario_${i}`);
                const select = document.querySelector(`select[name="${newName}"]`);
                if (select) {
                    select.value = savedSelect.value;
                }
            });
        }

        // Ripristina gli stati dei catch events
        if (window.savedCatchEventStates && window.savedCatchEventStates[i]) {
            const catchEventStates = window.savedCatchEventStates[i];
            
            for (const elementId in catchEventStates) {
                const state = catchEventStates[elementId];
                
                // Ripristina duration type
                const durationTypeSelect = document.getElementById(`scenario_${i}_catchEventDurationType_${elementId}`);
                if (durationTypeSelect && state.durationType) {
                    durationTypeSelect.value = state.durationType;
                    updateCatchEventTimeDistribution(elementId, i);
                }
                
                // Ripristina duration time unit
                const timeUnitSelect = document.getElementById(`scenario_${i}_catchEventDurationTimeUnit_${elementId}`);
                if (timeUnitSelect && state.durationTimeUnit) {
                    timeUnitSelect.value = state.durationTimeUnit;
                }
            }
        }
    }
}

/**
 * Aggiorna i nomi degli input in un container per un nuovo indice di scenario
 */
function updateScenarioInputNames(container, newIndex) {
    const inputs = container.querySelectorAll('input, select, textarea');
    inputs.forEach(input => {
        if (input.name && input.name.startsWith('scenario_')) {
            input.name = input.name.replace(/scenario_\d+/, `scenario_${newIndex}`);
        }
        if (input.id && input.id.startsWith('scenario_')) {
            input.id = input.id.replace(/scenario_\d+/, `scenario_${newIndex}`);
        }
    });
}

/**
 * Aggiorna gli attributi for delle label per un nuovo indice di scenario
 */
function updateScenarioLabelFor(container, newIndex) {
    const labels = container.querySelectorAll('label[for]');
    labels.forEach(label => {
        const forAttr = label.getAttribute('for');
        if (forAttr && forAttr.startsWith('scenario_')) {
            label.setAttribute('for', forAttr.replace(/scenario_\d+/, `scenario_${newIndex}`));
        }
    });
}

/**
 * Aggiorna gli ID dei container in un scenario
 */
function updateContainerIds(container, scenarioIndex) {
    const instancesContainer = container.querySelector('[id^="instances-container"]');
    if (instancesContainer) instancesContainer.id = `instances-container-${scenarioIndex}`;
    
    const timetablesContainer = container.querySelector('[id^="timetables-container"]');
    if (timetablesContainer) timetablesContainer.id = `timetables-container-${scenarioIndex}`;
    
    const resourcesContainer = container.querySelector('[id^="resources-container"]');
    if (resourcesContainer) resourcesContainer.id = `resources-container-${scenarioIndex}`;
    
    const elementsContainer = container.querySelector('[id^="elements-container"]');
    if (elementsContainer) elementsContainer.id = `elements-container-${scenarioIndex}`;
    
    const gatewaysContainer = container.querySelector('[id^="gateways-container"]');
    if (gatewaysContainer) gatewaysContainer.id = `gateways-container-${scenarioIndex}`;
    
    const catchEventsContainer = container.querySelector('[id^="catch-events-container"]');
    if (catchEventsContainer) catchEventsContainer.id = `catch-events-container-${scenarioIndex}`;
}

/**
 * Pulisce i container dinamici (instances, timetables, resources)
 */
function clearDynamicContainers(container, scenarioIndex) {
    const instancesContainer = container.querySelector(`#instances-container-${scenarioIndex}`);
    if (instancesContainer) instancesContainer.innerHTML = '';
    
    const timetablesContainer = container.querySelector(`#timetables-container-${scenarioIndex}`);
    if (timetablesContainer) timetablesContainer.innerHTML = '';
    
    const resourcesContainer = container.querySelector(`#resources-container-${scenarioIndex}`);
    if (resourcesContainer) resourcesContainer.innerHTML = '';

    const elementResourceContainers = container.querySelectorAll('[class*="element-resources-container-"]');
    elementResourceContainers.forEach(resContainer => {
        resContainer.innerHTML = '';
    });

    // Reset arrival rate distribution fields
    const arrivalTypeSelect = container.querySelector(`#scenario_${scenarioIndex}_arrival_type`);
    if (arrivalTypeSelect) arrivalTypeSelect.value = 'FIXED';
    
    const arrivalMean = container.querySelector(`#scenario_${scenarioIndex}_arrival_mean`);
    if (arrivalMean) arrivalMean.value = '';
    
    const arrivalArg1 = container.querySelector(`#scenario_${scenarioIndex}_arrival_arg1`);
    if (arrivalArg1) arrivalArg1.value = '';
    
    const arrivalArg2 = container.querySelector(`#scenario_${scenarioIndex}_arrival_arg2`);
    if (arrivalArg2) arrivalArg2.value = '';
    
    const arrivalTimeUnit = container.querySelector(`#scenario_${scenarioIndex}_arrival_time_unit`);
    if (arrivalTimeUnit) arrivalTimeUnit.value = 'seconds';

    // Reset BPMN elements fields
    const elementsContainer = container.querySelector(`#elements-container-${scenarioIndex}`);
    if (elementsContainer) {
        const allInputs = elementsContainer.querySelectorAll('input[type="text"], input[type="number"]');
        allInputs.forEach(input => {
            input.value = '';
        });
        
        const allSelects = elementsContainer.querySelectorAll('select');
        allSelects.forEach(select => {
            if (select.id.includes('durationType')) {
                select.value = 'FIXED';
            } else if (select.id.includes('TimeUnit')) {
                select.value = 'seconds';
            } else {
                select.selectedIndex = 0; // Reset to first option
            }
        });
    }

    // Reset catch events
    const catchEventsContainer = container.querySelector(`#catch-events-container-${scenarioIndex}`);
    if (catchEventsContainer) {
        const allInputs = catchEventsContainer.querySelectorAll('input[type="number"]');
        allInputs.forEach(input => {
            input.value = '';
        });
        
        const allSelects = catchEventsContainer.querySelectorAll('select');
        allSelects.forEach(select => {
            if (select.id.includes('DurationType')) {
                select.value = 'FIXED';
            } else if (select.id.includes('TimeUnit')) {
                select.value = 'seconds';
            }
        });
    }


    const gatewaysContainer = container.querySelector(`#gateways-container-${scenarioIndex}`);
    if (gatewaysContainer) {
        const gateways = gatewaysContainer.querySelectorAll('.gateway-group');
        gateways.forEach(gateway => {
            // Resetta execution probability
            const probInput = gateway.querySelector('input[name*="executionProbability"]');
            if (probInput) probInput.value = '';
            
            // Mantieni solo il primo forced instance type select, rimuovi gli altri
            const instanceTypesContainer = gateway.querySelector('.instance-types-container');
            if (instanceTypesContainer) {
                const allInstanceInputs = instanceTypesContainer.querySelectorAll('.instance-type-input');
                allInstanceInputs.forEach((input, index) => {
                    if (index === 0) {
                        // CAMBIA QUESTO: Svuota completamente le opzioni del primo select
                        const select = input.querySelector('select');
                        if (select) {
                            select.innerHTML = '<option value=""></option>';
                        }
                    } else {
                        // Rimuovi gli altri
                        input.remove();
                    }
                });
            }
        });
    }
}

/**
 * Aggiorna gli handler onclick dei bottoni
 */
function updateButtonHandlers(container, scenarioIndex) {
    const buttons = container.querySelectorAll('button[onclick]');
    buttons.forEach(btn => {
        const onclick = btn.getAttribute('onclick');
        if (onclick.includes('addInstanceGroup') || 
            onclick.includes('addTimetable') || 
            onclick.includes('addResource')) {
            btn.setAttribute('onclick', onclick.replace(/\(\d+\)/, `(${scenarioIndex})`));
        } else if (onclick.includes('addElementResource')) {
            // Mantieni il node_id ma aggiorna lo scenario index
            const match = onclick.match(/addElementResource\((\d+),\s*'([^']+)'\)/);
            if (match) {
                const elementId = match[2];
                btn.setAttribute('onclick', `addElementResource(${scenarioIndex}, '${elementId}')`);
            }
        }
    });
}

/**
 * Aggiorna i container delle risorse degli elementi BPMN
 */
function updateElementResourceContainers(container, scenarioIndex) {
    const elementResourceContainers = container.querySelectorAll('[class*="element-resources-container-"]');
    elementResourceContainers.forEach(resContainer => {
        const classes = resContainer.className.split(' ');
        const oldClass = classes.find(c => c.startsWith('element-resources-container-'));
        if (oldClass) {
            const match = oldClass.match(/element-resources-container-(\d+)-(.+)/);
            if (match) {
                const oldScenarioIndex = match[1];
                const elementId = match[2];
                const newClass = `element-resources-container-${scenarioIndex}-${elementId}`;
                
                // Aggiorna la classe del container
                resContainer.classList.remove(oldClass);
                resContainer.classList.add(newClass);
                
                // AGGIUNGI: Aggiorna tutti gli input/select all'interno del container
                const resourceInputs = resContainer.querySelectorAll('.resource-input');
                resourceInputs.forEach((resourceInput, index) => {
                    const resourceIndex = index + 1; // Le risorse partono da 1
                    
                    const nameSelect = resourceInput.querySelector('select[name*="resourceName"]');
                    const amountInput = resourceInput.querySelector('input[name*="amountNeeded"]');
                    const groupInput = resourceInput.querySelector('input[name*="groupId"]');
                    
                    if (nameSelect) {
                        nameSelect.name = `scenario_${scenarioIndex}_resourceName_${resourceIndex}_${elementId}`;
                    }
                    if (amountInput) {
                        amountInput.name = `scenario_${scenarioIndex}_amountNeeded_${resourceIndex}_${elementId}`;
                    }
                    if (groupInput) {
                        groupInput.name = `scenario_${scenarioIndex}_groupId_${resourceIndex}_${elementId}`;
                    }
                });
                
                // Aggiorna il contatore per questo elemento nel nuovo scenario
                const counterKey = `${scenarioIndex}_${elementId}`;
                elementResourceCounters[counterKey] = resourceInputs.length;
            }
        }
    });
}

/**
 * Aggiorna il campo hidden con il numero di scenari
 */
function updateScenarioCount() {
    document.getElementById('number_of_scenarios').value = scenarioCount;
}


// // Inizializza i contatori al caricamento della pagina
// document.addEventListener('DOMContentLoaded', function() {
//     initializeElementResourceCounters();
// });

// document.addEventListener('change', function() {
//     console.log(scenarioCount);
//     console.log(instanceCounters);
//     console.log(timetableCounters);
//     console.log(resourceCounters);
//     console.log(elementResourceCounters);
// });