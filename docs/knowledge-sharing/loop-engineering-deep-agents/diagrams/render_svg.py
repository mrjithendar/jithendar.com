#!/usr/bin/env python3
"""Fallback renderer: draws the .drawio files in this folder as SVG without the draw.io application.

    python3 docs/knowledge-sharing/loop-engineering-deep-agents/diagrams/render_svg.py
    # then, for the 2x PNGs:  rsvg-convert -z 2 <name>.svg -o <name>.png

export.sh (the draw.io CLI) is the real export and gives the same picture with draw.io's own text layout. This script
exists for machines without draw.io. It reads only what build_diagrams.py writes: rounded boxes, dashed zones, text,
legend swatches, and orthogonal or straight edges with fixed exit and entry points. Standard library only.
"""
import re
import xml.etree.ElementTree as ET
from html import escape, unescape
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "loop-engineering-deep-agents"
FONT = "Helvetica, Arial, sans-serif"


def parse_style(style):
    return dict(part.split("=", 1) if "=" in part else (part, "1") for part in style.split(";") if part)


def lines_of(value):
    """[(text, bold, px, colour)] for a cell's HTML label."""
    out = []
    for chunk in re.split(r"<br\s*/?>", value):
        bold = "<b" in chunk
        size = re.search(r"font-size:(\d+)px", chunk)
        colour = re.search(r"[^-]color:(#[0-9a-f]{6})", chunk)
        text = unescape(re.sub(r"<[^>]+>", "", chunk))
        out.append((text, bold, int(size.group(1)) if size else None, colour.group(1) if colour else None))
    return out


def wrap(text, px, bold, width):
    words, rows, row = text.split(), [], ""
    for word in words:
        trial = f"{row} {word}".strip()
        if len(trial) * px * (0.6 if bold else 0.54) > width and row:
            rows.append(row)
            row = word
        else:
            row = trial
    return rows + [row] if row else rows


def tspan(x, y, text, px, colour, bold=False, anchor="start"):
    weight = ' font-weight="bold"' if bold else ""
    return (f'<text x="{x:g}" y="{y:g}" font-family="{FONT}" font-size="{px}" fill="{colour}"{weight} '
            f'text-anchor="{anchor}">{escape(text)}</text>')


def side_point(geo, fx, fy):
    x, y, w, h = geo
    return (x + w * fx, y + h * fy)


def route(start, end, s, via):
    """Orthogonal path between two fixed points: explicit via points, a straight line, or one elbow in the middle."""
    if via:
        return [start, *via, end]
    if abs(start[0] - end[0]) < 0.5 or abs(start[1] - end[1]) < 0.5:
        return [start, end]
    if float(s.get("exitX", 0.5)) in (0.0, 1.0):
        mid = (start[0] + end[0]) / 2
        return [start, (mid, start[1]), (mid, end[1]), end]
    mid = (start[1] + end[1]) / 2
    return [start, (start[0], mid), (end[0], mid), end]


def midpoint(points):
    lengths = [abs(b[0] - a[0]) + abs(b[1] - a[1]) for a, b in zip(points, points[1:])]
    half = sum(lengths) / 2
    for (a, b), length in zip(zip(points, points[1:]), lengths):
        if half <= length and length:
            f = half / length
            return (a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f)
        half -= length
    return points[-1]


