#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import plotly.graph_objects as go
import numpy as np
import pandas as pd
import os
import yaml
from collections import defaultdict
import math

# Load configuration
def read_config(path="config.yaml"):
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    cfg.setdefault("display_xyz_in_tooltip", False)
    cfg.setdefault("actor_legislation_z_offset", True)
    cfg.setdefault("actor_z_offset", 0.2)
    cfg.setdefault("rotation_speed", 150)  # mention in ms per frame
    return cfg


def clean_string(value):
    if pd.isna(value):
        return None
    return str(value).strip() or None


def normalize_layer_name(value):
    if value is None:
        return None
    return str(value).strip().lower()


def generate_layer_colors(layers):
    palette = [
        "#4287f5", "#42f554", "#f54242", "#f5a142", "#9b42f5",
        "#42f5f2", "#d9f542", "#6f42f5", "#f5429e", "#999999"
    ]
    return {layer: palette[i % len(palette)] for i, layer in enumerate(layers)}

# File loading
def load_input_files():
    first_path = input("Enter path to your main dataset file (CSV or Excel): ").strip()
    if not os.path.isfile(first_path):
        raise FileNotFoundError(f"File not found: {first_path}")
    ext = os.path.splitext(first_path)[1].lower()
    if ext in [".xls", ".xlsx"]:
        edges_df = pd.read_excel(first_path, sheet_name="edges")
        try:
            layer_df = pd.read_excel(first_path, sheet_name="layers")
        except:
            print("⚠️ No 'layers' sheet found — layer order will be requested interactively.")
            layer_df = None
        return edges_df, layer_df
    elif ext == ".csv":
        edges_df = pd.read_csv(first_path)
        second_path = input("Enter optional path to layer order CSV (or press Enter to skip): ").strip()
        if second_path and os.path.isfile(second_path):
            layer_df = pd.read_csv(second_path)
        else:
            layer_df = None
        return edges_df, layer_df
    else:
        raise ValueError("Unsupported file type.")

# Preparing data for network definition
def prepare_network(edges_df, layer_df=None):
    edges_df.columns = [c.strip().lower() for c in edges_df.columns]
    required_cols = {'source', 'source_layer', 'source_actor/legislation'}
    if not required_cols.issubset(edges_df.columns):
        raise ValueError("Input data must contain required columns.")
    edges_df['source'] = edges_df['source'].apply(clean_string)
    edges_df['source_layer'] = edges_df['source_layer'].apply(normalize_layer_name)
    edges_df['source_actor/legislation'] = edges_df['source_actor/legislation'].apply(clean_string)
    if 'target' in edges_df.columns:
        edges_df['target'] = edges_df['target'].apply(clean_string)
    if 'target_layer' in edges_df.columns:
        edges_df['target_layer'] = edges_df['target_layer'].apply(normalize_layer_name)
    else:
        edges_df['target_layer'] = None
    if 'target_actor/legislation' in edges_df.columns:
        edges_df['target_actor/legislation'] = edges_df['target_actor/legislation'].apply(clean_string)
    else:
        edges_df['target_actor/legislation'] = None


    edges_df = edges_df.dropna(subset=['source','source_layer'])
    has_targets = {'target','target_layer'}.issubset(edges_df.columns)
    all_layers = sorted(set(edges_df['source_layer'].dropna()) | (set(edges_df['target_layer'].dropna()) if has_targets else set()))
    all_layers = [l for l in all_layers if l and not str(l).isspace()]
    if layer_df is None:
        layer_order = {}
        for layer in all_layers:
            while True:
                val = input(f"Order for layer '{layer}': ").strip()
                if val.isdigit() and int(val) not in layer_order.values():
                    layer_order[layer] = int(val)
                    break
        ordered_layers = [x for x, _ in sorted(layer_order.items(), key=lambda kv: kv[1])]
    else:
        layer_df.columns = [c.strip().lower() for c in layer_df.columns]
        if not {'layer', 'order'}.issubset(layer_df.columns):
            raise ValueError("Layer file missing columns.")
        layer_df['layer'] = layer_df['layer'].apply(normalize_layer_name)
        layer_df = layer_df.dropna(subset=['layer','order'])
        ordered_layers = [row['layer'] for _, row in layer_df.sort_values(by='order').iterrows() if row['layer'] in all_layers]
        if not ordered_layers:
            return prepare_network(edges_df, None)


    z_map = {layer: float(i) for i, layer in enumerate(reversed(ordered_layers))}
    color_map = generate_layer_colors(ordered_layers)


    node_layers = defaultdict(set)
    for _, row in edges_df.iterrows():
        if pd.notna(row['source']) and pd.notna(row['source_layer']):
            node_layers[row['source']].add(row['source_layer'])
        if has_targets and pd.notna(row['target']) and pd.notna(row['target_layer']):
            node_layers[row['target']].add(row['target_layer'])


    node_unique_names = {}
    for node_name, layers in node_layers.items():
        if len(layers) > 1:
            for lyr in layers:
                node_unique_names[(node_name, lyr)] = f"{node_name}__{lyr}"
        else:
            node_unique_names[(node_name, next(iter(layers)))] = node_name


    layers_dict = {}
    for layer in ordered_layers:
        nodes_in_layer = set()
        src_nodes = edges_df.loc[edges_df['source_layer'] == layer, 'source'].dropna().unique().tolist()
        tgt_nodes = []
        if has_targets:
            tgt_nodes = edges_df.loc[edges_df['target_layer'] == layer, 'target'].dropna().tolist()


        all_nodes_original = set(src_nodes) | set(tgt_nodes)
        for node_name in all_nodes_original:
            unique_name = node_unique_names.get((node_name, layer), node_name)
            nodes_in_layer.add(unique_name)


        if not nodes_in_layer:
            continue
        layers_dict[layer] = {'z': z_map[layer], 'color': color_map[layer], 'nodes': sorted(nodes_in_layer)}


    edges = []
    if has_targets:
        for _, row in edges_df.iterrows():
            s_unique = node_unique_names.get((row['source'], row['source_layer']), row['source'])
            t_unique = node_unique_names.get((row['target'], row['target_layer']), row['target'])
            edges.append({'source': s_unique, 'source_layer': row['source_layer'], 'target': t_unique, 'target_layer': row['target_layer']})


    node_types = {}
    for _, row in edges_df.iterrows():
        s_unique = node_unique_names.get((row['source'], row['source_layer']), row['source'])
        t_unique = node_unique_names.get((row['target'], row['target_layer']), row['target'])
        s_type = row.get('source_actor/legislation')
        t_type = row.get('target_actor/legislation')
        if s_unique not in node_types:
            node_types[s_unique] = s_type.lower() if s_type and s_type.lower() in ['actor', 'legislation'] else 'unknown'
        if t_unique not in node_types:
            node_types[t_unique] = t_type.lower() if t_type and t_type.lower() in ['actor', 'legislation'] else 'unknown'


    return {"layers": layers_dict, "edges": edges, "node_types": node_types}

