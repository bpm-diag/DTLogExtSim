/**
 * Aggiunge una risorsa a uno scenario
 */
function addResource(scenarioIndex) {
    const container = document.getElementById(`resources-container-${scenarioIndex}`);
    if (!container) {
        console.error(`Container resources-container-${scenarioIndex} not found`);
        return;
    }
    
    const resourceIndex = resourceCounters[scenarioIndex];
    resourceCounters[scenarioIndex]++;
    
    const resourceId = `scenario_${scenarioIndex}_resource_${resourceIndex}`;
    
    const resourceDiv = document.createElement('div');
    resourceDiv.className = 'resource-group mb-3 box';
    resourceDiv.setAttribute('data-resource-id', resourceId);
    
    resourceDiv.innerHTML = `
        <div class="row">
            <div class="form-group col-md-3">
                <label for="${resourceId}_name">Name:</label>
                <input type="text" class="form-control" 
                       id="${resourceId}_name" 
                       name="scenario_${scenarioIndex}_resource_name_${resourceIndex}" required>
            </div>
            <div class="form-group col-md-3">
                <label for="${resourceId}_amount">Amount:</label>
                <input type="number" class="form-control" 
                       id="${resourceId}_amount" 
                       name="scenario_${scenarioIndex}_resource_amount_${resourceIndex}" required>
            </div>
            <div class="form-group col-md-3">
                <label for="${resourceId}_cost">Cost per Hour:</label>
                <input type="number" class="form-control" 
                       id="${resourceId}_cost" 
                       name="scenario_${scenarioIndex}_resource_cost_${resourceIndex}" required>
            </div>
            <div class="form-group col-md-3">
                <label for="${resourceId}_timetable">Timetable:</label>
                <select id="${resourceId}_timetable" 
                        name="scenario_${scenarioIndex}_resource_timetable_${resourceIndex}" class="form-control">
                </select>
            </div>
        </div>
        <div class="setup-time-container" data-resource-id="${resourceId}">
            <h5>Setup Time (optional):</h5>
            <div class="row">
                <div class="form-group col-md-3">
                    <label for="${resourceId}_setupTimeType">Type:</label>
                    <select class="form-control setup-time-type" 
                            id="${resourceId}_setupTimeType" 
                            name="${resourceId}_setupTimeType" 
                            data-resource-id="${resourceId}">
                        <option value="FIXED">Fixed</option>
                        <option value="NORMAL">Normal</option>
                        <option value="EXPONENTIAL">Exponential</option>
                        <option value="UNIFORM">Uniform</option>
                        <option value="TRIANGULAR">Triangular</option>
                        <option value="LOGNORMAL">Log-Normal</option>
                        <option value="GAMMA">Gamma</option>
                        <option value="HISTOGRAM">Histogram</option>
                    </select>
                </div>
                <div class="form-group col-md-3 setup-time-param" data-param-type="mean" data-resource-id="${resourceId}">
                    <label for="${resourceId}_setupTimeMean">Mean:</label>
                    <input type="number" class="form-control" 
                           id="${resourceId}_setupTimeMean" 
                           name="${resourceId}_setupTimeMean">
                </div>
                <div class="form-group col-md-3 setup-time-param" data-param-type="arg1" data-resource-id="${resourceId}" style="display: none;">
                    <label for="${resourceId}_setupTimeArg1">Arg1:</label>
                    <input type="number" class="form-control" 
                           id="${resourceId}_setupTimeArg1" 
                           name="${resourceId}_setupTimeArg1">
                </div>
                <div class="form-group col-md-3 setup-time-param" data-param-type="arg2" data-resource-id="${resourceId}" style="display: none;">
                    <label for="${resourceId}_setupTimeArg2">Arg2:</label>
                    <input type="number" class="form-control" 
                           id="${resourceId}_setupTimeArg2" 
                           name="${resourceId}_setupTimeArg2">
                </div>
            </div>
            <div class="row">
                <div class="form-group col-md-6">
                    <label for="${resourceId}_setupTimeUnit">Time Unit:</label>
                    <select class="form-control" 
                            id="${resourceId}_setupTimeUnit" 
                            name="${resourceId}_setupTimeUnit">
                        <option value="seconds">Seconds</option>
                        <option value="minutes">Minutes</option>
                        <option value="hours">Hours</option>
                        <option value="days">Days</option>
                    </select>
                </div>
                <div class="form-group col-md-6">
                    <label for="${resourceId}_maxUsage">Max Usage before setup time is needed:</label>
                    <input type="number" class="form-control" 
                           id="${resourceId}_maxUsage" 
                           name="scenario_${scenarioIndex}_resource_maxUsage_${resourceIndex}">
                </div>
            </div>
        </div>
        <button type="button" class="btn btn-danger mt-3" 
                onclick="removeResource('${resourceId}', ${scenarioIndex})">Remove Resource</button>
    `;
    
    container.appendChild(resourceDiv);
    
    // Add event listener per il nome per aggiornare i select degli elementi
    document.getElementById(`${resourceId}_name`).addEventListener('input', function() {
        updateResourceOptions(scenarioIndex);
    });
    
    updateTimetableOptions(scenarioIndex);
    updateResourceOptions(scenarioIndex);

    // Inizializza lo stato della UI per il setup time (label e visibilità)
    updateResourceSetupTimeDistribution(scenarioIndex, resourceId);
}

