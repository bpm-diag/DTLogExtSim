function setCurrentDateTime(scenarioIndex) {
    const now = new Date();
    const defaultDateTime = now.toISOString().slice(0, 16);
    document.getElementById(`scenario_${scenarioIndex}_start_date`).value = defaultDateTime;
}

//listener per modificare il display della distribuzione temporale sia per inter-arrival che per resources setup time che per bpmn tasks duration distribution che per catch events
function updateInterArrivalTimeDistribution(scenarioIndex) {
    const timeTypeSelect = document.getElementById(`scenario_${scenarioIndex}_arrival_type`);
    const selectedType = timeTypeSelect.value;
    
    const meanParam = document.getElementById(`scenario_${scenarioIndex}_arrival_mean`);
    const meanContainer = meanParam.closest(".col-md-2");
    const labelMean = meanContainer.querySelector('label');

    const arg1Param = document.getElementById(`scenario_${scenarioIndex}_arrival_arg1`);
    const arg1Container = arg1Param.closest(".col-md-2");
    const labelArg1 = arg1Container.querySelector('label');

    const arg2Param = document.getElementById(`scenario_${scenarioIndex}_arrival_arg2`);
    const arg2Container = arg2Param.closest(".col-md-2");
    const labelArg2 = arg2Container.querySelector('label');

    if (selectedType === 'FIXED') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'none';
        arg2Container.style.display = 'none';
        labelMean.textContent = "Amount:";
    } else if (selectedType === 'NORMAL') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'none';
        labelMean.textContent = "Mean:";
        labelArg1.textContent = 'Std. Deviation:';
    } else if (selectedType === 'EXPONENTIAL') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'none';
        arg2Container.style.display = 'none';
        labelMean.textContent = "Mean:";
    } else if (selectedType === 'UNIFORM') {
        meanContainer.style.display = 'none';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'block';
        labelArg1.textContent = 'Low:';
        labelArg2.textContent = 'High:';
    } else if (selectedType === 'TRIANGULAR') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'block';
        labelMean.textContent = 'Mode:';
        labelArg1.textContent = 'Low:';
        labelArg2.textContent = 'High:';
    } else if (selectedType === 'LOGNORMAL') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'none';
        labelMean.textContent = 'Mean:';
        labelArg1.textContent = 'Variance:';
    } else if (selectedType === 'GAMMA') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'none';
        labelMean.textContent = 'Mean:';
        labelArg1.textContent = 'Variance:';
    } else if (selectedType === 'HISTOGRAM') {
        meanContainer.style.display = 'none';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'block';
        labelArg1.textContent = 'Bin Edges (comma-separated):';
        labelArg2.textContent = 'Frequencies (comma-separated):';
    }
    
}

