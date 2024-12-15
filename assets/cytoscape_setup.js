
function initializeCytoscape(elements, stylesheet, container, graphId) { // Declare globally
    window[graphId] = cytoscape({
        container: container,
        elements: elements,
        style: stylesheet
    });

    window[graphId].on('mouseover', 'node', function (evt) {
        var node = evt.target;
        var content = `<h6>${node.data('label')}</h6><p>${node.data('info')}</p>`;
        var tooltip = document.getElementById('tooltip');
        tooltip.innerHTML = content;
        tooltip.style.display = 'block';
        tooltip.style.left = evt.renderedPosition.x + 10 + 'px';
        tooltip.style.top = evt.renderedPosition.y + 10 + 'px';
    });

    window[graphId].on('mouseout', 'node', function (evt) {
        document.getElementById('tooltip').style.display = 'none';
    });

    container.addEventListener('mouseout', function(event) {
        if (!event.relatedTarget || !event.relatedTarget.closest('#' + graphId)) {
            document.getElementById('tooltip').style.display = 'none';
        }
    });
}


window.addEventListener('load', function() { // Wait for the page to fully load
    const graphId = 'network-graph-diagram'; // Match your graph ID
    const container = document.getElementById(graphId);

    if (container) { //Check the container exists
        const elements = JSON.parse(container.getAttribute('data-elements')); // Get elements from data attribute
        const stylesheet = JSON.parse(container.getAttribute('data-stylesheet')); // Get stylesheet from data attribute
        window[graphId] = cytoscape({
            container: container,
            elements: elements,
            style: stylesheet
        });

        window[graphId].on('mouseover', 'node', function (evt) {
            var node = evt.target;
            var content = `<h6><span class="math-inline">\{node\.data\('label'\)\}</h6\><p\></span>{node.data('info')}</p>`;
            var tooltip = document.getElementById('tooltip');
            tooltip.innerHTML = content;
            tooltip.style.display = 'block';
            tooltip.style.left = evt.renderedPosition.x + 10 + 'px';
            tooltip.style.top = evt.renderedPosition.y + 10 + 'px';
        });

        window[graphId].on('mouseout', 'node', function (evt) {
            document.getElementById('tooltip').style.display = 'none';
        });

        container.addEventListener('mouseout', function(event) {
            if (!event.relatedTarget || !event.relatedTarget.closest('#' + graphId)) {
                document.getElementById('tooltip').style.display = 'none';
            }
        });
    } else {
        const observer = new MutationObserver(() => {
            const container = document.getElementById(graphId);
            if (container) {
                const elements = JSON.parse(container.getAttribute('data-elements')); // Get elements from data attribute
                const stylesheet = JSON.parse(container.getAttribute('data-stylesheet')); // Get stylesheet from data attribute
                initializeCytoscape(elements, stylesheet, container, graphId);
                observer.disconnect();
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    }
});