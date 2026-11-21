"""Label drift + floor detail for app/data/rag_eval.yaml.

1. For each blog folder, does every expected slug exist (non-draft) and every anchor exist in that article (anchors as the
   production chunker computes them)?
2. token-vector-div (the production config) on one folder: best expected-article cosine per answerable question, so
   we can list what the configured 0.66 floor would drop; plus how often the rag-eval article shows up in the top 6.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from app.embeddings import OnnxEmbeddings, chunk_markdown, token_counter
from app.rag_eval import LocalIndex, evaluate, load_articles, load_eval_set, slug_of
from app.retrieval import RetrievalConfig


def anchors_by_slug(blog: Path, emb) -> dict[str, set[str]]:
    counter = token_counter(emb)
    out = {}
    for a in load_articles(blog):
        out[a["slug"]] = {c.anchor for c in chunk_markdown(a["body"], a["title"], counter)}
    return out


async def main() -> None:
    model_dir, mode = sys.argv[1], sys.argv[2]
    blogs = [Path(p) for p in sys.argv[3:]]
    emb = OnnxEmbeddings(model_dir)
    qs = load_eval_set()
    if mode == "labels":
        for blog in blogs:
            ab = anchors_by_slug(blog, emb)
            missing_slugs, missing_anchors, dead_q = [], [], []
            for q in qs:
                if q.type == "no-answer":
                    continue
                live = [s for s in q.slugs if s in ab]
                for s in q.slugs:
                    if s not in ab:
                        missing_slugs.append((q.id, s))
                all_anchors = set().union(*(ab[s] for s in live)) if live else set()
                for an in q.anchors:
                    if an not in all_anchors:
                        missing_anchors.append((q.id, an))
                if not live:
                    dead_q.append(q.id)
            print(json.dumps({"blog": str(blog), "articles": len(ab), "missing_slugs": missing_slugs, "missing_anchors": missing_anchors, "questions_with_no_live_slug": dead_q}, indent=1))
        return
    blog = blogs[0]
    arts = load_articles(blog)
    ix = LocalIndex(emb, RetrievalConfig(mode="vector"), chunker="token")
    info = await ix.build(arts)
    res = await evaluate("token-vector-div", ix.search, qs)
    m = res.metrics
    print(json.dumps({"blog": str(blog), "articles": len(arts), "chunks": info["chunks"], **m, "calibrated_floor": res.calibrated_floor, "by_type": res.by_type, "by_tag": res.by_tag}, indent=1))
    first55 = [r for r in res.rows if not r.q.id.startswith("x")]
    from app.rag_eval import summarize
    s55 = summarize("first55", first55, 0.15)
    hard = [r for r in res.rows if r.q.id.startswith("x")]
    sh = summarize("hard", hard, 0.15)
    print("first55", s55.metrics, s55.calibrated_floor)
    print("hard40", sh.metrics, sh.calibrated_floor)
    print("lost at 0.66:", [(r.q.id, round(r.best_expected_cosine, 3)) for r in res.rows if r.best_expected_cosine is not None and r.best_expected_cosine < 0.66])
    print("missed in top6:", [r.q.id for r in res.rows if r.q.type != "no-answer" and r.rank is None])
    print("no-answer best cos:", [(r.q.id, round(r.best_cosine, 3), slug_of(r.hits[0].path) if r.hits else None) for r in res.rows if r.q.type == "no-answer"])
    meta = [(r.q.id, [i + 1 for i, h in enumerate(r.hits) if slug_of(h.path) == "rag-evaluation-ask-the-blog-jithendar-com"]) for r in res.rows]
    print("rag-eval article in top6:", [x for x in meta if x[1]])
    print("floor_table", res.floor_table)


asyncio.run(main())
