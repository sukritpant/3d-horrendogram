# 3D Horrendogram — Command-Line Tool

A Python script that turns a table of relationships between actors and legislation
into an interactive 3D multilayer network, saved as a single HTML file. Layers are
stacked as coloured rings, so you can see how governance levels connect.

Looking for the browser-based version? Use it online at
<https://sukritpant.com/3dhorrendogram/> with nothing to install, or see the
[`web-frontend`](https://github.com/sukritpant/3d-horrendogram/tree/web-frontend) branch.

---

## Features

- Multilayer network with a custom layer order and a colour per layer
- Different node shapes for actors, legislation and unknown types
- Configurable Z-offset between actors and legislation
- Animated camera rotation with play/pause buttons
- HTML output you can share
- Input from CSV or multi-sheet Excel files

---

## Installation

```bash
git clone https://github.com/sukritpant/3d-horrendogram
cd 3d-horrendogram
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

On Windows, activate with `venv\Scripts\activate`.

---

## Usage

### 1. Prepare your data

Use a CSV file, or an Excel file with a sheet named exactly `edges`.

| Column | Required | Meaning |
|---|---|---|
| `source` | Yes | Name of the actor or legislation |
| `source_layer` | Yes | Layer it belongs to |
| `source_actor/legislation` | Yes | `actor` or `legislation` |
| `target` | No | Name of the connected actor or legislation |
| `target_layer` | No | Layer the target belongs to |
| `target_actor/legislation` | No | `actor` or `legislation` |

Leave the target columns blank for a node with no connection. A type that isn't
`actor` or `legislation`, or a blank one, is shown as unknown.

Example:

```csv
source,source_layer,source_actor/legislation,target,target_layer,target_actor/legislation
Actor A,Layer 1,actor,Legislation X,Layer 2,legislation
Legislation X,Layer 2,legislation,Actor B,Layer 3,actor
```

### 2. Set the layer order (optional)

Provide either a separate CSV file or a `layers` sheet in your Excel file:

| Column | Meaning |
|---|---|
| `layer` | Layer name, as used in your data |
| `order` | A number starting from 1 |

Order `1` is the **top** layer. If you don't provide an order, the script asks you
to number each layer. That prompt uses the same numbering, so `1` is the top layer
even though the on-screen text may say "bottom to top".

### 3. Adjust the settings (optional)

Edit `config.yaml`:

```yaml
display_xyz_in_tooltip: false       # show coordinates in the tooltip
actor_legislation_z_offset: true    # separate actors and legislation vertically
actor_z_offset: 0.33                # size of that separation
rotation_speed: 250                 # milliseconds per animation frame
```

### 4. Run it

```bash
python3 3d-horrendogram.py
```

Enter the path to your data file when asked. The result is saved as `output.html`
in the current folder. Open it in a browser.

---

## Output

- Coloured rings for layers
- Circles for actors, squares for legislation, diamonds for unknown types
- Play/pause controls for the camera rotation

The file produced by the `text-based-cli` branch contains Plotly and works offline
(about 5 MB). The one produced by the `web-frontend` branch is much smaller but
loads Plotly from the internet when opened.

---

## Customization

- Change colours or marker shapes in the code (`generate_layer_colors`, `shape_map`)
- Change the vertical separation with `actor_z_offset`
- Change the animation speed with `rotation_speed`

---

## Troubleshooting

- **Edges not visible:** check that all columns are present and named correctly.
- **Node offsets not appearing:** set `actor_legislation_z_offset: true` in `config.yaml`.
- **Missing packages:** activate the venv and run `pip install -r requirements.txt`.

---

## Future work

- Develop the tool into a Python library
- Read from network libraries such as networkx and pymnet

---

## License

This work is licensed under a
[Creative Commons Attribution 4.0 International License](https://creativecommons.org/licenses/by/4.0/).

---

## Citing

This tool was created as part of the collaborative multidisciplinary project SOS3D
at Åbo Akademi University (Turku, Finland) in 2025. In accordance with the license,
any distribution, remixing, adaptation and development should acknowledge project
researcher Sukrit Pant as the creator.

You can also cite our Zenodo article: Engström, V., Pant, S., Grönberg, C., &
Teixeira, J. (2025). 3D Multilayer Governance Visualization. Zenodo.
[https://doi.org/10.5281/zenodo.17541211](https://doi.org/10.5281/zenodo.17541211)

## Project links

- [Project website](https://research.abo.fi/en/projects/3d-visualization-of-governance-and-regulatory-layers/)
- [Project model on Zenodo](https://doi.org/10.5281/zenodo.17541211)
