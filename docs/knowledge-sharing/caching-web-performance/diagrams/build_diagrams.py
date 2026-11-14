#!/usr/bin/env python3
"""Figures for the article "Caching, SSG, ISR and image optimisation on jithendar.com": one editable .drawio file per
figure and a matching SVG.

Reuses the layout, palette and draw.io writer of the RoboShop AI series (sites/jithendar.com/docs/knowledge-sharing/roboshop-ai/diagrams).
Run from www/. The SVG is rendered here, not exported by draw.io: if a .drawio file is edited in draw.io, re-export it
over the SVG. PNG copies: render_png.py (Playwright + Chromium).
Facts follow the implementation of #40/#41 (cache-handler.mjs, src/lib/page-cache.ts, src/lib/warm.ts, next.config.ts).
"""
import importlib.util
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE.parents[3] / "public" / "images" / "caching-web-performance"
spec = importlib.util.spec_from_file_location("series_diagrams", HERE.parents[1] / "roboshop-ai" / "diagrams" / "build_diagrams.py")
series = importlib.util.module_from_spec(spec)
sys.modules["series_diagrams"] = series
spec.loader.exec_module(series)
Page, Sequence = series.Page, series.Sequence


def layers():
    p = Page("caching-layers", "Caching layers", 720, 760, "The caching layers of jithendar.com, from the browser to the database",
             "A request first meets the browser cache, which keeps Next.js static files and optimised images for a year. An optional CDN "
             "could honour s-maxage=300 but is not deployed. The Istio ingress terminates TLS and compresses responses. In the Next.js pod "
             "the proxy runs first, then pages come from the in-memory ISR page cache in 5 to 9 milliseconds; a miss renders the page in "
             "about half a second from the per-process content cache and PostgreSQL. Images go to the next/image optimiser, which encodes "
             "AVIF or WebP with sharp, keeps the result on disk for 30 days and reads the original from Cloudflare R2 only on a miss. The "
             "cache bus over Valkey clears the page cache on every pod when content changes.")
    p.zone("Reader's device", 15, 12, 345, 100)
    p.zone("Edge (optional)", 375, 12, 330, 100)
    p.zone("Cluster ingress", 15, 124, 690, 88)
    p.zone("Next.js pod (2 replicas)", 15, 224, 690, 420)
    p.zone("Data", 15, 656, 690, 92, "br")
    p.node("browser", "browser", 30, 36, 315, 64, "Browser cache", "/_next/static/*: 1 year, immutable", "optimised images: 1 year · icon: 1 day")
    p.node("cdn", "absent", 390, 36, 300, 64, "CDN (not deployed)", "could honour s-maxage=300", "stale-while-revalidate ≤ 1 day")
    p.node("istio", "edge", 30, 148, 660, 52, "Istio ingress gateway", "TLS, Brotli/zstd compression (an article: 1.1 MB of HTML → 108 KB)")
    p.node("proxy", "gateway", 30, 248, 315, 64, "Next.js proxy (middleware)", "410 Gone, redirects, maintenance mode", "runs before the cache")
    p.node("isr", "service", 30, 346, 315, 80, "ISR page cache (in memory)", "cache-handler.mjs, ≤ 64 MB, LRU", "hit: 5–9 ms · refresh after 300 s",
           "cleared at once when content changes")
    p.node("render", "gateway", 30, 460, 315, 64, "Render on a miss", "React Server Components + MDX", "≈ 0.49 s for an article")
    p.node("content", "store", 30, 558, 315, 64, "Content cache (per process)", "30 s TTL + bus invalidation")
    p.node("imgopt", "service", 390, 346, 300, 80, "Image optimiser (next/image)", "sharp: AVIF / WebP, quality 75", "widths 96–1920 px",
           "disk cache 30 days, ≤ 200 MB")
    p.node("bus", "bus", 390, 558, 300, 64, "Cache bus (Valkey pub/sub)", "{kind, origin} messages only", "every pod clears its page cache")
    p.node("pg", "store", 30, 680, 315, 52, "PostgreSQL", "posts, pages, settings, categories")
    p.node("r2", "external", 390, 680, 300, 52, "Cloudflare R2", "original uploads (e.g. an 860 KB JPEG)")
    p.edge("browser", "istio", b_at=(187.5 - 30) / 660)
    p.edge("cdn", "istio", b_at=(540 - 30) / 660, kind="dashed")
    p.edge("istio", "proxy", a_at=(187.5 - 30) / 660)
    p.edge("proxy", "isr", label="pages, feeds, sitemap", dx=78)
    p.edge("proxy", "imgopt", a_side="r", b_side="t", via=[(540, 280)], label="/_next/image", dy=-10)
    p.edge("isr", "render", label="miss: render + store", dx=74)
    p.edge("render", "content")
    p.edge("content", "pg", label="reload after 30 s or a change", dx=104)
    p.edge("imgopt", "r2", a_side="r", b_side="r", via=[(700, 386), (700, 706)], label="miss: original", dx=-52, dy=-26)
    p.edge("bus", "isr", kind="async", a_side="l", b_side="r", via=[(368, 590), (368, 386)], label="clear", dx=30, t=0.1)
    return p


