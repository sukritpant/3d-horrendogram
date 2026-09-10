document.addEventListener('DOMContentLoaded', () => {
    // ─── State ────────────────────────────────────────────────────────────────
    let traceTagSets = [];   // parallel to Plotly traces: null | string[]
    let selectedTags = new Set();
    let currentSource = 'csv';
    let currentLayerOrder = [];      // live order shown/edited in the Filters tab
    let legendGroups = [];           // [{legendgroup, label, color, indices, category}]
    let edgeMeta = [];               // [{index, legendgroup, sourceGroup, targetGroup}] — one per edge trace
    let nodeTraceMeta = [];          // [{index, tagsPerNode, baseColor}] — one per node trace
    let nodeGroupVisible = {};       // legendgroup ("layer_type") -> boolean, from Node Types checkboxes
    let edgeGroupVisible = {};       // legendgroup ("intra_x" / "inter_x_y") -> boolean, from Edges checkboxes

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
            endpoint = '/process-obsidian';
        } else {
            const datasetFile = document.getElementById('dataset').files[0];
            if (!datasetFile) { alert('Please select a dataset file.'); return; }
            formData.append('file', datasetFile);
            const layerFile = document.getElementById('layers').files[0];
            if (layerFile) formData.append('layer_file', layerFile);
            endpoint = '/process';
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
    function renderVisualization(data) {
        const { network_data, positions, config } = data;
        const traces = [];
        traceTagSets = [];
        edgeMeta = [];
        nodeTraceMeta = [];
        const legendMeta = []; // parallel to `traces` — {legendgroup, label, color, category}
        const nodeGroupOf = (node, layer) => `${layer}_${network_data.node_types[node] || 'unknown'}`;

        // 1. Layer rings (structural — not filtered)
        Object.entries(network_data.layers).forEach(([lname, linfo]) => {
            const theta = Array.from({ length: 61 }, (_, i) => (2 * Math.PI * i) / 60);
            traces.push({
                type: 'scatter3d', mode: 'lines',
                x: theta.map(t => 4 * Math.cos(t)),
                y: theta.map(t => 4 * Math.sin(t)),
                z: new Array(61).fill(linfo.z),
                line: { color: linfo.color, width: 2 },
                name: `Layer: ${lname}`,
                legendgroup: `layer_${lname}`,
                showlegend: false,
                hoverinfo: 'skip'
            });
            traceTagSets.push(null); // rings are never tag-filtered
            legendMeta.push({ legendgroup: `layer_${lname}`, label: `Layer: ${lname}`, color: linfo.color, category: 'Layers' });
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
                line: { color: network_data.layers[layer].color, width: 2 },
                name: `Intra-layer (${layer})`,
                legendgroup,
                showlegend: false,
                hoverinfo: 'skip'
            });
            traceTagSets.push(e.tags || []);
            legendMeta.push({ legendgroup, label: `Intra-layer (${layer})`, color: network_data.layers[layer].color, category: 'Edges' });
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
            const color = interpolateColor(sp.color, tp.color, 0.5);
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
                    marker: { size: 8, color: linfo.color, line: { color: 'white', width: 1 }, symbol: shapeMap[type] },
                    text: nodes.map(n => n.split('__')[0]),
                    textposition: 'top center',
                    // Labels must stay legible regardless of the (often dark) layer color
                    // behind them, so force a bright, high-contrast font instead of the
                    // Plotly default (which reads as dark-on-dark against this theme).
                    textfont: { color: '#f8fafc', size: 11, family: 'Inter, -apple-system, sans-serif' },
                    name: `${lname} - ${type}`,
                    legendgroup: `${lname}_${type}`,
                    hovertext: hovers,
                    hoverinfo: 'none',
                    hoverlabel: { bgcolor: 'rgba(0,0,0,0)', bordercolor: 'rgba(0,0,0,0)', font: { color: 'rgba(0,0,0,0)' } },
                    showlegend: false
                });
                traceTagSets.push([...traceTags]);
                legendMeta.push({ legendgroup: `${lname}_${type}`, label: `${lname} — ${type}`, color: linfo.color, category: 'Node Types' });
                // Per-node tags (not just the trace-wide union) so the tag filter
                // can dim individual nodes. Without this, a whole layer+type group
                // lights up when any single member matches, which made untagged
                // nodes look active and their (correctly dimmed) edges look broken.
                nodeTraceMeta.push({
                    index: traces.length - 1,
                    tagsPerNode,
                    baseColor: linfo.color,
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
                    title: { text: 'Governance Layers', font: { color: '#94a3b8' } },
                    tickvals: Object.values(network_data.layers).map(l => l.z),
                    ticktext: Object.keys(network_data.layers),
                    tickfont: { color: '#94a3b8' },
                    gridcolor: '#334155'
                },
                aspectmode: 'manual',
                aspectratio: { x: 1, y: 1, z: 1 },
                camera: { eye: { x: 2, y: 2, z: 1 } }
            },
            margin: { l: 0, r: 0, b: 0, t: 30 },
            // The legend now lives in the sidebar's Filters tab (see populateLegendFilters)
            // so the plot canvas stays uncluttered — keep it off at the layout level too,
            // since per-trace showlegend alone wouldn't stop Plotly from reserving space for it.
            showlegend: false,
            template: 'plotly_dark'
        };

        Plotly.newPlot('plot', traces, layout, { responsive: true });

        // Info box on hover
        const infoBox = document.getElementById('info-box');
        infoBox.style.display = 'block';
        const plotEl = document.getElementById('plot');
        plotEl.on('plotly_hover', ({ points }) => {
            const point = points[0];
            let content = point.hovertext || point.text || '';
            if (!content && point.data) {
                const idx = point.pointNumber || 0;
                const src = point.data.hovertext || point.data.text;
                content = Array.isArray(src) ? src[idx] : (src || '');
            }
            if (content) infoBox.innerHTML = content;
        });
        plotEl.on('plotly_unhover', () => {
            infoBox.innerHTML = '<b>Network Details</b><br>Hover over a node or edge to explore descriptions.';
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
            swatch.style.background = (layersInfo[lname] && layersInfo[lname].color) || '#94a3b8';

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
            if (g.category === 'Node Types') nodeGroupVisible[g.legendgroup] = true;
            if (g.category === 'Edges') edgeGroupVisible[g.legendgroup] = true;
        });

        // Bucket into category sections in a fixed, readable order
        const categories = ['Layers', 'Node Types', 'Edges'];
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

                const swatch = document.createElement('span');
                swatch.className = 'legend-swatch';
                swatch.style.background = entry.color || '#94a3b8';

                const label = document.createElement('span');
                label.textContent = entry.label;

                row.append(checkbox, swatch, label);
                section.appendChild(row);

                checkbox.addEventListener('change', () => {
                    row.classList.toggle('dimmed', !checkbox.checked);
                    if (category === 'Node Types') {
                        // Toggling a node type must also hide any interlinkage
                        // that touches it — an edge only shows when BOTH its
                        // endpoints' node types are active.
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

    // An interlinkage is only shown when its own Edges toggle AND both of its
    // endpoints' Node Types toggles are active — hiding a node type should
    // hide every edge dangling from it, not leave it floating.
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
    const BG_COLOR = '#0f172a';   // matches --bg-color; dimmed nodes blend toward it

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
                colors.push(on ? m.baseColor : interpolateColor(m.baseColor, BG_COLOR, 0.82));
                texts.push(on ? m.names[i] : '');
            });
            Plotly.restyle('plot', {
                'marker.color': [colors],
                text: [texts]
            }, [m.index]);
        });
    }

    // ─── Utility ─────────────────────────────────────────────────────────────
    function interpolateColor(c1, c2, t) {
        const h2r = h => [1, 3, 5].map(i => parseInt(h.substr(i, 2), 16) / 255);
        const r2h = r => '#' + r.map(v => Math.round(v * 255).toString(16).padStart(2, '0')).join('');
        const rgb1 = h2r(c1), rgb2 = h2r(c2);
        return r2h(rgb1.map((v, i) => (1 - t) * v + t * rgb2[i]));
    }
});
