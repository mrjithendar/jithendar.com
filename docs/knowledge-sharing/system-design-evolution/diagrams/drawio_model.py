"""Small draw.io writer shared by the system-design-evolution figures (standard library only).

Every figure uses the same palette, shapes, arrow styles and legend, so the nine diagrams read as one set.
Labels are checked against their boxes before anything is written: the build fails instead of producing
a diagram whose text spills out. draw.io itself renders the SVGs (see export.sh).
"""
import xml.etree.ElementTree as ET
from html import escape

FONT = "Helvetica"
TITLE_PX, LINE_PX, EDGE_PX = 13, 12, 11

# kind: (fill, stroke, legend label)
KINDS = {
    "client": ("#f8fafc", "#334155", "Users and clients"),
    "network": ("#eef2ff", "#4338ca", "Network and edge"),
    "compute": ("#eff6ff", "#1d4ed8", "Servers and runtimes"),
    "service": ("#ecfdf5", "#047857", "Application code"),
    "data": ("#fffbeb", "#b45309", "Data stores"),
    "messaging": ("#fff1f2", "#be123c", "Messaging"),
    "ai": ("#f5f3ff", "#6d28d9", "AI components"),
    "ops": ("#f0fdfa", "#0f766e", "Delivery and operations"),
    "external": ("#f1f5f9", "#64748b", "Outside systems"),
    "security": ("#fef2f2", "#b91c1c", "Identity and control"),
    "optional": ("#ffffff", "#94a3b8", "Optional or not enabled"),
}
TEXT = "#0f172a"
SUBTEXT = "#334155"

# kind: (stroke, width, dash, legend label)
ARROWS = {
    "sync": ("#475569", 1.5, None, "Request and response"),
    "async": ("#be123c", 2, "6 4", "Message or event"),
    "batch": ("#b45309", 1.5, "2 3", "Scheduled or manual transfer"),
    "control": ("#0f766e", 1.5, "8 4", "Deploy, approve or observe"),
}

ZONE_TONES = {
    "plain": ("none", "#94a3b8"),
    "cluster": ("#f8fafc", "#1d4ed8"),
    "ai": ("#faf5ff", "#6d28d9"),
    "risk": ("#fff7f7", "#b91c1c"),
}


def fits(text, px, bold, width):
    return len(text) * px * (0.6 if bold else 0.54) <= width