# Calculate 3D positions for nodes to avoid overlap
def calculate_node_positions(network_data, cfg, radius=3.0):
    pos = {}
    actor_offset = cfg.get("actor_z_offset", 0.2)
    use_z_offset = cfg.get("actor_legislation_z_offset", True)
    for lname, linfo in network_data['layers'].items():
        nodes = linfo['nodes']
        n = len(nodes)
        for i, node in enumerate(nodes):
            angle = 2 * np.pi * i / n if n > 0 else 0
            x, y = radius * np.cos(angle), radius * np.sin(angle)
            base_z = linfo['z']
            ntype = network_data['node_types'].get(node, 'unknown').lower()
            z = base_z
            if use_z_offset:
                if ntype == 'actor':
                    z = base_z + actor_offset
            pos[node] = {'x': x, 'y': y, 'z': z, 'color': linfo['color']}
    return pos

# Blending colors for inter-layer edges
def blend_colors(c1, c2):
    def h2r(h): return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


    def r2h(rgb): return '#' + ''.join(f'{int(c):02x}' for c in rgb)


    rgb1, rgb2 = h2r(c1), h2r(c2)
    mix = tuple((a + b) // 2 for a, b in zip(rgb1, rgb2))
    return r2h(mix)



def interpolate_color(c1, c2, t):
    def h2r(h): return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))


    def r2h(rgb): return '#' + ''.join(f'{int(v * 255):02x}' for v in rgb)


    rgb1, rgb2 = h2r(c1), h2r(c2)
    blended = tuple((1 - t) * a + t * b for a, b in zip(rgb1, rgb2))
    return r2h(blended)


