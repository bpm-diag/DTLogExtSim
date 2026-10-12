// bpmn-diagram.js
// Renders the BPMN diagram (bpmn-js viewer) and lets the user click a gateway
// to edit its probabilities: the matching .gateway-group block (already built
// server-side, with all its existing validation/listener logic) is moved into
// a modal, then moved back to its original spot when the modal closes.

let gatewayModalPlaceholder = null;
let gatewayModalMovedElement = null;

function getActiveScenarioIndex() {
    const activeTab = document.querySelector('#scenarioTabs .nav-link.active');
    if (!activeTab) return 0;
    const match = activeTab.id.match(/^scenario-(\d+)-tab$/);
    return match ? parseInt(match[1], 10) : 0;
}

function openGatewayModal(gatewayGroupEl, title) {
    const modalBody = document.getElementById('gatewayModalBody');
    const modalLabel = document.getElementById('gatewayModalLabel');
    if (!modalBody || !modalLabel) return;

    gatewayModalPlaceholder = document.createComment('gateway-group-placeholder');
    gatewayGroupEl.parentNode.insertBefore(gatewayModalPlaceholder, gatewayGroupEl);
    gatewayModalMovedElement = gatewayGroupEl;

    modalLabel.textContent = title;
    modalBody.appendChild(gatewayGroupEl);

    const modalEl = document.getElementById('gatewayModal');
    bootstrap.Modal.getOrCreateInstance(modalEl).show();
}

function showBranchInfo(element) {
    const bar = document.getElementById('bpmn-branch-info');
    const text = document.getElementById('bpmn-branch-info-text');
    if (!bar || !text) return;

    const bo = element.businessObject;
    const sourceName = (bo.sourceRef && (bo.sourceRef.name || bo.sourceRef.id)) || '?';
    const targetName = (bo.targetRef && (bo.targetRef.name || bo.targetRef.id)) || '?';
    const flowLabel = bo.name ? `"${bo.name}" ` : '';

    text.innerHTML = `Branch ${flowLabel}<code>${element.id}</code> &nbsp;&mdash;&nbsp; ${sourceName} &rarr; ${targetName}`;
    bar.style.display = 'flex';
}

function hideBranchInfo() {
    const bar = document.getElementById('bpmn-branch-info');
    if (bar) bar.style.display = 'none';
}

function restoreGatewayGroup() {
    if (gatewayModalMovedElement && gatewayModalPlaceholder && gatewayModalPlaceholder.parentNode) {
        gatewayModalPlaceholder.parentNode.insertBefore(gatewayModalMovedElement, gatewayModalPlaceholder);
        gatewayModalPlaceholder.remove();
    }
    gatewayModalMovedElement = null;
    gatewayModalPlaceholder = null;
    const modalBody = document.getElementById('gatewayModalBody');
    if (modalBody) modalBody.innerHTML = '';
}

// scenario-management.js rebuilds scenario DOM (remove/duplicate/renumber) by reading whatever is
// currently inside #scenario-N -- if a .gateway-group is mid-visit in the modal at that moment, it's
// missing from that read and gets silently dropped from the rebuilt scenario (the gateway then stops
// responding to clicks in the diagram). Call this before any such rebuild to put the node back first.
window.closeGatewayModalIfOpen = function() {
    if (!gatewayModalMovedElement) return;
    restoreGatewayGroup();
    const modalEl = document.getElementById('gatewayModal');
    const instance = modalEl && bootstrap.Modal.getInstance(modalEl);
    if (instance) instance.hide();
};

function initBpmnDiagram() {
    const canvasEl = document.getElementById('bpmn-canvas');
    const errorEl = document.getElementById('bpmn-canvas-error');
    if (!canvasEl || typeof BpmnJS === 'undefined') return;

    const simulationPath = canvasEl.dataset.simulationPath;
    const simulationNoExt = canvasEl.dataset.simulationNoExt;
    if (!simulationPath || !simulationNoExt) return;

    const url = `/bpmn_source?simulation_path=${encodeURIComponent(simulationPath)}&simulation_no_ext=${encodeURIComponent(simulationNoExt)}`;

    const showError = (message) => {
        canvasEl.style.display = 'none';
        if (errorEl) {
            errorEl.textContent = message;
            errorEl.style.display = 'block';
        }
    };

    fetch(url)
        .then(response => {
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            return response.text();
        })
        .then(xml => {
            const viewer = new BpmnJS({ container: canvasEl });
            return viewer.importXML(xml).then(() => viewer);
        })
        .then(viewer => {
            window.bpmnViewer = viewer; // exposed for debugging/console access, same pattern as window.bpmn_dict
            const canvas = viewer.get('canvas');
            const eventBus = viewer.get('eventBus');
            canvas.zoom('fit-viewport');

            // Gateways with an editable .gateway-group are the same across every scenario
            // (only the values differ), so scenario 0 is enough to know which ones are configurable.
            document.querySelectorAll('#gateways-container-0 .gateway-group[data-gateway-id]').forEach(el => {
                canvas.addMarker(el.dataset.gatewayId, 'bpmn-gateway-configurable');
            });

            const zoomStep = 0.2;
            const zoomInBtn = document.getElementById('bpmn-zoom-in');
            const zoomOutBtn = document.getElementById('bpmn-zoom-out');
            const zoomFitBtn = document.getElementById('bpmn-zoom-fit');
            if (zoomInBtn) zoomInBtn.addEventListener('click', () => canvas.zoom(canvas.zoom() + zoomStep));
            if (zoomOutBtn) zoomOutBtn.addEventListener('click', () => canvas.zoom(Math.max(canvas.zoom() - zoomStep, 0.2)));
            if (zoomFitBtn) zoomFitBtn.addEventListener('click', () => canvas.zoom('fit-viewport'));

            const branchInfoClose = document.getElementById('bpmn-branch-info-close');
            if (branchInfoClose) branchInfoClose.addEventListener('click', hideBranchInfo);

            eventBus.on('element.click', e => {
                if (e.element.type === 'bpmn:SequenceFlow') {
                    showBranchInfo(e.element);
                    return;
                }

                const scenarioIndex = getActiveScenarioIndex();
                const container = document.getElementById(`gateways-container-${scenarioIndex}`);
                const gatewayGroupEl = container && container.querySelector(`.gateway-group[data-gateway-id="${e.element.id}"]`);
                if (!gatewayGroupEl) {
                    hideBranchInfo();
                    return;
                }

                hideBranchInfo();
                const title = (e.element.businessObject && e.element.businessObject.name) || e.element.id;
                openGatewayModal(gatewayGroupEl, title);
            });
        })
        .catch(err => {
            console.error('BPMN diagram rendering failed:', err);
            showError('Unable to render the BPMN diagram. Use the gateway list below to configure probabilities.');
        });
}

document.addEventListener('DOMContentLoaded', () => {
    initBpmnDiagram();

    const gatewayModalEl = document.getElementById('gatewayModal');
    if (gatewayModalEl) {
        gatewayModalEl.addEventListener('hidden.bs.modal', restoreGatewayGroup);
    }
});
