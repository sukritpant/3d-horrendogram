# 3D Multilayer Network Visualization

A Python tool to visualize multilayer networks in 3D focused on 3D visualization of Horrendograms using Plotly. Explore complex relationships as multiplex networks with color-coding, node shapes and labels — either from the command line, or through a browser-based web app.

The project now ships two ways to run the visualizer:

| Mode | Entry point | Best for |
|------|-------------|----------|
| CLI | `3d-horrendogram.py` | Local, offline use |
| Web app | `main.py` + `static/` | Sharing with non-technical collaborators |

---

## Features

- To visualize multilayer network with layer order and colors
- Display actor/legislation with different shapes and configure Z-offset for settings
- Create a rotation animation for viewing
- HTML export for sharing outputs
- Data loading through CSV files or Excel (multiple sheets), or by uploading an Obsidian vault ZIP (web app)
- Interactive layer reordering, legend/tag filtering, sidebar UI (web app)

---

## Installation

1. **Clone the repository**  
git clone https://github.com/sukritpant/3d-horrendogram
cd 3d-horrendogram

2. **Install required libraries**  
pip install -r requirements.txt

---

## CLI Usage

1. **Prepare your data files**

- **Main dataset**: Excel ('.xlsx') or CSV file containing your network edges. The Excel file should have an 'edges' sheet, and optionally a 'layers' sheet.  
  Required columns in 'edges':
    - source (name of actor/legislation)
    - source_layer (layer it belongs in)
    - source_actor/legislation (mention if actor/legislation)
    - target (name of actor/legislation)
    - target_layer (layer it belongs in)
    - target_actor/legislation (mention if actor/legislation)

  **Note**: Target is not necessary if a node needs to exist without target. At the moment the code only looks for actor/legislation or blank (unknown).
- **Layer order file** (optional): CSV or Excel sheet listing layers and their order.
    Required columns in 'layers' sheet if using multi-sheet Excel:
        - layer (same layer name as mention in source_layer and/or target_layer)
        - order (in number starting from 1)


2. **Edit configuration**

Open and modify 'config.yaml' as needed:

display_xyz_in_tooltip: false
actor_legislation_z_offset: false
actor_z_offset: 0.33
rotation_speed: 250 (Set time in millisecond per frame)


3. **Run the script**
python3 3d-horrendogram.py


The script will prompt for file paths and generate 'output.html' containing your interactive visualization. If you have not provided layer order, it will prompt for layer order as well.

---

## Output

- Interactive Plotly 3D graph with:
- Colored rings for layers
- Type/role-based node markers ("actor" as circles, "legislation" as squares, "unknown" as diamonds)
- Animated camera rotation via play/pause buttons
- Exported as a standalone HTML file

---

## Web Application

The web app is a browser-based frontend for the same visualization engine, meant for sharing with collaborators who don't want to run Python scripts directly.

**Install dependencies** (same `requirements.txt` as the CLI)

```bash
pip install -r requirements.txt
```

**Start the server**

```bash
uvicorn main:app --reload
```

Open `http://localhost:8000` in a browser.

### Architecture

```
3d-horrendogram/
├── core.py                  # Shared network logic (imported by all entry points)
├── parser.py                # Obsidian vault parser (directory or ZIP)
├── main.py                  # FastAPI backend
├── 3d-horrendogram.py       # CLI tool
├── config.yaml              # CLI configuration
├── requirements.txt         # Dependencies for CLI and web app
└── static/
    ├── index.html
    ├── script.js
    └── style.css
```

`main.py` exposes two endpoints, both returning `{ network_data, positions, config }`:

| Endpoint | Input | Description |
|----------|-------|-------------|
| `POST /process` | CSV or Excel file + optional layer order file | Standard edge/layer data |
| `POST /process-obsidian` | ZIP of an Obsidian vault | Parses actors, instruments, interlinkages |

### Data Inputs