def modes():
    p = Page("rendering-modes", "SSG, ISR, dynamic", 720, 470, "Three ways to make the HTML of a page",
             "SSG builds every page once with next build and serves the files until the next build. ISR serves pages from a cache and "
             "re-renders a page in the background after its revalidate time or at once when its data changes. Dynamic rendering builds "
             "the page from the database on every request, which is what jithendar.com did before: about half a second of server work "
             "for every visit.")
    p.zone("SSG: static site generation", 15, 12, 690, 132)
    p.zone("ISR: incremental static regeneration (jithendar.com now)", 15, 160, 690, 150)
    p.zone("Dynamic rendering (jithendar.com before)", 15, 326, 690, 132)
    p.node("b1", "gateway", 30, 52, 190, 64, "next build", "renders every page once")
    p.node("f1", "store", 265, 52, 190, 64, "HTML files", "frozen until the next build")
    p.node("r1", "browser", 500, 52, 190, 64, "Every request", "served as is: fastest", "new content needs a build")
    p.node("b2", "gateway", 30, 196, 190, 64, "First visit or warm-up", "renders the page once")
    p.node("f2", "service", 265, 196, 190, 64, "Page cache", "in memory, per pod", "≤ 64 MB, LRU")
    p.node("r2", "browser", 500, 196, 190, 64, "Every request", "served from memory", "5–9 ms")
    p.node("b3", "browser", 30, 366, 190, 64, "Every request", "no reuse between visitors")
    p.node("f3", "gateway", 265, 366, 190, 64, "PostgreSQL + render", "MDX, React, HTML", "≈ 0.49 s each time")
    p.node("r3", "browser", 500, 366, 190, 64, "Response", "Cache-Control: private,", "no-store")
    for a, b in (("b1", "f1"), ("f1", "r1"), ("b2", "f2"), ("f2", "r2"), ("b3", "f3"), ("f3", "r3")):
        p.edge(a, b, a_side="r", b_side="l")
    p.edge("f2", "b2", kind="async", a_side="b", b_side="b", via=[(360, 288), (125, 288)], label="after 300 s or on change: re-render", dy=12)
    return p


def lifecycle():
    p = Page("isr-request-lifecycle", "ISR request lifecycle", 720, 640, "One page over time: a miss, hits, then a background refresh",
             "The first request misses the page cache, renders the page from PostgreSQL in about half a second and stores it. The next "
             "requests are answered from memory in milliseconds. After 300 seconds the entry is stale: the next visitor still gets it at "
             "once, while Next.js re-renders the page in the background and replaces the entry. A change in the admin clears the cache "
             "before that, so the next request renders the new version.")
    s = Sequence(p, [("v", "browser", "Visitor", ""), ("n", "gateway", "Next.js server", ""), ("c", "service", "ISR page cache", "in memory"),
                     ("d", "store", "PostgreSQL", "")], bottom=624, w=150)
    s.message(100, "v", "n", "GET /blog/my-post (first visit)")
    s.message(132, "n", "c", "get → miss")
    s.message(164, "n", "d", "read the post, render")
    s.message(208, "n", "c", "set (generation g)", kind="write")
    s.message(240, "n", "v", "200, MISS, ≈ 0.49 s", kind="dashed")
    s.message(292, "v", "n", "GET /blog/my-post")
    s.message(324, "n", "c", "get → hit")
    s.message(356, "n", "v", "200, HIT, 5–9 ms", kind="dashed")
    s.self_note(384, "c", "300 s later\nthe entry is stale", 44, 176, kind="absent")
    s.message(468, "v", "n", "GET /blog/my-post")
    s.message(500, "n", "v", "200, the stale copy, at once", kind="dashed")
    s.message(532, "n", "d", "re-render in the background")
    s.message(576, "n", "c", "set: fresh entry", kind="write")
    return p