# Create 3D visualization
def create_3d_visualization(network_data, pos, cfg):
    fig = go.Figure()
    shape_map = {'actor': 'circle', 'legislation': 'square', 'unknown': 'diamond'}
    display_xyz = cfg.get("display_xyz_in_tooltip", False)


    for lname, linfo in network_data['layers'].items():
        theta = np.linspace(0, 2 * np.pi, 60)
        x, y = 4 * np.cos(theta), 4 * np.sin(theta)
        z = np.full_like(x, linfo['z'])
        fig.add_trace(go.Scatter3d(x=x, y=y, z=z, mode='lines',
                                   line=dict(color=linfo['color'], width=2),
                                   name=f"Layer: {lname}",
                                   legendgroup=f"layer_{lname}",
                                   showlegend=True,
                                   visible=True))


    intra_layer_edges = [e for e in network_data['edges'] if e['source_layer'] == e['target_layer']]
    inter_layer_edges = [e for e in network_data['edges'] if e['source_layer'] != e['target_layer']]


    for lname in network_data['layers']:
        intra_x, intra_y, intra_z = [], [], []
        for e in intra_layer_edges:
            if e['source_layer'] == lname and e['source'] in pos and e['target'] in pos:
                sp, tp = pos[e['source']], pos[e['target']]
                intra_x.extend([sp['x'], tp['x'], None])
                intra_y.extend([sp['y'], tp['y'], None])
                intra_z.extend([sp['z'], tp['z'], None])
        if intra_x:
            color = network_data['layers'][lname]['color']
            fig.add_trace(go.Scatter3d(x=intra_x, y=intra_y, z=intra_z,
                                       mode='lines',
                                       line=dict(color=color, width=2),
                                       name=f"Intra-layer edges ({lname})",
                                       legendgroup=f"intra_{lname}",
                                       showlegend=True,
                                       visible=True))


    inter_edge_groups = {}
    for e in inter_layer_edges:
        if e['source'] not in pos or e['target'] not in pos:
            continue
        key = tuple(sorted([e['source_layer'], e['target_layer']]))
        inter_edge_groups.setdefault(key, []).append((pos[e['source']], pos[e['target']]))


    for (l1, l2), segments in inter_edge_groups.items():
        for i, (sp, tp) in enumerate(segments):
            color = interpolate_color(sp['color'], tp['color'], 0.5)
            fig.add_trace(go.Scatter3d(
                x=[sp['x'], tp['x']],
                y=[sp['y'], tp['y']],
                z=[sp['z'], tp['z']],
                mode='lines',
                line=dict(color=color, width=4),
                name=f"Inter-layer edges: {l1}–{l2}" if i == 0 else None,
                legendgroup=f"inter_{l1}_{l2}",
                showlegend=i == 0,
                hoverinfo='text',
                text=f"{l1} ↔ {l2}",
                visible=True))


    for lname, linfo in network_data['layers'].items():
        nodes_by_type = {'actor': [], 'legislation': [], 'unknown': []}
        for node in linfo['nodes']:
            ntype = network_data['node_types'].get(node, 'unknown')
            nodes_by_type[ntype].append(node)
        for ntype, nodes in nodes_by_type.items():
            if not nodes:
                continue
            xs = [pos[n]['x'] for n in nodes]
            ys = [pos[n]['y'] for n in nodes]
            zs = [pos[n]['z'] for n in nodes]
            if display_xyz:
                hover = [f"<b>{n.split('__')[0]}</b><br>Layer: {lname}<br>Type: {ntype}"
                         f"<br>x: {pos[n]['x']:.2f}<br>y: {pos[n]['y']:.2f}<br>z: {pos[n]['z']:.2f}<extra></extra>"
                         for n in nodes]
            else:
                hover = [f"<b>{n.split('__')[0]}</b><br>Layer: {lname}<br>Type: {ntype}<extra></extra>" for n in nodes]
            fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs,
                                       mode='markers+text',
                                       marker=dict(size=10, color=linfo['color'], line=dict(color='white', width=1),
                                                   symbol=shape_map.get(ntype, 'diamond')),
                                       text=[n.split('__')[0] for n in nodes],
                                       textposition='top center',
                                       name=f"{lname} - {ntype}",
                                       legendgroup=f"{lname}_{ntype}",
                                       showlegend=True,
                                       hovertemplate=hover,
                                       visible=True))


    initial_eye = {'x': 2, 'y': 2, 'z': 0.7}
    radius = math.sqrt(initial_eye['x'] ** 2 + initial_eye['y'] ** 2)
    elevation = initial_eye['z']
    n_frames = 120
    rotation_speed = cfg.get("rotation_speed", 150)


    frames = []
    for i in range(n_frames):
        angle = 2 * math.pi * i / n_frames
        eye = dict(x=radius * math.cos(angle), y=radius * math.sin(angle), z=elevation)
        frames.append(go.Frame(layout=dict(scene_camera_eye=eye)))


    fig.frames = frames


    fig.update_layout(
        updatemenus=[dict(
            type='buttons',
            showactive=False,
            y=1,
            x=1.3,
            xanchor='right',
            yanchor='top',
            buttons=[
                dict(label='Play', method='animate', args=[None,
                                                          dict(frame=dict(duration=rotation_speed, redraw=True),
                                                               transition=dict(duration=0),
                                                               fromcurrent=True,
                                                               mode='immediate',
                                                               loop=True)]),
                dict(label='Pause', method='animate', args=[[None], dict(frame=dict(duration=0, redraw=False), mode='immediate')])
            ]
        )]
    )


    fig.update_layout(title='3D Multilayer Governance Network',
                      scene=dict(zaxis=dict(title='Governance Layers',
                                            tickvals=[v['z'] for v in network_data['layers'].values()],
                                            ticktext=list(network_data['layers'].keys())),
                                 aspectmode='manual', aspectratio=dict(x=1, y=1, z=0.8)),
                      legend=dict(bgcolor='rgba(255,255,255,0.9)', bordercolor='black', borderwidth=1, itemsizing='constant'),
                      width=1200, height=900)


    return fig



def main():
    global cfg
    cfg = read_config()
    edges_df, layer_df = load_input_files()
    network_data = prepare_network(edges_df, layer_df)
    pos = calculate_node_positions(network_data, cfg)
    fig = create_3d_visualization(network_data, pos, cfg)
    fig.show()
    fig.write_html("output.html")
    print("\n✅ Visualization saved to: output.html")



if __name__ == "__main__":
    main()
