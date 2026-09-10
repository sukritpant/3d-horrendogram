#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import plotly.graph_objects as go
import plotly.offline as pyo
import numpy as np
import pandas as pd
import os
import yaml
import math

from core import (
    prepare_network,
    calculate_node_positions,
    interpolate_color,
    get_all_layers,
)


def read_config(path="config.yaml"):
    with open(path, "r") as f:
        cfg = yaml.safe_load(f)
    cfg.setdefault("display_xyz_in_tooltip", False)
    cfg.setdefault("actor_legislation_z_offset", True)
    cfg.setdefault("actor_z_offset", 0.2)
    cfg.setdefault("rotation_speed", 150)
    return cfg


def load_input_files():
    first_path = input("Enter path to your main dataset file (CSV or Excel): ").strip()
    if not os.path.isfile(first_path):
        raise FileNotFoundError(f"File not found: {first_path}")
    ext = os.path.splitext(first_path)[1].lower()
    if ext in (".xls", ".xlsx"):
        edges_df = pd.read_excel(first_path, sheet_name="edges")
        try:
            layer_df = pd.read_excel(first_path, sheet_name="layers")
        except Exception:
            print("No 'layers' sheet found — layer order will be requested interactively.")
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


def prompt_layer_order(layers):
    """Interactively ask the user to assign an order number to each layer."""
    layer_order = {}
    print("Assign an order number (starting from 1, bottom to top) to each layer:")
    for layer in layers:
        while True:
            val = input(f"  Order for '{layer}': ").strip()
            if val.isdigit() and int(val) not in layer_order.values():
                layer_order[layer] = int(val)
                break
            else:
                print("  Please enter a unique positive integer.")
    return [x for x, _ in sorted(layer_order.items(), key=lambda kv: kv[1])]


def create_3d_visualization(network_data, pos, cfg):
    fig = go.Figure()
    shape_map = {'actor': 'circle', 'legislation': 'square', 'instrument': 'square', 'unknown': 'diamond'}
    display_xyz = cfg.get("display_xyz_in_tooltip", False)

    # Layer rings
    for lname, linfo in network_data['layers'].items():
        theta = np.linspace(0, 2 * np.pi, 60)
        x, y = 4 * np.cos(theta), 4 * np.sin(theta)
        z = np.full_like(x, linfo['z'])
        fig.add_trace(go.Scatter3d(
            x=x, y=y, z=z, mode='lines',
            line=dict(color=linfo['color'], width=2),
            name=f"Layer: {lname}",
            legendgroup=f"layer_{lname}",
            showlegend=True
        ))

    intra = [e for e in network_data['edges'] if e['source_layer'] == e['target_layer']]
    inter = [e for e in network_data['edges'] if e['source_layer'] != e['target_layer']]

    # Intra-layer edges — one trace per edge for hover text
    for lname in network_data['layers']:
        for i, e in enumerate([e for e in intra if e['source_layer'] == lname]):
            if e['source'] not in pos or e['target'] not in pos:
                continue
            sp, tp = pos[e['source']], pos[e['target']]
            hover = f"<b>{e['source_orig']} → {e['target_orig']}</b><br>Layer: {lname}"
            if e.get('tags'):
                hover += f"<br>Tags: {', '.join(e['tags'])}"
            if e.get('description'):
                hover += f"<br>{e['description']}"
            fig.add_trace(go.Scatter3d(
                x=[sp['x'], tp['x']], y=[sp['y'], tp['y']], z=[sp['z'], tp['z']],
                mode='lines',
                line=dict(color=network_data['layers'][lname]['color'], width=5),
                name=f"Intra-layer ({lname})" if i == 0 else None,
                legendgroup=f"intra_{lname}",
                showlegend=i == 0,
                hoverinfo='none',
                hovertext=hover
            ))

    # Inter-layer edges
    inter_groups = {}
    for e in inter:
        if e['source'] not in pos or e['target'] not in pos:
            continue
        key = tuple(sorted([e['source_layer'], e['target_layer']]))
        inter_groups.setdefault(key, []).append(e)

    for (l1, l2), edges in inter_groups.items():
        for i, e in enumerate(edges):
            sp, tp = pos[e['source']], pos[e['target']]
            color = interpolate_color(sp['color'], tp['color'], 0.5)
            hover = f"<b>{e['source_orig']} ({l1}) ↔ {e['target_orig']} ({l2})</b>"
            if e.get('tags'):
                hover += f"<br>Tags: {', '.join(e['tags'])}"
            if e.get('description'):
                hover += f"<br>{e['description']}"
            fig.add_trace(go.Scatter3d(
                x=[sp['x'], tp['x']], y=[sp['y'], tp['y']], z=[sp['z'], tp['z']],
                mode='lines',
                line=dict(color=color, width=7),
                name=f"Inter-layer: {l1}–{l2}" if i == 0 else None,
                legendgroup=f"inter_{l1}_{l2}",
                showlegend=i == 0,
                hoverinfo='none',
                hovertext=hover
            ))

    # Nodes
    for lname, linfo in network_data['layers'].items():
        nodes_by_type = {'actor': [], 'legislation': [], 'instrument': [], 'unknown': []}
        for node in linfo['nodes']:
            ntype = network_data['node_types'].get(node, 'unknown')
            nodes_by_type[ntype].append(node)

        for ntype, nodes in nodes_by_type.items():
            if not nodes:
                continue
            xs = [pos[n]['x'] for n in nodes]
            ys = [pos[n]['y'] for n in nodes]
            zs = [pos[n]['z'] for n in nodes]
            hovers = []
            for n in nodes:
                name_clean = n.split('__')[0]
                tags = network_data['node_tags'].get(n, [])
                desc = network_data['node_descriptions'].get(n)
                h = f"<b>{name_clean}</b><br>Layer: {lname}<br>Type: {ntype.capitalize()}"
                if tags:
                    h += f"<br>Tags: {', '.join(tags)}"
                if desc:
                    h += f"<br>{desc}"
                if display_xyz:
                    h += f"<br>x: {pos[n]['x']:.2f}  y: {pos[n]['y']:.2f}  z: {pos[n]['z']:.2f}"
                hovers.append(h)

            fig.add_trace(go.Scatter3d(
                x=xs, y=ys, z=zs,
                mode='markers+text',
                marker=dict(size=10, color=linfo['color'],
                            line=dict(color='white', width=1),
                            symbol=shape_map.get(ntype, 'diamond')),
                text=[n.split('__')[0] for n in nodes],
                textposition='top center',
                name=f"{lname} - {ntype}",
                legendgroup=f"{lname}_{ntype}",
                showlegend=True,
                hoverinfo='none',
                hovertext=hovers
            ))

    # Camera rotation animation
    initial_eye = {'x': 2, 'y': 2, 'z': 0.7}
    radius = math.sqrt(initial_eye['x'] ** 2 + initial_eye['y'] ** 2)
    n_frames = 120
    rotation_speed = cfg.get("rotation_speed", 150)

    fig.frames = [
        go.Frame(layout=dict(scene_camera_eye=dict(
            x=radius * math.cos(2 * math.pi * i / n_frames),
            y=radius * math.sin(2 * math.pi * i / n_frames),
            z=initial_eye['z']
        ))) for i in range(n_frames)
    ]

    fig.update_layout(
        updatemenus=[dict(
            type='buttons', showactive=False, y=1, x=1.3,
            xanchor='right', yanchor='top',
            buttons=[
                dict(label='Play', method='animate',
                     args=[None, dict(frame=dict(duration=rotation_speed, redraw=True),
                                     transition=dict(duration=rotation_speed, easing='linear'),
                                     fromcurrent=True, mode='immediate', loop=True)]),
                dict(label='Pause', method='animate',
                     args=[[None], dict(frame=dict(duration=0, redraw=False), mode='immediate')])
            ]
        )],
        title='3D Multilayer Governance Network',
        scene=dict(
            zaxis=dict(
                title='Governance Layers',
                tickvals=[v['z'] for v in network_data['layers'].values()],
                ticktext=list(network_data['layers'].keys())
            ),
            aspectmode='manual',
            aspectratio=dict(x=1, y=1, z=0.8)
        ),
        legend=dict(bgcolor='rgba(255,255,255,0.9)', bordercolor='black', borderwidth=1, itemsizing='constant'),
        width=1200, height=900
    )

    return fig