**Option 1 — CSV or Excel**: same format as the CLI tool, see [CLI Usage](#cli-usage) above.

**Option 2 — Obsidian Vault ZIP**: zip your Obsidian vault (or just the relevant folders) and upload it. The ZIP must contain three folders, matched by case-insensitive name:

| Folder name contains | Content |
|----------------------|---------|
| `Actors` | One `.md` file per actor node |
| `Instruments` | One `.md` file per instrument/legislation node |
| `Interlinkages` | One `.md` file per edge between nodes |

Actor / Instrument frontmatter format:

```yaml
---
type: actor          # or: instrument, legislation
level: national      # becomes the layer name
tags:
  - governance
  - nutrients
---

## Description

Free-text description of this node.
```

Interlinkage frontmatter format:

```yaml
---
from: "[[Source Node Name]]"
to: "[[Target Node Name]]"
tags:
  - governance
---

## Description

Free-text description of this relationship.
```

### Sidebar: Setup vs. Filters

The sidebar is split into two tabs, purely a view toggle with no reprocessing on switch:

| Tab | Contents |
|-----|----------|
| **Setup** | Data source picker, dataset/ZIP upload, visual settings, **Generate Visualization** button |
| **Filters** | Layer order, legend (trace visibility), tag filter — populated once a visualization has been generated |

- **Layer Order**: reorder governance layers with the ▲/▼ buttons (or drag via the grip handle), then click **Apply Order** to re-render with the new order. This reuses `core.py`'s `manual_order` support in `prepare_network(edges_df, layer_df, manual_order)`.
- **Legend**: checklist of Layers / Node Types / Edges to toggle trace visibility, replacing the on-plot Plotly legend so it doesn't compete for space with the 3D view.
- **Tag Filter**: click tags to highlight matching nodes/edges (OR logic across multiple tags); non-matching items dim rather than disappear.

### Visual Settings

| Setting | Default | Description |
|---------|---------|-------------|
| Enable Actor Z-Offset | on | Elevates actor nodes slightly above the layer plane |
| Actor Z-Offset | 0.33 | Vertical separation amount |
| Rotation Speed | 250 ms | Camera rotation animation speed |
| Show X,Y,Z in Tooltip | off | Displays raw coordinates in the hover panel |

---

## File Structure

| File                      | Purpose                                         |
|---------------------------|-------------------------------------------------|
| 3d-horrendogram.py        | CLI visualization script                        |
| core.py                   | Shared network logic used by CLI and web app    |
| parser.py                 | Obsidian vault parser                           |
| main.py                   | FastAPI backend for the web app                 |
| static/                   | Web app frontend (HTML/CSS/JS)                  |
| config.yaml               | Configuration file for display/animation options|
| requirements.txt          | Python dependencies                             |
| README.md                 | Documentation and usage examples                |
| *your_data_files.xlsx*    | Your network edge/layer data                    |

---

## Customization

- Modify colors or marker shapes in the Python script as needed ('generate_layer_colors', 'shape_map').
- Set custom Z offsets via 'actor_z_offset' in the config file.
- Tune rotary speed with 'rotation_speed'.

---

## Troubleshooting

- **Edges not visible**: Ensure all required columns are present and properly named.
- **Node offsets not appearing**: Set 'actor_legislation_z_offset: true' in 'config.yaml'.
- **Dependencies missing**: Run 'pip install -r requirements.txt'.

---
## Future features to work on

- **Python library**: Develop this program into a Python library.
- **Integration with other libraries**: Integrate the tool to read from other popular network libaries such as networkx, pymnet.

## License

This work is licensed under a Creative Commons Attribution 4.0 International License.
[Link to official license](https://creativecommons.org/licenses/by/4.0/)

---

## Citing

This tool was created as part of the collaborative multidisciplinary project SOS3D at Åbo Akademi University (Turku, Finland) in 2025. In accordance with the license any distribution, remixing, adaptation, and development should acknowledge project researcher Sukrit Pant as the creator.

You can also cite our Zenodo article from the link below: Engström, V., Pant, S., Grönberg, C., & Teixeira, J. (2025). 3D Multilayer Governance Visualization. Zenodo.[https://doi.org/10.5281/zenodo.17541211](https://doi.org/10.5281/zenodo.17541211)

## Link to project
Visit our project website for further details̀: [Link to Project](https://research.abo.fi/en/projects/3d-visualization-of-governance-and-regulatory-layers/)

Visit Zenodo for the project model: [Link to Project Model](https://doi.org/10.5281/zenodo.17541211)