def invalidation():
    p = Page("publish-invalidation", "Publish across replicas", 720, 600, "A publish on one pod reaches every pod's page cache",
             "The editor saves an article on pod A. Pod A writes PostgreSQL and bumps its page-cache generation, which makes every cached "
             "page stale at once, then publishes a content message on Valkey. Pod B receives it and bumps its own generation. The next "
             "request on either pod renders the new version. Ten seconds later each pod's warm-up renders every page in the sitemap "
             "again, so readers get cached pages.")
    s = Sequence(p, [("e", "browser", "Editor", "admin"), ("a", "gateway", "Pod A", ""), ("v", "bus", "Valkey", "pub/sub"),
                     ("b", "gateway", "Pod B", ""), ("r", "browser", "Reader", "")], bottom=584, w=120)
    s.message(100, "e", "a", "save the article", kind="write")
    s.self_note(124, "a", "PostgreSQL write\ngeneration + 1", 44, 150)
    s.message(208, "a", "v", "publish {kind: content}", kind="async")
    s.message(240, "v", "b", "message", kind="async")
    s.self_note(264, "b", "generation + 1\n(no request in progress)", 44, 176)
    s.message(348, "r", "b", "GET /blog")
    s.message(380, "b", "r", "MISS: the new version", kind="dashed")
    s.self_note(408, "a", "+10 s: warm-up\nrenders the sitemap", 44, 150, kind="service")
    s.self_note(408, "b", "+10 s: warm-up\nrenders the sitemap", 44, 150, kind="service")
    s.message(508, "r", "b", "GET /blog/my-post")
    s.message(540, "b", "r", "HIT, 5–9 ms", kind="dashed")
    return p


def images():
    p = Page("image-pipeline", "Image pipeline", 720, 600, "From an 860 KB upload to a 9 KB card image",
             "An author uploads an image; the site checks its real type and size and stores the original in Cloudflare R2. A reader's "
             "browser picks a width from the srcset and says which formats it accepts. The next/image optimiser reads the original once, "
             "resizes and encodes it with sharp, keeps the result on disk for 30 days and sends it with a one-year cache lifetime. Measured "
             "on the live site: 860 KB original, 116 KB JPEG, 86 KB WebP or 47 KB AVIF at 1200 pixels, 9 KB AVIF at 384 pixels.")
    p.zone("Upload (once)", 15, 12, 690, 100)
    p.zone("Every image request", 15, 128, 690, 300)
    p.zone("Measured on jithendar.com (one cover image)", 15, 444, 690, 144)
    p.node("author", "browser", 30, 36, 190, 64, "Author", "admin media library")
    p.node("check", "gateway", 265, 36, 190, 64, "Upload check", "real type from the bytes", "≤ 10 MB")
    p.node("r2", "external", 500, 36, 190, 64, "Cloudflare R2", "original kept as uploaded")
    p.node("reader", "browser", 30, 176, 190, 92, "Reader's browser", "srcset + sizes: picks a width", "Accept: image/avif, webp",
           "lazy, async decoding")
    p.node("opt", "service", 265, 176, 190, 92, "next/image optimiser", "sharp: resize + encode", "AVIF → WebP → original", "quality 75")
    p.node("disk", "store", 500, 176, 190, 92, "Optimised-image cache", "pod disk, 30 days", "≤ 200 MB, per pod")
    p.node("hdr", "browser", 265, 330, 425, 52, "Response", "Cache-Control: public, max-age=31536000 · the browser asks once")
    p.node("m1", "external", 30, 480, 150, 92, "Original", "JPEG", "860 KB")
    p.node("m2", "store", 200, 480, 150, 92, "1200 px", "JPEG 116 KB", "WebP 86 KB", "AVIF 47 KB")
    p.node("m3", "service", 370, 480, 150, 92, "384 px (cards)", "AVIF 9 KB", "≈ 1 % of the", "original")
    p.node("m4", "gateway", 540, 480, 150, 92, "Saving", "≈ 95 % at 1200 px", "AVIF vs the upload")
    p.edge("author", "check", a_side="r", b_side="l", kind="write")
    p.edge("check", "r2", a_side="r", b_side="l", kind="write")
    p.edge("reader", "opt", a_side="r", b_side="l", label="w=1200", dy=-12)
    p.edge("opt", "disk", a_side="r", b_side="l", label="hit", dy=-12)
    p.edge("r2", "opt", a_side="b", b_side="t", a_at=0.3, via=[(557, 140), (360, 140)], kind="dashed", label="miss: original", dy=-10, t=0.3)
    p.edge("opt", "hdr", a_at=0.5, b_at=(360 - 265) / 425)
    p.edge("hdr", "reader", a_side="l", b_side="b", via=[(125, 356)], kind="dashed", label="AVIF 47 KB", dx=-40)
    return p


