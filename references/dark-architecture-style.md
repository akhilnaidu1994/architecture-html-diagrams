# Dark Architecture Diagram Style

Use this reference to create diagrams in the dark technical style: near-black canvas, faint grid, compact labels, thin colored strokes, dashed system boundaries, and clean directional arrows.

## Page Theme

- Body background: `#050816` or `#020617`.
- Diagram shell: translucent slate panel with a thin border, not a heavy card.
- SVG background: dark fill plus a 32-40px grid pattern using low-opacity slate lines.
- Font: JetBrains Mono for all visible text.
- Avoid decorative blobs, large gradients, oversized heroes, and stock imagery.

## Palette

| Meaning | Fill | Stroke/Text |
| --- | --- | --- |
| Frontend, clients, source-of-truth | `rgba(8, 51, 68, 0.42)` | `#22d3ee` |
| Backend, services, workers, runtime | `rgba(6, 78, 59, 0.42)` | `#34d399` |
| Databases, search, AI/ML, retrieval | `rgba(76, 29, 149, 0.40)` | `#a78bfa` |
| Cloud infra, storage, queues, deploy | `rgba(120, 53, 15, 0.34)` | `#fbbf24` |
| Auth, policy, secrets, security | `rgba(136, 19, 55, 0.40)` | `#fb7185` |
| Event streams, async buses | `rgba(251, 146, 60, 0.28)` | `#fb923c` |
| External systems, users, generic | `rgba(30, 41, 59, 0.58)` | `#94a3b8` |

Use white `#f8fafc` for primary node labels, `#94a3b8` for sublabels, and `#475569` for quiet metadata.

## Typography

- Title outside SVG: 22-28px, weight 700.
- Group labels: 10-12px, weight 700, matching the group stroke.
- Node title: 10-13px, weight 700.
- Node details: 8-10px, muted.
- Arrow labels: 8-10px.
- Do not scale font size with viewport width.
- Manually split long SVG labels into multiple `<text>` lines. Keep each line short enough to fit the node.

## Nodes

Use two rectangles for every node that sits over arrows:

```svg
<rect x="X" y="Y" width="W" height="H" rx="8" fill="#0b1120"/>
<rect x="X" y="Y" width="W" height="H" rx="8" fill="rgba(...)" stroke="#..." stroke-width="1.4"/>
```

Recommended sizes:

- Small integration: 80-110px wide, 48-64px high.
- Standard service: 120-180px wide, 64-90px high.
- Major subsystem: 180-240px wide, 90-130px high.
- Group boundary padding: at least 32px on all sides.

## Groups

- Use dashed rounded rectangles for regions, VPCs, clusters, repos, agent zones, data stores, and trust boundaries.
- Group labels should sit inside the top-left corner with 16-20px padding.
- Do not let a group boundary cut through nodes or arrows labels.
- Nested groups are acceptable, but keep dashed patterns distinct enough to read.

## Arrows

- Draw arrows before nodes so nodes mask crossing lines.
- Use `marker-end` arrowheads that match the line color when the flow is semantic.
- Use orthogonal paths for dense diagrams:

```svg
<path d="M 220 260 L 360 260 L 360 310 L 500 310" fill="none" stroke="#64748b" stroke-width="1.6" marker-end="url(#arrow)"/>
```

- Use curved paths only for long cross-system or control-plane relationships.
- Use dashed lines for auth, sync, deployment, control-plane, optional, or future flows.
- Put labels in open space above or beside the path. If the label crosses a grid or line, put it on a small dark pill.

## Legend And Cards

- Put the legend outside the largest group boundary.
- Include only colors and line styles that appear in the diagram.
- Use 3-4 summary cards below the SVG. Cards should explain architecture concerns, not duplicate every node.

## Visual QA

Reject and revise if:

- Any label extends outside a node.
- An arrowhead points into empty space or the wrong target.
- Arrows run through node text.
- Group labels overlap nodes.
- The diagram reads as one color family.
- The diagram requires zooming vertically and horizontally because too many nodes were crammed into the canvas.
