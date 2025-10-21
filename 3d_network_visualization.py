#!/usr/bin/env python3

#Building a 3D Multilayer Network Visualization (Horrendogram)
#Using Python and Plotly for interactive 3d visualization


import plotly.graph_objects as go
import numpy as np

# Hard coding data structure
# Defining the layers in the network (This will be auto created when ingesting files)
network_data = {
    "layers": {
        "Global": {
            "z": 2.0,
            "color": "#4287f5",
            "nodes": ["CBD", "ICES", "IMO", "UNEP", "UNFCCC", "UNCLOS", "UN"]
        },
        "Regional (Baltic Sea)": {
            "z": 1.0,
            "color": "#42f554",
            "nodes": [
                "EU MSFD", "Helsinki Convention", "EU WFD", "HELCOM", "EU",
                "HELCOM Recommendations", "EU Biodiversity strategy for 2030",
                "EU MSPD", "HELCOM BSAP", "UNEP Regional Seas Programme"
            ]
        },
        "National (Finland)": {
            "z": 0.0,
            "color": "#f54242",
            "nodes": [
                "Lag om vattenvårds- och havsvårdsförvaltningen",
                "Ministry of Agriculture and Forestry of Finland",
                "Havsvårdsförordningen",
                "Markanvändnings/bygglag (Land Use and Building Act)",
                "Naturvårdslag (Nature Conservation Act)",
                "Metsähallitus",
                "Ministry of the Environment",
                "Vattenlag (Water Act)",
                "Miljöskyddslagen",
                "Finnish Environment Institute (SYKE)"
            ]
        }
    },
    # These are also hard coded and will take data in the structure of source, source_layer, target and target_layer
    "edges": [
        {"source": "UNCLOS", "source_layer": "Global", "target": "Helsinki Convention", "target_layer": "Regional (Baltic Sea)"},
        {"source": "UNCLOS", "source_layer": "Global", "target": "EU MSFD", "target_layer": "Regional (Baltic Sea)"},
        {"source": "CBD", "source_layer": "Global", "target": "HELCOM BSAP", "target_layer": "Regional (Baltic Sea)"},
        {"source": "UNFCCC", "source_layer": "Global", "target": "EU", "target_layer": "Regional (Baltic Sea)"},
        {"source": "UN", "source_layer": "Global", "target": "EU", "target_layer": "Regional (Baltic Sea)"},
        {"source": "UNEP", "source_layer": "Global", "target": "UNEP Regional Seas Programme", "target_layer": "Regional (Baltic Sea)"},
        {"source": "Helsinki Convention", "source_layer": "Regional (Baltic Sea)", "target": "Miljöskyddslagen", "target_layer": "National (Finland)"},
        {"source": "HELCOM BSAP", "source_layer": "Regional (Baltic Sea)", "target": "Lag om vattenvårds- och havsvårdsförvaltningen", "target_layer": "National (Finland)"},
        {"source": "HELCOM Recommendations", "source_layer": "Regional (Baltic Sea)", "target": "Havsvårdsförordningen", "target_layer": "National (Finland)"},
        {"source": "EU MSFD", "source_layer": "Regional (Baltic Sea)", "target": "Lag om vattenvårds- och havsvårdsförvaltningen", "target_layer": "National (Finland)"},
        {"source": "EU WFD", "source_layer": "Regional (Baltic Sea)", "target": "Vattenlag (Water Act)", "target_layer": "National (Finland)"},
        {"source": "EU MSPD", "source_layer": "Regional (Baltic Sea)", "target": "Markanvändnings/bygglag (Land Use and Building Act)", "target_layer": "National (Finland)"},
        {"source": "EU Biodiversity strategy for 2030", "source_layer": "Regional (Baltic Sea)", "target": "Naturvårdslag (Nature Conservation Act)", "target_layer": "National (Finland)"},
        {"source": "EU", "source_layer": "Regional (Baltic Sea)", "target": "Ministry of the Environment", "target_layer": "National (Finland)"},
        {"source": "HELCOM", "source_layer": "Regional (Baltic Sea)", "target": "Finnish Environment Institute (SYKE)", "target_layer": "National (Finland)"},
        {"source": "UN", "source_layer": "Global", "target": "UNCLOS", "target_layer": "Global"},
        {"source": "UN", "source_layer": "Global", "target": "CBD", "target_layer": "Global"},
        {"source": "ICES", "source_layer": "Global", "target": "IMO", "target_layer": "Global"},
        {"source": "HELCOM", "source_layer": "Regional (Baltic Sea)", "target": "HELCOM BSAP", "target_layer": "Regional (Baltic Sea)"},
        {"source": "HELCOM", "source_layer": "Regional (Baltic Sea)", "target": "HELCOM Recommendations", "target_layer": "Regional (Baltic Sea)"},
        {"source": "EU", "source_layer": "Regional (Baltic Sea)", "target": "EU MSFD", "target_layer": "Regional (Baltic Sea)"},
        {"source": "EU", "source_layer": "Regional (Baltic Sea)", "target": "EU WFD", "target_layer": "Regional (Baltic Sea)"},
        {"source": "EU", "source_layer": "Regional (Baltic Sea)", "target": "EU MSPD", "target_layer": "Regional (Baltic Sea)"},
        {"source": "Ministry of the Environment", "source_layer": "National (Finland)", "target": "Finnish Environment Institute (SYKE)", "target_layer": "National (Finland)"},
        {"source": "Ministry of Agriculture and Forestry of Finland", "source_layer": "National (Finland)", "target": "Metsähallitus", "target_layer": "National (Finland)"}
    ]
}

