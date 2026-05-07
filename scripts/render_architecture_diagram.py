#!/usr/bin/env python3
"""Render management-grade dark architecture diagrams from a JSON spec.

The renderer computes edge endpoints from component IDs, routes orthogonal
paths, validates overlap, and outputs a standalone HTML file with inline SVG.
"""

from __future__ import annotations

import argparse
import html
import json
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PALETTE = {
    "frontend": ("rgba(8, 51, 68, 0.42)", "#22d3ee"),
    "service": ("rgba(6, 78, 59, 0.42)", "#34d399"),
    "data": ("rgba(76, 29, 149, 0.40)", "#a78bfa"),
    "infra": ("rgba(120, 53, 15, 0.34)", "#fbbf24"),
    "auth": ("rgba(136, 19, 55, 0.40)", "#fb7185"),
    "event": ("rgba(251, 146, 60, 0.28)", "#fb923c"),
    "external": ("rgba(30, 41, 59, 0.58)", "#94a3b8"),
    "generic": ("rgba(30, 41, 59, 0.50)", "#94a3b8"),
}

GROUP_STROKES = {
    "cloud": "#fbbf24",
    "web": "#22d3ee",
    "cost": "#94a3b8",
    "vpc": "#34d399",
    "subnet": "#38bdf8",
    "data": "#94a3b8",
    "deploy": "#94a3b8",
    "discovery": "#fb923c",
    "generic": "#94a3b8",
}

EDGE_STROKES = {
    "primary": "#7c8aa5",
    "frontend": "#22d3ee",
    "service": "#34d399",
    "data": "#a78bfa",
    "cost": "#fbbf24",
    "deploy": "#fb923c",
    "auth": "#fb7185",
    "control": "#fb7185",
    "generic": "#7c8aa5",
}


