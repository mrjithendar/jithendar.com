# System Design Evolution (two-part series)

Status: **drafts for author review, not published.** Written 2026-11-08 on branch `blog/system-design-evolution`, uncommitted.

| Part | File | Words* |
| --- | --- | --- |
| 1 | `content/blog/system-design-evolution-1990s-to-microservices.mdx` | ~3,400 |
| 2 | `content/blog/system-design-evolution-cloud-native-ai-2026.mdx` | ~3,500 |

\* Prose, headings and table cells; image alt text and front matter excluded. The brief allowed a split when one article would pass 4,000 words. Covering all 13 sections plus 9 figures in one piece would have run to about 7,000, so it is split. Publish both parts together: each links to the other, and Part 1's `related` list names Part 2.

Brief section → part: 1–5 and the timeline → Part 1; 6–13 and the FAQ → Part 2.

## SEO and publishing metadata

| Field | Part 1 | Part 2 |
| --- | --- | --- |
| H1 (`title`) | System Design from the 1990s to 2026, Part 1: From Client-Server Applications to Microservices | System Design from the 1990s to 2026, Part 2: Cloud-Native, AI-Native and One Shop Built Three Times |
| SEO title | System Design Evolution, Part 1: 1990s to Microservices (55) | System Design Evolution, Part 2: Cloud-Native and AI in 2026 (60) |
| Meta description | 158 characters, see `seoDescription` | 155 characters, see `seoDescription` |
| Slug | `system-design-evolution-1990s-to-microservices` | `system-design-evolution-cloud-native-ai-2026` |
| Open Graph title / description | `socialTitle` / `socialDescription` in front matter | same |
| Category / type | `devops-sre` / `analysis` | `devops-sre` / `analysis` |
| Cover | `system-design-timeline.png` (1922×1174) | `2026-ai-native-architecture.png` (1722×1638) |

The brief's alternative title, "System Design Then vs Now: 35 Years of Software Architecture Evolution", is used (with the part number) as the Part 1 `socialTitle`.

**Keywords placed naturally.** Primary: *system design evolution* (both SEO titles and descriptions, Part 1 intro, Part 2 FAQ). Secondary: *1990s vs 2026* (Part 2 comparison section), *history of software architecture*, *monolith vs microservices* (Part 1 table), *client-server architecture* (Part 1 section, FAQ), *evolution of distributed systems* (Part 1 2000s section), *cloud-native architecture*, *modern system design*, *AI-native system architecture* (Part 2), *system design for beginners* (definitions in both parts, FAQ).

**Featured image concept (if you want a designed cover rather than a diagram).** Split frame on a white background. On the left, a beige 1992 desktop PC with a CRT, a tape reel and a server tower, drawn in thin slate lines. On the right, the same footprint redrawn as a grid of small rounded service boxes with dashed connections and one violet "AI" node. A single horizontal arrow labelled 1992 → 2026 runs across the middle. Use the site's palette (indigo, emerald, amber, violet); no text beyond the two years. 1200×630 for social cards.

## Structured data

The site already emits `Article` / `BlogPosting` JSON-LD for every post (see `src/lib/seo`). It does **not** emit `FAQPage` (checked 2026-11-07, see the DevOps interview article notes), so the FAQ below is reference only. Google currently shows FAQ rich results only for a limited set of sites, so adding `FAQPage` support is optional.

```json
{
  "@context": "https://schema.org",
  "@type": "BlogPosting",
  "headline": "System Design from the 1990s to 2026, Part 1: From Client-Server Applications to Microservices",
  "description": "How system design moved from mainframes and client-server apps to the web, SOA, the cloud and microservices, and why each change happened. Part 1 of 2.",
  "image": "https://jithendar.com/images/system-design-evolution/system-design-timeline.png",
  "author": { "@type": "Person", "name": "Jithendar Dharmapuri", "url": "https://jithendar.com/about" },
  "publisher": { "@type": "Organization", "name": "Jithendar.com" },
  "mainEntityOfPage": "https://jithendar.com/blog/system-design-evolution-1990s-to-microservices",
  "articleSection": "DevOps, SRE & Platform Engineering",
  "isPartOf": { "@type": "CreativeWorkSeries", "name": "System Design from the 1990s to 2026" },
  "keywords": "system design evolution, history of software architecture, client-server architecture, monolith vs microservices, evolution of distributed systems"
}
```