def render(path):
    model = ET.parse(path).getroot().find("diagram/mxGraphModel")
    width, height = int(model.get("pageWidth")), int(model.get("pageHeight"))
    cells = [c for c in model.find("root") if c.get("style") is not None]
    geos = {}
    for c in cells:
        g = c.find("mxGeometry")
        if c.get("vertex"):
            geos[c.get("id")] = tuple(float(g.get(k)) for k in ("x", "y", "width", "height"))
    svg, markers = [], {}
    for c in cells:
        s, value, g = parse_style(c.get("style")), c.get("value") or "", c.find("mxGeometry")
        if c.get("vertex"):
            x, y, w, h = geos[c.get("id")]
            fill, stroke = s.get("fillColor", "none"), s.get("strokeColor", "none")
            dash = f' stroke-dasharray="{s["dashPattern"]}"' if s.get("dashed") == "1" else ""
            sw = s.get("strokeWidth", "1")
            if c.get("id") == "page":
                svg.append(f'<rect width="{width}" height="{height}" fill="#ffffff"/>')
            elif "text" in s:
                rows = []
                for text, bold, px, colour in lines_of(value):
                    px = px or int(s.get("fontSize", 12))
                    rows += [(r, bold, px) for r in wrap(text, px, bold, w + 4)]
                ty = y
                for text, bold, px in rows:
                    ty += px * 1.2
                    svg.append(tspan(x, ty - px * 0.2, text, px, s.get("fontColor", "#334155"), bold))
            elif s.get("shape") == "line":
                svg.append(f'<line x1="{x:g}" y1="{y + h / 2:g}" x2="{x + w:g}" y2="{y + h / 2:g}" stroke="{stroke}" '
                           f'stroke-width="{sw}"{dash}/>')
            else:
                zone = s.get("arcSize") == "3"
                radius = {"3": 6, "20": 3}.get(s.get("arcSize"), 8) if s.get("rounded") == "1" else 0
                svg.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius}" fill="{fill}" '
                           f'stroke="{stroke}" stroke-width="{sw}"{dash}/>')
                if zone and value:
                    right = s.get("align") == "right"
                    svg.append(tspan(x + w - 12 if right else x + 12, y + 19, unescape(value), 12,
                                     s.get("fontColor", "#475569"), True, "end" if right else "start"))
                elif value:
                    rows = lines_of(value)
                    ty = y + h / 2 - 8 * len(rows) + 12
                    for text, bold, px, colour in rows:
                        svg.append(tspan(x + w / 2, ty, text, px or 12, colour or s.get("fontColor", "#0f172a"), bold, "middle"))
                        ty += 16
        else:
            points = [(float(p.get("x")), float(p.get("y"))) for p in g.findall("mxPoint") if p.get("as") in ("sourcePoint", "targetPoint")]
            if not points:
                start = side_point(geos[c.get("source")], float(s.get("exitX", 0.5)), float(s.get("exitY", 0.5)))
                end = side_point(geos[c.get("target")], float(s.get("entryX", 0.5)), float(s.get("entryY", 0.5)))
                via = [(float(p.get("x")), float(p.get("y"))) for p in g.findall("Array/mxPoint")]
                points = route(start, end, s, via)
            stroke = s["strokeColor"]
            mid = markers.setdefault(stroke, f"arrow{len(markers)}")
            dash = f' stroke-dasharray="{s["dashPattern"]}"' if s.get("dashed") == "1" else ""
            ends = "" if s.get("endArrow") == "none" else f' marker-end="url(#{mid})"'
            ends += f' marker-start="url(#{mid})"' if s.get("startArrow") == "block" else ""
            d = "M" + " L".join(f"{px:g},{py:g}" for px, py in points)
            svg.append(f'<path d="{d}" fill="none" stroke="{stroke}" stroke-width="{s.get("strokeWidth", 1.5)}" '
                       f'stroke-linejoin="round"{dash}{ends}/>')
            label = unescape(re.sub(r"<[^>]+>", " ", value)).strip()
            if label:
                cx, cy = midpoint(points)
                tw = len(label) * 11 * 0.54 + 8
                svg.append(f'<rect x="{cx - tw / 2:g}" y="{cy - 8:g}" width="{tw:g}" height="16" fill="#ffffff"/>')
                svg.append(tspan(cx, cy + 4, label, 11, "#0f172a", anchor="middle"))
    defs = "".join(
        f'<marker id="{mid}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{stroke}"/></marker>'
        for stroke, mid in markers.items())
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
            f"<defs>{defs}</defs>\n" + "\n".join(svg) + "\n</svg>\n")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name in (HERE / "figures.txt").read_text().split():
        (OUT / f"{name}.svg").write_text(render(HERE / f"{name}.drawio"))
        print(f"{OUT.name}/{name}.svg")
