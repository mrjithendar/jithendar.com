"""Sweep the reranker's cost knobs on the 95-question set: build the vector index once, then rerank the top n with
t threads for each model. Prints Recall@3, MRR and p95 of the whole search (embed + vector + rerank).

  PYTHONPATH=<moks-seo-agent> <moks-seo-agent>/.venv/bin/python rerank_sweep.py <moks-seo-agent> <models>

<models> holds bge-small-en-v1.5/, rr-int8/ and rr-fp32/ (model.onnx + tokenizer.json each). Run 2026-11-22 on an
M3 Pro: ../results/2026-11-22-sweep-m3pro.txt. It calls CrossEncoderReranker directly (top n, then rerank), which is
what the gate does with RAG_RERANKER_CANDIDATES = n.
"""

import asyncio
import sys
import time
from pathlib import Path

WT, SP = Path(sys.argv[1]), Path(sys.argv[2])
sys.path.insert(0, str(WT))
sys.path.insert(0, str(WT / "scripts"))

from app.embeddings import OnnxEmbeddings  # noqa: E402
from app.rag_eval import BLOG_DIR, LocalIndex, evaluate, load_articles, load_eval_set  # noqa: E402
from app.reranker import CrossEncoderReranker  # noqa: E402
from app.retrieval import RetrievalConfig  # noqa: E402
from rag_eval import CachedEmbeddings  # noqa: E402

MODELS = {"fp32": SP / "rr-fp32", "int8": SP / "rr-int8"}
GRID = [(m, n, t) for m in ("int8", "fp32") for n in (20, 10, 6) for t in (2, 4)]


async def main() -> None:
    emb = CachedEmbeddings(OnnxEmbeddings(str(SP / "bge-small-en-v1.5")))
    ix = LocalIndex(emb, RetrievalConfig(mode="vector"), chunker="token")
    await ix.build(load_articles(BLOG_DIR))
    qs = load_eval_set()
    base = await evaluate("base", ix.search, qs, floor=0.66)
    print(f"{'baseline':22s} R@3 {base.metrics['recall@3']:.4f} MRR {base.metrics['mrr']:.4f} p50 {base.latency_ms['p50']} p95 {base.latency_ms['p95']}", flush=True)
    for m, n, t in GRID:
        rr = CrossEncoderReranker(str(MODELS[m]), threads=t)
        await rr.rerank("warm up", (await ix.search("warm up", n)), 6)

        async def search(q: str, k: int, rr: CrossEncoderReranker = rr, n: int = n) -> list:
            return await rr.rerank(q, await ix.search(q, n), k)

        t0 = time.perf_counter()
        r = await evaluate(f"{m}-n{n}-t{t}", search, qs, floor=0.66)
        print(f"{m}-n{n}-t{t:<14} R@3 {r.metrics['recall@3']:.4f} MRR {r.metrics['mrr']:.4f} p50 {r.latency_ms['p50']} p95 {r.latency_ms['p95']}  ({time.perf_counter() - t0:.0f}s)", flush=True)


asyncio.run(main())