function updateResourceSetupTimeDistribution(scenarioIndex, resourceId) {
    const setupTimeTypeSelect = document.getElementById(`${resourceId}_setupTimeType`);

    const selectedType = setupTimeTypeSelect.value;
    const setupTimeContainer = document.querySelector(`.setup-time-container[data-resource-id="${resourceId}"]`);

    const meanParam = setupTimeContainer.querySelector('.setup-time-param[data-param-type="mean"]');
    const arg1Param = setupTimeContainer.querySelector('.setup-time-param[data-param-type="arg1"]');
    const arg2Param = setupTimeContainer.querySelector('.setup-time-param[data-param-type="arg2"]');


    const labelMean = meanParam.querySelector('label');
    const labelArg1 = arg1Param.querySelector('label');
    const labelArg2 = arg2Param.querySelector('label');

    if (selectedType === 'FIXED') {
        meanParam.style.display = 'block';
        arg1Param.style.display = 'none';
        arg2Param.style.display = 'none';
        labelMean.textContent = "Amount:";
    } else if (selectedType === 'NORMAL') {
        meanParam.style.display = 'block';
        arg1Param.style.display = 'block';
        arg2Param.style.display = 'none';
        labelMean.textContent = "Mean:";
        labelArg1.textContent = 'Std. Deviation:';
    } 
    else if (selectedType === 'EXPONENTIAL') {
        meanParam.style.display = 'block';
        arg1Param.style.display = 'none';
        arg2Param.style.display = 'none';
        labelMean.textContent = "Mean:";
    } else if (selectedType === 'UNIFORM') {
        meanParam.style.display = 'none';
        arg1Param.style.display = 'block';
        arg2Param.style.display = 'block';
        labelArg1.textContent = 'Low:';
        labelArg2.textContent = 'High:';
    } else if (selectedType === 'TRIANGULAR') {
        meanParam.style.display = 'block';
        arg1Param.style.display = 'block';
        arg2Param.style.display = 'block';
        labelMean.textContent = 'Mode:';
        labelArg1.textContent = 'Low:';
        labelArg2.textContent = 'High:';
    } else if (selectedType === 'LOGNORMAL') {
        meanParam.style.display = 'block';
        arg1Param.style.display = 'block';
        arg2Param.style.display = 'none';
        labelMean.textContent = 'Mean:';
        labelArg1.textContent = 'Variance:';
    } else if (selectedType === 'GAMMA') {
        meanParam.style.display = 'block';
        arg1Param.style.display = 'block';
        arg2Param.style.display = 'none';
        labelMean.textContent = 'Mean:';
        labelArg1.textContent = 'Variance:';
    } else if (selectedType === 'HISTOGRAM') {
        meanParam.style.display = 'none';
        arg1Param.style.display = 'block';
        arg2Param.style.display = 'block';
        labelArg1.textContent = 'Bin Edges (comma-separated):';
        labelArg2.textContent = 'Frequencies (comma-separated):';
    }
}

function updateActivityTimeDistribution(elementId, scenarioIndex) {
    const typeSelectId = `scenario_${scenarioIndex}_durationType_${elementId}`;
    const typeSelect = document.getElementById(typeSelectId);

    
    const selectedType = typeSelect.value;
    const elementGroup = typeSelect.closest('.element-group');
    
    // Trova i container dei parametri
    const meanContainer = elementGroup.querySelector('.form-group:has(input[id$="_durationMean_' + elementId + '"])');
    const arg1Container = elementGroup.querySelector('.duration-param-arg1');
    const arg2Container = elementGroup.querySelector('.duration-param-arg2');
    
    const labelMean = meanContainer.querySelector('label');
    const labelArg1 = arg1Container.querySelector('label');
    const labelArg2 = arg2Container.querySelector('label');

    if (selectedType === 'FIXED') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'none';
        arg2Container.style.display = 'none';
        labelMean.textContent = "Amount:";
    } else if (selectedType === 'NORMAL') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'none';
        labelMean.textContent = "Mean:";
        labelArg1.textContent = 'Std. Deviation:';
    } 
    else if (selectedType === 'EXPONENTIAL') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'none';
        arg2Container.style.display = 'none';
        labelMean.textContent = "Mean:";
    } else if (selectedType === 'UNIFORM') {
        meanContainer.style.display = 'none';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'block';
        labelArg1.textContent = 'Low:';
        labelArg2.textContent = 'High:';
    } else if (selectedType === 'TRIANGULAR') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'block';
        labelMean.textContent = 'Mode:';
        labelArg1.textContent = 'Low:';
        labelArg2.textContent = 'High:';
    } else if (selectedType === 'LOGNORMAL') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'none';
        labelMean.textContent = 'Mean:';
        labelArg1.textContent = 'Variance:';
    } else if (selectedType === 'GAMMA') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'none';
        labelMean.textContent = 'Mean:';
        labelArg1.textContent = 'Variance:';
    } else if (selectedType === 'HISTOGRAM') {
        meanContainer.style.display = 'none';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'block';
        labelArg1.textContent = 'Bin Edges (comma-separated):';
        labelArg2.textContent = 'Frequencies (comma-separated):';
    }

}

/**
 * Aggiorna i parametri della duration distribution per catch events
 */
