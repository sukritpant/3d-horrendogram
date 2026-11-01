document.addEventListener('DOMContentLoaded', () => {
    // ─── State ────────────────────────────────────────────────────────────────
    let traceTagSets = [];   // parallel to Plotly traces: null | string[]
    let selectedTags = new Set();
    let currentSource = 'csv';
    let currentLayerOrder = [];      // live order shown/edited in the Filters tab
    let legendGroups = [];           // [{legendgroup, label, color, indices, category}]
    let edgeMeta = [];               // [{index, legendgroup, sourceGroup, targetGroup}] — one per edge trace
    let nodeTraceMeta = [];          // [{index, tagsPerNode, baseColor}] — one per node trace
    let nodeGroupVisible = {};       // legendgroup ("nodes_<layer>") -> boolean, from the Layers checkboxes
    let edgeGroupVisible = {};       // legendgroup ("intra_x" / "inter_x_y") -> boolean, from Edges checkboxes
    let lastRender = null;           // last {network_data, positions, config} — the export payload
    let pinned = false;              // details panel holding a clicked node/edge

    const PLOTLY_CDN = 'https://cdn.plot.ly/plotly-3.4.0.min.js';

    // ─── Theme ───────────────────────────────────────────────────────────────
    // Dark is a selected set of steps, not an inversion: a colour tuned for a
    // white surface sits outside the lightness band a dark surface needs. The
    // backend always sends the light step; this maps it to its dark twin.
    const LAYER_DARK = {
        '#2a78d6': '#3987e5', '#eb6834': '#d95926', '#1baf7a': '#199e70',
        '#eda100': '#c98500', '#e87ba4': '#d55181', '#008300': '#008300',
        '#4a3aa7': '#9085e9', '#e34948': '#e66767', '#7f7f7f': '#9a9a9a',
        '#525252': '#767676'
    };

    const isDark = () => document.documentElement.getAttribute('data-theme') === 'dark';

    /** Layer colour for the active theme. Unknown colours pass through. */
    const paint = hex => (isDark() && LAYER_DARK[hex]) || hex;

    /** Plot chrome that has to track the theme (Plotly can't read CSS vars). */
    function themeTokens() {
        const css = getComputedStyle(document.documentElement);
        const v = name => css.getPropertyValue(name).trim();
        return {
            text: v('--text-main') || (isDark() ? '#f4f4f2' : '#18181b'),
            muted: v('--text-muted') || (isDark() ? '#a1a19a' : '#6b7280'),
            grid: v('--plot-grid') || (isDark() ? '#35352f' : '#e4e4e7'),
            surface: v('--bg-color') || (isDark() ? '#1a1a19' : '#ffffff'),
            markerRing: isDark() ? 'rgba(255,255,255,0.35)' : 'rgba(0,0,0,0.25)'
        };
    }

    // ─── Theme Toggle ────────────────────────────────────────────────────────
    // The initial theme is stamped on <html> by an inline script in index.html,
    // before first paint, so a dark-mode reload doesn't flash white.
    document.getElementById('themeToggle').addEventListener('click', () => {
        const next = isDark() ? 'light' : 'dark';
        if (next === 'dark') document.documentElement.setAttribute('data-theme', 'dark');
        else document.documentElement.removeAttribute('data-theme');
        try { localStorage.setItem('horrendogram-theme', next); } catch (e) { /* private mode */ }

        // Plotly holds resolved colours per trace, so a theme change means a
        // re-render. Carry the viewer's state across it rather than resetting
        // the camera and every filter they had set.
        if (!lastRender) return;
        const state = captureViewState();
        renderVisualization(lastRender, { camera: state.camera });
        restoreViewState(state);
    });

    /** Camera plus whatever the viewer has filtered, so a re-render is invisible. */
    function captureViewState() {
        const gd = document.getElementById('plot');
        let camera = null;
        try { camera = gd && gd._fullLayout && gd._fullLayout.scene
            ? JSON.parse(JSON.stringify(gd._fullLayout.scene.camera)) : null; } catch (e) { /* not yet drawn */ }
        return {
            camera,
            tags: [...selectedTags],
            hidden: [...Object.entries({ ...nodeGroupVisible, ...edgeGroupVisible })
                .filter(([, on]) => !on).map(([group]) => group)]
        };
    }

    /** Replays the captured state as real UI events, so one code path applies it. */
    function restoreViewState(state) {
        state.hidden.forEach(group => {
            const box = document.querySelector(`#legend-filters input[data-legendgroup="${group}"]`);
            if (box && box.checked) {
                box.checked = false;
                box.dispatchEvent(new Event('change'));
            }
        });
        state.tags.forEach(tag => {
            const chip = [...document.querySelectorAll('#tag-chips .tag-chip')]
                .find(c => c.textContent === tag);
            if (chip && !chip.classList.contains('active')) chip.click();
        });
    }

    // ─── Sidebar Page Tabs (Setup / Filters) ─────────────────────────────────
    document.querySelectorAll('.sidebar-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.sidebar-tab').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const page = btn.dataset.page;
            document.querySelectorAll('.sidebar-page').forEach(p => p.classList.remove('active'));
            document.getElementById(`${page}-page`).classList.add('active');
        });
    });

    // ─── Source Toggle ────────────────────────────────────────────────────────
    document.querySelectorAll('.source-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.source-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentSource = btn.dataset.source;
            document.getElementById('csv-inputs').style.display = currentSource === 'csv' ? 'block' : 'none';
            document.getElementById('obsidian-inputs').style.display = currentSource === 'obsidian' ? 'block' : 'none';
        });
    });

    // ─── Generate / Apply Order ───────────────────────────────────────────────
    const processBtn = document.getElementById('processBtn');
    processBtn.addEventListener('click', () => runProcess());

    const applyOrderBtn = document.getElementById('applyOrderBtn');
    applyOrderBtn.addEventListener('click', () => runProcess({ manual_order: currentLayerOrder }));

    async function runProcess(extraConfig) {
        const formData = new FormData();
        let endpoint;

        if (currentSource === 'obsidian') {
            const zipFile = document.getElementById('obsidian-zip').files[0];
            if (!zipFile) { alert('Please select an Obsidian vault ZIP file.'); return; }
            formData.append('file', zipFile);
            // Relative (no leading slash) so the app works both locally at /
            // and when deployed under a subdirectory, e.g. /3dhorrendogram/
            endpoint = 'process-obsidian';
        } else {
            const datasetFile = document.getElementById('dataset').files[0];
            if (!datasetFile) { alert('Please select a dataset file.'); return; }
            formData.append('file', datasetFile);
            const layerFile = document.getElementById('layers').files[0];
            if (layerFile) formData.append('layer_file', layerFile);
            endpoint = 'process';
        }

        const config = {
            actor_legislation_z_offset: document.getElementById('enableOffset').checked,
            actor_z_offset: parseFloat(document.getElementById('offsetValue').value),
            rotation_speed: parseInt(document.getElementById('rotationSpeed').value),
            display_xyz_in_tooltip: document.getElementById('showXYZ').checked,
            ...extraConfig
        };
        formData.append('config', JSON.stringify(config));

        document.getElementById('emptyState').style.display = 'none';
        document.getElementById('loader').style.display = 'flex';
        processBtn.disabled = true;
        applyOrderBtn.disabled = true;

        try {
            const response = await fetch(endpoint, { method: 'POST', body: formData });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Processing failed');
            }
            const data = await response.json();
            renderVisualization(data);
        } catch (err) {
            alert(`Error: ${err.message}`);
            document.getElementById('emptyState').style.display = 'block';
        } finally {
            document.getElementById('loader').style.display = 'none';
            processBtn.disabled = false;
            applyOrderBtn.disabled = false;
        }
    }

    // ─── Visualization Renderer ───────────────────────────────────────────────
    function renderVisualization(data, opts = {}) {
        const { network_data, positions, config } = data;
        lastRender = data;
        const tokens = themeTokens();
        const traces = [];
        traceTagSets = [];
        edgeMeta = [];
        nodeTraceMeta = [];
        const legendMeta = []; // parallel to `traces` — {legendgroup, label, color, category}
        // One visibility group per layer — actors and instruments toggle together.
        const nodeGroupOf = (node, layer) => `nodes_${layer}`;

        // 1. Layer rings (structural — not filtered)
        Object.entries(network_data.layers).forEach(([lname, linfo]) => {
            const theta = Array.from({ length: 61 }, (_, i) => (2 * Math.PI * i) / 60);
            traces.push({
                type: 'scatter3d', mode: 'lines',
                x: theta.map(t => 4 * Math.cos(t)),
                y: theta.map(t => 4 * Math.sin(t)),
                z: new Array(61).fill(linfo.z),
                line: { color: paint(linfo.color), width: 2 },
                name: `Layer: ${lname}`,
                legendgroup: `nodes_${lname}`,
                showlegend: false,
                hoverinfo: 'skip'
            });
            traceTagSets.push(null); // rings are never tag-filtered
            // Pushed first, so this entry supplies the group's label and colour;
            // the layer's node traces below just add their indices to it.
            legendMeta.push({ legendgroup: `nodes_${lname}`, label: lname, color: paint(linfo.color), category: 'Layers' });
        });

        // 2. Intra-layer edges (same layer on both ends) — one trace per edge,
        // sharing a legendgroup per layer, so each can still be individually
        // hidden when either endpoint's node type is filtered out
        const intraEdges = network_data.edges.filter(e => e.source_layer === e.target_layer);
        intraEdges.forEach(e => {
            const sp = positions[e.source], tp = positions[e.target];
            if (!sp || !tp) return;
            const layer = e.source_layer;
            const legendgroup = `intra_${layer}`;
            traces.push({
                type: 'scatter3d', mode: 'lines',
                x: [sp.x, tp.x], y: [sp.y, tp.y], z: [sp.z, tp.z],
                line: { color: paint(network_data.layers[layer].color), width: 2 },
                name: `Intra-layer (${layer})`,
                legendgroup,
                showlegend: false,
                hoverinfo: 'skip'
            });
            traceTagSets.push(e.tags || []);
            legendMeta.push({ legendgroup, label: `Intra-layer (${layer})`, color: paint(network_data.layers[layer].color), category: 'Edges' });
            edgeMeta.push({
                index: traces.length - 1,
                legendgroup,
                sourceGroup: nodeGroupOf(e.source, e.source_layer),
                targetGroup: nodeGroupOf(e.target, e.target_layer),
                sourceTags: (network_data.node_tags && network_data.node_tags[e.source]) || [],
                targetTags: (network_data.node_tags && network_data.node_tags[e.target]) || []
            });
        });

        // 3. Inter-layer edges (one trace per edge for hover text)
        const interEdges = network_data.edges.filter(e => e.source_layer !== e.target_layer);
        const seenInterLegend = new Set();
        interEdges.forEach(e => {
            const sp = positions[e.source], tp = positions[e.target];
            if (!sp || !tp) return;
            const color = interpolateColor(paint(sp.color), paint(tp.color), 0.5);
            const legendKey = [e.source_layer, e.target_layer].sort().join('_');
            let hoverText = `<b>${e.source_orig || e.source} (${e.source_layer}) ↔ ${e.target_orig || e.target} (${e.target_layer})</b>`;
            if (e.tags && e.tags.length) hoverText += `<br>Tags: ${e.tags.join(', ')}`;
            if (e.description) hoverText += `<br>${e.description}`;

            traces.push({
                type: 'scatter3d', mode: 'lines',
                x: [sp.x, tp.x], y: [sp.y, tp.y], z: [sp.z, tp.z],
                line: { color, width: 4 },
                name: `Inter-layer: ${e.source_layer}–${e.target_layer}`,
                legendgroup: `inter_${legendKey}`,
                showlegend: false,
                hoverinfo: 'none',
                hovertext: hoverText,
                hoverlabel: { bgcolor: 'rgba(0,0,0,0)', bordercolor: 'rgba(0,0,0,0)', font: { color: 'rgba(0,0,0,0)' } }
            });
            traceTagSets.push(e.tags || []);
            legendMeta.push({
                legendgroup: `inter_${legendKey}`,
                label: `Inter-layer: ${e.source_layer}–${e.target_layer}`,
                color: seenInterLegend.has(legendKey) ? null : color,
                category: 'Edges'
            });
            edgeMeta.push({
                index: traces.length - 1,
                legendgroup: `inter_${legendKey}`,
                sourceGroup: nodeGroupOf(e.source, e.source_layer),
                targetGroup: nodeGroupOf(e.target, e.target_layer),
                sourceTags: (network_data.node_tags && network_data.node_tags[e.source]) || [],
                targetTags: (network_data.node_tags && network_data.node_tags[e.target]) || []
            });
            seenInterLegend.add(legendKey);
        });

        // 4. Nodes (grouped by layer + type)
        const shapeMap = { actor: 'circle', legislation: 'square', instrument: 'square', unknown: 'diamond' };
        Object.entries(network_data.layers).forEach(([lname, linfo]) => {
            const nodesByType = { actor: [], legislation: [], instrument: [], unknown: [] };
            linfo.nodes.forEach(node => {
                const type = network_data.node_types[node] || 'unknown';
                if (nodesByType[type]) nodesByType[type].push(node);
            });

            Object.entries(nodesByType).forEach(([type, nodes]) => {
                if (!nodes.length) return;
                const traceTags = new Set();
                const tagsPerNode = [];
                const hovers = nodes.map(n => {
                    const name = n.split('__')[0];
                    const tags = network_data.node_tags ? (network_data.node_tags[n] || []) : [];
                    const desc = network_data.node_descriptions ? network_data.node_descriptions[n] : null;
                    tags.forEach(t => traceTags.add(t));
                    tagsPerNode.push(tags);
                    let h = `<b>${name}</b><br>Layer: ${lname}<br>Type: ${type.charAt(0).toUpperCase() + type.slice(1)}`;
                    if (tags.length) h += `<br>Tags: ${tags.join(', ')}`;
                    if (desc) h += `<br>${desc}`;
                    if (config.display_xyz_in_tooltip) {
                        const p = positions[n];
                        h += `<br>x: ${p.x.toFixed(2)}  y: ${p.y.toFixed(2)}  z: ${p.z.toFixed(2)}`;
                    }
                    return h;
                });

                traces.push({
                    type: 'scatter3d', mode: 'markers+text',
                    x: nodes.map(n => positions[n].x),
                    y: nodes.map(n => positions[n].y),
                    z: nodes.map(n => positions[n].z),
                    marker: { size: 8, color: paint(linfo.color), line: { color: tokens.markerRing, width: 1 }, symbol: shapeMap[type] },
                    text: nodes.map(n => n.split('__')[0]),
                    textposition: 'top center',
                    // Labels wear the theme's ink rather than a series colour, so they
                    // stay legible against whatever layer colour sits behind them.
                    textfont: { color: tokens.text, size: 11, family: 'inherit' },
                    name: `${lname} - ${type}`,
                    legendgroup: `nodes_${lname}`,
                    hovertext: hovers,
                    hoverinfo: 'none',
                    hoverlabel: { bgcolor: 'rgba(0,0,0,0)', bordercolor: 'rgba(0,0,0,0)', font: { color: 'rgba(0,0,0,0)' } },
                    showlegend: false
                });
                traceTagSets.push([...traceTags]);
                legendMeta.push({ legendgroup: `nodes_${lname}`, label: lname, color: paint(linfo.color), category: 'Layers' });
                // Per-node tags (not just the trace-wide union) so the tag filter
                // can dim individual nodes. Without this, a whole layer+type group
                // lights up when any single member matches, which made untagged
                // nodes look active and their (correctly dimmed) edges look broken.
                nodeTraceMeta.push({
                    index: traces.length - 1,
                    tagsPerNode,
                    baseColor: paint(linfo.color),
                    names: nodes.map(n => n.split('__')[0])
                });
            });
        });

        const layout = {
            paper_bgcolor: 'rgba(0,0,0,0)',
            plot_bgcolor: 'rgba(0,0,0,0)',
            scene: {
                xaxis: { visible: false },
                yaxis: { visible: false },
                zaxis: {
                    title: { text: 'Governance Layers', font: { color: tokens.muted } },
                    tickvals: Object.values(network_data.layers).map(l => l.z),
                    ticktext: Object.keys(network_data.layers),
                    tickfont: { color: tokens.muted },
                    gridcolor: tokens.grid
                },
                aspectmode: 'manual',
                aspectratio: { x: 1, y: 1, z: 1 },
                // Keep the viewer's camera across a theme switch, which re-renders.
                camera: opts.camera || { eye: { x: 2, y: 2, z: 1 } }
            },
            margin: { l: 0, r: 0, b: 0, t: 30 },
            // The legend now lives in the sidebar's Filters tab (see populateLegendFilters)
            // so the plot canvas stays uncluttered — keep it off at the layout level too,
            // since per-trace showlegend alone wouldn't stop Plotly from reserving space for it.
            showlegend: false,
            font: { color: tokens.text, family: 'inherit' }
        };

        Plotly.newPlot('plot', traces, layout, { responsive: true });

        // Details panel: hover previews, click pins, double-click dismisses.
        // Pinning is what makes links reachable -- while unpinned, moving the
        // pointer toward a link is itself the unhover that would clear it.
        const infoBox = document.getElementById('info-box');
        infoBox.style.display = 'block';
        const plotEl = document.getElementById('plot');

        plotEl.on('plotly_hover', ({ points }) => {
            if (pinned) return;   // a pinned item outranks whatever is under the cursor
            const content = pointDetails(points);
            if (content) infoBox.innerHTML = renderDetails(content);
        });

        plotEl.on('plotly_unhover', () => {
            if (!pinned) showPlaceholder();
        });

        plotEl.on('plotly_click', ({ points }) => {
            const content = pointDetails(points);
            if (!content) return;
            pinned = true;
            infoBox.classList.add('pinned');
            infoBox.innerHTML = renderDetails(content) + PIN_HINT;
        });

        // Tag filter
        populateTagFilter(network_data.all_tags || []);

        // Reset tag state from previous load
        selectedTags.clear();

        // Layer order + legend filters (Filters tab)
        document.getElementById('filters-empty').style.display = 'none';
        document.getElementById('filters-content').style.display = 'block';
        populateLayerOrder(network_data.ordered_layers || Object.keys(network_data.layers), network_data.layers);
        populateLegendFilters(legendMeta);
    }

    // ─── Layer Order (reorder via up/down buttons, or drag-and-drop) ─────────
    // Up/down buttons are the primary, guaranteed-reliable mechanism — native
    // HTML5 drag-and-drop (kept below as a bonus) is inconsistent across
    // browsers (Safari in particular silently drops reorders without a
    // dataTransfer payload), so correctness can't depend on it alone.
    let dragSrcIndex = null;

    function syncLayerOrderFromDom(list) {
        currentLayerOrder = [...list.children].map(el => el.dataset.layer);
    }

    function populateLayerOrder(orderedLayers, layersInfo) {
        currentLayerOrder = [...orderedLayers];
        const list = document.getElementById('layer-order-list');
        list.innerHTML = '';

        orderedLayers.forEach(lname => {
            const li = document.createElement('li');
            li.className = 'layer-order-item';
            li.draggable = true;
            li.dataset.layer = lname;

            const swatch = document.createElement('span');
            swatch.className = 'layer-swatch';
            swatch.style.background = paint((layersInfo[lname] && layersInfo[lname].color) || '') || 'var(--text-muted)';

            const name = document.createElement('span');
            name.className = 'layer-name';
            name.textContent = lname;

            const handle = document.createElement('i');
            handle.className = 'fas fa-grip-lines drag-handle';

            const moveButtons = document.createElement('span');
            moveButtons.className = 'layer-move-buttons';

            const upBtn = document.createElement('button');
            upBtn.type = 'button';
            upBtn.className = 'layer-move-btn';
            upBtn.innerHTML = '<i class="fas fa-chevron-up"></i>';
            upBtn.title = 'Move up';
            upBtn.addEventListener('click', () => {
                const prev = li.previousElementSibling;
                if (prev) {
                    list.insertBefore(li, prev);
                    syncLayerOrderFromDom(list);
                }
            });

            const downBtn = document.createElement('button');
            downBtn.type = 'button';
            downBtn.className = 'layer-move-btn';
            downBtn.innerHTML = '<i class="fas fa-chevron-down"></i>';
            downBtn.title = 'Move down';
            downBtn.addEventListener('click', () => {
                const next = li.nextElementSibling;
                if (next) {
                    list.insertBefore(next, li);
                    syncLayerOrderFromDom(list);
                }
            });

            moveButtons.append(upBtn, downBtn);
            li.append(handle, swatch, name, moveButtons);
            list.appendChild(li);

            li.addEventListener('dragstart', (e) => {
                dragSrcIndex = [...list.children].indexOf(li);
                li.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
                // Safari requires a data payload to be set for the drag to be
                // accepted at all — without this, dragover/drop may never fire.
                e.dataTransfer.setData('text/plain', lname);
            });
            li.addEventListener('dragend', () => {
                li.classList.remove('dragging');
                list.querySelectorAll('.layer-order-item').forEach(el => el.classList.remove('drag-over'));
                syncLayerOrderFromDom(list);
            });
            li.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                li.classList.add('drag-over');
            });
            li.addEventListener('dragleave', () => li.classList.remove('drag-over'));
            li.addEventListener('drop', (e) => {
                e.preventDefault();
                li.classList.remove('drag-over');
                const targetIndex = [...list.children].indexOf(li);
                if (dragSrcIndex === null || targetIndex === dragSrcIndex) return;
                const items = [...list.children];
                const dragged = items[dragSrcIndex];
                if (dragSrcIndex < targetIndex) {
                    li.after(dragged);
                } else {
                    li.before(dragged);
                }
                syncLayerOrderFromDom(list);
            });
        });
    }

    // ─── Legend Filters (replaces the on-canvas Plotly legend) ──────────────
    function populateLegendFilters(legendMeta) {
        const container = document.getElementById('legend-filters');
        container.innerHTML = '';

        // Group by legendgroup, collecting every trace index that shares it
        // (e.g. all inter-layer edges between the same two layers toggle together)
        const groups = new Map();
        const order = [];
        legendMeta.forEach((meta, idx) => {
            if (!groups.has(meta.legendgroup)) {
                groups.set(meta.legendgroup, { ...meta, indices: [] });
                order.push(meta.legendgroup);
            }
            groups.get(meta.legendgroup).indices.push(idx);
        });
        legendGroups = order.map(key => groups.get(key));

        // Reset per-group visibility state — everything starts checked/visible
        nodeGroupVisible = {};
        edgeGroupVisible = {};
        legendGroups.forEach(g => {
            if (g.category === 'Layers') nodeGroupVisible[g.legendgroup] = true;
            if (g.category === 'Edges') edgeGroupVisible[g.legendgroup] = true;
        });

        // Bucket into category sections in a fixed, readable order
        const categories = ['Layers', 'Edges'];
        categories.forEach(category => {
            const entries = legendGroups.filter(g => g.category === category);
            if (!entries.length) return;

            const section = document.createElement('div');
            section.className = 'legend-group';
            const title = document.createElement('div');
            title.className = 'legend-group-title';
            title.textContent = category;
            section.appendChild(title);

            entries.forEach(entry => {
                const row = document.createElement('label');
                row.className = 'legend-row';

                const checkbox = document.createElement('input');
                checkbox.type = 'checkbox';
                checkbox.checked = true;
                checkbox.dataset.legendgroup = entry.legendgroup;

                const swatch = document.createElement('span');
                swatch.className = 'legend-swatch';
                swatch.style.background = entry.color || 'var(--text-muted)';

                const label = document.createElement('span');
                label.textContent = entry.label;

                row.append(checkbox, swatch, label);
                section.appendChild(row);

                checkbox.addEventListener('change', () => {
                    row.classList.toggle('dimmed', !checkbox.checked);
                    if (category === 'Layers') {
                        // A layer row covers its ring and every node in it, and
                        // must also hide any interlinkage that touches the layer —
                        // an edge only shows when BOTH its endpoints are active.
                        nodeGroupVisible[entry.legendgroup] = checkbox.checked;
                        Plotly.restyle('plot', { visible: checkbox.checked }, entry.indices);
                        updateEdgeVisibility();
                    } else if (category === 'Edges') {
                        edgeGroupVisible[entry.legendgroup] = checkbox.checked;
                        updateEdgeVisibility();
                    } else {
                        Plotly.restyle('plot', { visible: checkbox.checked }, entry.indices);
                    }
                });
            });

            container.appendChild(section);
        });

        updateEdgeVisibility();
    }

    // An interlinkage is only shown when its own Edges toggle AND both of the
    // layers it connects are active — hiding a layer should hide every edge
    // dangling from it, not leave it floating with one end invisible.
    function updateEdgeVisibility() {
        if (!edgeMeta.length) return;
        const indices = edgeMeta.map(m => m.index);
        const visible = edgeMeta.map(m =>
            edgeGroupVisible[m.legendgroup] !== false &&
            nodeGroupVisible[m.sourceGroup] !== false &&
            nodeGroupVisible[m.targetGroup] !== false
        );
        Plotly.restyle('plot', { visible }, indices);
    }

    // ─── Tag Filter ───────────────────────────────────────────────────────────
    function populateTagFilter(allTags) {
        const section = document.getElementById('tag-filter-section');
        const container = document.getElementById('tag-chips');
        container.innerHTML = '';
        document.getElementById('clearTagsBtn').style.display = 'none';

        if (!allTags.length) {
            section.style.display = 'none';
            return;
        }

        section.style.display = 'block';
        allTags.forEach(tag => {
            const chip = document.createElement('button');
            chip.className = 'tag-chip';
            chip.textContent = tag;
            chip.addEventListener('click', () => toggleTag(tag, chip));
            container.appendChild(chip);
        });
    }

    function toggleTag(tag, chipEl) {
        if (selectedTags.has(tag)) {
            selectedTags.delete(tag);
            chipEl.classList.remove('active');
        } else {
            selectedTags.add(tag);
            chipEl.classList.add('active');
        }
        const clearBtn = document.getElementById('clearTagsBtn');
        clearBtn.style.display = selectedTags.size > 0 ? 'flex' : 'none';
        applyTagFilter();
    }

    document.getElementById('clearTagsBtn').addEventListener('click', () => {
        selectedTags.clear();
        document.querySelectorAll('.tag-chip.active').forEach(c => c.classList.remove('active'));
        document.getElementById('clearTagsBtn').style.display = 'none';
        applyTagFilter();
    });

    const DIM = 0.07;
    // Dimmed nodes blend toward the current surface, so the effect reads the
    // same in both themes (blending toward navy on a white page would look
    // like a colour change rather than a fade).
    const dimTarget = () => themeTokens().surface;

    function applyTagFilter() {
        if (!traceTagSets.length) return;
        const anySelected = selectedTags.size > 0;
        // A node "matches" the filter if it carries any selected tag (or if no
        // filter is active at all, in which case everyone trivially matches).
        const nodeMatches = tags => !anySelected || (tags || []).some(t => selectedTags.has(t));
        const edgeMetaByIndex = new Map(edgeMeta.map(m => [m.index, m]));
        const nodeTraceIndices = new Set(nodeTraceMeta.map(m => m.index));

        const opacities = traceTagSets.map((tagSet, idx) => {
            // Node traces stay fully opaque — they're dimmed per-node below via
            // marker/text colors, since trace opacity can only dim a whole group.
            if (nodeTraceIndices.has(idx)) return 1.0;
            // Interlinkages depend on their endpoints: an edge only stays
            // highlighted when BOTH connected nodes match the selected tag(s),
            // so an edge is never left bright between two dimmed nodes.
            const edge = edgeMetaByIndex.get(idx);
            if (edge) {
                return (nodeMatches(edge.sourceTags) && nodeMatches(edge.targetTags)) ? 1.0 : DIM;
            }
            if (tagSet === null) return anySelected ? 0.35 : 1.0;   // layer rings
            if (!anySelected) return 1.0;
            if (!tagSet.length) return DIM;                          // no tags — dim
            return tagSet.some(t => selectedTags.has(t)) ? 1.0 : DIM;
        });

        Plotly.restyle('plot', { opacity: opacities });

        // Dim non-matching nodes individually. Trace-level opacity would dim the
        // entire layer+type group, so this works per-point instead — which keeps
        // "which nodes are active" truthful and makes the edge rule above read
        // as correct rather than arbitrary.
        //
        // Dimming blends the layer color toward the page background and blanks the
        // label. Only attributes scatter3d honours per-point are usable: it ignores
        // the alpha channel of per-point rgba() colors and rejects arrays for
        // textfont.color, so a translucent color renders as no change at all.
        //
        // marker.size is deliberately left alone. Passing it as an array makes
        // Plotly recompute sizeref from the data and shrink EVERY marker in the
        // trace, including the matching ones — so matching nodes must keep the
        // scalar size set at trace creation.
        nodeTraceMeta.forEach(m => {
            const colors = [], texts = [];
            m.tagsPerNode.forEach((tags, i) => {
                const on = nodeMatches(tags);
                colors.push(on ? m.baseColor : interpolateColor(m.baseColor, dimTarget(), 0.82));
                texts.push(on ? m.names[i] : '');
            });
            Plotly.restyle('plot', {
                'marker.color': [colors],
                text: [texts]
            }, [m.index]);
        });
    }

    // ─── Export ──────────────────────────────────────────────────────────────
    const exportBtn = document.getElementById('exportBtn');
    exportBtn.addEventListener('click', () => exportInteractiveHtml());

    async function exportInteractiveHtml() {
        if (!lastRender) {
            alert('Generate a visualization before exporting.');
            return;
        }
        const bundlePlotly = document.getElementById('bundlePlotly').checked;
        const originalLabel = exportBtn.innerHTML;
        exportBtn.disabled = true;
        exportBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Building…';

        try {
            // Rebuild from the app's own index.html rather than a duplicated
            // template, so exported markup can never drift from the real thing.
            const [shell, css, js] = await Promise.all([
                fetch('index.html').then(r => r.text()),
                fetch('style.css').then(r => r.text()),
                fetch('script.js').then(r => r.text())
            ]);

            let plotlyTag = `<script src="${PLOTLY_CDN}"><\/script>`;
            if (bundlePlotly) {
                const lib = await fetch(PLOTLY_CDN).then(r => r.text());
                plotlyTag = `<script>${lib}<\/script>`;
            }

            // Escaping '<' keeps a description containing a closing script
            // tag from ending the tag the data is embedded in.
            const payload = JSON.stringify(lastRender).replace(/</g, '\\u003c');

            // Each replacement uses a function, never a replacement string: in
            // a string, "$&" expands to the matched text. Plotly's bundle
            // contains the literal "\\$&" (d3's requote), which would otherwise
            // swallow the <script src=...> tag being replaced -- injecting a
            // stray closing tag and corrupting the library. A function's return
            // value is inserted verbatim.
            //
            // Each is also asserted: a pattern that silently fails to match
            // yields a file missing its stylesheet or its script, which opens
            // as a blank page. Better to fail here with a usable message.
            const substitutions = [
                [/<link rel="stylesheet" href="style\.css[^"]*">/, () => `<style>\n${css}\n</style>`, 'stylesheet link'],
                [/<script src="https:\/\/cdn\.plot\.ly[^"]*"><\/script>/, () => plotlyTag, 'Plotly script tag'],
                [/<script src="script\.js[^"]*"><\/script>/,
                    () => `<script>window.__HORRENDOGRAM_DATA__ = ${payload};<\/script>\n<script>\n${js}\n<\/script>`,
                    'app script tag']
            ];

            let html = shell;
            for (const [pattern, replacer, label] of substitutions) {
                if (!pattern.test(html)) {
                    throw new Error(`could not find the ${label} in index.html — the page may be a cached older version; hard-refresh and retry`);
                }
                html = html.replace(pattern, replacer);
            }

            const stamp = new Date().toISOString().slice(0, 10);
            downloadFile(html, `horrendogram-${stamp}.html`, 'text/html');
        } catch (err) {
            alert(`Export failed: ${err.message}`);
        } finally {
            exportBtn.disabled = false;
            exportBtn.innerHTML = originalLabel;
        }
    }

    function downloadFile(content, filename, type) {
        const url = URL.createObjectURL(new Blob([content], { type }));
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.style.display = 'none';
        document.body.appendChild(a);
        a.click();
        // Tearing this down synchronously can cut the browser off while it is
        // still reading the blob -- saving an empty file, or navigating the tab
        // to a now-dead blob URL (a blank page) when the browser ignores the
        // download attribute. Likeliest with the ~4.8 MB offline bundle.
        setTimeout(() => {
            a.remove();
            URL.revokeObjectURL(url);
        }, 60000);
    }

    // ─── Details Panel: hover preview / click to pin ─────────────────────────
    const PLACEHOLDER = '<b>Network Details</b><br>Hover a node or edge to preview it. Click to keep it open.';
    const PIN_HINT = '<div class="pin-hint">Double-click anywhere to dismiss</div>';

    function showPlaceholder() {
        const box = document.getElementById('info-box');
        box.classList.remove('pinned');
        box.innerHTML = PLACEHOLDER;
    }

    /** Text for the hovered/clicked point, whether the trace stores it per-point or trace-wide. */
    function pointDetails(points) {
        const point = points && points[0];
        if (!point) return '';
        let content = point.hovertext || point.text || '';
        if (!content && point.data) {
            const idx = point.pointNumber || 0;
            const src = point.data.hovertext || point.data.text;
            content = Array.isArray(src) ? src[idx] : (src || '');
        }
        return content;
    }

    // Detach on a double-click anywhere -- except inside the panel itself, where
    // double-click is how you select a word of the description you're reading.
    document.addEventListener('dblclick', event => {
        if (!pinned) return;
        const box = document.getElementById('info-box');
        if (box.contains(event.target)) return;
        pinned = false;
        showPlaceholder();
    });

    // ─── Details Panel Rendering ─────────────────────────────────────────────
    // Hover text arrives as a string mixing markup we built (<b>, <br>) with
    // raw description text from the vault. Only the description can contain
    // links, so conversion happens here rather than at trace-build time --
    // that keeps <a> tags out of Plotly's own hover label entirely.
    // Three link shapes, tried in order. The first two cover malformed markdown
    // the vault actually contains -- an empty link left beside a real one, and
    // a link pasted inside another link -- which would otherwise leak their
    // raw brackets into the panel.
    const LINK_PATTERNS = new RegExp([
        // [outer]([inner](url)) — link pasted inside a link; keep the outer
        // label and the inner URL. The outer ')' is often missing, so it's optional.
        /\[([^\]]*)\]\(\s*\[[^\]]*\]\((https?:\/\/[^\s)]+)\)[^)]*\)?/.source,
        // [label](url) — trailing title text inside the parens is tolerated
        /\[([^\]]*)\]\(\s*(https?:\/\/[^\s)]+)[^)]*\)/.source,
        // bare URL
        /(https?:\/\/[^\s<>()[\]]+)/.source
    ].join('|'), 'g');

    function escapeAttr(value) {
        return value.replace(/&/g, '&amp;').replace(/"/g, '&quot;');
    }

    function escapeText(value) {
        return value.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function renderDetails(html) {
        const text = html
            // Obsidian [[wiki links]] point at vault notes, which have no web
            // target -- show the name as plain text instead of a dead link.
            .replace(/\[\[([^\]]+)\]\]/g, '$1')
            // Empty markdown links are editing residue, not content.
            .replace(/\[\s*\]\(\s*\)/g, '');

        // One pass over every shape: a separate bare-URL pass would match again
        // inside the href of an anchor an earlier pass had just produced.
        // Only http/https match, so a javascript: URL can never become a link.
        return text.replace(LINK_PATTERNS, (match, nestLabel, nestUrl, mdLabel, mdUrl, bareUrl) => {
            let url, label, trailing = '';
            if (nestUrl) {
                url = nestUrl;
                label = nestLabel || nestUrl;
            } else if (mdUrl) {
                url = mdUrl;
                label = mdLabel || mdUrl;
            } else {
                // Don't swallow sentence punctuation into the href.
                url = bareUrl.replace(/[.,;:!?]+$/, '');
                trailing = bareUrl.slice(url.length);
                label = url;
            }
            return `<a href="${escapeAttr(url)}" target="_blank" rel="noopener noreferrer">${escapeText(label)}</a>${trailing}`;
        });
    }

    // ─── Utility ─────────────────────────────────────────────────────────────
    function interpolateColor(c1, c2, t) {
        const h2r = h => [1, 3, 5].map(i => parseInt(h.substr(i, 2), 16) / 255);
        const r2h = r => '#' + r.map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('');
        const rgb1 = h2r(c1), rgb2 = h2r(c2);
        return r2h(rgb1.map((v, i) => (1 - t) * v + t * rgb2[i]));
    }

    // ─── Exported Viewer Bootstrap ───────────────────────────────────────────
    // An exported file carries its data inline: skip the upload flow and render
    // straight away. CSS keyed on body[data-viewer] hides Setup, layer
    // reordering and the export control itself.
    //
    // Must stay last: rendering here runs far earlier in the script's lifetime
    // than a click-triggered render would, so anything it touches has to be
    // initialised already -- a `const` declared below this point would still be
    // in its temporal dead zone.
    if (window.__HORRENDOGRAM_DATA__) {
        document.body.dataset.viewer = '';
        document.querySelectorAll('.sidebar-page').forEach(p => p.classList.remove('active'));
        document.getElementById('filters-page').classList.add('active');
        document.getElementById('emptyState').style.display = 'none';
        renderVisualization(window.__HORRENDOGRAM_DATA__);
    }
});
