# LanceDB on Cloudflare R2 (24 November 2026): evidence and review notes

Draft (status `review`, written 2026-11-24): `content/blog/lancedb-cloudflare-r2-seo-agent-admin-browser.mdx`, about
the page at `/admin/lancedb` and the table behind it: a copy of the seo-agent's pgvector article index, kept in LanceDB
on Cloudflare R2.

## Sources

| Source | What it gave |
|---|---|
| mrjithendar/moks-seo-agent 88bf4ea | `app/lance_admin.py` (browser API, checks), `app/lance_index.py` (the copy), `app/main.py` (wiring, routes), `app/admin_settings/groups/retrieval.py`, `pyproject.toml`, the tests' names |
| mrjithendar/moks-cms 0336cc2 | `docs/seo/DECISIONS.md` D-47, D-91, D-92, D-93; `src/app/admin/lancedb/page.tsx`; `src/lib/seo-agent/callbacks.ts` (`lancedbStorage`); `src/lib/user-guide.ts`; merge times of #121, #122, #124 |
| mk4, namespace `jithendar` (read-only `kubectl exec` in the seo-agent pod) | the table, its versions and size, pgvector counts, reindex runs and schedule, query timings: `evidence/checks.txt` |
| LanceDB docs (0.41.0 pages; the image has lancedb 0.40.0) | [Embedded](https://docs.lancedb.com/oss/v0-41-0/basics/lancedb-embedded.md), [Storage](https://docs.lancedb.com/storage), [Guarantees](https://docs.lancedb.com/oss/v0-41-0/basics/guarantees.md), [Cleanup](https://docs.lancedb.com/oss/v0-41-0/maintenance/cleanup.md), [Vector indexes](https://docs.lancedb.com/oss/v0-41-0/indexing/vector-index.md) |
| The owner's screenshot of `/admin/lancedb` | cropped to the page body (no browser chrome, admin bar or name): `public/images/lancedb-r2/lancedb-r2-admin-page.png` |

The checks never print keys, the R2 endpoint or the account id. Keep it that way when you edit.

## Not known or not decided yet (Todo items in the article)

1. **Deleting an article doesn't update the copy.** The deleted article's chunks leave pgvector with the post, but no
   reindex runs, so `article_chunks` keeps them until the next reindex that changes something.
2. **Publishing in Admin → Posts doesn't reindex the article.** Only `publish_flow` does. The two articles published on
   23 November have no chunks, so Ask the Blog can't find them until the weekly reindex (Sunday 03:17 UTC) or a manual
   run of `reindex_flow`.
3. **The page's description** says "CrewAI memory and the article index"; memory isn't built.
4. **Latency** was measured once (six queries each). Measure again before planning a LanceDB retriever.

## Figures

Built with `diagrams/build_diagrams.py` (standard library only, using the shared `drawio_model.py` writer), then
exported with `diagrams/export.sh` (draw.io desktop CLI, light theme) to `public/images/lancedb-r2/`:

| Figure | Shows |
|---|---|
| `lancedb-r2-architecture` | who opens LanceDB, where the keys come from, who searches what; the cover image |
| `lancedb-r2-sync` | how a sync runs, and how the copy drifted between 15 and 24 November |
| `lancedb-r2-edit` | the path of an edit and the six checks in `app/lance_admin.py` |

The screenshot `lancedb-r2-admin-page.png` is not built: it's a crop of the owner's screenshot, resized to 1600 px wide.
