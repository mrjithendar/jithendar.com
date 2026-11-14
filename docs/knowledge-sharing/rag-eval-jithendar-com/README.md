# How I Evaluate RAG on jithendar.com (draft, 13 November 2026)

Article: `content/blog/rag-evaluation-ask-the-blog-jithendar-com.mdx` (`status: review`, about 2,200 words of prose).

## Sources

Every claim comes from the repository on 13 November 2026: `.github/workflows/rag-eval.yml` and `ci-seo-agent.yml`,
`services/seo-agent/scripts/rag_eval.py`, `rag_mine_eval.py`, `app/rag_eval.py`, `app/seo_ml/train.py` (`run_rag_eval`),
`app/metrics.py`, `tests/fixtures/rag_eval.yaml`, `kubernetes/seo-agent-40-seo-agent.yaml`, `docs/seo/RAG.md`, `ML.md`,
`prometheus-alerts.yml` and the reports in `docs/seo/rag-eval/` (2026-11-10). GitHub shows one run of `rag-eval.yml`
(2026-11-11, commit `2293d8d`, 95 questions, success); its report was not committed.

## Figures

`ask-the-blog-eval-map`, `rag-eval-four-loops`, `rag-eval-workflow` (draw.io), exported to
`public/images/rag-evaluation-ask-the-blog-jithendar-com/`.

```bash
python3 sites/jithendar.com/docs/knowledge-sharing/rag-eval-jithendar-com/diagrams/build_diagrams.py   # writes the .drawio files
bash sites/jithendar.com/docs/knowledge-sharing/rag-eval-jithendar-com/diagrams/export.sh              # draw.io CLI → public/images/…
```

`drawio_model.py` is a copy of the one in `how-i-built-jithendar-com`. After editing a `.drawio` file by hand, run
only `export.sh`.

## SEO

- **SEO title (58 chars):** RAG Evaluation in Practice: Testing Ask the Blog Retrieval
- **Meta description (149 chars):** in the frontmatter (`seoDescription`).
- **Tags:** RAG, Retrieval Evaluation, pgvector, Embeddings, GitHub Actions, AI Engineering, LLMOps

## Questions for the author

1. **Hard-set results with the real model.** The 2026-11-11 `rag-eval.yml` run used all 95 questions, but its report
   only went to the job summary. Copy it into `docs/seo/rag-eval/` and the article can replace "the real numbers need
   the ONNX run" with paraphrase / multi-hop / exact / near-miss figures.
2. **Generation eval.** Has `rag_eval.py --generation` been run with a real key? If so, add its citation precision and
   faithfulness numbers (and cost). The article currently describes it as opt-in only.
3. **Weekly live eval.** Is `seo-flow-ml` applied on mk4 and has `seo_rag_eval_recall_at_3` produced values? A Grafana
   screenshot would help. There is no alert on that gauge yet; should the article say what threshold you'd alert on?
4. **Ask the Blog status.** The manifests have `ASK_BLOG_ENABLED: "false"`. If you've enabled it live, the intro and the
   "real questions flow back in" section should change.