def warmup():
    p = Page("pod-warmup", "Pod start and warm-up", 720, 520, "Static generation without a build-time database",
             "The build has no database, so pages are not prerendered at build time. When a pod starts it runs migrations, connects the "
             "cache bus and warms the content cache. Once it answers its health check, the warm-up reads the pod's own sitemap and requests "
             "every page, two at a time, so the page cache is full before readers arrive. When the cache is cleared, the warm-up runs again "
             "ten seconds later; a burst of edits leads to one pass.")
    p.node("start", "external", 30, 30, 200, 64, "Pod starts", "image from CI, no database", "used at build time")
    p.node("init", "gateway", 260, 30, 200, 64, "instrumentation.ts", "migrations, cache bus,", "content cache warm-up")
    p.node("ready", "gateway", 490, 30, 200, 64, "Server ready", "GET /api/health → 200")
    p.node("sitemap", "service", 490, 150, 200, 64, "Warm-up", "GET /sitemap.xml on 127.0.0.1", "+ feeds, search index")
    p.node("render", "service", 260, 150, 200, 64, "Render every page", "2 at a time", "≈ 0.5 s each on a cold pod")
    p.node("cache", "store", 30, 150, 200, 64, "Page cache full", "readers get HITs", "from the first request")
    p.node("clear", "bus", 30, 300, 200, 64, "Cache cleared", "publish, edit, settings", "(this pod or another)")
    p.node("debounce", "absent", 260, 300, 200, 64, "Wait 10 s", "more clears restart the timer")
    p.node("again", "service", 490, 300, 200, 64, "Warm-up again", "one pass per burst")
    p.node("metrics", "browser", 140, 420, 440, 72, "Prometheus + Grafana", "jithendar_page_cache_{hits,misses,clears}_total",
           "jithendar_page_warmups_total, _duration_seconds")
    p.edge("start", "init", a_side="r", b_side="l")
    p.edge("init", "ready", a_side="r", b_side="l")
    p.edge("ready", "sitemap")
    p.edge("sitemap", "render", a_side="l", b_side="r")
    p.edge("render", "cache", a_side="l", b_side="r", kind="write")
    p.edge("cache", "clear", kind="async")
    p.edge("clear", "debounce", a_side="r", b_side="l")
    p.edge("debounce", "again", a_side="r", b_side="l")
    p.edge("again", "sitemap", a_side="t", b_side="b", label="same pass", dx=36)
    p.edge("again", "metrics", a_at=0.5, b_side="r", via=[(590, 456)], kind="dashed")
    return p


FILES = {"caching-layers": layers, "rendering-modes": modes, "isr-request-lifecycle": lifecycle, "publish-invalidation": invalidation,
         "image-pipeline": images, "pod-warmup": warmup}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    built = []
    for name, make in FILES.items():
        page = make()
        for e in page.edges:
            for x, y in e["points"]:
                if not (0 <= x <= page.w and 0 <= y <= page.h):
                    raise SystemExit(f"{page.figure}: edge {e['id']} leaves the page")
        for n in page.nodes.values():
            if n["x"] < 0 or n["y"] < 0 or n["x"] + n["w"] > page.w or n["y"] + n["h"] > page.h:
                raise SystemExit(f"{page.figure}: {n['id']} leaves the page")
        mxfile = ET.Element("mxfile", host="app.diagrams.net", agent="build_diagrams.py", version="24.7.17", type="device")
        mxfile.append(series.page_xml(page, 0))
        ET.indent(mxfile)
        (HERE / f"{name}.drawio").write_bytes(ET.tostring(mxfile, encoding="utf-8", xml_declaration=False))
        (OUT / f"{page.figure}.svg").write_text(series.page_svg(page), encoding="utf-8")
        built.append((page.figure, page.w, page.h))
    (HERE / "figures.txt").write_text("".join(f"{f} {w} {h}\n" for f, w, h in built), encoding="utf-8")
    print("\n".join(f"{f}: {w}×{h}" for f, w, h in built))


if __name__ == "__main__":
    main()
