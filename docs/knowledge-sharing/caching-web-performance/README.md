# Caching, SSG, ISR and image optimisation article

Status: **draft for author review, not published.** Written 2026-11-11 against jithendar.com `master` after #40
(SSG + ISR) and #41 (cache tuning).

| Asset | Location |
| --- | --- |
| Article | `content/blog/caching-isr-ssg-image-optimisation-nextjs.mdx` (`status: review`, no `publishedAt`) |
| Figures | 6 SVGs + 2× PNGs in `public/images/caching-web-performance/`; editable `.drawio` sources here in `diagrams/` |
| Featured image | `/images/caching-web-performance/caching-layers.png` (1440 × 1520) |
| Reading time | 15 min by the site's formula (`readingTimeMinutes`, 220 words/min) once the `<Todo>` is removed |

Figures: `python3 sites/jithendar.com/docs/knowledge-sharing/caching-web-performance/diagrams/build_diagrams.py` writes the `.drawio` files
and the SVGs (it reuses the RoboShop series' writer and checks that every label fits its box);
`CHROMIUM_PATH=/opt/pw-browsers/chromium python3 sites/jithendar.com/docs/knowledge-sharing/caching-web-performance/diagrams/render_png.py`
writes the PNGs (any Chromium; leave `CHROMIUM_PATH` unset if the project's Playwright has its own browser). The SVGs are
rendered by the builder, not exported by draw.io: after editing a `.drawio` file in draw.io, export it over the SVG.

## SEO and publishing metadata

| Field | Value |
| --- | --- |
| H1 (`title`) | Caching a Next.js Web Application: Layers, SSG, ISR and Image Optimisation in Practice |
| SEO title | Next.js Caching Guide: SSG, ISR and Image Optimisation |
| Slug | `caching-isr-ssg-image-optimisation-nextjs` |
| Primary keyword | Next.js caching |
| Secondary keywords | ISR vs SSG; Next.js image optimisation; cache invalidation multiple instances |
| Category | `devops-sre` (**placeholder**: no web-development category exists) |

**Overlap**: `content/blog/ssg-isr-nextjs-jithendar-com.mdx` (also `status: review`) covers the ISR part in less depth.
Publish one, or both as a series with this one as the overview (it already lists the other in `related`).

## Facts the article relies on (check before publishing)

- Server times from a standalone production build against PostgreSQL 18 (2026-11-11): article render ≈ 0.49 s, cache
  hit 5–9 ms, article Open Graph image 194 ms → 6 ms. Live TTFB was **not** measured from a real client (the agent
  sandbox's proxy adds 0.3–0.7 s): measure it and add it to "What it changed".
- Live site, 2026-11-11: every public page `x-nextjs-cache: HIT`; one cover image 860 KB original → 116 KB JPEG /
  86 KB WebP / 47 KB AVIF at 1200 px, 9 KB AVIF at 384 px, all `Cache-Control: public, max-age=31536000`; an article's
  HTML 1,148,742 bytes raw, 107,924 bytes Brotli.
- `stale-while-revalidate=86100` and the news-sitemap/OG-image caching assume #41 is deployed.
- Code excerpts are abridged from `cache-handler.mjs`, `src/lib/page-cache.ts`, `src/lib/warm.ts`,
  `src/lib/site-config/index.ts`, `src/components/ContentImage.tsx` and `next.config.ts`.
- Every `sources` URL answered 200 on 2026-11-11.
