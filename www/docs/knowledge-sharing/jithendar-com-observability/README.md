# Article: How We Implemented Logging, Tracing, and Observability on jithendar.com

Draft: `content/blog/logging-tracing-observability-jithendar-com.mdx` (`status: review`, category `devops-sre`).
Evidence was read from mk4 on 2026-11-04; the fixes it describes are listed in `docs/OBSERVABILITY.md` ("Review
fixes") and were uncommitted and undeployed when it was written.

| Field | Value |
|---|---|
| Slug | `logging-tracing-observability-jithendar-com` (no existing post or live URL uses it) |
| SEO title | Next.js Observability on Kubernetes: OpenTelemetry, Loki, Jaeger, Prometheus |
| Meta description | Structured logs, OpenTelemetry traces and Prometheus metrics for a self-hosted Next.js site: the real setup, a slow-request investigation and the fixes. |
| Excerpt (`description`) | How jithendar.com ties structured logs, OpenTelemetry traces and Prometheus metrics together on Kubernetes, and the gaps a review found and fixed. |
| Featured image | `/images/jithendar-com-observability/jithendar-com-telemetry-flow.png` (1240 × 1408); alt text in the frontmatter |

Internal links (`related`), all answering 200 on 2026-11-04: `/blog/github-actions-authenticate-minikube`,
`/blog/learning-typescript-real-project-jithendar-com`, `/blog/mermaid-diagrams-on-jithendar-com`,
`/blog/learning-terraform-real-project-tools-repository`. Every URL in `sources` answered 200 on the same day.

Figure: `python3 docs/knowledge-sharing/jithendar-com-observability/diagrams/build_diagrams.py` writes the `.drawio`
and SVG; `sh docs/knowledge-sharing/jithendar-com-observability/diagrams/render_png.sh` the PNG (Google Chrome).