function removeResource(resourceId, scenarioIndex) {
    const resourceDiv = document.querySelector(`.resource-group[data-resource-id="${resourceId}"]`);
    if (resourceDiv) {
        resourceDiv.remove();
        renumberResources(scenarioIndex);
        updateResourceOptions(scenarioIndex);
    }
}

function renumberResources(scenarioIndex) {
    const container = document.getElementById(`resources-container-${scenarioIndex}`);
    const allResources = Array.from(container.querySelectorAll('.resource-group'));
    
    allResources.forEach((resourceDiv, newIndex) => {
        const oldResourceId = resourceDiv.getAttribute('data-resource-id');
        const newResourceId = `scenario_${scenarioIndex}_resource_${newIndex}`;
        
        // Aggiorna data-resource-id
        resourceDiv.setAttribute('data-resource-id', newResourceId);
        
        // Aggiorna tutti gli input della risorsa
        const nameInput = resourceDiv.querySelector('input[id$="_name"]');
        const amountInput = resourceDiv.querySelector('input[id$="_amount"]');
        const costInput = resourceDiv.querySelector('input[id$="_cost"]');
        const timetableSelect = resourceDiv.querySelector('select[id$="_timetable"]');
        const maxUsageInput = resourceDiv.querySelector('input[name*="_resource_maxUsage_"]');
        
        if (nameInput) {
            const nameValue = nameInput.value;
            nameInput.id = `${newResourceId}_name`;
            nameInput.name = `scenario_${scenarioIndex}_resource_name_${newIndex}`;
            
            // Ricrea listener
            const newInput = nameInput.cloneNode(true);
            newInput.value = nameValue;
            newInput.addEventListener('input', () => updateResourceOptions(scenarioIndex));
            nameInput.parentNode.replaceChild(newInput, nameInput);
        }
        
        if (amountInput) {
            amountInput.id = `${newResourceId}_amount`;
            amountInput.name = `scenario_${scenarioIndex}_resource_amount_${newIndex}`;
        }
        
        if (costInput) {
            costInput.id = `${newResourceId}_cost`;
            costInput.name = `scenario_${scenarioIndex}_resource_cost_${newIndex}`;
        }
        
        if (timetableSelect) {
            timetableSelect.id = `${newResourceId}_timetable`;
            timetableSelect.name = `scenario_${scenarioIndex}_resource_timetable_${newIndex}`;
        }
        
        if (maxUsageInput) {
            maxUsageInput.id = `${newResourceId}_maxUsage`;
            maxUsageInput.name = `scenario_${scenarioIndex}_resource_maxUsage_${newIndex}`;
        }
        
        // Aggiorna setup time container e relativi campi
        const setupTimeContainer = resourceDiv.querySelector('.setup-time-container');
        if (setupTimeContainer) {
            setupTimeContainer.setAttribute('data-resource-id', newResourceId);
            
            const setupTypeSelect = setupTimeContainer.querySelector('.setup-time-type');
            const meanInput = setupTimeContainer.querySelector('input[id$="_setupTimeMean"]');
            const arg1Input = setupTimeContainer.querySelector('input[id$="_setupTimeArg1"]');
            const arg2Input = setupTimeContainer.querySelector('input[id$="_setupTimeArg2"]');
            const timeUnitSelect = setupTimeContainer.querySelector('select[id$="_setupTimeUnit"]');
            
            if (setupTypeSelect) {
                setupTypeSelect.id = `${newResourceId}_setupTimeType`;
                setupTypeSelect.name = `${newResourceId}_setupTimeType`;
                setupTypeSelect.setAttribute('data-resource-id', newResourceId);
            }
            
            if (meanInput) {
                meanInput.id = `${newResourceId}_setupTimeMean`;
                meanInput.name = `${newResourceId}_setupTimeMean`;
            }
            
            if (arg1Input) {
                arg1Input.id = `${newResourceId}_setupTimeArg1`;
                arg1Input.name = `${newResourceId}_setupTimeArg1`;
            }
            
            if (arg2Input) {
                arg2Input.id = `${newResourceId}_setupTimeArg2`;
                arg2Input.name = `${newResourceId}_setupTimeArg2`;
            }
            
            if (timeUnitSelect) {
                timeUnitSelect.id = `${newResourceId}_setupTimeUnit`;
                timeUnitSelect.name = `${newResourceId}_setupTimeUnit`;
            }
            
            // Aggiorna data-resource-id sui param divs
            const paramDivs = setupTimeContainer.querySelectorAll('.setup-time-param');
            paramDivs.forEach(div => {
                div.setAttribute('data-resource-id', newResourceId);
            });
        }
        
        // Aggiorna label for
        const labels = resourceDiv.querySelectorAll('label[for]');
        labels.forEach(label => {
            const forAttr = label.getAttribute('for');
            if (forAttr.includes(oldResourceId)) {
                label.setAttribute('for', forAttr.replace(oldResourceId, newResourceId));
            }
        });
        
        // Aggiorna onclick del bottone remove
        const removeBtn = resourceDiv.querySelector('button[onclick*="removeResource"]');
        if (removeBtn) {
            removeBtn.setAttribute('onclick', `removeResource('${newResourceId}', ${scenarioIndex})`);
        }
    });
    
    resourceCounters[scenarioIndex] = allResources.length;
}