# Creating position for various nodes across each layer
def calculate_node_positions(network_data, radius=3.0):
    #Calculate 3D positions for nodes in circular layout per layer
    node_positions = {}

    for layer_name, layer_info in network_data['layers'].items():
        nodes = layer_info['nodes']
        n = len(nodes)
        z = layer_info['z']

        for i, node in enumerate(nodes):
            angle = 2 * np.pi * i / n
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            node_positions[node] = {
                'x': x, 
                'y': y, 
                'z': z, 
                'layer': layer_name,
                'color': layer_info['color']
            }

    return node_positions

# Creating visualization and extracting data and positions from previous codes
def create_3d_network_visualization(network_data, node_positions):
    #Create interactive 3D network visualization using Plotly

    fig = go.Figure()

    # Add layer platforms (semi-transparent discs)
    for layer_name, layer_info in network_data['layers'].items():
        theta = np.linspace(0, 2*np.pi, 50)
        platform_radius = 4.0
        x_platform = platform_radius * np.cos(theta)
        y_platform = platform_radius * np.sin(theta)
        z_platform = np.full_like(x_platform, layer_info['z'])

        fig.add_trace(go.Scatter3d(
            x=x_platform,
            y=y_platform,
            z=z_platform,
            mode='lines',
            line=dict(color=layer_info['color'], width=2),
            name=f"{layer_name} Platform",
            showlegend=True,
            hoverinfo='name'
        ))

    # Adding edges
    edge_traces_intra = []  # Within layer
    edge_traces_inter = []  # Between layers

    for edge in network_data['edges']:
        source = edge['source']
        target = edge['target']

        if source not in node_positions or target not in node_positions:
            continue

        src_pos = node_positions[source]
        tgt_pos = node_positions[target]

        # Determine if intra-layer or inter-layer edge
        is_intra = (edge['source_layer'] == edge['target_layer'])

        edge_trace = go.Scatter3d(
            x=[src_pos['x'], tgt_pos['x'], None],
            y=[src_pos['y'], tgt_pos['y'], None],
            z=[src_pos['z'], tgt_pos['z'], None],
            mode='lines',
            line=dict(
                color='rgba(128,128,128,0.3)' if is_intra else 'rgba(255,140,0,0.6)',
                width=2 if is_intra else 4
            ),
            hoverinfo='text',
            text=f"{source} → {target}",
            showlegend=False
        )

        if is_intra:
            edge_traces_intra.append(edge_trace)
        else:
            edge_traces_inter.append(edge_trace)

    # Adding edge traces
    for trace in edge_traces_inter + edge_traces_intra:
        fig.add_trace(trace)

    # Adding nodes grouping by layers
    for layer_name, layer_info in network_data['layers'].items():
        nodes_in_layer = [n for n in layer_info['nodes'] if n in node_positions]

        x_nodes = [node_positions[n]['x'] for n in nodes_in_layer]
        y_nodes = [node_positions[n]['y'] for n in nodes_in_layer]
        z_nodes = [node_positions[n]['z'] for n in nodes_in_layer]

        fig.add_trace(go.Scatter3d(
            x=x_nodes,
            y=y_nodes,
            z=z_nodes,
            mode='markers+text',
            marker=dict(
                size=10,
                color=layer_info['color'],
                line=dict(color='white', width=2),
                opacity=0.9
            ),
            text=nodes_in_layer,
            textposition='top center',
            textfont=dict(size=8, color='black'),
            name=layer_name,
            hoverinfo='text',
            hovertext=[f"<b>{n}</b><br>Layer: {layer_name}" for n in nodes_in_layer],
            showlegend=True
        ))

    # Updating the layout
    fig.update_layout(
        title={
            'text': "Interactive 3D Multilayer Governance Network (Horrendogram)",
            'x': 0.5,
            'xanchor': 'center',
            'font': {'size': 18, 'color': '#333'}
        },
        scene=dict(
            xaxis=dict(showgrid=True, title='', showticklabels=False),
            yaxis=dict(showgrid=True, title='', showticklabels=False),
            zaxis=dict(showgrid=True, title='Governance Levels', 
                      ticktext=['National (Finland)', 'Regional (Baltic Sea)', 'Global'],
                      tickvals=[0.0, 1.0, 2.0]),
            camera=dict(
                eye=dict(x=1.5, y=1.5, z=1.2),
                center=dict(x=0, y=0, z=0)
            ),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.8)
        ),
        showlegend=True,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='black',
            borderwidth=1
        ),
        width=1200,
        height=900,
        hovermode='closest'
    )

    return fig


def main():
    #Main function to create and display the visualization
    print("Creating 3D Multilayer Network Visualization...")
    print(f"Total layers: {len(network_data['layers'])}")
    print(f"Total edges: {len(network_data['edges'])}")

    # Calculating node positions
    node_positions = calculate_node_positions(network_data)
    print(f"Total nodes: {len(node_positions)}")

    # Creating visualization
    fig = create_3d_network_visualization(network_data, node_positions)

    # Displaying in browser
    print("\nOpening visualization in browser...")
    fig.show()

    # Saving to HTML
    output_file = "3d_network_visualization.html"
    fig.write_html(output_file)
    print(f"Visualization saved to: {output_file}")


if __name__ == "__main__":
    main()
