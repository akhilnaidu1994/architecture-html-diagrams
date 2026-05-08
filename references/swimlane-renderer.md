# Swimlane Renderer

Use `scripts/render_swimlane_diagram.py` when the requested output is a lane-based workflow, BPMN-like process map, case-management flow, actor/system interaction diagram, or process architecture diagram.

## Command

```bash
python3 architecture-html-diagrams/scripts/render_swimlane_diagram.py spec.json --out diagram.html --strict
```

Strict mode fails on invalid node references, nodes outside lanes, node overlaps, diagonal edges, edge routes through unrelated nodes, edge labels overlapping nodes, labels likely too wide for their boxes, labels placed on top of their own arrow path, tiny arrow stubs, excessive bends, and declared primary-flow alignment failures.

## Required Spec Sections

- `theme`: use `"dark"` by default to match the dark-grid architecture style; use `"light"` only when the user explicitly asks to match a light swimlane reference.
- `canvas`: `width`, `height`, and `minWidth`.
- `headerHeight`: lane header height in pixels.
- `lanes`: lane columns with `id`, `label`, `x`, `w`, `headerFill`, and `bodyFill`.
- `rowLines`: horizontal separators between major process bands.
- `sections`: colored row/region bands with optional yellow `labelBox`.
- `nodes`: workflow steps with `id`, `lane`, `shape`, `kind`, `label`, `x`, `y`, `w`, and `h`.
- `edges`: relationships with `from`, `to`, optional `fromPort`, `toPort`, `via`, and `label`.
- `alignmentGroups`: optional but recommended for primary top-to-bottom or left-to-right chains. Declare node IDs that must share the same center `x` or `y`.

## Node Shapes

- `rect`: actors, systems, services, and external applications.
- `decision`: diamond decision nodes.
- `database`: cylinder with label below it.
- `queue`: broker/server/event component.
- `connector`: small connector badge.

## Routing Rules

- Always reference source and target components by node ID.
- Use ports (`left`, `right`, `top`, `bottom`) to control exact arrow attachment.
- Align primary sequences on the same centerline before drawing arrows. For example, stack rules-engine decisions on the same center `x`; place left-to-right handoffs on the same center `y`.
- Mark primary edges with `preferStraight: "vertical"` or `preferStraight: "horizontal"` so strict validation rejects avoidable 90-degree bends.
- Use orthogonal `via` points to reserve open lanes and avoid crossing nodes.
- Do not use tiny jogs such as 10px horizontal/vertical corrections before an arrowhead. Move the boxes instead. Default strict validation requires 28px of terminal runway and 18px for every segment.
- Keep labels in open space. Set `labelX` and `labelY` when the midpoint would collide with a node or another label.
- Prefer `labelSegment`, `labelSide`, and `labelOffset` over raw `labelX`/`labelY`. Put labels above/below horizontal segments and left/right of vertical segments; strict mode rejects labels that sit on top of their own arrow.
- Route long cross-lane arrows through empty horizontal bands instead of through dense decision clusters.
- For Yes/No branches, put branch labels beside the first clear segment after the decision, not inside the diamond.

## Visual Rules

- Default swimlane output should still use the skill's dark technical canvas: near-black SVG background, faint grid, translucent lane bodies, thin neon strokes, and compact monospace labels.
- Lane headers should be strong and readable; body fills should stay low-contrast.
- Decision diamonds should be large enough for two-line labels.
- Databases need extra height because the cylinder and its label are validated together.
- Section labels should sit on top of the relevant row, not over arrows.
- Prefer increasing canvas height over compressing stacked decisions.
