# SSG and ISR article

Status: **draft for author review, not published.** Written 2026-11-11 for the "SSG + ISR for public pages" change
(`docs/PROGRESS.md`). **Publish only after that change is deployed**, and re-measure TTFB on the live site first: the
"after" numbers in the article come from a production build run locally against PostgreSQL 18.

| Asset | Location |
| --- | --- |
| Article | `content/blog/ssg-isr-nextjs-jithendar-com.mdx` (`status: review`, no `publishedAt`) |
| Diagrams | 2 Mermaid blocks inside the article (a flowchart and a sequence diagram); no image files |

## SEO and publishing metadata

| Field | Value |
| --- | --- |
| H1 (`title`) | SSG and ISR in Next.js: How jithendar.com Went From Half a Second to 9 Milliseconds Per Page |
| SEO title (`seoTitle`) | SSG and ISR in Next.js: Implementation and Benefits |
| Meta description | What static site generation and incremental static regeneration are, and how jithendar.com moved to ISR with a cross-replica page cache in Next.js 16. |
| Slug | `ssg-isr-nextjs-jithendar-com` |
| Primary keyword | ISR in Next.js |
| Secondary keywords | SSG vs ISR; Next.js custom cache handler; ISR with multiple instances |
| Category | `devops-sre` (**placeholder**: no web-development category exists) |

## Facts the article relies on (check before publishing)

- Before: 36 `force-dynamic` routes; server render of an article ≈ 0.49 s per request (local production build).
  The live TTFB figures quoted earlier (homepage 1.03 s, `/blog` 0.60 s, article 0.48 s) were measured through the
  agent sandbox's HTTPS proxy, which adds 0.3–0.7 s, so they were removed from the article. Measure live TTFB from a
  real client (`curl -w %{time_starttransfer}`, PageSpeed Insights) before publishing.
- Live since #40 (2026-11-11 03:42 UTC): every public page answers `x-nextjs-cache: HIT`, `s-maxage=300`.
- After (local production build): first render 0.49 s, cache hits 5–9 ms; startup warm-up, edit/unpublish visibility,
  two-replica sync over Redis and draft-mode non-caching all verified by hand (`docs/PROGRESS.md`).
- Code excerpts are abridged from `cache-handler.mjs`, `src/lib/page-cache.ts`, `src/lib/warm.ts`,
  `src/lib/site-config/index.ts` and `src/app/blog/[slug]/page.tsx` at the commit that adds this file.