function updateTimetableOptions(scenarioIndex) {
    // Aggiorna i select dei timetable per tutte le risorse di questo scenario
    const resourceSelects = document.querySelectorAll(`#resources-container-${scenarioIndex} select[id$="_timetable"]`);
    
    resourceSelects.forEach(select => {
        const selectedValue = select.value;
        select.innerHTML = '';
        
        // Cerca tutti i timetable di questo scenario
        const timetableInputs = document.querySelectorAll(`#timetables-container-${scenarioIndex} input[id*="_timetable_name_"]`);
        timetableInputs.forEach(input => {
            const timetableName = input.value;
            if (timetableName) {
                const option = new Option(timetableName, timetableName, false, timetableName === selectedValue);
                select.add(option);
            }
        });
    });
}

function updateResourceOptions(scenarioIndex) {
    // Aggiorna i select delle risorse per tutti gli elementi BPMN di questo scenario
    const resourceSelects = document.querySelectorAll(`#scenario-${scenarioIndex} .element-group select[name*="resourceName"]`);
    
    // Raccogli tutti i nomi delle risorse
    const resourceNames = [];
    const resourceInputs = document.querySelectorAll(`#resources-container-${scenarioIndex} input[id$="_name"]`);
    resourceInputs.forEach(input => {
        if (input.value) {
            resourceNames.push(input.value);
        }
    });
    
    resourceSelects.forEach(select => {
        const selectedValue = select.value;
        select.innerHTML = '<option value=""></option>';
        
        resourceNames.forEach(name => {
            const option = new Option(name, name, false, name === selectedValue);
            select.add(option);
        });
    });
}