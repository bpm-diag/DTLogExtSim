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
        const meanInput = document.getElementById(`scenario_${scenarioIndex}_arrival_mean`);
        const arg1Input = document.getElementById(`scenario_${scenarioIndex}_arrival_arg1`);
        const arg2Input = document.getElementById(`scenario_${scenarioIndex}_arrival_arg2`);
        const timeUnitSelect = document.getElementById(`scenario_${scenarioIndex}_arrival_time_unit`);

        if (meanInput) meanInput.value = arrival.mean || '';
        if (arg1Input) arg1Input.value = arrival.arg1 || '';
        if (arg2Input) arg2Input.value = arrival.arg2 || '';
        if (timeUnitSelect) timeUnitSelect.value = arrival.timeUnit || 'seconds';

        if (typeSelect && arrival.type) {
            typeSelect.value = arrival.type;
            updateInterArrivalTimeDistribution(scenarioIndex);
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
            
            // Setup Time 
            if (resource.setupTime && resource.setupTime.type) {
                const setupTime = resource.setupTime;
                
                const setupTypeSelect = document.getElementById(`${resourceId}_setupTimeType`);
                const setupMeanInput = document.getElementById(`${resourceId}_setupTimeMean`);
                const setupArg1Input = document.getElementById(`${resourceId}_setupTimeArg1`);
                const setupArg2Input = document.getElementById(`${resourceId}_setupTimeArg2`);
                const setupTimeUnitSelect = document.getElementById(`${resourceId}_setupTimeUnit`);
                

                if (setupMeanInput) setupMeanInput.value = setupTime.mean || '';
                if (setupArg1Input) setupArg1Input.value = setupTime.arg1 || '';
                if (setupArg2Input) setupArg2Input.value = setupTime.arg2 || '';
                if (setupTimeUnitSelect) setupTimeUnitSelect.value = setupTime.timeUnit || 'seconds';
                
                if (setupTypeSelect) {
                    setupTypeSelect.value = setupTime.type;
                    updateResourceSetupTimeDistribution(scenarioIndex, resourceId);
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
                        if (meanInput) meanInput.value = duration.mean || '';
                        if (arg1Input) arg1Input.value = duration.arg1 || '';
                        if (arg2Input) arg2Input.value = duration.arg2 || '';
                        if (timeUnitSelect) timeUnitSelect.value = duration.timeUnit || 'seconds';
                        
                        typeSelect.value = duration.type || 'FIXED';

                        updateActivityTimeDistribution(elementId, scenarioIndex);
                    }
                }
                
                if (element.durationThreshold) {
                    const thresholdInput = document.getElementById(`scenario_${scenarioIndex}_durationThreshold_${elementId}`);
                    if (thresholdInput) thresholdInput.value = element.durationThreshold;
                }
                if (element.durationThresholdTimeUnit) {
                    const thresholdUnitSelect = document.getElementById(`scenario_${scenarioIndex}_durationThresholdTimeUnit_${elementId}`);
                    if (thresholdUnitSelect) thresholdUnitSelect.value = element.durationThresholdTimeUnit;
                }
                
                if (element.batchMaxSize) {
                    const maxSizeInput = document.getElementById(`scenario_${scenarioIndex}_batchMaxSize_${elementId}`);
                    const minSizeInput = document.getElementById(`scenario_${scenarioIndex}_batchMinSize_${elementId}`);
                    const mixedInput = document.getElementById(`scenario_${scenarioIndex}_batchAllowMixedTypes_${elementId}`);
                    const toggle = document.getElementById(`scenario_${scenarioIndex}_batchEnabled_${elementId}`);
                    if (maxSizeInput) maxSizeInput.value = element.batchMaxSize;
                    if (minSizeInput) minSizeInput.value = element.batchMinSize || '';
                    if (mixedInput) mixedInput.checked = !!element.batchAllowMixedTypes;
                    if (toggle) {
                        toggle.checked = true;
                        if (typeof setBatchEnabled === 'function') setBatchEnabled(toggle, true);
                    }
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
                    if (meanInput) meanInput.value = eventData.mean || '';
                    if (arg1Input) arg1Input.value = eventData.arg1 || '';
                    if (arg2Input) arg2Input.value = eventData.arg2 || '';
                    if (timeUnitSelect) timeUnitSelect.value = eventData.timeUnit || 'seconds';

                    typeSelect.value = eventData.type || 'FIXED';

                    updateCatchEventTimeDistribution(eventId, scenarioIndex);
                }
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
                if (probInput) {
                    probInput.value = flow.executionProbability || '';
                    probInput.dispatchEvent(new Event('input'));
                }

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

                // restore own timer
                if (flow.hasOwnTimer) {
                    const toggle = document.getElementById(`scenario_${scenarioIndex}_hasOwnTimer_${flowId}`);
                    const timer = flow.ownTimer || {};
                    const typeEl = document.getElementById(`scenario_${scenarioIndex}_ownTimerType_${flowId}`);
                    const meanEl = document.getElementById(`scenario_${scenarioIndex}_ownTimerMean_${flowId}`);
                    const arg1El = document.getElementById(`scenario_${scenarioIndex}_ownTimerArg1_${flowId}`);
                    const arg2El = document.getElementById(`scenario_${scenarioIndex}_ownTimerArg2_${flowId}`);
                    const unitEl = document.getElementById(`scenario_${scenarioIndex}_ownTimerTimeUnit_${flowId}`);
                    if (typeEl) typeEl.value = timer.type || 'FIXED';
                    if (meanEl) meanEl.value = timer.mean || '';
                    if (arg1El) arg1El.value = timer.arg1 || '';
                    if (arg2El) arg2El.value = timer.arg2 || '';
                    if (unitEl) unitEl.value = timer.timeUnit || 'seconds';
                    if (toggle) {
                        toggle.checked = true;
                        if (typeof setBranchTimerEnabled === 'function') setBranchTimerEnabled(toggle, true);
                    }
                }

                // restore conditions (grouped: rows inside a group combine via that group's own
                // operator, groups combine with each other left to right via each group's own
                // connector to the group right before it). Falls back to treating a pre-groups flat
                // 'conditions' list (saved before this feature existed) as one implicit AND-group.
                const conditionGroups = flow.conditionGroups
                    ? flow.conditionGroups.slice()
                    : (flow.conditions && flow.conditions.length > 0 ? [{ operator: 'AND', conditions: flow.conditions }] : []);

                // Legacy 'Forced Instance Types' on an exclusive-gateway branch (identifiable by having
                // a conditions-container at all -- inclusive gateways don't) becomes an implicit
                // OR-group of instanceType conditions, ANDed onto whatever's already there. Matches
                // the migration simulator_engine.py's normalize_condition_groups() does at run time,
                // so what the user sees here is what would actually be evaluated.
                const hasConditionsContainer = !!document.querySelector(`.conditions-container[data-flow-id="${flowId}"][data-scenario="${scenarioIndex}"]`);
                if (hasConditionsContainer && flow.types && flow.types.length > 0) {
                    conditionGroups.push({
                        operator: 'OR',
                        conditions: flow.types.map(t => ({ kind: 'instanceType', value: t.type })),
                        ...(conditionGroups.length > 0 ? { connector: 'AND' } : {})
                    });
                }

                if (conditionGroups.length > 0) {
                    const conditionsContainer = document.querySelector(`.conditions-container[data-flow-id="${flowId}"][data-scenario="${scenarioIndex}"]`);
                    if (conditionsContainer) {
                        // capture the server-rendered activity options before clearing the template row,
                        // since addConditionRow() below copies options from whatever row is already present
                        const templateSelect = conditionsContainer.querySelector('.condition-activity-select');
                        const activityOptionsHtml = templateSelect ? templateSelect.innerHTML : '<option value=""></option>';

                        conditionsContainer.querySelectorAll('.condition-group, .condition-group-connector').forEach(el => el.remove());

                        conditionGroups.forEach((group, groupPos) => {
                            if (typeof addConditionGroup !== 'function') return;
                            addConditionGroup(flowId, scenarioIndex);
                            const groups = conditionsContainer.querySelectorAll('.condition-group');
                            const groupEl = groups[groups.length - 1];
                            if (!groupEl) return;
                            const groupIdx = groupEl.dataset.groupIdx;

                            const opSelect = groupEl.querySelector('.group-operator-select');
                            if (opSelect) opSelect.value = group.operator || 'AND';

                            if (groupPos > 0) {
                                // addConditionGroup() creates this group's connector as its immediately
                                // preceding sibling when it's not the first group.
                                const connectorEl = groupEl.previousElementSibling;
                                const connSelect = connectorEl && connectorEl.querySelector('.connector-operator-select');
                                if (connSelect) connSelect.value = group.connector || 'OR';
                            }

                            // addConditionGroup() seeds one empty row -- drop it, we add exactly as
                            // many rows as this group needs below.
                            groupEl.querySelectorAll('.condition-input').forEach(row => row.remove());

                            (group.conditions || []).forEach((cond) => {
                                addConditionRow(flowId, scenarioIndex, groupIdx);
                                const rows = groupEl.querySelectorAll('.condition-input');
                                const lastRow = rows[rows.length - 1];
                                if (!lastRow) return;
                                const kindSelect = lastRow.querySelector('select[name$="_kind"]');
                                const activitySelect = lastRow.querySelector('.condition-activity-select');
                                const typeSelect = lastRow.querySelector('.condition-instancetype-select');
                                const comparatorSelect = lastRow.querySelector('.condition-comparator-select');
                                const countInput = lastRow.querySelector('.condition-count-input');
                                if (activitySelect) activitySelect.innerHTML = activityOptionsHtml;
                                const condValue = cond.value !== undefined ? cond.value : cond.activityId;
                                setTimeout(() => {
                                    if (kindSelect) kindSelect.value = cond.kind || '';
                                    if (activitySelect) activitySelect.value = condValue || '';
                                    if (typeSelect) typeSelect.value = condValue || '';
                                    if (comparatorSelect) comparatorSelect.value = cond.comparator || '>=';
                                    if (countInput) countInput.value = cond.count !== undefined ? cond.count : 1;
                                    updateConditionValueVisibility(lastRow);
                                }, 100);
                            });
                        });
                    }
                }
            });

            console.log('  ✓ Sequence flows loaded');
        }

        // restore timeConstrainedGateways
        if (scenarioData.timeConstrainedGateways) {
            Object.keys(scenarioData.timeConstrainedGateways).forEach(gwId => {
                const gwData = scenarioData.timeConstrainedGateways[gwId];
                const toggle = document.getElementById(`scenario_${scenarioIndex}_tcgEnabled_${gwId}`);
                if (toggle) {
                    toggle.checked = true;
                    if (typeof setTcgEnabled === 'function') setTcgEnabled(toggle, true);
                }
                const typeEl = document.getElementById(`scenario_${scenarioIndex}_tcgDurationType_${gwId}`);
                const meanEl = document.getElementById(`scenario_${scenarioIndex}_tcgDurationMean_${gwId}`);
                const arg1El = document.getElementById(`scenario_${scenarioIndex}_tcgDurationArg1_${gwId}`);
                const arg2El = document.getElementById(`scenario_${scenarioIndex}_tcgDurationArg2_${gwId}`);
                const unitEl = document.getElementById(`scenario_${scenarioIndex}_tcgDurationTimeUnit_${gwId}`);
                if (typeEl) typeEl.value = gwData.type || 'FIXED';
                if (meanEl) meanEl.value = gwData.mean || '';
                if (arg1El) arg1El.value = gwData.arg1 || '';
                if (arg2El) arg2El.value = gwData.arg2 || '';
                if (unitEl) unitEl.value = gwData.timeUnit || 'seconds';
            });
        }

        // Aggiorna i badge somma DOPO che i valori delle probabilità sono stati impostati.
        // Le condizioni (kind/activity select) vengono scritte in un setTimeout annidato di 100ms
        // (vedi sopra), quindi questo ricalcolo deve girare dopo, altrimenti i branch con
        // condizione risultano ancora "senza condizione" e vengono inclusi per errore nella somma.
        setTimeout(() => {
            if (window.updateAllGatewaySums) window.updateAllGatewaySums();
        }, 150);
    }, 500);
}