```json
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    { "@type": "Question", "name": "What is system design evolution?", "acceptedAnswer": { "@type": "Answer", "text": "The way software architecture changed as constraints changed: from centralised mainframes and client-server applications in the early 1990s, to three-tier web applications, distributed systems and SOA in the 2000s, to cloud, containers and microservices in the 2010s, and to platform engineering and optional AI components in the 2020s." } },
    { "@type": "Question", "name": "Is a monolith still a good choice in 2026?", "acceptedAnswer": { "@type": "Answer", "text": "Often, yes. A well-structured modular monolith is easier to build, test, deploy and debug than microservices, and one database transaction keeps data consistent. Microservices pay off when many teams need to deploy independently or parts of the system have very different scaling needs." } },
    { "@type": "Question", "name": "What is the difference between client-server and three-tier architecture?", "acceptedAnswer": { "@type": "Answer", "text": "In two-tier client-server, a desktop program holds the user interface and much of the business logic and talks directly to a database. Three-tier architecture separates presentation, business logic and data, so each tier can be secured and scaled on its own." } },
    { "@type": "Question", "name": "Does every modern application need AI?", "acceptedAnswer": { "@type": "Answer", "text": "No. AI components such as RAG, agents and MCP tools are optional capabilities. Use them where they add clear value, and keep authorization, prices, payments and other writes in deterministic application code." } },
    { "@type": "Question", "name": "What should I learn first for system design interviews?", "acceptedAnswer": { "@type": "Answer", "text": "The fundamentals: latency, throughput, consistency, availability, data modelling and caching. Then how they apply to distributed systems: replication, partitioning, queues, idempotency, observability and cost." } }
  ]
}
```

## Internal links (each returned HTTP 200 on 2026-11-08)

`/blog/kubernetes-history-origins-evolution-milestones`, `/blog/roboshop-ai-microservices-architecture`, `/blog/learning-terraform-real-project-tools-repository`, `/blog/four-ai-systems-one-cluster`, `/blog/roboshop-ai-architecture`, `/blog/roboshop-ai-mcp-server`, `/blog/devops-interview-preparation-guide`. Part 1 ↔ Part 2 links resolve in the content checker and go live when both are published. `/blog/deploy-nextjs-kubernetes-github-actions` returned 404 and is not linked.

## Figures

Nine draw.io diagrams. The sources are in `diagrams/*.drawio` and open in draw.io desktop or app.diagrams.net. The site images in `public/images/system-design-evolution/` are **exported by the draw.io desktop CLI 32.6.10** (`export.sh`), SVG for articles and 2× PNG for covers. `build_diagrams.py` generates the .drawio files from one layout model (shared palette, legend, shapes and arrow styles) and fails if a label does not fit its box. After hand-editing a .drawio file, rerun only `export.sh`.

| Figure | File | Part |
| --- | --- | --- |
| 1 Two-tier client-server, failure points | `1990s-client-server` | 1 |
| 2 Three-tier web shop | `late-1990s-three-tier-web` | 1 |
| 3 Cloud-native microservices | `2010s-cloud-native-microservices` | 1 |
| 4 Timeline 1989–2026 | `system-design-timeline` | 1 |
| 5 AI-native architecture | `2026-ai-native-architecture` | 2 |
| 6–8 One shop in 1992, 2012, 2026 (same rows) | `retail-1992-client-server`, `retail-2012-web-tier`, `retail-2026-cloud-native` | 2 |
| 9 RoboShop AI on mk4 | `roboshop-ai-on-mk4` | 2 |

Every figure's alt text is in the article Markdown and describes the full flow, not just the title. The SVGs use a fixed light theme (`--theme light`) with a white background, matching the site's other diagrams.

## Where each fact came from

| Claim | Source (checked 2026-11-08) |
| --- | --- |
| System/360 launched 7 April 1964 | IBM history page |
| Sabre 7,500 reservations/hour by the mid-1960s; 90 minutes to seconds | IBM history page (quoted sentence) |
| Web proposal March 1989; Web software public domain 30 April 1993 | CERN short history; CERN timeline |
| CGI in use since 1993 | RFC 3875, section 1 |
| Apache 0.6.2 April 1995; 1.0 on 1 December 1995 | httpd.apache.org ABOUT_APACHE |
| Java announced 23 May 1995 at SunWorld | Computer History Museum Revolution exhibit (search result); several secondary sources agree |
| HTTP/1.0 RFC 1945 (May 1996) | RFC Editor |
| SOAP 1.1 W3C Note, 8 May 2000 | W3C TR URL |
| REST in Fielding's 2000 dissertation | UCI dissertation page |
| GFS SOSP 2003, MapReduce OSDI 2004, Bigtable OSDI 2006, Borg EuroSys 2015 | Google Research publication pages (venue text read) |
| Dynamo SOSP October 2007; shopping-cart motivation | All Things Distributed post (text read) |
| CAP at PODC 2000; Gilbert & Lynch proof; Brewer quote | InfoQ "CAP Twelve Years Later" (quote matched word for word); MIT PDF |
| S3 13 March 2006; EC2 beta 24 August 2006 | AWS What's New posts |
| Twelve-Factor written by Adam Wiggins | 12factor.net footer |
| Docker first shown at PyCon on 15 March 2013 | Docker blog "Nine Years YOUNG" (search result text) |
| Kubernetes first commit 6 June 2014; 1.0 and CNCF 21 July 2015 | Kubernetes blog; sources table in `../kubernetes-history/README.md` |
| OpenTelemetry from the OpenTracing + OpenCensus merger, 2019 | opentelemetry.io; CNCF blog 2019-05-21 |
| Argo graduated in the CNCF 6 December 2022 | CNCF project page |
| RAG paper submitted 22 May 2020 | arXiv 2005.11401 |
| MCP introduced 25 November 2024 | Anthropic announcement |

