# JSON Renderer

Use `scripts/render_architecture_diagram.py` for complex or management-grade diagrams. It renders a standalone dark HTML/SVG page from a JSON spec and validates geometry before writing the output.

## Command

```bash
python3 architecture-html-diagrams/scripts/render_architecture_diagram.py spec.json --out diagram.html --strict
```

Use `--strict` for final output. Strict mode fails on overlap, invalid references, edge routes through unrelated nodes, badge/node collisions, and labels likely too wide for their boxes.

## Required Spec Sections

- `canvas`: `width`, `height`, and `minWidth`.
- `groups`: dashed container boxes with `id`, `label`, `x`, `y`, `w`, `h`, `kind`, and optional `parent`.
- `nodes`: components with `id`, `label`, `sublabel`, `x`, `y`, `w`, `h`, `kind`, and optional `group`.
- `edges`: relationships with `from`, `to`, optional `badge`, `kind`, `fromPort`, `toPort`, and `via`.
- `legend`, `cards`, and `footer` for management-ready context.

## Routing Rules

- Reference nodes by ID, never by hard-coded endpoint coordinates.
- Use `fromPort` and `toPort` (`left`, `right`, `top`, `bottom`) for exact arrow attachment.
- Use `fromPoint` or `toPoint` for wide bus/bar components that need multiple distinct connection points instead of one center anchor.
- Use `via` points to route around groups or reserve lanes:

```json
{
  "from": "api-gateway",
  "to": "lambda-search",
  "fromPort": "right",
  "toPort": "left",
  "via": [[900, 430], [900, 610]],
  "badge": "17",
  "badgeX": 870,
  "badgeY": 430
}
```

The renderer still computes the first and last points from the source and target node boxes.

## Pixel-Perfect Checklist

- Peer groups must not overlap.
- Nodes must be fully inside their assigned groups.
- Nodes must not overlap or sit closer than the configured gap.
- Arrow routes must not pass through unrelated nodes.
- Badges must sit in open lanes, not over nodes.
- Long labels must be manually split into multiple lines or the node width must be increased.