def main():
    cfg = read_config()
    edges_df, layer_df = load_input_files()

    manual_order = None
    if layer_df is None:
        layers = get_all_layers(edges_df)
        manual_order = prompt_layer_order(layers)

    network_data = prepare_network(edges_df, layer_df, manual_order=manual_order)
    pos = calculate_node_positions(network_data, cfg)
    fig = create_3d_visualization(network_data, pos, cfg)

    plot_div = pyo.plot(fig, output_type='div', include_plotlyjs='cdn')

    html_content = fr"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>3D Multilayer Governance Network</title>
    <style>
        body, html {{ margin: 0; padding: 0; height: 100%; font-family: "Open Sans", verdana, arial, sans-serif; background: white; overflow: hidden; }}
        #plot-container {{ height: 100vh; width: 100vw; position: relative; }}
        #info-box {{
            position: absolute; bottom: 40px; right: 40px; width: 320px;
            background: rgba(255,255,255,0.9); border: 1px solid #777; border-radius: 4px;
            padding: 15px; color: #333; font-size: 13px;
            box-shadow: 2px 2px 10px rgba(0,0,0,0.1); z-index: 1000;
            pointer-events: none; line-height: 1.5;
        }}
        #info-box b {{ color: black; }}
        .plotly-graph-div {{ height: 100% !important; width: 100% !important; }}
    </style>
</head>
<body>
    <div id="plot-container">
        {plot_div}
        <div id="info-box"><b>Network Details</b><br>Hover over a node or edge to explore descriptions.</div>
    </div>
    <script>
        window.addEventListener('load', function() {{
            const plotDiv = document.querySelector('.plotly-graph-div');
            if (!plotDiv) return;
            plotDiv.on('plotly_hover', function(data) {{
                const point = data.points[0];
                let content = point.hovertext || point.text || '';
                if (!content && point.data) {{
                    const idx = point.pointNumber || 0;
                    const src = point.data.hovertext || point.data.text;
                    content = Array.isArray(src) ? src[idx] : (src || '');
                }}
                if (content) document.getElementById('info-box').innerHTML = content;
            }});
            plotDiv.on('plotly_doubleclick', function() {{
                document.getElementById('info-box').innerHTML = '<b>Network Details</b><br>Hover over a node or edge to explore descriptions.';
            }});
        }});
    </script>
</body>
</html>"""

    with open("output.html", "w", encoding="utf-8") as f:
        f.write(html_content)

    print("\nVisualization saved to: output.html")


if __name__ == "__main__":
    main()