function updateCatchEventTimeDistribution(elementId, scenarioIndex) {
    const typeSelectId = `scenario_${scenarioIndex}_catchEventDurationType_${elementId}`;
    const typeSelect = document.getElementById(typeSelectId);

    
    const selectedType = typeSelect.value;
    const catchEventGroup = document.querySelector(`#scenario-${scenarioIndex} .catch-event-group`);
    
    // Trova i container dei parametri
    const meanContainer = catchEventGroup.querySelector('.form-group:has(input[id*="_catchEventDurationMean_"])');
    const arg1Container = catchEventGroup.querySelector('.catch-event-duration-param-arg1');
    const arg2Container = catchEventGroup.querySelector('.catch-event-duration-param-arg2');

    
    const labelMean = meanContainer.querySelector('label');
    const labelArg1 = arg1Container.querySelector('label');
    const labelArg2 = arg2Container.querySelector('label');

    if (selectedType === 'FIXED') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'none';
        arg2Container.style.display = 'none';
        labelMean.textContent = "Amount:";
    } else if (selectedType === 'NORMAL') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'none';
        labelMean.textContent = "Mean:";
        labelArg1.textContent = 'Std. Deviation:';
    } 
    else if (selectedType === 'EXPONENTIAL') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'none';
        arg2Container.style.display = 'none';
        labelMean.textContent = "Mean:";
    } else if (selectedType === 'UNIFORM') {
        meanContainer.style.display = 'none';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'block';
        labelArg1.textContent = 'Low:';
        labelArg2.textContent = 'High:';
    } else if (selectedType === 'TRIANGULAR') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'block';
        labelMean.textContent = 'Mode:';
        labelArg1.textContent = 'Low:';
        labelArg2.textContent = 'High:';
    } else if (selectedType === 'LOGNORMAL') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'none';
        labelMean.textContent = 'Mean:';
        labelArg1.textContent = 'Variance:';
    } else if (selectedType === 'GAMMA') {
        meanContainer.style.display = 'block';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'none';
        labelMean.textContent = 'Mean:';
        labelArg1.textContent = 'Variance:';
    } else if (selectedType === 'HISTOGRAM') {
        meanContainer.style.display = 'none';
        arg1Container.style.display = 'block';
        arg2Container.style.display = 'block';
        labelArg1.textContent = 'Bin Edges (comma-separated):';
        labelArg2.textContent = 'Frequencies (comma-separated):';
    }
}

document.addEventListener('DOMContentLoaded', function() {
    setCurrentDateTime(0);
    updateInterArrivalTimeDistribution(0);
    initializeActivityDurationListeners(0);
    initializeCatchEventDurationListeners(0);

    // Event delegation per tutti i select
    document.addEventListener('change', (event) => {
        // Arrival type selects
        if (event.target.matches('select[id*="_arrival_type"]')) {
            const scenarioMatch = event.target.id.match(/scenario_(\d+)_arrival_type/);
            if (scenarioMatch) {
                const scenarioIndex = parseInt(scenarioMatch[1]);
                updateInterArrivalTimeDistribution(scenarioIndex);
            }
        }
        
        // Setup time type selects
        if (event.target.matches('select.setup-time-type')) {
            const resourceId = event.target.dataset.resourceId;
            if (resourceId) {
                const scenarioMatch = resourceId.match(/scenario_(\d+)_resource_/);
                const scenarioIndex = scenarioMatch ? parseInt(scenarioMatch[1]) : 0;
                updateResourceSetupTimeDistribution(scenarioIndex, resourceId);
            }
        }


        if (event.target.matches('.duration-type')) {
            const elementId = event.target.dataset.elementId;
            const scenarioIndex = event.target.dataset.scenario;
            if (elementId && scenarioIndex !== undefined) {
                updateActivityTimeDistribution(elementId, parseInt(scenarioIndex));
            }
        }

        if (event.target.matches('.catch-event-duration-type')) {
            const elementId = event.target.dataset.elementId;
            const scenarioIndex = event.target.dataset.scenario;
            if (elementId && scenarioIndex !== undefined) {
                updateCatchEventTimeDistribution(elementId, parseInt(scenarioIndex));
            }
        }
    });

    // Event delegation per il bottone "Add Instance Type" nei gateway
    document.addEventListener('click', (event) => {
        if (event.target.matches('.add-instance-type')) {
            const flowId = event.target.dataset.flowId;
            const scenarioIndex = parseInt(event.target.dataset.scenario);
            if (flowId && scenarioIndex !== undefined) {
                addInstanceTypeInput(flowId, scenarioIndex);
            }
        }
    });
});