#!/usr/bin/env python3
"""Figures for content/blog/lancedb-cloudflare-r2-seo-agent-admin-browser.mdx (LanceDB on R2 in the seo-agent).

    python3 docs/knowledge-sharing/lancedb-r2/diagrams/build_diagrams.py   # writes the .drawio files
    bash docs/knowledge-sharing/lancedb-r2/diagrams/export.sh              # draw.io CLI → public/images/lancedb-r2/

If you edit a .drawio file by hand, run only export.sh afterwards. Running this script overwrites the edits.

Code facts come from mrjithendar/moks-seo-agent 88bf4ea (app/lance_admin.py, app/lance_index.py, app/main.py) and
mrjithendar/moks-cms 0336cc2 (src/app/admin/lancedb/page.tsx, src/lib/seo-agent/callbacks.ts). Numbers come from the
read-only checks on 24 November 2026 in ../evidence/checks.txt.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from drawio_model import ARROWS, TEXT, Diagram  # noqa: E402

# Arrow kinds for this article only (the shared writer stays unchanged).
ARROWS["step"] = ("#475569", 1.5, None, "Next step")
ARROWS["check"] = ("#b91c1c", 1.5, None, "Next check (a failed check stops the request)")

HERE = Path(__file__).resolve().parent


def architecture():
    d = Diagram("lancedb-r2-architecture", 960, 500, "Where the seo-agent's LanceDB lives, who opens it, and who searches what")
    d.zone("z-web", "Web app (jithendar-com)", 20, 50, 230, 335, "plain")
    d.zone("z-agent", "seo-agent (one replica, one writer)", 300, 50, 290, 335, "cluster")
    d.zone("z-data", "Data", 700, 50, 240, 335, "plain")

    d.node("browser", "client", 35, 85, 200, 92, "/admin/lancedb", "admin only; 25 rows a page",
           "edit or delete one row", "audit log entry per write")
    d.node("storage", "security", 35, 220, 200, 92, "Admin → Storage", "bucket, endpoint and keys",
           "(R2 or Amazon S3), sent", "over the internal port")

    d.node("admin", "service", 315, 85, 260, 92, "lance_admin.py", "GET /lancedb, /tables/{name}",
           "POST …/row, /update, /delete", "bearer SEO_AGENT_TOKEN")
    d.node("mirror", "service", 315, 200, 260, 76, "lance_index.py (ArticleMirror)", "after a reindex that changed",
           "something: rewrite the copy")
    d.node("ask", "ai", 315, 296, 260, 76, "Ask the Blog and the crews", "search PgVectorIndex (pgvector)",
           "LanceDB retriever: not built")

    d.node("r2", "data", 715, 85, 210, 110, "Cloudflare R2 (LanceDB)", "s3://<bucket>/jithendar/",
           "seo-agent/lancedb", "article_chunks", shape="db")
    d.node("pg", "data", 715, 230, 210, 130, "PostgreSQL + pgvector", "seo_article_chunks",
           "the source of truth", "3,147 chunks, 67 articles", shape="db")

    d.edge("browser", "admin", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("storage", "admin", "uri + keys", exit=(1, 0.25), entry=(0, 0.85))
    d.edge("admin", "r2", "page reads, 1-row edits", exit=(1, 0.5), entry=(0, 0.42))
    d.edge("pg", "mirror", "chunks + vectors", kind="batch", exit=(0, 0.25), entry=(1, 0.822))
    d.edge("mirror", "r2", "overwrite", kind="batch", exit=(1, 0.25), entry=(0, 0.85))
    d.edge("ask", "pg", "vector search", exit=(1, 0.5), entry=(0, 0.83))

    d.text("note", 20, 400, 920, 40, "<b>Live on 24 November 2026:</b> one table, 3,179 rows from 68 articles, 384-dimension "
           "bge-small vectors, one 6.6 MB data file, version 2, no vector index. Nothing searches it yet, and it is "
           "rewritten only after a reindex that changed something, so it can lag behind Postgres.", color=TEXT)
    d.legend(452, labels={"client": "Admin page", "security": "Keys and settings", "service": "seo-agent code",
                          "ai": "Search users", "data": "Stores"})
    return d


def sync():
    d = Diagram("lancedb-r2-sync", 960, 680, "How the copy is written, and how it drifted from Postgres in its first week")
    d.zone("z-how", "How a sync runs (app/lance_index.py)", 20, 50, 450, 560, "cluster")
    d.zone("z-live", "What happened on mk4 (times UTC)", 490, 50, 450, 560, "plain")

    steps = [
        ("1. reindex_flow finishes", "weekly, Sunday 03:17 UTC, or one article", "from publish_flow (approved AI drafts)"),
        ("2. Did anything change?", "embedded, reused, deleted or swapped > 0;", "if not, write only when the table is missing"),
        ("3. Read pgvector", "the published articles' chunks with the", "vectors Postgres already holds (no re-embed)"),
        ("4. Guards", "an empty result keeps the existing copy;", "mixed vector sizes are refused"),
        ("5. create_table(mode=\"overwrite\")", "the whole table written as one new version,", "under the agent's reindex lock"),
        ("6. optimize(cleanup_older_than=1 h)", "older versions removed; a failed sync is a", "warning and the reindex still succeeds"),
    ]
    y0, rh, gap = 82, 76, 10
    for i, (title, *lines) in enumerate(steps):
        d.node(f"s{i}", "service", 35, y0 + i * (rh + gap), 420, rh, title, *lines, align="left")
        if i:
            d.edge(f"s{i - 1}", f"s{i}", exit=(0.5, 1), entry=(0.5, 0), kind="step")

    events = [
        ("ops", "15 Nov, 03:17: weekly reindex", "52 articles, 2,514 chunks embedded", "(before the LanceDB copy existed)"),
        ("data", "22 Nov, 03:17 to 03:23: weekly reindex", "68 articles: 671 embedded, 2,508 unchanged;",
         "copy rewritten as version 2, 3,179 rows"),
        ("security", "After the sync: one article deleted", "its 32 chunks left pgvector with the post,",
         "but stay in the copy: no reindex ran"),
        ("security", "23 Nov: two articles published by hand", "Admin → Posts does not start a reindex:",
         "no chunks in pgvector or in LanceDB"),
        ("data", "24 Nov: the two stores differ", "pgvector: 3,147 chunks from 67 articles", "LanceDB: 3,179 chunks from 68 articles"),
        ("optional", "29 Nov, 03:17: next weekly reindex", "embeds the two new articles, so the copy",
         "is rewritten and matches Postgres again"),
    ]
    for i, (kind, title, *lines) in enumerate(events):
        d.node(f"e{i}", kind, 505, y0 + i * (rh + gap), 420, rh, title, *lines, align="left")
        if i:
            d.edge(f"e{i - 1}", f"e{i}", exit=(0.5, 1), entry=(0.5, 0), kind="step")
    d.legend(626, labels={"service": "Sync step", "ops": "Reindex before the copy", "data": "Copy written or compared",
                          "security": "Where the stores drift", "optional": "Expected, not happened yet"})
    return d


def edit():
    d = Diagram("lancedb-r2-edit", 960, 580, "What stands between the Save button and a changed row")
    d.node("form", "client", 20, 60, 250, 76, "Row form on /admin/lancedb", "only changed columns are sent;",
           "delete needs a ticked box")
    d.node("action", "service", 300, 60, 250, 76, "Server action (web app)", "saveRow or deleteRow,",
           "actor = the signed-in admin")
    d.node("api", "service", 580, 60, 360, 76, "seo-agent internal API", "POST /lancedb/tables/{name}/update",
           "or …/delete, with the bearer token")
    d.edge("form", "action", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("action", "api", exit=(1, 0.5), entry=(0, 0.5))

    d.zone("z-checks", "Checks in app/lance_admin.py, in order", 20, 172, 920, 225, "risk")
    checks = [  # (id, x, y, title, lines)
        ("c1", 635, 205, "1. Table name", "a plain identifier that exists,", "else 404"),
        ("c2", 335, 205, "2. Key column", "an existing scalar column;", "vectors and lists cannot be keys"),
        ("c3", 35, 205, "3. Key value → one literal", "quotes doubled, NUL refused, numbers", "finite, timestamps ISO 8601"),
        ("c4", 35, 305, "4. Exactly one row", "count_rows(where) = 0: 404;", "more than one: 409"),
        ("c5", 335, 305, "5. Columns to change", "text, number, true/false, timestamp;", "vectors read-only; NOT NULL kept"),
        ("c6", 635, 305, "6. Write", "table.update(where, values) or", "delete(where): one new table version"),
    ]
    for id, x, y, title, *lines in checks:
        d.node(id, "security", x, y, 290, 76, title, *lines, align="left")
    d.edge("api", "c1", kind="check", exit=(0.555, 1), entry=(0.5, 0))
    d.edge("c1", "c2", kind="check", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("c2", "c3", kind="check", exit=(0, 0.5), entry=(1, 0.5))
    d.edge("c3", "c4", kind="check", exit=(0.5, 1), entry=(0.5, 0))
    d.edge("c4", "c5", kind="check", exit=(1, 0.5), entry=(0, 0.5))
    d.edge("c5", "c6", kind="check", exit=(1, 0.5), entry=(0, 0.5))

    d.node("note", "optional", 20, 425, 450, 76, "Until the next sync", "article_chunks is rewritten from pgvector",
           "after a reindex: edit the article instead", align="left")
    d.node("log", "ops", 490, 425, 450, 76, "Recorded twice", "agent log: lancedb_update or lancedb_delete",
           "web audit log: lancedb.update; delete at warning", align="left")
    d.edge("c6", "log", exit=(0.5, 1), entry=(0.645, 0))
    d.legend(522, labels={"client": "Admin page", "service": "Request path", "security": "Check",
                          "ops": "Record", "optional": "Limit of an edit"})
    return d


def main():
    for build in (architecture, sync, edit):
        d = build()
        (HERE / f"{d.name}.drawio").write_text(d.xml() + "\n")
        print(f"wrote {d.name}.drawio ({d.w}x{d.h})")


if __name__ == "__main__":
    main()
