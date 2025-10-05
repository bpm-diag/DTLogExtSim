

/**
 * Aggiunge una risorsa a un elemento BPMN specifico
 */
function addElementResource(scenarioIndex, elementId) {
    const containerClass = `element-resources-container-${scenarioIndex}-${elementId}`;
    const container = document.querySelector(`.${containerClass}`);
    
    if (!container) {
        console.error(`Container ${containerClass} not found`);
        return;
    }
    
    const counterKey = `${scenarioIndex}_${elementId}`;
    const existingCount = container.querySelectorAll('.resource-input').length;
    const resourceIndex = existingCount + 1;
    elementResourceCounters[counterKey] = resourceIndex;
    
    const resourceDiv = document.createElement('div');
    resourceDiv.className = 'resource-input row mb-2';
    resourceDiv.innerHTML = `
        <div class="form-group col-md-4">
            <label for="scenario_${scenarioIndex}_resourceName_${resourceIndex}_${elementId}">Resource Name:</label>
            <select class="form-control form-control-sm" 
                    id="scenario_${scenarioIndex}_resourceName_${resourceIndex}_${elementId}"
                    name="scenario_${scenarioIndex}_resourceName_${resourceIndex}_${elementId}">
                <option value=""></option>
            </select>
        </div>
        <div class="form-group col-md-3">
            <label for="scenario_${scenarioIndex}_amountNeeded_${resourceIndex}_${elementId}">Amount Needed:</label>
            <input type="number" class="form-control form-control-sm" 
                id="scenario_${scenarioIndex}_amountNeeded_${resourceIndex}_${elementId}"
                name="scenario_${scenarioIndex}_amountNeeded_${resourceIndex}_${elementId}">
        </div>
        <div class="form-group col-md-3">
            <label for="scenario_${scenarioIndex}_groupId_${resourceIndex}_${elementId}">Group ID:</label>
            <input type="text" class="form-control form-control-sm" 
                id="scenario_${scenarioIndex}_groupId_${resourceIndex}_${elementId}"
                name="scenario_${scenarioIndex}_groupId_${resourceIndex}_${elementId}">
        </div>
        <div class="col-md-2 d-flex align-items-end">
            <button type="button" class="btn btn-sm btn-danger w-100" 
                    onclick="removeElementResource(this, ${scenarioIndex}, '${elementId}')">×</button>
        </div>
    `;
    container.appendChild(resourceDiv);
    
    updateResourceOptions(scenarioIndex);
}


/**
 * Rimuove e rinumera le risorse di un elemento BPMN
 */
function removeElementResource(button, scenarioIndex, elementId) {
    button.closest('.resource-input').remove();
    renumberElementResources(scenarioIndex, elementId);
}

function renumberElementResources(scenarioIndex, elementId) {
    const containerClass = `element-resources-container-${scenarioIndex}-${elementId}`;
    const container = document.querySelector(`.${containerClass}`);
    
    if (!container) return;
    
    const allResources = Array.from(container.querySelectorAll('.resource-input'));
    
    allResources.forEach((resourceDiv, newIndex) => {
        const resourceIndex = newIndex + 1; // Le risorse partono da 1
        
        const nameSelect = resourceDiv.querySelector('select[name*="resourceName"]');
        const amountInput = resourceDiv.querySelector('input[name*="amountNeeded"]');
        const groupInput = resourceDiv.querySelector('input[name*="groupId"]');
        
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
    
    const counterKey = `${scenarioIndex}_${elementId}`;
    elementResourceCounters[counterKey] = allResources.length;
}

/**
 * Inizializza i listener per tutti gli elementi BPMN di uno scenario
 */
function initializeActivityDurationListeners(scenarioIndex) {
    const scenarioContainer = document.getElementById(`scenario-${scenarioIndex}`);
    if (!scenarioContainer) return;
    
    const durationTypeSelects = scenarioContainer.querySelectorAll('.duration-type');
    durationTypeSelects.forEach(select => {
        const elementId = select.dataset.elementId;
        if (elementId) {
            // Chiama subito per impostare lo stato iniziale
            updateActivityTimeDistribution(elementId, scenarioIndex);
        }
    });
}



/**
 * Aggiunge un input per instance type in un gateway
 */
function addInstanceTypeInput(flowId, scenarioIndex) {
    const instanceTypesContainer = document.querySelector(
        `.instance-types-container[data-flow-id="${flowId}"][data-scenario="${scenarioIndex}"]`
    );
    
    if (!instanceTypesContainer) {
        console.error(`Instance types container not found for flow ${flowId} in scenario ${scenarioIndex}`);
        return;
    }
    
    const instanceTypeCount = instanceTypesContainer.querySelectorAll('.instance-type-input').length + 1;
    const instanceTypeInput = document.createElement('div');
    instanceTypeInput.className = 'instance-type-input row mb-2';
    instanceTypeInput.innerHTML = `
        <div class="form-group col-md-10">
            <select class="form-control" 
                    id="scenario_${scenarioIndex}_forcedInstanceType_${flowId}_${instanceTypeCount}" 
                    name="scenario_${scenarioIndex}_forcedInstanceType_${flowId}_${instanceTypeCount}">
                <option value=""></option> 
            </select>
        </div>
        <div class="col-md-2 d-flex align-items-end">
            <button type="button" class="btn btn-sm btn-danger w-100" 
                    onclick="this.closest('.instance-type-input').remove()">×</button>
        </div>
    `;
    instanceTypesContainer.appendChild(instanceTypeInput);
    updateInstanceTypeSelects(scenarioIndex);
}

/**
 * Aggiorna i select dei forced instance types nei gateway
 */
function updateInstanceTypeSelects(scenarioIndex) {
    // Raccogli tutti i tipi di istanza da questo scenario
    let instanceTypes = [];
    const instanceTypeInputs = document.querySelectorAll(`#instances-container-${scenarioIndex} input[id*="instance_type_"]`);
    instanceTypeInputs.forEach(input => {
        if (input.value) {
            instanceTypes.push(input.value);
        }
    });

    // Aggiorna i select nei gateway di questo scenario
    const instanceTypeSelects = document.querySelectorAll(`#gateways-container-${scenarioIndex} select[name*="forcedInstanceType"]`);
    instanceTypeSelects.forEach(select => {
        const selectedValue = select.value;
        select.innerHTML = '<option value=""></option>';
        instanceTypes.forEach(instanceType => {
            const isSelected = instanceType === selectedValue;
            select.add(new Option(instanceType, instanceType, false, isSelected));
        });
    });
}

/**
 * Inizializza i listener per tutti i catch events di uno scenario
 */
function initializeCatchEventDurationListeners(scenarioIndex) {
    const scenarioContainer = document.getElementById(`scenario-${scenarioIndex}`);
    if (!scenarioContainer) return;
    
    const durationTypeSelects = scenarioContainer.querySelectorAll('.catch-event-duration-type');
    durationTypeSelects.forEach(select => {
        const elementId = select.dataset.elementId;
        if (elementId) {
            updateCatchEventTimeDistribution(elementId, scenarioIndex);
        }
    });
}