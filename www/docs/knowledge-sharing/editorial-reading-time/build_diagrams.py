#!/usr/bin/env python3
"""Figures added in the November 2026 reading-time edit: one editable .drawio file per figure, next to its
article's notes in docs/knowledge-sharing/<topic>/diagrams/, and a matching SVG in public/images/<topic>/.

Reuses the layout, palette and draw.io writer of the RoboShop AI series. Run from www/. The SVG is rendered here,
not exported by draw.io: if a .drawio file is edited by hand, re-export it from draw.io over the SVG.
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTES = HERE.parent
IMAGES = HERE.parents[2] / "public" / "images"
spec = importlib.util.spec_from_file_location("series_diagrams", NOTES / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page = series.Page


def typescript_comment_flow():
    """Posting a comment, as traced in the TypeScript tutorial (jithendar.com dc249e8)."""
    p = Page("typescript-comment-flow", "Posting a comment", 620, 728, "Posting a comment on jithendar.com, end to end",
             "In the browser, the Composer client component holds the text as string state and calls onSubmit, typed "
             "ComposerSubmit. Discussion.tsx calls the server action postCommentAction directly. On the server, "
             "postCommentAction reads the user from the session cookie through signedIn, then calls submitComment, which "
             "checks again at runtime: cleanBody, isUuid and a database read, assertOpen and the client-key pattern. Drizzle "
             "inserts the row into PostgreSQL, whose unique index and foreign keys add their own rules. The result returns "
             "as a CommentResult discriminated union.")
    p.zone("Browser: client components", 15, 12, 590, 196)
    p.zone("Server: Next.js", 15, 220, 590, 364)
    p.zone("Database", 15, 596, 590, 120, "br")
    p.node("composer", "browser", 30, 40, 270, 70, "Composer.tsx", "body: useState(initial), a string", "onSubmit: ComposerSubmit")
    p.node("discussion", "browser", 320, 40, 270, 70, "Discussion.tsx", "post(body, clientKey, parentId)", "reads r.id only when r.ok")
    p.node("result", "absent", 30, 128, 300, 70, "CommentResult (compile time)", "{ ok: true, id, status, thread }",
           "| { ok: false, error }")
    p.node("action", "gateway", 30, 248, 560, 70, "postCommentAction  (_actions/comments.ts, \"use server\")",
           "signedIn(): the user comes from the session cookie, never from the arguments",
           "return type inferred, and step 2 relies on it")
    p.node("submit", "service", 30, 346, 560, 112, "submitComment(input: SubmitInput)  (lib/comments.ts)",
           "runtime checks: cleanBody(body: unknown) for type and length",
           "isUuid and a database read: the post exists, is published, not deleted",
           "assertOpen: discussion not closed or locked; client key /^[A-Za-z0-9_-]{8,64}$/",
           "status from the user's role on the server")
    p.node("drizzle", "service", 30, 486, 560, 70, "Drizzle insert  (db/schema.ts)",
           ".notNull() columns are string, the rest string | null",
           "a missing required column does not compile")
    p.node("pg", "store", 30, 618, 560, 62, "PostgreSQL table comment",
           "unique index on user and client key; foreign keys keep a reply on its parent's post")
    p.edge("composer", "discussion", a_side="r", b_side="l", label="onSubmit", dy=-12)
    p.edge("discussion", "action", a_at=0.5, b_at=0.759, label="server action call", dx=-70)
    p.edge("action", "submit")
    p.edge("submit", "drizzle", kind="write")
    p.edge("drizzle", "pg", kind="write", label="insert", dx=30)
    p.edge("action", "result", a_side="t", b_side="b", a_at=0.161, b_at=0.5, kind="dashed", label="result", dx=26)
    return p


FILES = {
    "typescript-tutorial": [typescript_comment_flow],
}


def write(topic, page):
    for e in page.edges:
        for x, y in e["points"]:
            if not (0 <= x <= page.w and 0 <= y <= page.h):
                raise SystemExit(f"{page.figure}: edge {e['id']} leaves the page")
    for n in page.nodes.values():
        if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > page.w or n["y"] + n["h"] > page.h:
            raise SystemExit(f"{page.figure}: {n['id']} leaves the page")
    drawio_dir, image_dir = NOTES / topic / "diagrams", IMAGES / topic
    drawio_dir.mkdir(parents=True, exist_ok=True)
    image_dir.mkdir(parents=True, exist_ok=True)
    mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="build_diagrams.py", version="24.7.17", type="device")
    mxfile.append(series.page_xml(page, 0))
    ET.indent(mxfile)
    (drawio_dir / f"{page.figure}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
    (image_dir / f"{page.figure}.svg").write_text(series.page_svg(page), encoding="utf-8")
    return f"{topic}/{page.figure} {page.w} {page.h}\n"


def main():
    built = [write(topic, make()) for topic, makers in FILES.items() for make in makers]
    (HERE / "figures.txt").write_text("".join(built), encoding="utf-8")
    print(f"{len(built)} .drawio files and SVGs")


if __name__ == "__main__":
    main()
