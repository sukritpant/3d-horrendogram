# 3D Multilayer Network Visualization

A Python tool to visualize multilayer networks in 3D focused on 3D visualization of Horrendograms using Plotly. The script allows to explore complex relationships as multiplex networks with color-coding, node shapes and labels.

---

## Features

- To visualize multilayer network with layer order and colors
- Display actor/legislation with different shapes and configure Z-offset for settings
- Create a rotation animation for viewing
- HTML export for sharing outputs
- Data loading through CSV files or Excel (multiple sheets)

---

## Installation

1. **Clone the repository**  
git clone https://github.com/sukritpant/3d-horrendogram
cd 3d-horrendogram

2. **Install required libraries**  
pip install numpy pandas plotly pyyaml

---

## Usage

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

## File Structure

| File                      | Purpose                                         |
|---------------------------|-------------------------------------------------|
| 3d_multilayer_network.py  | Main visualization script                       |
| config.yaml               | Configuration file for display/animation options|
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
- **Dependencies missing**: Run 'pip install numpy pandas plotly pyyaml'.

---
## Future features to work on

- **Python library**: Develop this program into a Python library.
- **Interactive Web-Tool**: Create a web-based tool for non-technical users
- **Integration with other libraries**: Integrate the tool to read from other popular network libaries such as networkx, pymnet.

## License

This work is licensed under a Creative Commons Attribution 4.0 International License.
[Link to official license](https://creativecommons.org/licenses/by/4.0/)

---

## Citing

This tool was created as part of the collaborative multidisciplinary project SOS3D at Åbo Akademi University (Turku, Finland) in 2025. In accordance with the license any distribution, remixing, adaptation, and development should acknowledge project researcher Sukrit Pant as the creator.

## Link to project
Visit our project website for further details̀: [Link to Project](https://research.abo.fi/en/projects/3d-visualization-of-governance-and-regulatory-layers/)
Visit Zenodo for the project model: [Link to Project Model](https://doi.org/10.5281/zenodo.17541211)
