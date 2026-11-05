# Kubernetes history article

Status: **draft for author review, not published.** Written 2026-11-05. Article: `content/blog/kubernetes-history-origins-evolution-milestones.mdx` (`status: review`, no `publishedAt`). `tests/content.test.ts` and `tests/links.test.ts` pass; every external link returned HTTP 200 on 2026-11-05.

## SEO and publishing metadata

| Field | Value |
| --- | --- |
| H1 (`title`) | Kubernetes: How It Started, How It Evolved, and the Milestones That Shaped It |
| SEO title (57 chars) | Kubernetes History: Origins, Evolution and Key Milestones |
| Meta description (158 chars) | How Kubernetes grew from Google's Borg and Omega lessons into a CNCF project: the 2014 launch, 1.0, key features, dockershim, and where it is heading in 2026. |
| Slug | `kubernetes-history-origins-evolution-milestones` |
| Category / type | `kubernetes` / `analysis` |
| Length | about 3,190 words from the introduction to the end of the "today" section, counting headings and table cells; code, diagram and references not counted |

## Where each fact came from

Most kubernetes.io claims were read from the Markdown sources in `kubernetes/website` (`content/en/blog/_posts`), not from rendered pages.

| Claim | Source |
| --- | --- |
| First commit 2014-06-06 23:40 UTC by Joe Beda, "First commit", 250 files | GitHub API for commit 2c4b3a5; 10 Years of Kubernetes |
| Announced 2014-06-10, Eric Brewer, DockerCon keynote | 10 Years of Kubernetes |
| Founding team of eight names; prototype late fall 2013 | 10 Years of Kubernetes; Burns, 2018 history post |
| Beda suggested Docker (summer 2013); "inevitable"; McLuckie whitepapers; OpenShift team | Burns, 2018 history post (quoted) |
| Project Seven of Nine; logo "has seven sides" | McLuckie, Google Cloud blog, 2016-07-23 (quoted). The brief said "seven-spoke"; the source says sides, so the article states both |
| Name means helmsman or pilot; K8s = eight letters | kubernetes.io Overview docs |
| Pods from allocs, Services, Labels, IP-per-Pod | Borg: The Predecessor to Kubernetes (2015-04-23) |
| Omega lessons, API server mediates all store access | ACM Queue paper, **paraphrased**: the ACM page returned 403, so only the Google Research listing (authors, ACM Queue vol. 14, 2016) was read. Check the wording |
| 1.0 on 2015-07-21; CNCF announced the same day; Google contributes Kubernetes "as a seed technology" | 10 Years post; CNCF press release (dateline 2015-07-21; its URL says 2015/06/21) |
| Accepted 2016-03-10 (incubating); graduated 2018-03-06; CII badge Aug 2016 | CNCF project page; CNCF graduation announcement |
| Steering Committee election results, 2017-10-05; bootstrap committee from 5 companies | Kubernetes blog |
| v1.0 types: Pod, RC, Service, Namespace, Secret, PV, PVC | `pkg/api/v1/types.go` at tag v1.0.0 |
| 1.1: HPA beta | 1.1 release post (2015-11-09) |
| 1.2: Deployment, DaemonSet, Ingress beta; ReplicaSet, batch/v1 Job in tree | 1.2 release post; source tree at v1.2.0 |
| PetSet alpha 1.3, StatefulSet beta 1.5, CRI 1.5 | 1.3 and 1.5 release posts; CRI post 2016-12-19 |
| NetworkPolicy stable, TPR replaced by CRD in 1.7 | 1.7 release post |
| RBAC beta 1.6, GA 1.8 | RBAC GA post. Alpha version not verified, so the article omits it |
| apps/v1 GA in 1.9 (2017-12-15) | 1.9 release post |
| CSI alpha 1.9, beta 1.10, GA 1.13; CoreDNS default 1.13 | 1.13 release post |
| CRD GA 1.16 (2019-09-18) | 1.16 release post |
| Dockershim deprecated with 1.20 (Dec 2020), removed 1.24 (2022-05-03); Docker-built images keep working | Don't Panic (2020-12-02); Moving on from dockershim (2022-01-07); 1.24 post |
| PSP deprecated 1.21, removed 1.25, never stable; PSA stable 1.25 | PSP deprecation post (2021-04-06); PSP historical context (2022-08-23) |
| CronJob GA 1.21 | CronJob GA post (2021-04-09) |
| 3 releases a year from 2021 | Release cadence post (2021-07-20) |
| Artifacts signed with cosign from 1.24; binaries in 1.26 | 1.24 post; signing post (2022-12-12) |
| Gateway API v1.0, 2023-10-31 | Gateway API GA post |
| In-place resize beta 1.33, stable 1.35; DRA core GA 1.34 | 1.33, 1.34, 1.35 release posts |
| 1.36 (2026-04-22) and 1.37 (2026-08-26) features; v1.37.2 published 2026-10-28 | release posts; GitHub releases API |
| Ingress NGINX retired 2026-03-24; recommends Gateway API | 1.36 post; retirement notice (2025-11-11) |
| AI Conformance programme, 2025-11-11 | CNCF announcement |
| Kueue 2022-10-04; JobSet 2025-03-23 | Kubernetes blog introduction posts |
| Helm graduated 2020-05-01, Prometheus 2018-08-09, Argo 2022-12-06 | CNCF project pages |
| GKE GA 2015-08-26 | Google Cloud Platform blog title and date (body not readable) plus press coverage |
| EKS GA 2018-06-05 | AWS What's New post |
| AKS GA 2018-06-13 | Microsoft blog API record and press coverage; the post itself was not read |
| CoreOS operators, November 2016 | Press coverage only (TechCrunch, The Register, 2016-11-03). The article gives no exact day and no link |

## Open items for the author

1. Check the Omega paragraph against the ACM Queue paper text.
2. "v1.37 is the newest minor release" is date-sensitive. v1.38 is due around December 2026; recheck it before publishing.
3. The milestone table has 15 rows. Trim it if the page feels long on mobile.
4. Add your own commentary, confirm the AI-assistance line against the AI use policy, then set `status` and `publishedAt`. Live posts are in Postgres, so paste the approved text into the editor.
