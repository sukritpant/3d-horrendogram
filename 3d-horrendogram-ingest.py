#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# 3D Multilayer Network Visualization with file handling and ingestion

import plotly.graph_objects as go
import numpy as np
import pandas as pd


# Assign a distinct color for each layer
def generate_layer_colors(layers):
    palette = [
        "#4287f5", "#42f554", "#f54242", "#f5a142", "#9b42f5",
        "#42f5f2", "#d9f542", "#6f42f5", "#f5429e", "#999999"
    ]
    return {layer: palette[i % len(palette)] for i, layer in enumerate(layers)}

# Making sure empty strings are treated as None
def clean_string(value):
    if pd.isna(value):
        return None
    val = str(value).strip()
    return val if val else None


# Load CSV and skip empty layers/nodes
def load_network_from_csv(csv_path):
    df = pd.read_csv(csv_path)

    # Normalize headers
    df.columns = [c.strip().lower() for c in df.columns]

    required_cols = {'source', 'source_layer'}
    if not required_cols.issubset(df.columns):
        raise ValueError("CSV must include at least: 'source' and 'source_layer'")

    # Clean and discard blank sources/layers
    df['source'] = df['source'].apply(clean_string)
    df['source_layer'] = df['source_layer'].apply(clean_string)
    if 'target' in df.columns:
        df['target'] = df['target'].apply(clean_string)
    if 'target_layer' in df.columns:
        df['target_layer'] = df['target_layer'].apply(clean_string)

    df = df.dropna(subset=['source', 'source_layer'])

    # Determine if there are valid targets
    has_targets = {'target', 'target_layer'}.issubset(df.columns)

    # Collect valid, non-empty layer names
    all_layers = sorted(
        set(df['source_layer'].dropna()) |
        (set(df['target_layer'].dropna()) if has_targets else set())
    )
    all_layers = [l for l in all_layers if l and not str(l).isspace()]

    if not all_layers:
        raise ValueError("No valid layer names found in file.")

    print("\nDetected layers:")
    for lay in all_layers:
        print(f" - {lay}")

    # Ask numeric order once per layer
    print("\nAssign numeric order to layers (1 = top level):")
    layer_positions = {}
    for layer in all_layers:
        while True:
            val = input(f"Order number for layer '{layer}': ").strip()
            if not val.isdigit():
                print("❌ Please enter a valid numeric value.")
                continue
            order = int(val)
            if order in layer_positions.values():
                print(f"⚠️ Number {order} already used — please pick a unique number.")
                continue
            layer_positions[layer] = order
            break

    # Sort and create z-map
    ordered_layers = [x for x, _ in sorted(layer_positions.items(), key=lambda kv: kv[1])]
    z_map = {layer: float(i) for i, layer in enumerate(reversed(ordered_layers))}
    color_map = generate_layer_colors(ordered_layers)

    # Building each layer’s node list
    layers_dict = {}
    for layer in ordered_layers:
        src_nodes = df.loc[df['source_layer'] == layer, 'source'].dropna().unique().tolist()
        tgt_nodes = []
        if has_targets:
            tgt_nodes = df.loc[df['target_layer'] == layer, 'target'].dropna().unique().tolist()
        nodes = sorted(set(src_nodes + tgt_nodes))
        if not nodes:
            continue
        layers_dict[layer] = {
            'z': z_map[layer],
            'color': color_map[layer],
            'nodes': nodes
        }

    # Building edge list
    edges = []
    if has_targets:
        for _, row in df.iterrows():
            src, src_l = row.get('source'), row.get('source_layer')
            tgt, tgt_l = row.get('target'), row.get('target_layer')
            if not (src and src_l and tgt and tgt_l):
                continue
            edges.append({
                'source': src,
                'source_layer': src_l,
                'target': tgt,
                'target_layer': tgt_l
            })

    print("\n✅ Registered layers (with node contents):")
    for l, info in layers_dict.items():
        print(f"  {l}: {len(info['nodes'])} nodes")

    return {"layers": layers_dict, "edges": edges}


# Compute position to avoid overlap
def calculate_node_positions(network_data, radius=3.0):
    positions = {}
    for lname, linfo in network_data['layers'].items():
        nodes, z = linfo['nodes'], linfo['z']
        n = len(nodes)
        for i, node in enumerate(nodes):
            angle = 2 * np.pi * i / n if n > 0 else 0
            x = radius * np.cos(angle)
            y = radius * np.sin(angle)
            positions[node] = {'x': x, 'y': y, 'z': z,
                               'layer': lname, 'color': linfo['color']}
    return positions


