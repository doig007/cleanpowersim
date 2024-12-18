function resizeSVG(container) {
    const width = window.innerWidth * 0.9; // Use 90% of the window width
    const height = window.innerHeight * 0.8; // Use 80% of the window height

    d3.select(container)
        .select("svg")
        .attr("width", width)
        .attr("height", height)
        .attr("viewBox", `0 0 ${width} ${height}`); // Adjust the viewBox as well

    return { width, height };
}


window.dash_clientside = Object.assign({}, window.dash_clientside, {
    clientside: {
        createMap: function(data) {
            console.log("Starting JS file...");

            if (!data) {
                console.error("No data received.");
                return window.dash_clientside.no_update;
            }
    
            const container = document.getElementById('d3-container');
            if (container) {
                const parsedData = typeof data === "string" ? JSON.parse(data) : data;
                const nodes = parsedData.nodes;
                const links = parsedData.links.map(link => ({
                    source: String(link.source), 
                    target: String(link.target), 
                    type: link.type
                }));

                const { width, height } = resizeSVG(container);

                let svg = d3.select(container).select("svg");
                if (svg.empty()) {
                    svg = d3.select(container).append("svg")
                        .attr("width", width)
                        .attr("height", height)
                        .attr("viewBox", `0 0 ${width} ${height}`)
                        .call(d3.zoom().on("zoom", function (event) {
                            svg.attr("transform", event.transform);
                        }));
                } else {
                    svg.attr("width", width);
                    svg.attr("height", height);
                    svg.attr("viewBox", `0 0 ${width} ${height}`);
                }

                const longitudes = nodes.map(d => d.x);
                const latitudes = nodes.map(d => d.y);
                const minLongitude = Math.min(...longitudes);
                const maxLongitude = Math.max(...longitudes);
                const minLatitude = Math.min(...latitudes);
                const maxLatitude = Math.max(...latitudes);

                const centerLongitude = (minLongitude + maxLongitude) / 2;
                const centerLatitude = (minLatitude + maxLatitude) / 2;

                const projection = d3.geoMercator()
                    .center([centerLongitude, centerLatitude]);

                const xScale = width / (maxLongitude - minLongitude);
                const yScale = height / (maxLatitude - minLatitude);
                const scale = Math.min(xScale, yScale) * 15;

                projection.scale(scale).translate([width / 2, height / 2]);

                // Project nodes
                nodes.forEach(d => {
                    [d.x, d.y] = projection([d.x, d.y]);
                });

                // Fix the co-ordinates of bus nodes as it's the others that we wish to re-arrange
                nodes.forEach(d => {
                    if (d.type === "bus") {
                        d.fx = d.x;
                        d.fy = d.y;
                    }
                });

                // Calculate radius scale only for valid p_nom values
                const validPNoms = nodes.filter(d => d.capacity !== undefined && !isNaN(d.capacity)).map(d => d.capacity);

                // Define radiusScale for valid p_nom values
                const radiusScale = d3.scaleLinear()
                    .domain([d3.min(validPNoms), d3.max(validPNoms)])
                    .range([5, 50]); // Scale for valid p_nom values

                // Tooltip div
                const tooltip = d3.select("body")
                    .append("div")
                    .style("position", "absolute")
                    .style("background", "rgba(255, 255, 255, 0.8)")
                    .style("border", "1px solid #ccc")
                    .style("padding", "5px")
                    .style("border-radius", "5px")
                    .style("pointer-events", "none")
                    .style("display", "none")
                    .style("font-size", "12px");

                const linkGroup = svg.append("g").attr("class", "links");
                const nodeGroup = svg.append("g").attr("class", "nodes");

                const link = linkGroup.selectAll("line")
                    .data(links)
                    .join("line")
                    //.attr("class", "link");
                    .classed("link",true)
                    .classed("primary", d => d.type === "primary")
                    .classed("secondary", d => d.type === "secondary");


                // Filter the nodes for type 'bus' only
                const busNodes = nodes.filter(d => d.type === 'bus');
                const genNodes = nodes.filter(d => d.type === 'generator');
                const storageNodes = nodes.filter(d => d.type === 'storage');

                const node_bus = nodeGroup.append("g")
                    .selectAll("rect")
                    .data(busNodes)
                    .enter()
                    .append("rect")
                    .attr("class", "node_bus")
                    .attr("width",15)
                    .attr("height",15)                   
                    .attr("transform", d => `translate(${d.x}, ${d.y})`)
                    .on("mouseenter", (event, d) => {
                            tooltip.style("display", "block").html(
                                `<strong>${d.id}</strong><br>
                                Type: ${d.type}`
                            );
                        }
                    )
                    .on("mousemove", (event) => {
                        tooltip.style("top", (event.pageY + 10) + "px")
                               .style("left", (event.pageX + 10) + "px");
                    })
                    .on("mouseleave", () => {
                        tooltip.style("display", "none");
                    });

                const node_generators = nodeGroup.append("g")
                    .selectAll("circle")
                    .data(genNodes)
                    .enter()
                    .append("circle")
                    .attr("class", "node_generator")
                    .attr("r", d => {
                        if (d.capacity === undefined || isNaN(d.capacity)) {
                            return 10; // Default radius for nodes without p_nom
                        } else {
                            return radiusScale(d.capacity); // Scale radius for valid p_nom
                        }
                    })
                    .attr("transform", d => `translate(${d.x}, ${d.y})`)
                    .on("mouseenter", (event, d) => {
                            tooltip.style("display", "block").html(
                                `<strong>${d.id}</strong><br>
                                Type: ${d.type}<br>
                                Capacity: ${d.capacity.toFixed(0)}MW`
                            );
                        }
                    )
                    .on("mousemove", (event) => {
                        tooltip.style("top", (event.pageY + 10) + "px")
                               .style("left", (event.pageX + 10) + "px");
                    })
                    .on("mouseleave", () => {
                        tooltip.style("display", "none");
                    });

                const simulation = d3.forceSimulation(nodes)
                    .force("link", d3.forceLink(links).id(d => d.id).distance(2))
                    .force("charge", d3.forceManyBody().strength(-200))
                    .force("center", d3.forceCenter(width / 2, height / 2))
                    .force("collision", d3.forceCollide().radius(d => d.type === "bus" ? 20 : 10))
                    .on("tick", () => {
                        link.attr("x1", d => d.source.x)
                            .attr("y1", d => d.source.y)
                            .attr("x2", d => d.target.x)
                            .attr("y2", d => d.target.y);

                        node_generators.attr("transform", d => `translate(${d.x},${d.y})`);
                    });
            }
            
            // Handle window resizing
            window.addEventListener("resize", () => {
                const { width, height } = resizeSVG(container);
                svg.attr("width", width).attr("height", height);
            });
            
            return window.dash_clientside.no_update;

        }
    }
});