**RoboShop AI (roboshop-ai `02a4478`, mk4 checked read-only 2026-11-08):**

| Claim | Evidence |
| --- | --- |
| 11 app Deployments/StatefulSets, all 1 replica; Argo apps `roboshop-*` Synced/Healthy | `kubectl -n roboshop-ai get deploy,statefulset`; `-n argocd get applications` |
| Traefik ingress `/roboshop` → web, prefix stripped | `argocd-minikube/apps/routing/`; live ingress class `traefik` |
| NGINX proxies `/api/*`, `/moks/*`; `/api/chat` returns 403 | `services/web/nginx/snippets/routes.conf` |
| ai-gateway FastAPI 0.159.1, JSON ledger with one writer, outbox via Pika with publisher confirms, Idempotency-Key | `services/ai-gateway/README.md`, `requirements.txt` |
| PostgreSQL ledger exists but is off | `lifecycle.py` `COMMERCE_BACKEND` defaults to `json`; deployment sets no backend |
| user (Waitress, MongoDB), cart (Waitress, Redis, Lua CAS, 7-day expiry), catalogue (Node, read-only MongoDB), payment (Node built-ins, Razorpay, test mode), shipping (Spring Boot, PostgreSQL, dedupes event IDs), currency (Go stdlib, ECB hourly) | each service README and dependency file |
| kafka-bridge acks RabbitMQ only after Kafka confirms; no Kafka in checkout | `services/kafka-bridge/README.md` |
| mcp-server FastMCP 4.1.3 on MCP SDK 2.3.0, ClusterIP, NetworkPolicy, caller's session | `services/mcp-server/README.md`; live `networkpolicy mcp-server-clients` |
| Moks: LangGraph START → search_catalogue → ground_evidence → generate_answer → END; no MCP | `services/moks/agent.py`; mcp-server README |
| No model configured on mk4 | `GET https://jithendar.com/roboshop/moks/available` → `"aiConfigured": false` |
| `OTEL_SDK_DISABLED=true` on mk4, no per-Deployment override | ConfigMap `roboshop-config`; Deployment env |
| No HPAs | `kubectl get hpa` → none |

Historical figures are labelled "illustration". Product names inside them (Oracle7, DB2, NetWare, Apache, Memcached, MySQL) are examples of what was available in the era, not claims about one system.

## Technical accuracy checklist

- [x] Every dated milestone has a primary or first-party source above; no undated claim is presented as a date.
- [x] The one direct quotation (Brewer, 2012) matches the source word for word.
- [x] RoboShop AI components described only as verified; "not enabled" items (model provider, PostgreSQL ledger, tracing, public MCP route) are stated as such.
- [x] No code blocks, so there is no code to run. Figures carry no version numbers that could go stale, except the RoboShop figure, which is dated.
- [x] `tests/content.test.ts`, `tests/links.test.ts`, `tests/editor-workflow.test.ts` pass; the full `npm test` run (470 tests) passed except one editor-fidelity case, which was fixed and rerun green. `npm run lint` and `npm run typecheck` pass.
- [ ] Rendered-page check in a browser (not done: no local database for the article route).
- [ ] Author review of opinions: "ESB became a bottleneck" is labelled a common criticism; "for a team of five, Version B is usually better" is the author's judgement.
- [ ] Recheck the two date-sensitive RoboShop facts (no model configured, tracing off) on publish day.

## Open items for the author

1. Read both parts, add your own commentary, then set `status: published` and `publishedAt` on both at the same time. Live posts are in Postgres: paste the bodies into the CMS editor, or use `npm run push-post` (see `publishJithendar.sh`) with `--dry-run` first.
2. Upload the nine SVGs (and the two cover PNGs) to the site if the CMS does not serve `/images/system-design-evolution/` from the image.
3. The Java date comes from a Computer History Museum page found via search; oracle.com returned 403. Several independent sources agree on 23 May 1995.
4. Decide whether to keep `devops-sre` as the category for Part 2 or move it to `ai-engineering`.

## LinkedIn post

> In 1992, shipping a new version of a bank's loan application meant walking from desk to desk with installation disks. In 2026, it means merging a pull request.
>
> I wrote a two-part series on how system design got from there to here: mainframes and fat clients, the three-tier web, SOA and Dynamo, Docker and Kubernetes, and now GitOps, RAG, agents and MCP. It covers *why* each change happened, not just what changed.
>
> A few things I found while writing it:
> • Brewer himself called the "2 of 3" reading of CAP misleading, back in 2012.
> • Amazon's Dynamo was designed around one requirement: a customer must always be able to add to their cart.
> • A well-built modular monolith is still the right answer for most small teams.
>
> Part 2 builds the same online shop three times, in 1992, 2012 and 2026, with draw.io diagrams for each. It then checks my own RoboShop AI project against its live cluster, including the parts that aren't switched on yet.
>
> Part 1: https://jithendar.com/blog/system-design-evolution-1990s-to-microservices
> Part 2: https://jithendar.com/blog/system-design-evolution-cloud-native-ai-2026
>
> #SystemDesign #SoftwareArchitecture #DistributedSystems #CloudNative #Kubernetes #AIEngineering