# Color blending and gradient
def blend_colors(c1, c2):
    def hex_to_rgb(h): return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))
    def rgb_to_hex(rgb): return '#' + ''.join(f'{int(c):02x}' for c in rgb)
    rgb1, rgb2 = hex_to_rgb(c1), hex_to_rgb(c2)
    blended = tuple((a + b) / 2 for a, b in zip(rgb1, rgb2))
    return rgb_to_hex(blended)


def interpolate_color(c1, c2, t):
    def hex_to_rgb(h): return tuple(int(h[i:i+2], 16)/255 for i in (1, 3, 5))
    def rgb_to_hex(rgb): return '#' + ''.join(f'{int(v*255):02x}' for v in rgb)
    rgb1, rgb2 = hex_to_rgb(c1), hex_to_rgb(c2)
    blended = tuple((1-t)*a + t*b for a, b in zip(rgb1, rgb2))
    return rgb_to_hex(blended)


# Create 3D visualization
def create_3d_visualization(network_data, positions):
    fig = go.Figure()

    # Layer discs
    for lname, linfo in network_data['layers'].items():
        theta = np.linspace(0, 2*np.pi, 60)
        x_disc = 4 * np.cos(theta)
        y_disc = 4 * np.sin(theta)
        z_disc = np.full_like(x_disc, linfo['z'])
        fig.add_trace(go.Scatter3d(
            x=x_disc, y=y_disc, z=z_disc,
            mode='lines',
            line=dict(color=linfo['color'], width=2),
            name=lname
        ))

    # Edges
    for e in network_data['edges']:
        s, t = e['source'], e['target']
        sl, tl = e['source_layer'], e['target_layer']
        if s not in positions or t not in positions:
            continue
        sp, tp = positions[s], positions[t]
        if sl != tl:
            steps = 10
            xs = np.linspace(sp['x'], tp['x'], steps)
            ys = np.linspace(sp['y'], tp['y'], steps)
            zs = np.linspace(sp['z'], tp['z'], steps)
            for i in range(steps - 1):
                c = interpolate_color(sp['color'], tp['color'], i / (steps - 1))
                fig.add_trace(go.Scatter3d(
                    x=[xs[i], xs[i+1]], y=[ys[i], ys[i+1]], z=[zs[i], zs[i+1]],
                    mode='lines', line=dict(color=c, width=4),
                    hoverinfo='text', text=f"{s} → {t}", showlegend=False
                ))
        else:
            c = blend_colors(sp['color'], tp['color'])
            fig.add_trace(go.Scatter3d(
                x=[sp['x'], tp['x']], y=[sp['y'], tp['y']], z=[sp['z'], tp['z']],
                mode='lines', line=dict(color=c, width=2),
                hoverinfo='text', text=f"{s} → {t}", showlegend=False
            ))

    # Nodes
    for lname, linfo in network_data['layers'].items():
        if not linfo['nodes']:
            continue
        xs = [positions[n]['x'] for n in linfo['nodes']]
        ys = [positions[n]['y'] for n in linfo['nodes']]
        zs = [positions[n]['z'] for n in linfo['nodes']]
        fig.add_trace(go.Scatter3d(
            x=xs, y=ys, z=zs,
            mode='markers+text',
            marker=dict(size=10, color=linfo['color'], line=dict(color='white', width=1)),
            text=linfo['nodes'],
            textposition='top center',
            name=lname,
            hovertext=[f"<b>{n}</b><br>Layer: {lname}" for n in linfo['nodes']]
        ))

    fig.update_layout(
        title="3D Multilayer Governance Network Visualization",
        scene=dict(
            zaxis=dict(
                title="Governance Layers",
                tickvals=[v['z'] for v in network_data['layers'].values()],
                ticktext=list(network_data['layers'].keys())
            ),
            xaxis=dict(showticklabels=False),
            yaxis=dict(showticklabels=False),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.8)
        ),
        legend=dict(bgcolor='rgba(255,255,255,0.9)', bordercolor='black'),
        width=1200, height=900
    )
    return fig


def main():
    csv_path = input("Enter path to CSV file: ").strip()
    network_data = load_network_from_csv(csv_path)
    positions = calculate_node_positions(network_data)
    fig = create_3d_visualization(network_data, positions)
    fig.show()
    fig.write_html("3d_horrendogram_network.html")
    print("\n✅ Visualization saved to 3d_horrendogram_network.html")


if __name__ == "__main__":
    main()
