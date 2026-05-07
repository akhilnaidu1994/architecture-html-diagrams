#!/usr/bin/env python3
"""Render lane-based workflow architecture diagrams from a JSON spec.

This renderer is for management-grade swimlane/process diagrams where lane
boundaries, process bands, arrow attachment, and label placement must be
validated instead of hand-tuned in raw SVG.
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


NODE_STYLES = {
    "actor": {"fill": "#061942", "stroke": "#00112f", "text": "#ffffff"},
    "client": {"fill": "#174aa6", "stroke": "#0b2f78", "text": "#ffffff"},
    "service": {"fill": "#04713f", "stroke": "#024f2d", "text": "#ffffff"},
    "external": {"fill": "#5817b8", "stroke": "#3d0b8f", "text": "#ffffff"},
    "decision": {"fill": "#9a5a08", "stroke": "#6f3d03", "text": "#ffffff"},
    "data": {"fill": "#fff7fb", "stroke": "#ff00b8", "text": "#111827"},
    "queue": {"fill": "#1479bd", "stroke": "#0b5287", "text": "#ffffff"},
    "mail": {"fill": "#174aa6", "stroke": "#0b2f78", "text": "#ffffff"},
    "connector": {"fill": "#f43f5e", "stroke": "#be123c", "text": "#ffffff"},
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

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2

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

    def point_inside(self, point: tuple[float, float], padding: float = 0) -> bool:
        x, y = point
        return (
            self.left - padding <= x <= self.right + padding
            and self.top - padding <= y <= self.bottom + padding
        )


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(v) for v in value]
    return [str(value)]


def rect_from(item: dict[str, Any]) -> Rect:
    return Rect(
        id=str(item["id"]),
        x=float(item["x"]),
        y=float(item["y"]),
        w=float(item["w"]),
        h=float(item["h"]),
    )


def anchor(rect: Rect, port: str, offset: list[float] | tuple[float, float] | None = None) -> tuple[float, float]:
    if port == "left":
        point = (rect.left, rect.cy)
    elif port == "right":
        point = (rect.right, rect.cy)
    elif port == "top":
        point = (rect.cx, rect.top)
    elif port == "bottom":
        point = (rect.cx, rect.bottom)
    elif port == "center":
        point = (rect.cx, rect.cy)
    else:
        raise ValueError(f"Unknown port: {port}")
    if offset:
        return point[0] + float(offset[0]), point[1] + float(offset[1])
    return point


def auto_ports(src: Rect, dst: Rect) -> tuple[str, str]:
    dx = dst.cx - src.cx
    dy = dst.cy - src.cy
    if abs(dx) >= abs(dy):
        return ("right", "left") if dx >= 0 else ("left", "right")
    return ("bottom", "top") if dy >= 0 else ("top", "bottom")


def route_points(edge: dict[str, Any], nodes: dict[str, Rect]) -> list[tuple[float, float]]:
    src = nodes[str(edge["from"])]
    dst = nodes[str(edge["to"])]
    from_port, to_port = auto_ports(src, dst)
    from_port = str(edge.get("fromPort", from_port))
    to_port = str(edge.get("toPort", to_port))
    start = anchor(src, from_port, edge.get("fromOffset"))
    end = anchor(dst, to_port, edge.get("toOffset"))
    via = [(float(p[0]), float(p[1])) for p in edge.get("via", [])]
    if via:
        return [start, *via, end]

    x1, y1 = start
    x2, y2 = end
    if abs(x1 - x2) < 0.1 or abs(y1 - y2) < 0.1:
        return [start, end]
    if from_port in {"left", "right"}:
        mid_x = float(edge.get("midX", (x1 + x2) / 2))
        return [start, (mid_x, y1), (mid_x, y2), end]
    mid_y = float(edge.get("midY", (y1 + y2) / 2))
    return [start, (x1, mid_y), (x2, mid_y), end]


def path_d(points: list[tuple[float, float]]) -> str:
    first, *rest = points
    out = [f"M {first[0]:.1f} {first[1]:.1f}"]
    out.extend(f"L {x:.1f} {y:.1f}" for x, y in rest)
    return " ".join(out)


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


def segment_hits_rect(a: tuple[float, float], b: tuple[float, float], rect: Rect, pad: float = 6) -> bool:
    x1, y1 = a
    x2, y2 = b
    left = rect.left - pad
    right = rect.right + pad
    top = rect.top - pad
    bottom = rect.bottom + pad
    if abs(y1 - y2) < 0.1:
        if not top <= y1 <= bottom:
            return False
        return max(min(x1, x2), left) <= min(max(x1, x2), right)
    if abs(x1 - x2) < 0.1:
        if not left <= x1 <= right:
            return False
        return max(min(y1, y2), top) <= min(max(y1, y2), bottom)
    return False


def label_rect(edge: dict[str, Any], points: list[tuple[float, float]]) -> Rect | None:
    label = edge.get("label")
    if not label:
        return None
    text_lines = lines(label)
    x = float(edge.get("labelX", midpoint(points)[0]))
    y = float(edge.get("labelY", midpoint(points)[1] - 8))
    width = max(30, max((len(item) for item in text_lines), default=0) * 7.2 + 16)
    height = len(text_lines) * 16 + 8
    return Rect(str(edge.get("id", "edge-label")), x - width / 2, y - 13, width, height)


def validate(spec: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    canvas = spec.get("canvas", {})
    width = float(canvas.get("width", 1800))
    height = float(canvas.get("height", 2600))
    header_h = float(spec.get("headerHeight", 82))
    node_gap = float(spec.get("validation", {}).get("minNodeGap", 16))
    lane_padding = float(spec.get("validation", {}).get("lanePadding", 8))
    edge_padding = float(spec.get("validation", {}).get("edgePadding", 5))

    lanes = {str(lane["id"]): rect_from({**lane, "y": 0, "h": height}) for lane in spec.get("lanes", [])}
    nodes = {str(node["id"]): rect_from(node) for node in spec.get("nodes", [])}
    if len(lanes) != len(spec.get("lanes", [])):
        errors.append("Duplicate lane IDs found.")
    if len(nodes) != len(spec.get("nodes", [])):
        errors.append("Duplicate node IDs found.")

    for lane_id, lane in lanes.items():
        if lane.left < 0 or lane.right > width:
            errors.append(f"Lane '{lane_id}' is outside the canvas width.")

    for node in spec.get("nodes", []):
        node_id = str(node["id"])
        rect = nodes[node_id]
        if rect.left < 0 or rect.right > width or rect.top < header_h or rect.bottom > height:
            errors.append(f"Node '{node_id}' is outside the usable canvas.")
        lane_id = node.get("lane")
        if lane_id:
            lane = lanes.get(str(lane_id))
            if not lane:
                errors.append(f"Node '{node_id}' references missing lane '{lane_id}'.")
            else:
                lane_body = Rect(lane.id, lane.x, header_h, lane.w, height - header_h)
                if not lane_body.contains(rect, lane_padding):
                    errors.append(f"Node '{node_id}' is not fully inside lane '{lane_id}'.")
        max_label = max((len(item) for item in lines(node.get("label"))), default=0)
        font_size = float(node.get("fontSize", 12))
        if max_label * font_size * 0.58 > rect.w - 18:
            warnings.append(f"Node '{node_id}' label may be too wide for its box.")

    node_items = list(nodes.items())
    for idx, (left_id, left) in enumerate(node_items):
        for right_id, right in node_items[idx + 1 :]:
            if left.overlaps(right, node_gap):
                errors.append(f"Nodes '{left_id}' and '{right_id}' overlap or are closer than {node_gap}px.")

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
        try:
            points = route_points(edge, nodes)
        except ValueError as exc:
            errors.append(f"Edge '{edge_id}' has an invalid port: {exc}")
            continue
        for a, b in zip(points, points[1:]):
            if abs(a[0] - b[0]) >= 0.1 and abs(a[1] - b[1]) >= 0.1:
                errors.append(f"Edge '{edge_id}' contains a diagonal segment. Use orthogonal via points.")
            for node_id, rect in nodes.items():
                if node_id in {src_id, dst_id} or node_id in edge.get("ignoreIntersections", []):
                    continue
                if segment_hits_rect(a, b, rect, edge_padding):
                    errors.append(f"Edge '{edge_id}' route crosses unrelated node '{node_id}'.")
        label = label_rect(edge, points)
        if label:
            for node_id, rect in nodes.items():
                if node_id in edge.get("ignoreLabelIntersections", []):
                    continue
                if label.overlaps(rect, 0):
                    errors.append(f"Edge '{edge_id}' label overlaps node '{node_id}'.")

    return errors, warnings


def render_lanes(spec: dict[str, Any], width: float, height: float) -> str:
    header_h = float(spec.get("headerHeight", 82))
    out: list[str] = []
    for lane in spec.get("lanes", []):
        x = float(lane["x"])
        w = float(lane["w"])
        header_fill = lane.get("headerFill", "#e5e7eb")
        body_fill = lane.get("bodyFill", "#f8fafc")
        out.append(f'<rect x="{x:g}" y="0" width="{w:g}" height="{height:g}" fill="{esc(body_fill)}"/>')
        out.append(f'<rect x="{x:g}" y="0" width="{w:g}" height="{header_h:g}" fill="{esc(header_fill)}"/>')
        out.append(f'<text x="{x + w / 2:g}" y="{header_h / 2 + 8:g}" class="lane-title">{esc(lane.get("label", lane["id"]))}</text>')
        out.append(f'<line x1="{x:g}" y1="0" x2="{x:g}" y2="{height:g}" class="lane-line"/>')
    out.append(f'<line x1="{width:g}" y1="0" x2="{width:g}" y2="{height:g}" class="lane-line"/>')
    out.append(f'<line x1="0" y1="{header_h:g}" x2="{width:g}" y2="{header_h:g}" class="lane-line strong"/>')
    for y in spec.get("rowLines", []):
        out.append(f'<line x1="0" y1="{float(y):g}" x2="{width:g}" y2="{float(y):g}" class="row-line"/>')
    return "\n".join(out)


def render_sections(spec: dict[str, Any]) -> str:
    out: list[str] = []
    for section in spec.get("sections", []):
        x = float(section["x"])
        y = float(section["y"])
        w = float(section["w"])
        h = float(section["h"])
        fill = section.get("fill", "#fef3c7")
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{esc(fill)}" opacity="{section.get("opacity", 0.72)}"/>')
    return "\n".join(out)


def render_section_labels(spec: dict[str, Any]) -> str:
    out: list[str] = []
    for section in spec.get("sections", []):
        if not section.get("label"):
            continue
        box = section.get("labelBox", {})
        x = float(box.get("x", section["x"] + section["w"] - 230))
        y = float(box.get("y", section["y"]))
        w = float(box.get("w", 230))
        h = float(box.get("h", 48))
        fill = box.get("fill", "#ffd91f")
        stroke = box.get("stroke", "#b58900")
        out.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" fill="{esc(fill)}" stroke="{esc(stroke)}" stroke-width="2"/>')
        for idx, text in enumerate(lines(section["label"])):
            out.append(f'<text x="{x + w / 2:g}" y="{y + h / 2 + 6 + idx * 15:g}" class="section-label">{esc(text)}</text>')
    return "\n".join(out)


def text_block(x: float, y: float, text_lines: list[str], klass: str, line_height: float = 15, anchor_text: str = "middle") -> str:
    out = []
    first_y = y - (len(text_lines) - 1) * line_height / 2
    for idx, text in enumerate(text_lines):
        out.append(f'<text x="{x:g}" y="{first_y + idx * line_height:g}" class="{klass}" text-anchor="{anchor_text}">{esc(text)}</text>')
    return "\n".join(out)


def render_node(node: dict[str, Any]) -> str:
    rect = rect_from(node)
    shape = str(node.get("shape", "rect"))
    kind = str(node.get("kind", "service"))
    style = {**NODE_STYLES.get(kind, NODE_STYLES["service"]), **node.get("style", {})}
    label = lines(node.get("label", node["id"]))
    sublabel = lines(node.get("sublabel"))
    rx = float(node.get("rx", 6))
    font_size = float(node.get("fontSize", 12))
    out: list[str] = [f'<g id="node-{esc(rect.id)}">']

    if shape == "decision":
        points = f"{rect.cx:g},{rect.top:g} {rect.right:g},{rect.cy:g} {rect.cx:g},{rect.bottom:g} {rect.left:g},{rect.cy:g}"
        out.append(f'<polygon points="{points}" fill="{esc(style["fill"])}" stroke="{esc(style["stroke"])}" stroke-width="2" filter="url(#shadow)"/>')
        out.append(text_block(rect.cx, rect.cy + 4, label, "node-text", 14))
    elif shape == "database":
        cyl_h = min(64, rect.h - 34)
        cyl_y = rect.y + 8
        out.append(f'<path d="M {rect.x + 10:g} {cyl_y + 14:g} C {rect.x + 10:g} {cyl_y + 4:g}, {rect.right - 10:g} {cyl_y + 4:g}, {rect.right - 10:g} {cyl_y + 14:g} L {rect.right - 10:g} {cyl_y + cyl_h - 12:g} C {rect.right - 10:g} {cyl_y + cyl_h:g}, {rect.x + 10:g} {cyl_y + cyl_h:g}, {rect.x + 10:g} {cyl_y + cyl_h - 12:g} Z" fill="{esc(style["fill"])}" stroke="{esc(style["stroke"])}" stroke-width="2" filter="url(#shadow)"/>')
        out.append(f'<ellipse cx="{rect.cx:g}" cy="{cyl_y + 14:g}" rx="{rect.w / 2 - 10:g}" ry="14" fill="{esc(style["fill"])}" stroke="{esc(style["stroke"])}" stroke-width="2"/>')
        out.append(f'<path d="M {rect.x + 10:g} {cyl_y + cyl_h - 12:g} C {rect.x + 10:g} {cyl_y + cyl_h:g}, {rect.right - 10:g} {cyl_y + cyl_h:g}, {rect.right - 10:g} {cyl_y + cyl_h - 12:g}" fill="none" stroke="{esc(style["stroke"])}" stroke-width="2"/>')
        out.append(text_block(rect.cx, rect.y + cyl_h + 34, label, "data-text", 14))
    elif shape == "queue":
        out.append(f'<rect x="{rect.x:g}" y="{rect.y:g}" width="{rect.w:g}" height="{rect.h:g}" rx="{rx:g}" fill="{esc(style["fill"])}" stroke="{esc(style["stroke"])}" stroke-width="2" filter="url(#shadow)"/>')
        out.append(f'<path d="M {rect.x + rect.w - 28:g} {rect.y + 10:g} L {rect.x + rect.w - 10:g} {rect.y + 18:g} L {rect.x + rect.w - 28:g} {rect.y + 26:g} Z" fill="rgba(255,255,255,.24)"/>')
        out.append(text_block(rect.cx, rect.cy + 5, label, "node-text", 15))
    elif shape == "connector":
        out.append(f'<rect x="{rect.x:g}" y="{rect.y:g}" width="{rect.w:g}" height="{rect.h:g}" rx="{rx:g}" fill="{esc(style["fill"])}" stroke="{esc(style["stroke"])}" stroke-width="2"/>')
        out.append(text_block(rect.cx, rect.cy + 4, label, "node-text small", 12))
    else:
        out.append(f'<rect x="{rect.x:g}" y="{rect.y:g}" width="{rect.w:g}" height="{rect.h:g}" rx="{rx:g}" fill="{esc(style["fill"])}" stroke="{esc(style["stroke"])}" stroke-width="2" filter="url(#shadow)"/>')
        out.append(text_block(rect.cx, rect.cy - (7 if sublabel else 0), label, "node-text", 15))
        if sublabel:
            out.append(text_block(rect.cx, rect.cy + 20, sublabel, "node-subtext", 13))

    if node.get("labelOutside"):
        outside = node["labelOutside"]
        out.append(text_block(float(outside["x"]), float(outside["y"]), lines(outside["text"]), "outside-label", 14))
    out.append("</g>")
    return "\n".join(out).replace('class="node-text"', f'class="node-text" style="font-size:{font_size:g}px; fill:{esc(style["text"])}"')


def render_edge(edge: dict[str, Any], nodes: dict[str, Rect]) -> str:
    points = route_points(edge, nodes)
    stroke = edge.get("stroke", "#111827")
    marker = "arrow-blue" if edge.get("kind") == "data" else "arrow"
    width = float(edge.get("strokeWidth", 2))
    dash = ' stroke-dasharray="7 5"' if edge.get("dashed") else ""
    out = [f'<path d="{path_d(points)}" class="edge" stroke="{esc(stroke)}" stroke-width="{width:g}"{dash} marker-end="url(#{marker})"/>']
    label = lines(edge.get("label"))
    if label:
        lx = float(edge.get("labelX", midpoint(points)[0]))
        ly = float(edge.get("labelY", midpoint(points)[1] - 8))
        bg = label_rect(edge, points)
        if bg:
            out.append(f'<rect x="{bg.x:g}" y="{bg.y:g}" width="{bg.w:g}" height="{bg.h:g}" rx="2" fill="{esc(edge.get("labelFill", "#ffffff"))}" opacity="{edge.get("labelOpacity", 0.82)}"/>')
        out.append(text_block(lx, ly, label, "edge-label", 14))
    return "\n".join(out)


def render_cards(cards: list[dict[str, Any]]) -> str:
    if not cards:
        return ""
    out = ['<section class="cards" aria-label="Workflow summary">']
    for card in cards:
        out.append("<article>")
        out.append(f'<h2>{esc(card.get("title", "Summary"))}</h2>')
        for item in card.get("items", []):
            out.append(f"<p>{esc(item)}</p>")
        out.append("</article>")
    out.append("</section>")
    return "\n".join(out)


def render_html(spec: dict[str, Any]) -> str:
    canvas = spec.get("canvas", {})
    width = float(canvas.get("width", 1800))
    height = float(canvas.get("height", 2600))
    min_width = float(canvas.get("minWidth", min(width, 1300)))
    title = spec.get("title", "Swimlane Workflow")
    subtitle = spec.get("subtitle", "")
    meta = "<br>".join(esc(item) for item in lines(spec.get("meta", ["standalone HTML + inline SVG", "validated swimlane renderer"])))
    nodes = {str(node["id"]): rect_from(node) for node in spec.get("nodes", [])}
    lanes_svg = render_lanes(spec, width, height)
    sections_svg = render_sections(spec)
    section_labels_svg = render_section_labels(spec)
    edges_svg = "\n".join(render_edge(edge, nodes) for edge in spec.get("edges", []))
    nodes_svg = "\n".join(render_node(node) for node in spec.get("nodes", []))
    cards = render_cards(spec.get("cards", []))

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{esc(title)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      min-height: 100vh;
      padding: 28px;
      font-family: Arial, Helvetica, sans-serif;
      color: #0f172a;
      background: linear-gradient(180deg, #eef4fb 0%, #dce6f1 100%);
    }}
    .page {{ max-width: {max(width + 56, 1320):.0f}px; margin: 0 auto; }}
    .header {{ display: flex; justify-content: space-between; gap: 24px; align-items: flex-end; margin-bottom: 18px; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; line-height: 1.15; letter-spacing: 0; }}
    .subtitle {{ margin: 0; color: #334155; font-size: 15px; line-height: 1.45; }}
    .meta {{ color: #475569; font-size: 12px; line-height: 1.45; text-align: right; white-space: nowrap; }}
    .diagram-shell {{
      overflow-x: auto;
      border: 1px solid #8aa0b7;
      border-radius: 8px;
      background: #fff;
      box-shadow: 0 22px 70px rgba(15, 23, 42, .18);
    }}
    svg {{ display: block; width: 100%; min-width: {min_width:.0f}px; height: auto; }}
    .lane-title {{ font-size: 21px; font-weight: 800; text-anchor: middle; fill: #000; }}
    .lane-line {{ stroke: #8797ab; stroke-width: 1.25; }}
    .lane-line.strong {{ stroke: #64748b; stroke-width: 1.4; }}
    .row-line {{ stroke: #c2cedb; stroke-width: 1.1; }}
    .section-label {{ font-size: 16px; font-weight: 800; text-anchor: middle; fill: #000; }}
    .edge {{ fill: none; stroke-linecap: square; stroke-linejoin: miter; }}
    .edge-label {{ font-size: 13px; font-weight: 700; fill: #111827; text-anchor: middle; }}
    .node-text {{ font-weight: 800; text-anchor: middle; dominant-baseline: middle; pointer-events: none; }}
    .node-text.small {{ font-size: 10px; }}
    .node-subtext {{ font-size: 11px; font-weight: 700; fill: rgba(255,255,255,.9); text-anchor: middle; dominant-baseline: middle; }}
    .data-text {{ font-size: 12px; font-weight: 800; fill: #111827; text-anchor: middle; }}
    .outside-label {{ font-size: 12px; font-weight: 700; fill: #111827; text-anchor: middle; }}
    .cards {{ display: grid; grid-template-columns: repeat(4, minmax(220px, 1fr)); gap: 14px; margin-top: 18px; }}
    .cards article {{ background: rgba(255,255,255,.72); border: 1px solid #c7d2de; border-radius: 8px; padding: 14px 16px; min-height: 112px; }}
    .cards h2 {{ margin: 0 0 8px; font-size: 14px; }}
    .cards p {{ margin: 0 0 6px; color: #334155; font-size: 12px; line-height: 1.45; }}
    .footer {{ color: #475569; font-size: 12px; text-align: center; margin: 18px 0 0; }}
    @media (max-width: 760px) {{
      body {{ padding: 18px; }}
      .header {{ align-items: flex-start; flex-direction: column; }}
      .meta {{ text-align: left; white-space: normal; }}
      .cards {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <main class="page">
    <header class="header">
      <div>
        <h1>{esc(title)}</h1>
        <p class="subtitle">{esc(subtitle)}</p>
      </div>
      <div class="meta">{meta}</div>
    </header>
    <section class="diagram-shell" aria-label="Swimlane workflow diagram">
      <svg viewBox="0 0 {width:g} {height:g}" role="img" aria-labelledby="diagram-title diagram-desc">
        <title id="diagram-title">{esc(title)}</title>
        <desc id="diagram-desc">{esc(spec.get("description", subtitle or title))}</desc>
        <defs>
          <marker id="arrow" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="strokeWidth">
            <path d="M 0 1 L 11 6 L 0 11 z" fill="#111827"/>
          </marker>
          <marker id="arrow-blue" markerWidth="12" markerHeight="12" refX="10" refY="6" orient="auto" markerUnits="strokeWidth">
            <path d="M 0 1 L 11 6 L 0 11 z" fill="#2563eb"/>
          </marker>
          <filter id="shadow" x="-20%" y="-30%" width="140%" height="170%">
            <feDropShadow dx="0" dy="5" stdDeviation="5" flood-color="#0f172a" flood-opacity=".22"/>
          </filter>
        </defs>
        <rect width="{width:g}" height="{height:g}" fill="#ffffff"/>
        {lanes_svg}
        {sections_svg}
        {edges_svg}
        {nodes_svg}
        {section_labels_svg}
      </svg>
    </section>
    {cards}
    <p class="footer">{esc(spec.get("footer", "Generated as standalone HTML/SVG"))}</p>
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
