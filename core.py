import numpy as np
import pandas as pd
from collections import defaultdict


def clean_string(value):
    if pd.isna(value):
        return None
    return str(value).strip() or None


def normalize_layer_name(value):
    if value is None:
        return None
    return str(value).strip().lower()


def parse_tags(value):
    """Parse tags from either a comma-separated string or a list."""
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return [str(t).strip() for t in value if str(t).strip()]
    try:
        if pd.isna(value):
            return []
    except (TypeError, ValueError):
        pass
    return [t.strip() for t in str(value).split(',') if t.strip()]


def generate_layer_colors(layers):
    palette = [
        "#4287f5", "#42f554", "#f54242", "#f5a142", "#9b42f5",
        "#42f5f2", "#d9f542", "#6f42f5", "#f5429e", "#999999"
    ]
    return {layer: palette[i % len(palette)] for i, layer in enumerate(layers)}


def interpolate_color(c1, c2, t):
    def h2r(h): return tuple(int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    def r2h(rgb): return '#' + ''.join(f'{int(v * 255):02x}' for v in rgb)
    rgb1, rgb2 = h2r(c1), h2r(c2)
    blended = tuple((1 - t) * a + t * b for a, b in zip(rgb1, rgb2))
    return r2h(blended)


def get_all_layers(edges_df):
    """Return sorted list of unique layer names from an edges DataFrame."""
    df = edges_df.copy()
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={'source_actor/legislation': 'source_type', 'target_actor/legislation': 'target_type'})
    has_target = 'target_layer' in df.columns
    layers = set(df['source_layer'].dropna().apply(normalize_layer_name))
    if has_target:
        layers |= set(df['target_layer'].dropna().apply(normalize_layer_name))
    return [l for l in sorted(layers) if l and not str(l).isspace()]


