import json
import os
import sys
from pathlib import Path

def main():
    graph_path = Path("devonboard/knowledge-graph.json")
    if not graph_path.exists():
        print("Error: devonboard/knowledge-graph.json does not exist. Please run scan and history ingest first!")
        sys.exit(1)

    print(f"Loading {graph_path}...")
    with open(graph_path, "r", encoding="utf-8") as f:
        graph_data = json.load(f)

    output_path = Path("graph_visualization.html")
    print("Filtering and generating visualization...")

    # Filter nodes and edges to keep the visualization fast and responsive
    allowed_types = {"file", "module", "service", "claim"}
    
    nodes = []
    node_ids = set()
    for node in graph_data.get("nodes", []):
        if node.get("type") in allowed_types:
            nodes.append({
                "id": node["id"],
                "label": node["name"],
                "group": node["type"],
                "title": f"Type: {node['type']}<br>Summary: {node['summary']}"
            })
            node_ids.add(node["id"])
            if len(nodes) >= 1500:  # safety limit to prevent browser freezing
                break
                
    edges = []
    for edge in graph_data.get("edges", []):
        if edge["source"] in node_ids and edge["target"] in node_ids:
            edges.append({
                "from": edge["source"],
                "to": edge["target"],
                "label": edge["type"],
                "arrows": "to"
            })
            if len(edges) >= 2500:  # safety limit
                break

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>DevOnboard - Knowledge Graph Visualization</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style type="text/css">
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 0;
            background-color: #f8f9fa;
        }}
        #header {{
            background: linear-gradient(135deg, #1e293b, #0f172a);
            color: white;
            padding: 15px 25px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }}
        #header h1 {{
            margin: 0;
            font-size: 20px;
            font-weight: 600;
        }}
        #container {{
            display: flex;
            height: calc(100vh - 60px);
        }}
        #mynetwork {{
            flex: 1;
            height: 100%;
            background-color: #ffffff;
        }}
        #sidebar {{
            width: 320px;
            background-color: #ffffff;
            border-left: 1px solid #e2e8f0;
            padding: 20px;
            overflow-y: auto;
            box-shadow: -4px 0 6px -1px rgba(0, 0, 0, 0.05);
        }}
        #sidebar h2 {{
            margin-top: 0;
            font-size: 16px;
            color: #1e293b;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 8px;
            margin-bottom: 12px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        .legend-color {{
            width: 16px;
            height: 16px;
            border-radius: 4px;
            margin-right: 10px;
        }}
        .file-color {{ background-color: #93c5fd; border: 1px solid #3b82f6; }}
        .module-color {{ background-color: #c7d2fe; border: 1px solid #6366f1; }}
        .service-color {{ background-color: #fef08a; border: 1px solid #ca8a04; }}
        .claim-color {{ background-color: #fde047; border: 1px solid #eab308; }}
        #details {{
            margin-top: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            font-size: 14px;
            word-break: break-all;
        }}
        .info-title {{
            font-weight: bold;
            color: #0f172a;
        }}
    </style>
</head>
<body>
    <div id="header">
        <h1>DevOnboard - Codebase Knowledge Graph</h1>
        <span style="font-size: 14px; opacity: 0.8;">Showing {len(nodes)} main nodes and {len(edges)} relations</span>
    </div>
    <div id="container">
        <div id="mynetwork"></div>
        <div id="sidebar">
            <h2>Legend</h2>
            <div class="legend-item"><div class="legend-color file-color"></div><span>File (Blue)</span></div>
            <div class="legend-item"><div class="legend-color module-color"></div><span>Module (Indigo)</span></div>
            <div class="legend-item"><div class="legend-color service-color"></div><span>Service (Yellow)</span></div>
            <div class="legend-item"><div class="legend-color claim-color"></div><span>Claim (Amber)</span></div>
            
            <h2 style="margin-top: 25px;">Selection Info</h2>
            <div id="details">Click on a node or edge to view properties.</div>
        </div>
    </div>

    <script type="text/javascript">
        // create an array with nodes
        var nodes = new vis.DataSet({json.dumps(nodes)});

        // create an array with edges
        var edges = new vis.DataSet({json.dumps(edges)});

        // create a network
        var container = document.getElementById('mynetwork');
        var data = {{
            nodes: nodes,
            edges: edges
        }};
        var options = {{
            nodes: {{
                shape: 'dot',
                size: 16,
                font: {{
                    size: 12,
                    color: '#334155'
                }},
                borderWidth: 2
            }},
            edges: {{
                width: 1,
                color: {{ color: '#cbd5e1', highlight: '#3b82f6' }},
                smooth: {{
                    type: 'continuous'
                }}
            }},
            groups: {{
                file: {{
                    color: {{ background: '#93c5fd', border: '#3b82f6', highlight: {{ background: '#bfdbfe', border: '#2563eb' }} }}
                }},
                module: {{
                    color: {{ background: '#c7d2fe', border: '#6366f1', highlight: {{ background: '#e0e7ff', border: '#4f46e5' }} }}
                }},
                service: {{
                    color: {{ background: '#fef08a', border: '#ca8a04', highlight: {{ background: '#fef9c3', border: '#a16207' }} }}
                }},
                claim: {{
                    color: {{ background: '#fde047', border: '#eab308', highlight: {{ background: '#fef08a', border: '#ca8a04' }} }}
                }}
            }},
            physics: {{
                stabilization: true,
                barnesHut: {{
                    gravitationalConstant: -8000,
                    springConstant: 0.04,
                    springLength: 95
                }}
            }}
        }};
        var network = new vis.Network(container, data, options);

        network.on("click", function (params) {{
            var detailsDiv = document.getElementById('details');
            if (params.nodes.length > 0) {{
                var nodeId = params.nodes[0];
                var clickedNode = nodes.get(nodeId);
                detailsDiv.innerHTML = '<span class="info-title">ID:</span> ' + clickedNode.id + '<br>' +
                                       '<span class="info-title">Label:</span> ' + clickedNode.label + '<br>' +
                                       '<span class="info-title">Group:</span> ' + clickedNode.group + '<br>' +
                                       '<br><span class="info-title">Details:</span><br>' + clickedNode.title;
            }} else if (params.edges.length > 0) {{
                var edgeId = params.edges[0];
                var clickedEdge = edges.get(edgeId);
                detailsDiv.innerHTML = '<span class="info-title">From:</span> ' + clickedEdge.from + '<br>' +
                                       '<span class="info-title">To:</span> ' + clickedEdge.to + '<br>' +
                                       '<span class="info-title">Relation:</span> ' + clickedEdge.label;
            }} else {{
                detailsDiv.innerHTML = 'Click on a node or edge to view properties.';
            }}
        }});
    </script>
</body>
</html>
"""
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    
    print(f"Success! Visualization generated at: {output_path.absolute()}")
    print("You can open this file in any web browser to explore the graph interactively.")

if __name__ == "__main__":
    main()
