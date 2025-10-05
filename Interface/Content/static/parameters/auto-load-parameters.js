// ========================================
// AUTO-LOAD PARAMETERS FROM EXTRA.JSON (MULTI-SCENARIO)
// ========================================

document.addEventListener('DOMContentLoaded', function() {
    console.log('=== Starting auto-load parameters (multi-scenario) ===');

    // Verifica se extraData è disponibile
    if (typeof extraData === 'undefined' || !extraData) {
        console.log('No extra data to load - using empty form');
        return;
    }

    console.log('Extra data found:', extraData);

    // Determina quanti scenari ci sono (escludendo logging_opt)
    const scenarioIndices = Object.keys(extraData).filter(key => key !== 'logging_opt' && !isNaN(key)).map(Number);
    const numberOfScenarios = scenarioIndices.length;
    
    console.log(`Found ${numberOfScenarios} scenarios to load`);

    // ========================================
    // CREA GLI SCENARI NECESSARI
    // ========================================
    // Aggiungi scenari se necessario (il primo scenario 0 esiste già)
    for (let i = 1; i < numberOfScenarios; i++) {
        addScenario();
    }

    // Attendi che gli scenari siano stati creati
    setTimeout(() => {
        // ========================================
        // CARICA OGNI SCENARIO
        // ========================================
        scenarioIndices.forEach(scenarioIndex => {
            const scenarioData = extraData[scenarioIndex];
            console.log(`\n--- Loading Scenario ${scenarioIndex} ---`);
            
            loadScenarioData(scenarioIndex, scenarioData);
        });

        // ========================================
        // CARICA LOGGING OPTION (GLOBALE)
        // ========================================
        if (extraData.logging_opt !== undefined) {
            const loggingCheckbox = document.getElementById('logging_opt');
            if (loggingCheckbox) {
                loggingCheckbox.checked = (extraData.logging_opt === "1" || extraData.logging_opt === 1 || extraData.logging_opt === true);
            }
            console.log('✓ Logging option loaded');
        }

        console.log('\n=== Auto-load parameters completed successfully ===');
    }, 200 * numberOfScenarios); // Attendi che tutti gli scenari siano stati creati
});

