---
name: architecture-html-diagrams
description: Create polished standalone HTML pages with inline SVG architecture and process diagrams. Use when Codex needs to produce system architecture diagrams, cloud architecture diagrams, AWS/GCP/Azure infrastructure maps, microservice diagrams, AI/backend architecture maps, security flow diagrams, network topology diagrams, data-flow diagrams, swimlane workflow diagrams, BPMN-style process maps, case-management flows, actor/system lane diagrams, or complex component relationship diagrams with labeled arrows, grouped boundaries, legends, and management-ready visual quality.
---

# Architecture HTML Diagrams

Create a single self-contained `.html` file containing an SVG architecture or process diagram. Default architecture output should use the dark, grid-backed technical theme. Swimlane/process output may use a reference-matched light lane theme when the user provides a light workflow example. The output should be visually polished enough for docs, proposals, design reviews, screenshots, and management reviews.

## Workflow

1. Parse the user's request into:
   - Components: services, clients, databases, queues, agents, jobs, external APIs, infra.
   - Groups: cloud regions, VPCs, clusters, repos, bounded contexts, teams, trust zones.
   - Lanes when relevant: user/actor, client system, core platform, external system, partner/provider.
   - Flows: request paths, async events, data writes, process decisions, control-plane operations, auth/security paths.
   - Labels: protocols, ports, runtimes, storage details, SLAs, and numbered steps.
2. Choose the generation path:
   - For complex, management-facing, or "pixel perfect" diagrams, create a JSON spec and render it with `scripts/render_architecture_diagram.py --strict`.
   - For swimlane workflow, BPMN-like process maps, case-management flows, or actor/system lane diagrams, create a JSON spec and render it with `scripts/render_swimlane_diagram.py --strict`.
   - For quick drafts or small diagrams, start from `assets/template.html`.
3. Choose a canvas before drawing. Default to `viewBox="0 0 1440 840"` for complex systems and increase width/height rather than compressing nodes.
4. Lay out the diagram in flow order:
   - Left to right for request/data pipelines.
   - Top to bottom for lifecycle, deployment, or batch flows.
   - Multiple horizontal bands for very complex diagrams.
5. Draw SVG in this order: defs, grid/background, group boundaries, arrows/paths, opaque masks under nodes, styled nodes, labels, legend.
6. Verify the result visually. Fix overlaps, clipped text, confusing arrow direction, legends inside groups, or arrows running through labels.

## Resources

- Start from `assets/template.html` for the standalone page structure, dark theme, SVG defs, node examples, arrows, legend, cards, and footer.
- Use `scripts/render_architecture_diagram.py` for complex diagrams where arrows must attach to exact components and geometry must be validated.
- Use `scripts/render_swimlane_diagram.py` for lane-based workflow diagrams where lane containment, row bands, decision nodes, and arrow routes must be validated.
- Read `references/dark-architecture-style.md` when matching the dark technical theme or choosing colors, typography, spacing, and arrow treatments.
- Read `references/complex-diagram-workflow.md` before generating diagrams with more than 12 nodes, nested groups, many arrows, numbered flows, or multiple subsystems.
- Read `references/json-renderer.md` before using the renderer or creating a diagram JSON spec.
- Read `references/swimlane-renderer.md` before using the swimlane renderer or creating a lane-based process spec.

## Required Output

Always create one browser-openable `.html` file:

- Use inline SVG for the diagram.
- Use embedded CSS; the only external dependency allowed is Google Fonts for JetBrains Mono.
- Do not require JavaScript, build tools, Mermaid, Graphviz, external images, or icon CDNs.
- Keep the page responsive with a constrained outer container and horizontal scrolling for wide diagrams.
- Include a concise title, subtitle, main diagram, 3-4 summary cards when useful, and a small footer. Include a legend for architecture maps; swimlane diagrams may rely on lane headers and row labels instead.
- For management-grade output, run the renderer in strict mode and render screenshots in a browser before delivery.

## Diagram Quality Rules

- Prefer fewer, clearer labels over dense paragraphs inside nodes.
- Wrap long node names manually into multiple SVG `<text>` lines.
- Use a minimum 24px gap between adjacent nodes and 40px around group boundaries.
- Peer group boundaries must not overlap. Nested groups must declare parent/child intent in the renderer spec.
- Keep arrows orthogonal or gently curved. Avoid diagonal lines through dense clusters unless they are clearly readable.
- Attach arrows to component IDs through the renderer whenever possible. Do not hand-place arrow endpoints for complex diagrams.
- For swimlanes, keep every node assigned to a lane and route all arrows from source node IDs to target node IDs with explicit ports plus orthogonal `via` points when needed.
- Put arrow labels on small dark label pills or in open lanes, never on top of node borders.
- Use dashed lines only for secondary, auth, control-plane, replication, or planned/future flows.
- For nodes with transparent fills, draw an opaque `fill="#0b1120"` rect beneath the styled rect to hide arrows behind it.
- Put legends outside the largest boundary. Increase the SVG height if needed.
- For very complex architectures, group related nodes into labeled zones and add numbered step badges instead of routing every relationship through the center.

## Semantic Colors

Use the palette from `references/dark-architecture-style.md`:

- Cyan: clients, UI, edge, source-of-truth inputs.
- Emerald: services, workers, runtime, backend.
- Violet: databases, search, AI/ML, retrieval.
- Amber: cloud infrastructure, storage, queues, deployment.
- Rose: auth, security, secrets, policy, risk boundaries.
- Orange: event streams, buses, async processing.
- Slate: external systems, humans, generic components.

## Acceptance Checklist

Before finishing:

- The page opens directly as HTML.
- The dark grid theme is visible and not washed out.
- Every major arrow has a clear direction and label when needed.
- Text stays inside nodes and does not overlap other elements.
- Group boundaries do not cut through nodes.
- Legend and cards match the diagram colors.
- The diagram still works when the browser viewport is narrow because the SVG scrolls horizontally.
