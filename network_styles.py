cytoscape_styles=[
                    # Node styles for buses
                    {
                        'selector': '[type = "bus"]',
                        'style': {
                            'label': 'data(label)',
                            'width': '10px',
                            'height': '10px',
                            'background-color': '#2ECC40',
                            'text-valign': 'top',
                            'text-halign': 'center',
                            'font-size': '10px',
                            'color': 'black'
                        }
                    },
                    # Node styles for generators
                    {
                        'selector': '[type = "generator"]',
                        'style': {
                            'label': 'data(label)',
                            'shape': 'square',
                            'width': '5px',
                            'height': '5px',
                            'background-color': '#FF4136',
                            'text-valign': 'top',
                            'text-halign': 'center',
                            'font-size': '10px',
                            'color': 'grey'
                        }
                    },
                    # Node styles for storage units
                    {
                        'selector': '[type = "storage"]',
                        'style': {
                            'label': 'data(label)',
                            'shape': 'pentagon',
                            'width': '5px',
                            'height': '5px',
                            'background-color': '#FF851B',
                            'text-valign': 'top',
                            'text-halign': 'center',
                            'font-size': '10px',
                            'color': 'grey'
                        }
                    },
                    # Edge styles - buses
                    {
                        'selector': 'edge',
                        'style': {
                            'line-color': '#FF4136',
                            'width': 2,
                            'curve-style': 'bezier',
                            'label': 'data(label)',
                            'font-size': '8px',
                            'color': 'grey'
                        }
                    },
                    # Edge styles - generators and storage
                    {
                        'selector': '[edgeType = "secondary"]',
                        'style': {
                            'line-color': '#7FDBFF',
                            'width': 1,
                            'curve-style': 'bezier'
                        }
                    }
                ]