// ========================================
// FUNZIONE PER CARICARE I DATI DI UN SINGOLO SCENARIO
// ========================================
function loadScenarioData(scenarioIndex, scenarioData) {
    // 1. START DATE
    if (scenarioData.startDateTime) {
        const startDateInput = document.getElementById(`scenario_${scenarioIndex}_start_date`);
        if (startDateInput) {
            const dateStr = scenarioData.startDateTime.replace(' ', 'T').slice(0, 16);
            startDateInput.value = dateStr;
        }
        console.log('  ✓ Start date loaded');
    }

    // 2. INTER-ARRIVAL TIME
    if (scenarioData.arrivalRateDistribution) {
        const arrival = scenarioData.arrivalRateDistribution;

        const typeSelect = document.getElementById(`scenario_${scenarioIndex}_arrival_type`);
        if (typeSelect && arrival.type) {
            typeSelect.value = arrival.type;
            typeSelect.dispatchEvent(new Event('change'));
        }

        setTimeout(() => {
            if (arrival.mean) {
                const meanInput = document.getElementById(`scenario_${scenarioIndex}_arrival_mean`);
                if (meanInput) meanInput.value = arrival.mean;
            }
            if (arrival.arg1) {
                const arg1Input = document.getElementById(`scenario_${scenarioIndex}_arrival_arg1`);
                if (arg1Input) arg1Input.value = arrival.arg1;
            }
            if (arrival.arg2) {
                const arg2Input = document.getElementById(`scenario_${scenarioIndex}_arrival_arg2`);
                if (arg2Input) arg2Input.value = arrival.arg2;
            }
        }, 50);

        if (arrival.timeUnit) {
            const timeUnitSelect = document.getElementById(`scenario_${scenarioIndex}_arrival_time_unit`);
            if (timeUnitSelect) timeUnitSelect.value = arrival.timeUnit;
        }

        console.log('  ✓ Arrival rate distribution loaded');
    }

    // 3. PROCESS INSTANCES
    if (scenarioData.processInstances && scenarioData.processInstances.length > 0) {
        console.log('  Loading process instances:', scenarioData.processInstances.length);

        scenarioData.processInstances.forEach((instance, index) => {
            addInstanceGroup(scenarioIndex);
            
            const currentIndex = instanceCounters[scenarioIndex] - 1;
            const typeInput = document.getElementById(`scenario_${scenarioIndex}_instance_type_${currentIndex}`);
            const countInput = document.getElementById(`scenario_${scenarioIndex}_instance_count_${currentIndex}`);
            
            if (typeInput) {
                typeInput.value = instance.type || '';
                typeInput.dispatchEvent(new Event('input'));
            }
            if (countInput) countInput.value = instance.count || '';
        });

        console.log('  ✓ Process instances loaded');
    }

    // 4. TIMETABLES
    if (scenarioData.timetables && scenarioData.timetables.length > 0) {
        console.log('  Loading timetables:', scenarioData.timetables.length);

        scenarioData.timetables.forEach((timetable, index) => {
            addTimetable(scenarioIndex);
            
            const currentTimetableIndex = timetableCounters[scenarioIndex] - 1;
            
            const nameInput = document.getElementById(`scenario_${scenarioIndex}_timetable_name_${currentTimetableIndex}`);
            if (nameInput) {
                nameInput.value = timetable.name || '';
                nameInput.dispatchEvent(new Event('input'));
            }
            
            if (timetable.rules && timetable.rules.length > 0) {
                timetable.rules.forEach((rule, ruleIndex) => {
                    addRule(scenarioIndex, currentTimetableIndex);
                    
                    const currentRuleIndex = window.ruleCounters[scenarioIndex][currentTimetableIndex];
                    
                    const fromTimeInput = document.getElementById(`scenario_${scenarioIndex}_rule_from_time_${currentTimetableIndex}_${currentRuleIndex}`);
                    const toTimeInput = document.getElementById(`scenario_${scenarioIndex}_rule_to_time_${currentTimetableIndex}_${currentRuleIndex}`);
                    const fromDaySelect = document.getElementById(`scenario_${scenarioIndex}_rule_from_day_${currentTimetableIndex}_${currentRuleIndex}`);
                    const toDaySelect = document.getElementById(`scenario_${scenarioIndex}_rule_to_day_${currentTimetableIndex}_${currentRuleIndex}`);
                    
                    if (fromTimeInput) fromTimeInput.value = rule.fromTime ? rule.fromTime.slice(0, 5) : '';
                    if (toTimeInput) toTimeInput.value = rule.toTime ? rule.toTime.slice(0, 5) : '';
                    if (fromDaySelect) fromDaySelect.value = rule.fromWeekDay || 'MONDAY';
                    if (toDaySelect) toDaySelect.value = rule.toWeekDay || 'FRIDAY';
                });
            }
        });

        console.log('  ✓ Timetables loaded');
    }

    // 5. RESOURCES
    if (scenarioData.resources && scenarioData.resources.length > 0) {
        console.log('  Loading resources:', scenarioData.resources.length);

        scenarioData.resources.forEach((resource, index) => {
            addResource(scenarioIndex);
            
            const currentResourceIndex = resourceCounters[scenarioIndex] - 1;
            const resourceId = `scenario_${scenarioIndex}_resource_${currentResourceIndex}`;
            
            const nameInput = document.getElementById(`${resourceId}_name`);
            const amountInput = document.getElementById(`${resourceId}_amount`);
            const costInput = document.getElementById(`${resourceId}_cost`);
            const timetableSelect = document.getElementById(`${resourceId}_timetable`);
            
            if (nameInput) {
                nameInput.value = resource.name || '';
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
            
            if (resource.timetableName) {
                setTimeout(() => {
                    if (timetableSelect) {
                        timetableSelect.value = resource.timetableName;
                        timetableSelect.dispatchEvent(new Event('change'));
                    }
                }, 100);
            }
            
            if (resource.setupTime) {
                const setupTime = resource.setupTime;
                
                const setupTypeSelect = document.getElementById(`${resourceId}_setupTimeType`);
                const setupMeanInput = document.getElementById(`${resourceId}_setupTimeMean`);
                const setupArg1Input = document.getElementById(`${resourceId}_setupTimeArg1`);
                const setupArg2Input = document.getElementById(`${resourceId}_setupTimeArg2`);
                const setupTimeUnitSelect = document.getElementById(`${resourceId}_setupTimeUnit`);
                
                if (setupTypeSelect && setupTime.type) {
                    setupTypeSelect.value = setupTime.type;
                    setupTypeSelect.dispatchEvent(new Event('change'));
                    
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
            
            if (resource.maxUsage) {
                const maxUsageInput = document.getElementById(`${resourceId}_maxUsage`);
                if (maxUsageInput) {
                    maxUsageInput.value = resource.maxUsage;
                    maxUsageInput.dispatchEvent(new Event('input'));
                }
            }
        });

        console.log('  ✓ Resources loaded');
    }

    // 6. ELEMENTS (Tasks)
    setTimeout(() => {
        if (scenarioData.elements && scenarioData.elements.length > 0) {
            console.log('  Loading elements:', scenarioData.elements.length);
            
            scenarioData.elements.forEach((element, index) => {
                const elementId = element.elementId;
                
                if (element.fixedCost !== undefined) {
                    const fixedCostInput = document.getElementById(`scenario_${scenarioIndex}_fixedCost_${elementId}`);
                    if (fixedCostInput) fixedCostInput.value = element.fixedCost;
                }
                
                if (element.worklistId) {
                    const worklistInput = document.getElementById(`scenario_${scenarioIndex}_worklistId_${elementId}`);
                    if (worklistInput) worklistInput.value = element.worklistId;
                }

                if (element.costThreshold !== undefined) {
                    const costThresholdInput = document.getElementById(`scenario_${scenarioIndex}_costThreshold_${elementId}`);
                    if (costThresholdInput) costThresholdInput.value = element.costThreshold;
                }
                
                if (element.durationDistribution) {
                    const duration = element.durationDistribution;
                    
                    const typeSelect = document.getElementById(`scenario_${scenarioIndex}_durationType_${elementId}`);
                    const meanInput = document.getElementById(`scenario_${scenarioIndex}_durationMean_${elementId}`);
                    const arg1Input = document.getElementById(`scenario_${scenarioIndex}_durationArg1_${elementId}`);
                    const arg2Input = document.getElementById(`scenario_${scenarioIndex}_durationArg2_${elementId}`);
                    const timeUnitSelect = document.getElementById(`scenario_${scenarioIndex}_durationTimeUnit_${elementId}`);
                    
                    if (typeSelect) {
                        typeSelect.value = duration.type || 'FIXED';
                        typeSelect.dispatchEvent(new Event('change'));
                        
                        setTimeout(() => {
                            if (meanInput) meanInput.value = duration.mean || '';
                            if (arg1Input) arg1Input.value = duration.arg1 || '';
                            if (arg2Input) arg2Input.value = duration.arg2 || '';
                        }, 50);
                    }
                    if (timeUnitSelect) timeUnitSelect.value = duration.timeUnit || 'seconds';
                }
                
                if (element.durationThreshold) {
                    const thresholdInput = document.getElementById(`scenario_${scenarioIndex}_durationThreshold_${elementId}`);
                    if (thresholdInput) thresholdInput.value = element.durationThreshold;
                }
                if (element.durationThresholdTimeUnit) {
                    const thresholdUnitSelect = document.getElementById(`scenario_${scenarioIndex}_durationThresholdTimeUnit_${elementId}`);
                    if (thresholdUnitSelect) thresholdUnitSelect.value = element.durationThresholdTimeUnit;
                }
                
                if (element.resourceIds && element.resourceIds.length > 0) {
                    const resourcesContainer = document.querySelector(`.element-resources-container-${scenarioIndex}-${elementId}`);
                    
                    if (resourcesContainer) {
                        element.resourceIds.forEach((resourceAssignment, resIndex) => {
                            addElementResource(scenarioIndex, elementId);
                            
                            const resourceIndex = resIndex + 1;
                            const resourceNameSelect = document.getElementById(`scenario_${scenarioIndex}_resourceName_${resourceIndex}_${elementId}`);
                            const amountNeededInput = document.getElementById(`scenario_${scenarioIndex}_amountNeeded_${resourceIndex}_${elementId}`);
                            const groupIdInput = document.getElementById(`scenario_${scenarioIndex}_groupId_${resourceIndex}_${elementId}`);
                            
                            setTimeout(() => {
                                if (resourceNameSelect) resourceNameSelect.value = resourceAssignment.resourceName || '';
                                if (amountNeededInput) amountNeededInput.value = resourceAssignment.amountNeeded || '';
                                if (groupIdInput) groupIdInput.value = resourceAssignment.groupId || '1';
                            }, 200);
                        });
                    }
                }
            });
            
            console.log('  ✓ Elements loaded');
        }
    }, 300);

    // 7. CATCH EVENTS
    setTimeout(() => {
        if (scenarioData.catchEvents) {
            console.log('  Loading catch events:', Object.keys(scenarioData.catchEvents).length);
            
            Object.keys(scenarioData.catchEvents).forEach(eventId => {
                const eventData = scenarioData.catchEvents[eventId];
                
                const typeSelect = document.getElementById(`scenario_${scenarioIndex}_catchEventDurationType_${eventId}`);
                const meanInput = document.getElementById(`scenario_${scenarioIndex}_catchEventDurationMean_${eventId}`);
                const arg1Input = document.getElementById(`scenario_${scenarioIndex}_catchEventDurationArg1_${eventId}`);
                const arg2Input = document.getElementById(`scenario_${scenarioIndex}_catchEventDurationArg2_${eventId}`);
                const timeUnitSelect = document.getElementById(`scenario_${scenarioIndex}_catchEventDurationTimeUnit_${eventId}`);
                
                if (typeSelect) {
                    typeSelect.value = eventData.type || 'FIXED';
                    typeSelect.dispatchEvent(new Event('change'));
                    
                    setTimeout(() => {
                        if (meanInput) meanInput.value = eventData.mean || '';
                        if (arg1Input) arg1Input.value = eventData.arg1 || '';
                        if (arg2Input) arg2Input.value = eventData.arg2 || '';
                    }, 50);
                }
                if (timeUnitSelect) timeUnitSelect.value = eventData.timeUnit || 'seconds';
            });
            
            console.log('  ✓ Catch events loaded');
        }
    }, 400);

    // 8. SEQUENCE FLOWS (Gateways)
    setTimeout(() => {
        if (scenarioData.sequenceFlows && scenarioData.sequenceFlows.length > 0) {
            console.log('  Loading sequence flows:', scenarioData.sequenceFlows.length);
            
            scenarioData.sequenceFlows.forEach((flow, index) => {
                const flowId = flow.elementId;
                
                const probInput = document.getElementById(`scenario_${scenarioIndex}_executionProbability_${flowId}`);
                if (probInput) probInput.value = flow.executionProbability || '';
                
                if (flow.types && flow.types.length > 0) {
                    const instanceTypesContainer = document.querySelector(`.instance-types-container[data-flow-id="${flowId}"][data-scenario="${scenarioIndex}"]`);
                    
                    if (instanceTypesContainer) {
                        const existingInstances = instanceTypesContainer.querySelectorAll('.instance-type-input');
                        existingInstances.forEach(inst => inst.remove());
                        
                        flow.types.forEach((typeObj, typeIndex) => {
                            addInstanceTypeInput(flowId, scenarioIndex);
                            
                            const typeIndex1Based = instanceTypesContainer.querySelectorAll('.instance-type-input').length;
                            const typeSelect = document.getElementById(`scenario_${scenarioIndex}_forcedInstanceType_${flowId}_${typeIndex1Based}`);
                            
                            setTimeout(() => {
                                if (typeSelect) typeSelect.value = typeObj.type || '';
                            }, 100);
                        });
                    }
                }
            });
            
            console.log('  ✓ Sequence flows loaded');
        }
    }, 500);
}
