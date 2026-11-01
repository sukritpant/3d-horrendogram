# 3D Horrendogram — Web App

A browser-based tool for exploring governance networks in 3D. Upload a spreadsheet
or an Obsidian vault and see actors, instruments and the links between them as a
stack of layers you can rotate, filter and export.

Looking for the command-line version? See [README-CLI.md](README-CLI.md) or the
[`text-based-cli`](https://github.com/sukritpant/3d-horrendogram/tree/text-based-cli) branch.

---

## Features

- Interactive 3D view with one ring per governance layer
- Input from CSV, Excel or a zipped Obsidian vault
- Layer reordering without re-uploading
- Show/hide controls for layers and edges
- Tag filter that highlights matching nodes and edges
- Details panel with descriptions and clickable links
- Light and dark themes
- Export to a single interactive HTML file

---

## Getting started

### Use it online

Don't want to install anything? Use the hosted app at
<https://sukritpant.com/3dhorrendogram/>. Your files are uploaded to that server to
be processed, so install it locally if your data is sensitive.

### Install it locally

```bash
git clone -b web-frontend https://github.com/sukritpant/3d-horrendogram
cd 3d-horrendogram
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Open <http://localhost:8000>. On Windows, activate with `venv\Scripts\activate`.

To try it straight away, upload `sample_data_with_descriptions.csv` on the **Setup**
tab and click **Generate Visualization**.

---

## Preparing your data

### Option 1: CSV or Excel

Use a comma-separated, UTF-8 CSV file, or an Excel file with a sheet named exactly
`edges`.

| Column | Required | Meaning |
|---|---|---|
| `source` | Yes | Node name |
| `source_layer` | Yes | Layer it belongs to |
| `source_type` | Yes | `actor`, `instrument` or `legislation` |
| `target` | No | Connected node. Leave blank for a node with no connection |
| `target_layer` | No | Layer of the target |
| `target_type` | No | Type of the target |
| `description` | No | Describes the connection |
| `node_description` | No | Describes the source node |
| `target_node_description` | No | Describes the target node |
| `source_tags`, `target_tags`, `edge_tags` | No | Comma-separated tags |

The column names `source_actor/legislation` and `target_actor/legislation` are also
accepted in place of `source_type` and `target_type`.

To set the layer order, add a `layers` sheet or upload a separate file with the
columns `layer` and `order`, where `1` is the top layer. See `layer_order.csv` for
an example. You can also reorder layers in the app.

### Option 2: Obsidian vault

Upload a ZIP of a vault containing three folders, recognised by these words in their
names: `Actors`, `Instruments` and `Interlinkages`. A working example is in
[`starter-vault/`](starter-vault).

The file name of an actor or instrument note is the node's name:

```markdown
---
type: actor          # or: instrument, legislation
level: national      # becomes the layer name
tags:
  - governance
---

## Description

Text describing this node.
```

An interlinkage note connects two nodes, and its links must match their file names:

```markdown
---
from: "[[Source Node Name]]"
to: "[[Target Node Name]]"
tags:
  - governance
---

## Description

Text describing this relationship.
```

Notes with no interlinkages appear as standalone nodes on their layer.

---

## Using the app

The sidebar has two tabs.

**Setup**: choose your data source and files, adjust the visual settings, and
generate the visualization.

| Setting | Default | Description |
|---|---|---|
| Enable Actor Z-Offset | On | Lifts actors slightly above the layer plane |
| Actor Z-Offset | 0.33 | Size of that separation |
| Rotation Speed | 250 ms | Speed of the camera animation |
| Show X,Y,Z in Tooltip | Off | Adds coordinates to the details panel |

**Filters**: available once a visualization exists.

- **Layer Order:** move layers with ▲/▼ or by dragging, then click **Apply Order**
- **Tag Filter:** click tags to highlight matches; everything else dims
- **Show / Hide:** toggle layers and edges
- **Export:** save an interactive HTML file, with an option to work offline

Hover over a node or edge to preview its details, click to pin them, and
double-click to release. Circles are actors, squares are instruments or legislation,
and diamonds are unknown types.

---

## Project structure

```
3d-horrendogram/
├── main.py              # FastAPI backend
├── core.py              # Network logic
├── parser.py            # Obsidian vault parser
├── static/              # Frontend (HTML, CSS, JS)
├── starter-vault/       # Example Obsidian vault with templates
├── 3d-horrendogram.py   # Command-line tool (see README-CLI.md)
├── config.yaml          # Command-line tool settings
└── requirements.txt
```

| Endpoint | Input |
|---|---|
| `POST /process` | CSV or Excel file, plus an optional layer order file |
| `POST /process-obsidian` | ZIP of an Obsidian vault |

Both return `{ network_data, positions, config }`.

---

## Troubleshooting

- **A layer called `unknown`:** a note has no `level`, or a link doesn't match a file name.
- **Excel upload fails:** the data sheet must be named exactly `edges`.
- **CSV upload fails:** save it as comma-separated UTF-8. Some regional Excel settings
  use semicolons instead.
- **Changes don't appear:** hard-refresh the browser (⌘⇧R or Ctrl+Shift+R).

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