class Diagram:
    def __init__(self, name, width, height, heading):
        self.name, self.w, self.h = name, width, height
        self.cells, self.ids, self.kinds_used, self.arrows_used = [], {}, [], []
        self.text("heading", 20, 12, width - 40, 24, f"<b>{escape(heading)}</b>", size=15, color=TEXT)

    # geometry helpers -------------------------------------------------------------------------
    def _check_inside(self, id, x, y, w, h):
        if x < 0 or y < 0 or x + w > self.w or y + h > self.h:
            raise SystemExit(f"{self.name}/{id}: ({x},{y},{w},{h}) leaves the {self.w}x{self.h} page")

    def _add(self, id, value, style, x, y, w, h, vertex=True, **attrs):
        if id in self.ids:
            raise SystemExit(f"{self.name}: duplicate id {id}")
        self._check_inside(id, x, y, w, h)
        self.ids[id] = (x, y, w, h)
        self.cells.append(dict(id=id, value=value, style=style, geo=(x, y, w, h), vertex=vertex, attrs=attrs))

    @staticmethod
    def style(**parts):
        return ";".join(f"{k}={v}" for k, v in parts.items()) + ";"

    # shapes -----------------------------------------------------------------------------------
    def zone(self, id, label, x, y, w, h, tone="plain", corner="left", valign="top"):
        fill, stroke = ZONE_TONES[tone]
        style = self.style(rounded=1, arcSize=3, dashed=1, dashPattern="6 4", fillColor=fill, strokeColor=stroke,
                           align=corner, spacingRight=10, verticalAlign=valign, spacingLeft=10, spacingTop=4, spacingBottom=4, fontFamily=FONT,
                           fontSize=LINE_PX, fontStyle=1, fontColor=stroke if tone != "plain" else "#475569",
                           whiteSpace="wrap", html=1, container=0)
        if not fits(label, LINE_PX, True, w - 20):
            raise SystemExit(f"{self.name}/{id}: zone label too long")
        self._add(id, escape(label), style, x, y, w, h)

    def node(self, id, kind, x, y, w, h, title, *lines, shape="box", align="center"):
        fill, stroke, _ = KINDS[kind]
        pad = 14 if shape in ("db", "queue") else 10
        for i, line in enumerate((title, *lines)):
            bold = i == 0
            if not fits(line, TITLE_PX if bold else LINE_PX, bold, w - 2 * pad):
                raise SystemExit(f"{self.name}/{id}: '{line}' is too wide for a {w}px box")
        need = 20 + 16 * len(lines) + (14 if shape == "db" else 6)
        if need > h:
            raise SystemExit(f"{self.name}/{id}: needs {need}px of height, has {h}")
        parts = dict(whiteSpace="wrap", html=1, fillColor=fill, strokeColor=stroke, strokeWidth=1.5, fontColor=TEXT,
                     fontFamily=FONT, fontSize=LINE_PX, align=align, verticalAlign="middle", spacing=4,
                     spacingLeft=6 if align == "left" else 2)
        if shape == "box":
            parts.update(rounded=1, arcSize=10)
        elif shape == "db":
            parts.update(shape="cylinder3", boundedLbl=1, backgroundOutline=1, size=9, spacingTop=10)
        elif shape == "queue":  # box with double end bars; a rotated cylinder would also rotate its connection points
            parts.update(shape="process", size=10, fixedSize=1, backgroundOutline=1)
        elif shape == "cloud":
            parts.update(shape="cloud")
        if kind == "optional":
            parts.update(dashed=1, dashPattern="6 4")
        value = f'<b style="font-size:{TITLE_PX}px">{escape(title)}</b>' + "".join(
            f'<br><span style="font-size:{LINE_PX}px;color:{SUBTEXT}">{escape(l)}</span>' for l in lines)
        self._add(id, value, self.style(**parts), x, y, w, h)
        if kind not in self.kinds_used:
            self.kinds_used.append(kind)
        return id

    def text(self, id, x, y, w, h, html, size=LINE_PX, color=SUBTEXT, align="left"):
        style = "text;" + self.style(html=1, strokeColor="none", fillColor="none", align=align, verticalAlign="top", whiteSpace="wrap", fontFamily=FONT,
                           fontSize=size, fontColor=color, spacing=0)
        self._add(id, html, style, x, y, w, h)

    def marker(self, n, x, y):
        """A numbered red circle marking a failure point; (x, y) is its centre."""
        style = "ellipse;" + self.style(html=1, fillColor="#b91c1c", strokeColor="#ffffff", strokeWidth=2,
                           fontColor="#ffffff", fontStyle=1, fontFamily=FONT, fontSize=12, align="center",
                           verticalAlign="middle")
        self._add(f"fail{n}", str(n), style, x - 12, y - 12, 24, 24)

    # edges ------------------------------------------------------------------------------------
    def edge(self, a, b, label="", kind="sync", exit=None, entry=None, via=(), both=False, offset=None, t=0.0, arrow=True):
        for end in (a, b):
            if end not in self.ids:
                raise SystemExit(f"{self.name}: edge to unknown cell {end}")
        stroke, width, dash, _ = ARROWS[kind]
        parts = dict(edgeStyle="orthogonalEdgeStyle", rounded=1, html=1, strokeColor=stroke, strokeWidth=width,
                     endArrow="block", endFill=1, endSize=7, fontFamily=FONT, fontSize=EDGE_PX, fontColor=TEXT,
                     labelBackgroundColor="#ffffff", jumpStyle="gap", jumpSize=6)
        if dash:
            parts.update(dashed=1, dashPattern=dash)
        if both:
            parts.update(startArrow="block", startFill=1, startSize=7)
        if not arrow:
            parts.update(endArrow="none")
        for prefix, point in (("exit", exit), ("entry", entry)):
            if point:
                parts.update({f"{prefix}X": point[0], f"{prefix}Y": point[1], f"{prefix}Dx": 0, f"{prefix}Dy": 0,
                              f"{prefix}Perimeter": 0})
        id = f"e{len([c for c in self.cells if not c['vertex']])}"
        self.cells.append(dict(id=id, value=escape(label).replace("\n", "<br>"), style=self.style(**parts), geo=None,
                               vertex=False, attrs=dict(source=a, target=b), via=via, offset=offset, t=t))
        if arrow and kind not in self.arrows_used:
            self.arrows_used.append(kind)

    # legend -----------------------------------------------------------------------------------
    def legend(self, y, x=20, extra_kinds=(), failure=False, labels=None):
        """Swatches for the kinds and arrows this diagram uses, wrapped to the page width."""
        items = [("kind", k) for k in KINDS if k in self.kinds_used or k in extra_kinds]
        items += [("arrow", a) for a in ARROWS if a in self.arrows_used]
        if failure:
            items.append(("fail", None))
        self.h = max(self.h, y + 34)
        self.text("legend-title", x, y, 80, 18, "<b>Legend</b>", color=TEXT)
        cx, cy = x + 70, y
        for i, (what, key) in enumerate(items):
            label = {"kind": lambda k: (labels or {}).get(k, KINDS[k][2]), "arrow": lambda k: ARROWS[k][3], "fail": lambda k: "Failure point"}[what](key)
            width = 34 + len(label) * LINE_PX * 0.56
            if cx + width > self.w - 20:
                cx, cy = x + 70, cy + 24
            self.h = max(self.h, cy + 34)  # the legend is last, so the page grows to fit it
            if what == "kind":
                fill, stroke, _ = KINDS[key]
                dash = "dashed=1;dashPattern=4 3;" if key == "optional" else ""
                self._add(f"lg{i}", "", f"rounded=1;arcSize=20;fillColor={fill};strokeColor={stroke};strokeWidth=1.5;{dash}",
                          cx, cy + 2, 22, 14)
            elif what == "arrow":
                stroke, w, dash, _ = ARROWS[key]
                d = f"dashed=1;dashPattern={dash};" if dash else ""
                self._add(f"lg{i}", "", f"shape=line;strokeColor={stroke};strokeWidth={w};{d}", cx, cy + 4, 24, 10)
            else:
                self._add(f"lg{i}", "", "ellipse;fillColor=#b91c1c;strokeColor=#ffffff;", cx + 4, cy + 1, 16, 16)
            self.text(f"lgt{i}", cx + 30, cy + 1, width - 30, 18, escape(label), size=LINE_PX)
            cx += width + 12
        return cy + 24

    # output -----------------------------------------------------------------------------------
    def xml(self):
        mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="system-design-evolution/build_diagrams.py",
                            version="32.6.10", type="device")
        diagram = ET.SubElement(mxfile, "diagram", id=self.name, name=self.name)
        model = ET.SubElement(diagram, "mxGraphModel", dx="1000", dy="800", grid="1", gridSize="10", guides="1",
                              tooltips="1", connect="1", arrows="1", fold="1", page="1", pageScale="1",
                              pageWidth=str(self.w), pageHeight=str(self.h), background="#ffffff", math="0", shadow="0")
        root = ET.SubElement(model, "root")
        ET.SubElement(root, "mxCell", id="0")
        ET.SubElement(root, "mxCell", id="1", parent="0")
        # A white page-sized rectangle, so exports keep the full canvas and a white background.
        page = ET.SubElement(root, "mxCell", id="page", value="", vertex="1", parent="1",
                             style="rounded=0;fillColor=#ffffff;strokeColor=none;locked=1;")
        ET.SubElement(page, "mxGeometry", {"x": "0", "y": "0", "width": str(self.w), "height": str(self.h), "as": "geometry"})
        vertices = [c for c in self.cells if c["vertex"]]
        edges = [c for c in self.cells if not c["vertex"]]
        # zones first, then edges, then boxes, so boxes sit on top of the lines that meet them
        ordered = [c for c in vertices if c["style"].startswith("rounded=1;arcSize=3")] + edges + \
                  [c for c in vertices if not c["style"].startswith("rounded=1;arcSize=3")]
        for c in ordered:
            attrs = dict(id=c["id"], value=c["value"], style=c["style"], parent="1")
            if c["vertex"]:
                attrs["vertex"] = "1"
                cell = ET.SubElement(root, "mxCell", attrs)
                x, y, w, h = c["geo"]
                ET.SubElement(cell, "mxGeometry", {"x": str(x), "y": str(y), "width": str(w), "height": str(h), "as": "geometry"})
            else:
                attrs.update(edge="1", **c["attrs"])
                cell = ET.SubElement(root, "mxCell", attrs)
                geo = ET.SubElement(cell, "mxGeometry", {"x": str(c["t"]), "relative": "1", "as": "geometry"})
                if c["offset"]:
                    ET.SubElement(geo, "mxPoint", {"x": str(c["offset"][0]), "y": str(c["offset"][1]), "as": "offset"})
                if c["via"]:
                    arr = ET.SubElement(geo, "Array", {"as": "points"})
                    for x, y in c["via"]:
                        ET.SubElement(arr, "mxPoint", x=str(x), y=str(y))
        ET.indent(mxfile)
        return ET.tostring(mxfile, encoding="unicode")
