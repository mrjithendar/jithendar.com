# Content audit and update plan

Audit date: 2026-11-01. Status: **Batch 1 drafts ready; waiting for editorial review.** Nothing here has been published.

This repository is public, so this file holds no account IDs, private addresses or credentials.

## 1. How the audit was done

- **Live pages** were fetched from `jithendar.com`, including the sitemap, feed, robots, metadata and JSON-LD.
- **Source of truth:** published posts live in **PostgreSQL**. `content/*.mdx` is only imported by `/setup`, or per file as a draft, and an import refuses a slug that already exists. Editing a file does not change a live post.
- **Sources checked:** `roboshop-ai` c81e85a, `tools` 5ea85b7 plus its uncommitted `deploy/` move, `moks` 9c150e9, and this repository at 6bc2304.
- **Live systems:** read-only `kubectl`, `aws eks`, `dig` and `curl` checks against both clusters and the public site on 2026-11-01.
- **Priorities come from content inspection only.** No Search Console or analytics data was available, and the oldest post is five days old, so there is no evidence of search performance for any URL.

## 2. Inventory

Dates are from live JSON-LD (IST). No post has had a substantive update, so `dateModified` is absent everywhere.

| # | Live URL | Topic | Published | Reader and intent | Main problems | Action |
|---|---|---|---|---|---|---|
| 1 | [/projects/nextjs-site-on-kubernetes](https://jithendar.com/projects/nextjs-site-on-kubernetes) | How this site runs | 29 Oct, 20:25 | Engineers; "how is a self-hosted Next.js platform built" | H1 belongs to a different article. Claims Cloudflare CDN, DDoS protection and a hidden origin, all false. Stale CI and Turnstile claims | **Rewrite: drafted** |
| 2 | [/blog/deploy-roboshop-ai-amazon-eks](https://jithendar.com/blog/deploy-roboshop-ai-amazon-eks) | EKS tutorial | 30 Oct, 10:15 | Intermediate; "deploy microservices on EKS" | Follows a stack that was never built. All 3 repo links are 404, every `deploy/eks/*` command is gone, and the cover image names absent components | **Rewrite: drafted** |
| 3 | [/blog/roboshop-ai-microservices](https://jithendar.com/blog/roboshop-ai-microservices) | Boundaries and trade-offs | 29 Oct, 18:32 | Intermediate; "microservices architecture example" | Describes Traefik and Minikube. Meta description repeats the title. SEO title differs from H1. Overlaps #4 | **Rewrite and absorb #4: drafted** |
| 4 | [/blog/roboshop-ai-microservices-architecture](https://jithendar.com/blog/roboshop-ai-microservices-architecture) | Overview and old EKS plan | 27 Oct, 16:53 | Same as #3 | Says EKS is "switched off". Links to a 404 live demo. Competes with #3 and #5 | **Merge into #3** |
| 5 | [/blog/roboshop-ai-eks-system-design](https://jithendar.com/blog/roboshop-ai-eks-system-design) | EKS design | 30 Oct, 10:12 | Intermediate to senior; "EKS architecture with Istio" | Title promises Karpenter, KEDA and Gatekeeper. None exist on the cluster. Figures show `shipping-worker`, which does not exist. Its 2 repo links are 404 | **Substantial rewrite** |
| 6 | [/projects/roboshop-ai](https://jithendar.com/projects/roboshop-ai) | Project hub | 27 Oct, 16:51 | Portfolio visitors | Thin. Lists `frontend` and `nginx`, which are now `web`. No link to current state | **Substantial rewrite as a short hub** |
| 7 | [/blog/moks-rag-and-skills-design](https://jithendar.com/blog/moks-rag-and-skills-design) | RAG and skills design | 31 Oct, 20:53 | Senior; "RAG design for SRE agents" | Strongest piece. Reviewed at 9b94516, and "What has been proven" predates the EKS move. Closing Q&A reads as interview prep | **Update: drafted** |
| 8 | Not live (404): `content/blog/deploy-nextjs-kubernetes-github-actions.mdx` | Old site tutorial | Never | n/a | Describes a CI deploy job that no longer exists. Useful parts moved into #1 | **Retire (archive the file)** |

### Overlap

- **#3, #4 and #5** all target "RoboShop AI microservices/architecture". After the merge: #3 owns the application architecture, #5 owns the EKS design, #2 owns the how-to.
- **#1 and #8** cover the same site. The live post already shows #8's title on #1's body, which is how the wrong H1 happened.
- **#2 and #5** are a healthy pair as long as each links to the other and neither repeats the other.

### Findings across articles

| Finding | Evidence | Affected |
|---|---|---|
| The shop moved to EKS and off the apex | `jithendar.com/roboshop` is 404; `eks.jithendar.com/roboshop/` is 200 with `server: istio-envoy` | #2 to #6 |
| Gatekeeper, KEDA, Karpenter and External Secrets are absent | No such CRDs on the cluster; `argocd-eks/README.md` calls them a different design | #2, #5 |
| Moks shopping assistant not deployed on EKS | No Deployment, no `roboshop-demo-moks` Application, chat returns 502 | #2 to #6 |
| Mesh is rehearsing, not enforcing | PeerAuthentication `PERMISSIVE`; all 15 AuthorizationPolicies have `dry-run: true` | #2, #5 |
| Tracing is off on EKS | `OTEL_SDK_DISABLED=true`; no `observability` namespace | #3, #5 |
| Cloudflare proxy claims are false | Apex resolves directly to the origin, no `cf-ray` header, [DNS-only per Cloudflare's docs](https://developers.cloudflare.com/dns/proxy-status/) | #1, plus any copy elsewhere |
| Tutorial asks readers to fork proprietary code | `roboshop-ai/LICENSE` grants no rights | #2 |
| Weak cover alt text | Live alts include "roboshop" and "minikube to eks aws" | #1 to #3, likely others |

## 3. Priority order

1. **Batch 1 (drafted):** #1, #2, #3 with the merge of #4. These hold the false or unusable public claims.
2. **Batch 2:** #5, because its title and body promise a stack that does not exist, then #6.
3. **Batch 3:** #7, then retire #8.

Until Batch 2 ships, #5 is the most misleading live page. A short correction at the top is worth adding now if Batch 2 will take time.

## 4. Per-article SEO and links (Batch 1)

Frontmatter cannot hold SEO overrides, so set these in the post editor. Keep every slug.

### /blog/deploy-roboshop-ai-amazon-eks

| Field | Value |
|---|---|
| Primary intent | Deploy a multi-service app on EKS, in a safe order |
| Title / H1 | Deploy a microservices app on Amazon EKS with Terraform, Argo CD and Istio |
| SEO title | Deploy Microservices on Amazon EKS with Argo CD and Istio |
| Meta description | A checked EKS walkthrough from RoboShop AI: Terraform, a remote Argo CD hub, an NLB in front of Istio, a safe mesh rollout, failure modes and teardown. |
| Social title | How to deploy microservices on EKS without breaking the order |
| Cover | **Replace the image.** The current one is labelled with Gatekeeper, Karpenter and KEDA, which this article no longer covers |
| Links added | System design, microservices article, project hub, live demo. Istio, EKS, Let's Encrypt and AWS pricing docs |
| Links removed | All `deploy/eks/*` links (404) |

### /projects/nextjs-site-on-kubernetes

| Field | Value |
|---|---|
| Primary intent | How a self-hosted Next.js publishing platform is built and where it can fail |
| Title / H1 | How jithendar.com runs: a self-hosted Next.js platform on Kubernetes |
| SEO title | How jithendar.com Runs: Self-Hosted Next.js on Kubernetes |
| Meta description | The architecture of this site after its WordPress compromise: Next.js on one Minikube server, PostgreSQL, R2, the release path and its failure modes. |
| Social title | Rebuilding my site after a WordPress compromise |
| Links added | Cloudflare proxy status, R2 pricing and Turnstile docs |
| Git change | `content/projects/jithendar-com.mdx` renamed to `nextjs-site-on-kubernetes.mdx` to match the live slug |

### /blog/roboshop-ai-microservices

| Field | Value |
|---|---|
| Primary intent | A worked microservices example, including its costs |
| Title / H1 | RoboShop AI microservices architecture: service boundaries, request flows and trade-offs |
| SEO title | RoboShop AI Microservices: Boundaries, Flows and Trade-offs |
| Meta description | How RoboShop AI splits a demo store into services: three real request flows, what each boundary buys, what it costs, and when a monolith would be simpler. |
| Links added | Deployment guide, project hub, live demo. All repo links re-pinned to c81e85a |
| Images | Figure 1 replaced (new `roboshop-ai-eks-services.svg`). Observability figure removed because it shows the old stack |

## 5. Redirects

| From | To | Type | State |
|---|---|---|---|
| `/projects/jithendar-com` | `/projects/nextjs-site-on-kubernetes` | 308 | Live, single hop, no change |
| `/blog/roboshop-ai-microservices-architecture` | `/blog/roboshop-ai-microservices` | 308 | **Proposed, needs your approval** |

The second redirect needs care. The redirect table has no admin screen and `recordRedirect` only runs on a slug change, so it needs a database insert. The post must also leave `published` first, or it keeps being served. Its one live comment would stop being visible, so decide what to do with it first. Post #7 links to it in its body, and that link must change at the same time. It points directly at a live URL, so there is no chain.

`/blog/deploy-nextjs-kubernetes-github-actions` needs no redirect: it has never been public.

## 6. How to apply an approved draft

Do this only after approval. **Update** on a published post goes live straight away.

1. Resolve every `<Todo>` in the draft and delete those notes. Review notes must not be pasted into the editor.
2. In **Admin → Posts**, open the post and switch to **Markdown** mode.
3. Replace the body with the draft's text below the frontmatter.
4. Set the title, description, tags and related posts, then the SEO and social fields from section 4.
5. Tick **Substantive update**, which sets `dateModified` and the visible "Updated" date. The original publication date stays.
6. Deploy first if the draft uses a new image from `public/images/`.

To preview a draft locally: `npm run preview`.

## 7. Open questions for the owner

1. **Cloudflare:** keep the apex DNS-only and publish the corrected text, or turn the proxy on and edit the request path? The EKS runbook needs DNS-only for the NLB, so this interacts with any later cutover.
2. **Moks on EKS:** should the shopping assistant be deployed? Three drafts say it is not.
3. **Merge:** approve merging #4 into #3, including its comment?
4. **Licence:** the drafted tutorial tells readers to adapt the pattern because the code is proprietary. Keep that, or change the licence?
5. **Image pinning for this site:** production runs `:latest`, while the docs and an earlier article say digests are always pinned. `www/docs/DEPLOYMENT.md` and `AGENTS.md` still say CI has no cluster access, and CI now restarts the Deployment.
6. **Backups:** is a schedule on, and has a restore been tested?
7. **Personal voice:** the drafts leave marked places for your own reasons and lessons. They were not invented.
8. **Cover images:** the EKS cover must be replaced, because it names Gatekeeper, Karpenter and KEDA. The microservices cover shows generic boxes such as "Inventory" that do not match RoboShop's services, so consider replacing it too. Suggested alt text for what stays is in the change log.
9. **Structured data:** `analysis` posts render as `NewsArticle` and enter the news sitemap. These are evergreen engineering articles, so `BlogPosting` fits better. It is a one-line change to `src/lib/seo/jsonld.ts` and the news-sitemap type list, plus tests. Not changed here; approve it separately.
10. **Pages outside this audit:** `/about` says the site "uses no cookies, analytics or advertising scripts" while GA4 and AdSense integrations exist behind configuration, and it says every tutorial comes from systems that were built, which must stay true. The byline shows "AI Engineer" while `/about` says "cloud and platform engineer". `AGENTS.md` still lists TypeScript 5.9 and self-hosted runners.

## 8. Change log (Batch 1)

| Article | Before | After |
|---|---|---|
| EKS tutorial | Eleven lettered steps through scripts that no longer exist, for a stack never built. Claimed "offline only" | Eight ordered steps against the real cluster, with status table, real configuration, recorded validation output, how to read it, failure table and teardown. Unrun steps are labelled |
| Site project | Tool tour with false Cloudflare claims and the wrong H1 | Explains the compromise and what it changed, the true request path, the release path and its `:latest` trade-off, and a failure-mode table |
| Microservices | 2,600 words at 692e72d, plus a competing article | One article with three request flows, updated to EKS. The assistant's absence is used as a real fault-isolation example |

New assets: `public/images/roboshop-ai/roboshop-ai-eks-services.svg` and `roboshop-ai-eks-delivery.svg`, built by `docs/diagrams/roboshop-ai-microservices/build_diagrams.py`, with `.mmd` sources. Existing SVGs are unchanged, so live posts are not affected.

Suggested cover alt text:

- **EKS tutorial:** none. Replace the image first.
- **Microservices (if kept):** Illustration of a shopping app connected to request, AI chat and order-event flows, beside panels listing the benefits and trade-offs of microservices.
- **Site project:** Illustration of a Next.js app on Minikube Kubernetes with PostgreSQL, Redis, Cloudflare R2, encrypted backups, an admin panel and monitoring dashboards.

## 9. Evidence and sources

Verified 2026-11-01 unless noted.

- EKS: server 1.36.5, `eks.17`, two `t4g.large` arm64 nodes, add-on list, five control-plane log types.
- Argo CD: hub 3.5.5 on `mk4`, Applications all `Synced` and `Healthy`, no automated sync on those sampled.
- Istio: 1.30.7; [support table](https://istio.io/latest/docs/releases/supported-releases/) (1.30 end of life expected around December 2026; 1.31 supports Kubernetes 1.32 to 1.37); [dry run is Alpha](https://istio.io/latest/docs/tasks/security/authorization/authz-dry-run/).
- EKS lifecycle: [1.36 standard support ends 2 August 2027](https://docs.aws.amazon.com/eks/latest/userguide/kubernetes-versions.html).
- Let's Encrypt: [5 certificates per exact identifier set per 7 days](https://letsencrypt.org/docs/rate-limits/).
- Cloudflare: [DNS-only behaviour](https://developers.cloudflare.com/dns/proxy-status/), [R2 pricing](https://developers.cloudflare.com/r2/pricing/).
- Google: [Article structured data types and dates](https://developers.google.com/search/docs/appearance/structured-data/article).
- Link check before rewriting: 43 URLs in article sources, 4 repo links 404, 1 live-demo link 404, 2 harmless redirects.

## 10. Validation results

| Check | Result |
|---|---|
| `npm test` | 394 passed, 1 failed. The failure is `article-route` `future-post`, a fixture dated 2026-11-01 that is no longer in the future. It is unrelated to these drafts and will fail CI until the fixture date moves |
| `npm run lint`, `npm run typecheck` | Pass |
| `npm run build` (`APP_ENV=production`) | Pass |
| Editor round trip | All three drafts open in the visual editor without loss |
| Internal links and frontmatter | Pass, via `npm test` |
| External links in drafts | 37 URLs, all 200 except `/roboshop/metrics`, which is a deliberate 404 in an example |
| Rendering | Preview build: one H1, ordered H2/H3, all images have alt text and load |
| Mobile | No horizontal overflow at 320 or 390 px, in an emulated phone viewport |
| Private data scan | No account IDs, node names, subnet IDs or allowlisted addresses in drafts, SVGs or this file |
| Stock-phrase scan | None found |
| AWS deployment | **Not run.** Checks were read-only. Step 8, rollback and teardown are labelled as not exercised |

`www/docs/diagrams/moks-langgraph/` and `content/blog/langchain-vs-langgraph-sre-agent-moks.mdx` appeared in the working tree during this audit from separate work. That article is an unpublished draft and is not in the inventory.
