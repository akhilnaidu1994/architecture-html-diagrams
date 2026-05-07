# Complex Diagram Workflow

Use this workflow before generating diagrams with many nodes, nested groups, numbered flows, or cross-subsystem arrows.

## 1. Normalize The Architecture

Create a short internal inventory before drawing:

- Actors and clients.
- Entry points and gateways.
- Core services and workers.
- Data stores, search indexes, queues, streams, and caches.
- External integrations and third-party APIs.
- Security/auth/policy components.
- Deployment, observability, and operations components.
- Main synchronous, asynchronous, control-plane, and data persistence flows.

If the user gives vague input, choose conventional names and technologies only when the diagram needs them to be coherent. Do not invent unnecessary services.

## 2. Choose The Layout

Pick one primary layout:

- Left-to-right: users -> edge -> services -> data -> integrations.
- Top-to-bottom: source -> processing -> storage -> consumption.
- Hub-and-spoke: central bus, gateway, or orchestrator with surrounding systems.
- Multi-band: separate request path, async/event path, data plane, and operations plane.

For very complex systems, use multi-band layout. It is clearer than a single dense cluster.

## 3. Allocate Canvas And Zones

- Start at `1440 x 840` for complex diagrams.
- Use `1600-1900` width for 20+ nodes.
- Increase height for legends, cards, and multiple bands.
- Reserve lanes for long arrows before placing nodes.
- Keep outer margins of at least 48px.

Recommended bands:

- Top: control-plane, deployment, source-of-truth, or management flows.
- Middle: primary request/data path.
- Bottom: storage, analytics, observability, integrations, and supporting systems.

## 4. Route Flows Deliberately

- Place the most important flow on the cleanest horizontal lane.
- Route secondary flows around groups, not through the middle of nodes.
- Use numbered badges for long or crowded flows.
- Combine repeated arrows into a bus or shared path when many services publish/subscribe.
- Do not draw every implied relationship if it damages readability; show the important relationships and summarize the rest in a card.

## 5. Draw In Stable SVG Order

Use this order every time:

1. `<defs>` for grid, markers, filters, and any reusable symbols.
2. Dark background and grid.
3. Group boundaries and group labels.
4. Arrows and arrow labels.
5. Opaque node masks.
6. Styled node rectangles.
7. Node labels and annotations.
8. Legend.

This order prevents arrows from visually cutting through translucent nodes.

## 6. Labeling Rules

- Node title: one clear noun phrase.
- Sublabels: runtime, protocol, storage engine, queue topic, port, or role.
- Arrow labels: protocol, event name, query, write, sync, deploy, auth, or data type.
- Number badges: use when the sequence matters or arrows would otherwise be ambiguous.
- Avoid full sentences inside nodes.

## 7. Final Verification

Before delivering the HTML:

- Open or render the page when possible.
- Check desktop and narrow viewport behavior.
- Confirm every arrow has a target and no arrowhead is hidden under a node.
- Confirm labels remain readable at normal browser zoom.
- Confirm legends and footer do not sit inside any architecture boundary.
- Confirm the output is a single HTML file with embedded CSS and inline SVG.
