/**
 * Aggiunge un gruppo di istanze a uno scenario
 */
function addInstanceGroup(scenarioIndex) {
    const container = document.getElementById(`instances-container-${scenarioIndex}`);
    if (!container) {
        console.error(`Container instances-container-${scenarioIndex} not found`);
        return;
    }
    
    const instanceIndex = instanceCounters[scenarioIndex];
    instanceCounters[scenarioIndex]++;
    
    const instanceDiv = document.createElement('div');
    instanceDiv.className = 'instance-group mb-3 box';
    instanceDiv.innerHTML = `
        <div class="row">
            <div class="form-group col-md-6">
                <label for="scenario_${scenarioIndex}_instance_type_${instanceIndex}">Instance Type:</label>
                <input type="text" class="form-control" 
                       id="scenario_${scenarioIndex}_instance_type_${instanceIndex}" 
                       name="scenario_${scenarioIndex}_instance_type_${instanceIndex}" required>
            </div>
            <div class="form-group col-md-6">
                <label for="scenario_${scenarioIndex}_instance_count_${instanceIndex}">Count:</label>
                <input type="number" class="form-control" 
                       id="scenario_${scenarioIndex}_instance_count_${instanceIndex}" 
                       name="scenario_${scenarioIndex}_instance_count_${instanceIndex}" required>
            </div>
            <div class="col-md-12 mt-3">
                <button type="button" class="btn btn-danger btn-block" 
                        onclick="removeInstanceGroup(this, ${scenarioIndex})">Remove instance type</button>
            </div>
        </div>
    `;
    container.appendChild(instanceDiv);
    
    // Add event listener per aggiornare i select dei gateway
    const instanceTypeInput = document.getElementById(`scenario_${scenarioIndex}_instance_type_${instanceIndex}`);
    instanceTypeInput.addEventListener('input', () => updateInstanceTypeSelects(scenarioIndex));
}

function removeInstanceGroup(button, scenarioIndex) {
    const instanceGroupDiv = button.closest('.instance-group');
    instanceGroupDiv.remove();
    
    // Rinumera tutte le istanze rimaste
    renumberInstances(scenarioIndex);
    
    updateInstanceTypeSelects(scenarioIndex);
}

function renumberInstances(scenarioIndex) {
    const container = document.getElementById(`instances-container-${scenarioIndex}`);
    const allInstances = Array.from(container.querySelectorAll('.instance-group'));
    
    allInstances.forEach((instanceDiv, newIndex) => {
        // Trova tutti gli input e label in questa istanza
        const typeInput = instanceDiv.querySelector('input[name*="_instance_type_"]');
        const countInput = instanceDiv.querySelector('input[name*="_instance_count_"]');
        const typeLabel = instanceDiv.querySelector('label[for*="_instance_type_"]');
        const countLabel = instanceDiv.querySelector('label[for*="_instance_count_"]');
        
        if (typeInput) {
            typeInput.id = `scenario_${scenarioIndex}_instance_type_${newIndex}`;
            typeInput.name = `scenario_${scenarioIndex}_instance_type_${newIndex}`;
            
            // Rimuovi il vecchio listener e aggiungi quello nuovo
            const newInput = typeInput.cloneNode(true);
            newInput.addEventListener('input', () => updateInstanceTypeSelects(scenarioIndex));
            typeInput.parentNode.replaceChild(newInput, typeInput);
        }
        
        if (countInput) {
            countInput.id = `scenario_${scenarioIndex}_instance_count_${newIndex}`;
            countInput.name = `scenario_${scenarioIndex}_instance_count_${newIndex}`;
        }
        
        if (typeLabel) {
            typeLabel.setAttribute('for', `scenario_${scenarioIndex}_instance_type_${newIndex}`);
        }
        
        if (countLabel) {
            countLabel.setAttribute('for', `scenario_${scenarioIndex}_instance_count_${newIndex}`);
        }
    });
    
    // Aggiorna il contatore
    instanceCounters[scenarioIndex] = allInstances.length;
}