def prepare_network(edges_df, layer_df=None, manual_order=None):
    # astype(object) prevents pandas' string dtype from silently turning
    # None back into NaN when clean_string()/normalize_layer_name() assign it,
    # which otherwise crashes JSON serialization downstream (pandas >= 2.x with
    # the future.infer_string / pandas 3.0 default string dtype).
    edges_df = edges_df.copy().astype(object)
    edges_df.columns = [c.strip().lower() for c in edges_df.columns]
    edges_df = edges_df.rename(columns={
        'source_actor/legislation': 'source_type',
        'target_actor/legislation': 'target_type'
    })

    required_cols = {'source', 'source_layer', 'source_type'}
    if not required_cols.issubset(edges_df.columns):
        raise ValueError(f"Input data must contain required columns: {required_cols}")

    edges_df['source'] = edges_df['source'].apply(clean_string)
    edges_df['source_layer'] = edges_df['source_layer'].apply(normalize_layer_name)
    edges_df['source_type'] = edges_df['source_type'].apply(clean_string)

    for col in ('target', 'target_layer', 'target_type', 'description', 'node_description'):
        if col not in edges_df.columns:
            # Assigning a bare `None` here creates the column as float64 NaN under
            # pandas 3.x, even though the rest of the frame is object dtype (see the
            # astype(object) note above) — the object-dtype cast doesn't retroactively
            # apply to columns added afterwards. Build it as an explicit object Series
            # so it survives clean_string() without round-tripping back to NaN.
            edges_df[col] = pd.Series([None] * len(edges_df), index=edges_df.index, dtype=object)

    edges_df['target'] = edges_df['target'].apply(clean_string)
    edges_df['target_layer'] = edges_df['target_layer'].apply(normalize_layer_name)
    edges_df['target_type'] = edges_df['target_type'].apply(clean_string)
    edges_df['description'] = edges_df['description'].apply(clean_string)
    edges_df['node_description'] = edges_df['node_description'].apply(clean_string)

    edges_df = edges_df.dropna(subset=['source', 'source_layer'])
    has_targets = edges_df['target'].notna().any() and edges_df['target_layer'].notna().any()

    all_layers = sorted(
        set(edges_df['source_layer'].dropna()) |
        (set(edges_df['target_layer'].dropna()) if has_targets else set())
    )
    all_layers = [l for l in all_layers if l and not str(l).isspace()]

    if manual_order:
        ordered_layers = [l for l in manual_order if l in all_layers]
        ordered_layers += [l for l in all_layers if l not in ordered_layers]
    elif layer_df is not None:
        layer_df = layer_df.copy().astype(object)
        layer_df.columns = [c.strip().lower() for c in layer_df.columns]
        if {'layer', 'order'}.issubset(layer_df.columns):
            layer_df['layer'] = layer_df['layer'].apply(normalize_layer_name)
            layer_df = layer_df.dropna(subset=['layer', 'order'])
            ordered_layers = [
                row['layer'] for _, row in layer_df.sort_values('order').iterrows()
                if row['layer'] in all_layers
            ]
            ordered_layers += [l for l in all_layers if l not in ordered_layers]
        else:
            ordered_layers = all_layers
    else:
        ordered_layers = all_layers

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
        tgt_nodes = edges_df.loc[edges_df['target_layer'] == layer, 'target'].dropna().tolist() if has_targets else []
        for name in set(src_nodes) | set(tgt_nodes):
            nodes_in_layer.add(node_unique_names.get((name, layer), name))
        if not nodes_in_layer:
            continue
        layers_dict[layer] = {'z': z_map[layer], 'color': color_map[layer], 'nodes': sorted(nodes_in_layer)}

    edges = []
    if has_targets:
        for _, row in edges_df.iterrows():
            if pd.isna(row['target']) or pd.isna(row['target_layer']):
                continue
            s_unique = node_unique_names.get((row['source'], row['source_layer']), row['source'])
            t_unique = node_unique_names.get((row['target'], row['target_layer']), row['target'])
            edges.append({
                'source': s_unique,
                'source_layer': row['source_layer'],
                'target': t_unique,
                'target_layer': row['target_layer'],
                'source_orig': row['source'],
                'target_orig': row['target'],
                'tags': parse_tags(row.get('edge_tags')),
                # clean_string() re-normalizes here rather than trusting the earlier
                # column-level cleaning: pandas' iterrows() rebuilds each row as its own
                # Series and re-infers a dtype across all columns, which can silently
                # turn an already-cleaned None back into a float NaN (pandas 3.x).
                'description': clean_string(row.get('description'))
            })

    node_types = {}
    node_tags = {}
    node_descriptions = {}
    valid_types = {'actor', 'legislation', 'instrument'}

    for _, row in edges_df.iterrows():
        s_unique = node_unique_names.get((row['source'], row['source_layer']), row['source'])
        s_type = clean_string(row.get('source_type'))
        s_tags = parse_tags(row.get('source_tags'))
        s_desc = clean_string(row.get('node_description'))

        if s_unique not in node_types:
            node_types[s_unique] = s_type.lower() if s_type and s_type.lower() in valid_types else 'unknown'
        if s_tags and s_unique not in node_tags:
            node_tags[s_unique] = s_tags
        if s_desc and s_unique not in node_descriptions:
            node_descriptions[s_unique] = s_desc

        if has_targets and pd.notna(row.get('target')) and pd.notna(row.get('target_layer')):
            t_unique = node_unique_names.get((row['target'], row['target_layer']), row['target'])
            t_type = clean_string(row.get('target_type'))
            t_tags = parse_tags(row.get('target_tags'))
            if t_unique not in node_types:
                node_types[t_unique] = t_type.lower() if t_type and t_type.lower() in valid_types else 'unknown'
            if t_tags and t_unique not in node_tags:
                node_tags[t_unique] = t_tags

    all_tags_set = set()
    for tags in node_tags.values():
        all_tags_set.update(tags)
    for edge in edges:
        all_tags_set.update(edge['tags'])

    return {
        "layers": layers_dict,
        "edges": edges,
        "node_types": node_types,
        "node_tags": node_tags,
        "node_descriptions": node_descriptions,
        "ordered_layers": ordered_layers,
        "all_tags": sorted(all_tags_set)
    }


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
            z = base_z
            if use_z_offset and network_data['node_types'].get(node, 'unknown').lower() == 'actor':
                z = base_z + actor_offset
            pos[node] = {'x': float(x), 'y': float(y), 'z': float(z), 'color': linfo['color']}
    return pos
