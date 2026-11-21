"""token-vector-div (production retrieval) over a blog folder: one JSON row per question.

  dump_rows.py MODEL_DIR BLOG_DIR OUT.json [EXTRA_ARTICLE.mdx ...]

Extra articles are added to a copy of the folder (to measure what a new article does to the eval).
"""

from __future__ import annotations

import asyncio
import json
import shutil
import sys
import tempfile
from pathlib import Path

from app.embeddings import OnnxEmbeddings
from app.rag_eval import LocalIndex, evaluate, load_articles, load_eval_set, slug_of
from app.retrieval import RetrievalConfig


async def main() -> None:
    model_dir, blog, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
    extra = [Path(p) for p in sys.argv[4:]]
    with tempfile.TemporaryDirectory() as tmp:
        if extra:
            for f in blog.glob("*.mdx"):
                shutil.copy(f, tmp)
            for f in extra:
                shutil.copy(f, tmp)
            blog = Path(tmp)
        arts = load_articles(blog)
        ix = LocalIndex(OnnxEmbeddings(model_dir), RetrievalConfig(mode="vector"), chunker="token")
        await ix.build(arts)
        res = await evaluate("token-vector-div", ix.search, load_eval_set())
    rows = [
        {
            "id": r.q.id,
            "type": r.q.type,
            "tags": r.q.tags,
            "rank": r.rank,
            "anchor_hit": r.anchor_hit,
            "best_expected": r.best_expected_cosine,
            "best": r.best_cosine,
            "top": [(slug_of(h.path), h.anchor, round(h.score, 3)) for h in r.hits],
        }
        for r in res.rows
    ]
    out.write_text(json.dumps({"articles": len(arts), "metrics": res.metrics, "calibrated_floor": res.calibrated_floor, "by_type": res.by_type, "by_tag": res.by_tag, "rows": rows}, indent=1))
    print(len(arts), res.metrics, res.calibrated_floor, res.by_tag)


asyncio.run(main())