@dataclass(frozen=True)
class Rect:
    id: str
    x: float
    y: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.x

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def top(self) -> float:
        return self.y

    @property
    def bottom(self) -> float:
        return self.y + self.h

    def contains(self, other: "Rect", padding: float = 0) -> bool:
        return (
            other.left >= self.left + padding
            and other.right <= self.right - padding
            and other.top >= self.top + padding
            and other.bottom <= self.bottom - padding
        )

    def overlaps(self, other: "Rect", gap: float = 0) -> bool:
        return not (
            self.right + gap <= other.left
            or other.right + gap <= self.left
            or self.bottom + gap <= other.top
            or other.bottom + gap <= self.top
        )

    def point_inside(self, x: float, y: float, padding: float = 0) -> bool:
        return (
            self.left - padding <= x <= self.right + padding
            and self.top - padding <= y <= self.bottom + padding
        )


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def line_items(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def node_rect(node: dict[str, Any]) -> Rect:
    return Rect(
        str(node["id"]),
        float(node["x"]),
        float(node["y"]),
        float(node["w"]),
        float(node["h"]),
    )


def group_rect(group: dict[str, Any]) -> Rect:
    return Rect(
        str(group["id"]),
        float(group["x"]),
        float(group["y"]),
        float(group["w"]),
        float(group["h"]),
    )


def anchor(rect: Rect, port: str) -> tuple[float, float]:
    if port == "left":
        return rect.left, rect.y + rect.h / 2
    if port == "right":
        return rect.right, rect.y + rect.h / 2
    if port == "top":
        return rect.x + rect.w / 2, rect.top
    if port == "bottom":
        return rect.x + rect.w / 2, rect.bottom
    if port == "center":
        return rect.x + rect.w / 2, rect.y + rect.h / 2
    raise ValueError(f"Unknown port: {port}")


def auto_ports(src: Rect, dst: Rect) -> tuple[str, str]:
    sx = src.x + src.w / 2
    sy = src.y + src.h / 2
    dx = dst.x + dst.w / 2
    dy = dst.y + dst.h / 2
    if abs(dx - sx) >= abs(dy - sy):
        return ("right", "left") if dx >= sx else ("left", "right")
    return ("bottom", "top") if dy >= sy else ("top", "bottom")


def route_points(edge: dict[str, Any], src: Rect, dst: Rect) -> list[tuple[float, float]]:
    from_port, to_port = auto_ports(src, dst)
    from_port = edge.get("fromPort", from_port)
    to_port = edge.get("toPort", to_port)
    start = tuple(float(v) for v in edge.get("fromPoint", anchor(src, from_port)))
    end = tuple(float(v) for v in edge.get("toPoint", anchor(dst, to_port)))
    via = [(float(p[0]), float(p[1])) for p in edge.get("via", [])]
    if via:
        return [start, *via, end]

    x1, y1 = start
    x2, y2 = end
    if abs(y1 - y2) < 0.1 or abs(x1 - x2) < 0.1:
        return [start, end]
    if from_port in {"left", "right"}:
        mid_x = float(edge.get("midX", (x1 + x2) / 2))
        return [start, (mid_x, y1), (mid_x, y2), end]
    mid_y = float(edge.get("midY", (y1 + y2) / 2))
    return [start, (x1, mid_y), (x2, mid_y), end]


def path_d(points: list[tuple[float, float]]) -> str:
    first, *rest = points
    parts = [f"M {first[0]:.1f} {first[1]:.1f}"]
    parts.extend(f"L {x:.1f} {y:.1f}" for x, y in rest)
    return " ".join(parts)


def midpoint(points: list[tuple[float, float]]) -> tuple[float, float]:
    segments: list[tuple[float, float, float, float, float]] = []
    total = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        length = math.hypot(x2 - x1, y2 - y1)
        segments.append((x1, y1, x2, y2, length))
        total += length
    target = total / 2
    seen = 0.0
    for x1, y1, x2, y2, length in segments:
        if seen + length >= target:
            ratio = 0 if length == 0 else (target - seen) / length
            return x1 + (x2 - x1) * ratio, y1 + (y2 - y1) * ratio
        seen += length
    return points[-1]


def segment_hits_rect(a: tuple[float, float], b: tuple[float, float], rect: Rect, pad: float = 8) -> bool:
    x1, y1 = a
    x2, y2 = b
    left = rect.left - pad
    right = rect.right + pad
    top = rect.top - pad
    bottom = rect.bottom + pad
    if abs(y1 - y2) < 0.1:
        y = y1
        if not top <= y <= bottom:
            return False
        return max(min(x1, x2), left) <= min(max(x1, x2), right)
    if abs(x1 - x2) < 0.1:
        x = x1
        if not left <= x <= right:
            return False
        return max(min(y1, y2), top) <= min(max(y1, y2), bottom)
    return False


def validate(spec: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    groups = {str(g["id"]): group_rect(g) for g in spec.get("groups", [])}
    nodes = {str(n["id"]): node_rect(n) for n in spec.get("nodes", [])}
    if len(groups) != len(spec.get("groups", [])):
        errors.append("Duplicate group IDs found.")
    if len(nodes) != len(spec.get("nodes", [])):
        errors.append("Duplicate node IDs found.")

    min_gap = float(spec.get("validation", {}).get("minNodeGap", 18))
    group_padding = float(spec.get("validation", {}).get("groupPadding", 22))

    group_defs = {str(g["id"]): g for g in spec.get("groups", [])}
    for node in spec.get("nodes", []):
        node_id = str(node["id"])
        group_id = node.get("group")
        rect = nodes[node_id]
        if group_id and group_id in groups and not groups[str(group_id)].contains(rect, group_padding):
            errors.append(f"Node '{node_id}' is not fully inside group '{group_id}' with {group_padding}px padding.")
        elif group_id and group_id not in groups:
            errors.append(f"Node '{node_id}' references missing group '{group_id}'.")
        max_chars = max((len(s) for s in line_items(node.get("label"))), default=0)
        approx = max_chars * 7.1
        if approx > rect.w - 24:
            warnings.append(f"Node '{node_id}' label may be too wide for its box.")

    node_items = list(nodes.items())
    for i, (a_id, a) in enumerate(node_items):
        for b_id, b in node_items[i + 1 :]:
            if a.overlaps(b, min_gap):
                errors.append(f"Nodes '{a_id}' and '{b_id}' overlap or are closer than {min_gap}px.")

    group_items = list(groups.items())
    for i, (a_id, a) in enumerate(group_items):
        for b_id, b in group_items[i + 1 :]:
            a_parent = group_defs[a_id].get("parent")
            b_parent = group_defs[b_id].get("parent")
            nested = groups[a_id].contains(b) or groups[b_id].contains(a)
            if a_parent == b_parent and not nested and a.overlaps(b, 12):
                errors.append(f"Groups '{a_id}' and '{b_id}' overlap. Separate peer containers.")

    for edge in spec.get("edges", []):
        edge_id = str(edge.get("id", f"{edge.get('from')}->{edge.get('to')}"))
        src_id = str(edge.get("from"))
        dst_id = str(edge.get("to"))
        if src_id not in nodes:
            errors.append(f"Edge '{edge_id}' references missing source node '{src_id}'.")
            continue
        if dst_id not in nodes:
            errors.append(f"Edge '{edge_id}' references missing target node '{dst_id}'.")
            continue
        points = route_points(edge, nodes[src_id], nodes[dst_id])
        for a, b in zip(points, points[1:]):
            for node_id, rect in nodes.items():
                if node_id in {src_id, dst_id}:
                    continue
                if segment_hits_rect(a, b, rect):
                    errors.append(f"Edge '{edge_id}' route crosses unrelated node '{node_id}'.")
        if "badge" in edge:
            bx = float(edge.get("badgeX", midpoint(points)[0]))
            by = float(edge.get("badgeY", midpoint(points)[1]))
            for node_id, rect in nodes.items():
                if rect.point_inside(bx, by, 8):
                    errors.append(f"Edge '{edge_id}' badge overlaps node '{node_id}'.")

    return errors, warnings


def render_group(group: dict[str, Any]) -> str:
    rect = group_rect(group)
    kind = str(group.get("kind", "generic"))
    stroke = group.get("stroke", GROUP_STROKES.get(kind, GROUP_STROKES["generic"]))
    fill = group.get("fill", f"{stroke}08")
    dash = group.get("dash", "8 6")
    label = line_items(group.get("label", group["id"]))
    lines = []
    lines.append(
        f'<rect x="{rect.x:g}" y="{rect.y:g}" width="{rect.w:g}" height="{rect.h:g}" rx="{group.get("rx", 12)}" '
        f'fill="{esc(fill)}" stroke="{esc(stroke)}" stroke-width="{group.get("strokeWidth", 1.15)}" stroke-dasharray="{esc(dash)}"/>'
    )
    for idx, text in enumerate(label):
        lines.append(
            f'<text x="{rect.x + 20:g}" y="{rect.y + 28 + idx * 16:g}" fill="{esc(stroke)}" class="group-label">{esc(text)}</text>'
        )
    return "\n".join(lines)


def render_node(node: dict[str, Any]) -> str:
    rect = node_rect(node)
    kind = str(node.get("kind", "generic"))
    fill, stroke = PALETTE.get(kind, PALETTE["generic"])
    fill = node.get("fill", fill)
    stroke = node.get("stroke", stroke)
    label = line_items(node.get("label", node["id"]))
    sublabel = line_items(node.get("sublabel"))
    glow = ' filter="url(#glow)"' if node.get("glow") else ""
    lines = [
        f'<rect x="{rect.x:g}" y="{rect.y:g}" width="{rect.w:g}" height="{rect.h:g}" rx="{node.get("rx", 8)}" fill="#0b1120"/>',
        f'<rect x="{rect.x:g}" y="{rect.y:g}" width="{rect.w:g}" height="{rect.h:g}" rx="{node.get("rx", 8)}" fill="{esc(fill)}" stroke="{esc(stroke)}" stroke-width="{node.get("strokeWidth", 1.5)}"{glow}/>',
    ]
    title_start = rect.y + 26
    for idx, text in enumerate(label):
        lines.append(f'<text x="{rect.x + rect.w / 2:g}" y="{title_start + idx * 16:g}" class="label">{esc(text)}</text>')
    sub_start = title_start + len(label) * 16 + 6
    for idx, text in enumerate(sublabel):
        klass = "sub" if idx == 0 else "tiny"
        lines.append(f'<text x="{rect.x + rect.w / 2:g}" y="{sub_start + idx * 14:g}" class="{klass}">{esc(text)}</text>')
    return "\n".join(lines)


def render_edge(edge: dict[str, Any], nodes: dict[str, Rect]) -> str:
    points = route_points(edge, nodes[str(edge["from"])], nodes[str(edge["to"])])
    kind = str(edge.get("kind", "generic"))
    stroke = edge.get("stroke", EDGE_STROKES.get(kind, EDGE_STROKES["generic"]))
    marker = edge.get("marker", f"arrow-{kind}" if kind in {"frontend", "service", "data", "cost", "deploy", "auth", "control"} else "arrow")
    if marker == "arrow-control":
        marker = "arrow-auth"
    dash = ' stroke-dasharray="6 5"' if edge.get("dashed") or kind in {"auth", "control"} else ""
    lines = [
        f'<path d="{path_d(points)}" fill="none" stroke="{esc(stroke)}" stroke-width="{edge.get("strokeWidth", 1.75)}"{dash} marker-end="url(#{esc(marker)})"/>'
    ]
    if edge.get("label"):
        lx = float(edge.get("labelX", midpoint(points)[0]))
        ly = float(edge.get("labelY", midpoint(points)[1] - 8))
        lines.append(f'<text x="{lx:g}" y="{ly:g}" fill="{esc(stroke)}" font-size="8" text-anchor="middle">{esc(edge["label"])}</text>')
    if edge.get("badge"):
        bx = float(edge.get("badgeX", midpoint(points)[0]))
        by = float(edge.get("badgeY", midpoint(points)[1]))
        bw = max(32, len(str(edge["badge"])) * 10 + 16)
        lines.append(f'<rect x="{bx - bw / 2:g}" y="{by - 14:g}" width="{bw:g}" height="28" rx="6" class="badge-bg"/>')
        lines.append(f'<text x="{bx:g}" y="{by:g}" class="badge-text">{esc(edge["badge"])}</text>')
    return "\n".join(lines)


def render_legend(spec: dict[str, Any], canvas_h: float) -> str:
    legend = spec.get("legend", {})
    x = float(legend.get("x", 80))
    y = float(legend.get("y", canvas_h - 72))
    items = legend.get("items", [])
    lines = [f'<g transform="translate({x:g} {y:g})">', '<text x="0" y="0" fill="#f8fafc" font-size="11" font-weight="700">Legend</text>']
    cx = 0
    for item in items:
        kind = item.get("kind", "generic")
        fill, stroke = PALETTE.get(kind, PALETTE["generic"])
        text = item.get("label", kind)
        if item.get("line"):
            stroke = EDGE_STROKES.get(item.get("line"), EDGE_STROKES["generic"])
            dash = ' stroke-dasharray="5 4"' if item.get("dashed") else ""
            lines.append(f'<line x1="{cx:g}" y1="24" x2="{cx + 28:g}" y2="24" stroke="{stroke}"{dash} marker-end="url(#arrow)"/>')
            lines.append(f'<text x="{cx + 38:g}" y="28" fill="#94a3b8" font-size="9">{esc(text)}</text>')
            cx += 170
        else:
            lines.append(f'<rect x="{cx:g}" y="18" width="16" height="10" rx="2" fill="{esc(fill)}" stroke="{esc(stroke)}"/>')
            lines.append(f'<text x="{cx + 24:g}" y="27" fill="#94a3b8" font-size="9">{esc(text)}</text>')
            cx += max(170, len(str(text)) * 7 + 54)
    lines.append("</g>")
    return "\n".join(lines)


def render_cards(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return ""
    out = ['<section class="cards" aria-label="Architecture summary">']
    for card in cards:
        kind = card.get("kind", "generic")
        stroke = PALETTE.get(kind, PALETTE["generic"])[1]
        out.append('<article class="card">')
        out.append(f'<div class="card-title"><span class="card-dot" style="background: {stroke}"></span>{esc(card.get("title", "Summary"))}</div>')
        out.append("<ul>")
        for item in card.get("items", []):
            out.append(f"<li>{esc(item)}</li>")
        out.append("</ul></article>")
    out.append("</section>")
    return "\n".join(out)


def render_html(spec: dict[str, Any]) -> str:
    canvas = spec.get("canvas", {})
    width = float(canvas.get("width", 1600))
    height = float(canvas.get("height", 900))
    min_width = float(canvas.get("minWidth", min(width, 1300)))
    title = spec.get("title", "Architecture Diagram")
    subtitle = spec.get("subtitle", "")
    meta = line_items(spec.get("meta", ["standalone html + inline svg"]))
    nodes = {str(n["id"]): node_rect(n) for n in spec.get("nodes", [])}

    group_svg = "\n".join(render_group(g) for g in spec.get("groups", []))
    edge_svg = "\n".join(render_edge(e, nodes) for e in spec.get("edges", []))
    node_svg = "\n".join(render_node(n) for n in spec.get("nodes", []))
    legend_svg = render_legend(spec, height)
    cards = render_cards(spec.get("cards", []))
    meta_html = "<br>".join(esc(m) for m in meta)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{ --bg:#050816; --text:#f8fafc; --muted:#94a3b8; --faint:#475569; }}
    * {{ box-sizing:border-box; margin:0; padding:0; }}
    body {{
      min-height:100vh; padding:28px; color:var(--text); font-family:"JetBrains Mono",monospace;
      background: radial-gradient(circle at 14% 18%, rgba(34,211,238,.08), transparent 28%),
                  radial-gradient(circle at 86% 18%, rgba(251,191,36,.07), transparent 26%), var(--bg);
    }}
    .page {{ max-width:{max(width * 0.94, 1280):.0f}px; margin:0 auto; }}
    .header {{ display:flex; align-items:flex-end; justify-content:space-between; gap:24px; margin-bottom:18px; }}
    .title-row {{ display:flex; align-items:center; gap:12px; margin-bottom:8px; }}
    .status-dot {{ width:10px; height:10px; border-radius:999px; background:#fbbf24; box-shadow:0 0 22px rgba(251,191,36,.9); }}
    h1 {{ font-size:25px; line-height:1.2; font-weight:700; letter-spacing:0; }}
    .subtitle {{ margin-left:22px; color:var(--muted); font-size:13px; line-height:1.5; }}
    .meta {{ color:var(--faint); font-size:11px; text-align:right; white-space:nowrap; line-height:1.55; }}
    .diagram-shell {{ overflow-x:auto; border:1px solid rgba(148,163,184,.18); border-radius:12px; background:rgba(2,6,23,.74); box-shadow:0 24px 80px rgba(0,0,0,.35); }}
    svg {{ display:block; width:100%; min-width:{min_width:.0f}px; height:auto; }}
    .label {{ font-family:"JetBrains Mono",monospace; fill:#f8fafc; font-weight:700; font-size:11px; text-anchor:middle; }}
    .sub {{ font-family:"JetBrains Mono",monospace; fill:#94a3b8; font-size:8px; text-anchor:middle; }}
    .tiny {{ font-family:"JetBrains Mono",monospace; fill:#94a3b8; font-size:7px; text-anchor:middle; }}
    .group-label {{ font-family:"JetBrains Mono",monospace; font-size:11px; font-weight:700; }}
    .badge-bg {{ fill:#0284c7; stroke:#38bdf8; stroke-width:1; }}
    .badge-text {{ font-family:"JetBrains Mono",monospace; fill:white; font-size:10px; font-weight:700; text-anchor:middle; dominant-baseline:middle; }}
    .cards {{ display:grid; grid-template-columns:repeat(4,minmax(230px,1fr)); gap:14px; margin-top:18px; }}
    .card {{ border:1px solid rgba(148,163,184,.16); border-radius:8px; background:rgba(15,23,42,.62); padding:16px; min-height:126px; }}
    .card-title {{ display:flex; align-items:center; gap:8px; margin-bottom:10px; font-size:13px; font-weight:700; }}
    .card-dot {{ width:8px; height:8px; border-radius:999px; }}
    .card ul {{ list-style:none; color:var(--muted); font-size:11px; line-height:1.65; }}
    .footer {{ margin-top:18px; color:var(--faint); font-size:11px; text-align:center; }}
    @media (max-width:760px) {{ body {{ padding:18px; }} .header {{ align-items:flex-start; flex-direction:column; }} .meta {{ text-align:left; white-space:normal; }} .cards {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <main class="page">
    <header class="header">
      <div>
        <div class="title-row"><span class="status-dot"></span><h1>{esc(title)}</h1></div>
        <p class="subtitle">{esc(subtitle)}</p>
      </div>
      <div class="meta">{meta_html}</div>
    </header>
    <section class="diagram-shell" aria-label="Architecture diagram">
      <svg viewBox="0 0 {width:g} {height:g}" role="img" aria-labelledby="diagram-title diagram-desc">
        <title id="diagram-title">{esc(title)}</title>
        <desc id="diagram-desc">{esc(spec.get("description", title))}</desc>
        <defs>
          <pattern id="grid" width="34" height="34" patternUnits="userSpaceOnUse"><path d="M 34 0 L 0 0 0 34" fill="none" stroke="rgba(38,53,88,.42)" stroke-width=".8"/></pattern>
          <marker id="arrow" markerWidth="10" markerHeight="10" refX="8.4" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 1 L 9 5 L 0 9 z" fill="#7c8aa5"/></marker>
          <marker id="arrow-frontend" markerWidth="10" markerHeight="10" refX="8.4" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 1 L 9 5 L 0 9 z" fill="#22d3ee"/></marker>
          <marker id="arrow-service" markerWidth="10" markerHeight="10" refX="8.4" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 1 L 9 5 L 0 9 z" fill="#34d399"/></marker>
          <marker id="arrow-data" markerWidth="10" markerHeight="10" refX="8.4" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 1 L 9 5 L 0 9 z" fill="#a78bfa"/></marker>
          <marker id="arrow-cost" markerWidth="10" markerHeight="10" refX="8.4" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 1 L 9 5 L 0 9 z" fill="#fbbf24"/></marker>
          <marker id="arrow-deploy" markerWidth="10" markerHeight="10" refX="8.4" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 1 L 9 5 L 0 9 z" fill="#fb923c"/></marker>
          <marker id="arrow-auth" markerWidth="10" markerHeight="10" refX="8.4" refY="5" orient="auto" markerUnits="strokeWidth"><path d="M 0 1 L 9 5 L 0 9 z" fill="#fb7185"/></marker>
          <filter id="glow" x="-25%" y="-25%" width="150%" height="150%"><feGaussianBlur stdDeviation="2.4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
        </defs>
        <rect width="{width:g}" height="{height:g}" fill="#050816"/>
        <rect width="{width:g}" height="{height:g}" fill="url(#grid)" opacity=".92"/>
        <rect x="24" y="24" width="{width - 48:g}" height="{height - 48:g}" rx="18" fill="rgba(15,23,42,.34)" stroke="rgba(148,163,184,.13)"/>
        {group_svg}
        {edge_svg}
        {node_svg}
        {legend_svg}
      </svg>
    </section>
    {cards}
    <p class="footer">{esc(spec.get("footer", "Generated architecture diagram"))}</p>
  </main>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("spec", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--strict", action="store_true", help="Fail on warnings as well as errors.")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text())
    errors, warnings = validate(spec)
    for warning in warnings:
        print(f"[WARN] {warning}", file=sys.stderr)
    for error in errors:
        print(f"[ERROR] {error}", file=sys.stderr)
    if errors or (args.strict and warnings):
        return 1

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(render_html(spec))
    print(f"Wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
