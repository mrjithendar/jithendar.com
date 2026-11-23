"""Recall@3 as Ask the Blog sees it: the similarity floor filters candidates before the reranker (min_score in search).

  PYTHONPATH=<moks-seo-agent> <moks-seo-agent>/.venv/bin/python floor_check.py <moks-seo-agent> <models>

<models> holds bge-small-en-v1.5/ (model.onnx, tokenizer.json) and rr-int8/ (the reranker's int8 model.onnx and
tokenizer.json). Builds the production index (token chunker, vector, at most 3 per article) over the frozen corpus once,
then runs the eval set with and without the reranker at floors 0.66, 0.59 and none. Run 2026-11-22 on moks-seo-agent
f751033 (= b69c3f5): see ../README.md.
"""

import asyncio
import sys
from pathlib import Path
from types import SimpleNamespace

AGENT, MODELS = Path(sys.argv[1]), Path(sys.argv[2])
sys.path[:0] = [str(AGENT), str(AGENT / "scripts")]

from app.embeddings import OnnxEmbeddings  # noqa: E402
from app.rag_eval import BLOG_DIR, LocalIndex, evaluate, load_articles, load_eval_set  # noqa: E402
from app.reranker import RerankGate  # noqa: E402
from app.retrieval import RetrievalConfig  # noqa: E402
from rag_eval import CachedEmbeddings  # noqa: E402


async def main() -> None:
    emb = CachedEmbeddings(OnnxEmbeddings(str(MODELS / "bge-small-en-v1.5")))
    ix = LocalIndex(emb, RetrievalConfig(mode="vector"), chunker="token")
    await ix.build(load_articles(BLOG_DIR))
    qs = load_eval_set()
    gate = RerankGate(SimpleNamespace(rag_reranker_enabled=True, rag_reranker_dir=str(MODELS / "rr-int8"), rag_reranker_threads=4, rag_reranker_candidates=0))
    for name, reranker in (("no reranker", None), ("reranker int8", gate)):
        ix.reranker = reranker
        for floor in (0.66, 0.59, 0.0):
            r = await evaluate(name, lambda q, k, f=floor: ix.search(q, k, min_score=f), qs, floor=floor)
            m = r.metrics
            print(f"{name:14s} floor {floor} first: R@1 {m['recall@1']:.4f} R@3 {m['recall@3']:.4f} R@6 {m['recall@6']:.4f} MRR {m['mrr']:.4f}", flush=True)


asyncio.run(main())
