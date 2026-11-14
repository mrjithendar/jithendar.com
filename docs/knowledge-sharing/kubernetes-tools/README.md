# Kubernetes tools series (two parts): review package

Articles, both `status: review`, written 2026-11-08:

- Part 1: `content/blog/15-essential-kubernetes-tools-devops-engineers-2026.mdx` (Helm, Argo CD, Flux, Kustomize, K9s, Lens, Prometheus), 13 min by the site's count.
- Part 2: `content/blog/15-essential-kubernetes-tools-devops-engineers-2026-part-2.mdx` (Karpenter, KEDA, Istio, Linkerd, Cilium, cert-manager, Velero, Kyverno), 15 min.

Publish both together. Each lists the other in `related` and links to it in the body.

## SEO

| Field | Part 1 | Part 2 |
| --- | --- | --- |
| URL | `/blog/15-essential-kubernetes-tools-devops-engineers-2026` (the brief's URL) | `/blog/15-essential-kubernetes-tools-devops-engineers-2026-part-2` |
| SEO title | Kubernetes Tools for DevOps Engineers 2026 (Part 1) (51) | Kubernetes Tools 2026 (Part 2): Scaling and Security (52) |
| Meta description | The brief's text, 138 characters | 155 characters |
| Category / type | `kubernetes` / `tutorial` | same |
| Cover | `k8s-tools-ecosystem.png` 1800×1320 | `k8s-tools-production.png` 1800×1560 |

Primary keyword "Kubernetes tools for DevOps engineers" is in Part 1's second paragraph. Secondary keywords are covered by section headings: GitOps (Argo CD, Flux), monitoring (Prometheus), security (cert-manager, Kyverno), autoscaling (Karpenter, KEDA) and production architecture (Part 2).

How the brief's SEO list maps to this site:

| Brief | Site |
| --- | --- |
| H1/H2/H3, table of contents with anchors | Title is the H1; `TableOfContents` builds the TOC from H2/H3 automatically |
| Article structured data, Open Graph | Emitted from front matter (`socialTitle`, `socialDescription`, cover) |
| FAQ schema | Not emitted by the site (only Article and BreadcrumbList). The interview questions are H2 + H3 Q&A, ready if FAQPage support is added |
| Syntax highlighting, copy buttons | Shiki and the existing `CodeBlock`; ```promql is already used by other posts |
| Responsive tables | The site's table styles scroll sideways on phones |

## Diagrams (draw.io)

`diagrams/build_diagrams.py` writes eight editable `.drawio` files plus SVGs into `public/images/kubernetes-tools/`, reusing the RoboShop series writer. `diagrams/render_png.sh` makes 2× PNGs with headless Chrome. The SVGs are rendered by the script, not exported from draw.io, so re-export from draw.io if you edit a `.drawio` by hand. Each SVG carries a full `<desc>`; the alt text in the body is kept short because the site counts alt text toward reading time.

| Figure | Used in |
| --- | --- |
| k8s-tools-ecosystem | Part 1 cover and intro |
| k8s-tools-gitops-flow | Part 1, Argo CD |
| k8s-tools-prometheus-flow | Part 1, Prometheus |
| k8s-tools-mk4-lab | Part 1, lab |
| k8s-tools-autoscaling-chain | Part 2, Karpenter |
| k8s-tools-service-mesh | Part 2, Istio |
| k8s-tools-cert-manager-flow | Part 2, cert-manager |
| k8s-tools-production | Part 2 cover and architecture |

## Verification

```bash
python3.11 -m venv /tmp/k8s-tools-venv && /tmp/k8s-tools-venv/bin/pip install pyyaml jsonschema cel-python
/tmp/k8s-tools-venv/bin/python sites/jithendar.com/docs/knowledge-sharing/kubernetes-tools/verify_examples.py --context mk4
```

On 2026-11-08: **137 checks passed, 0 failed, 0 skipped** (with `--context mk4`). They cover:

- **YAML blocks.** Every YAML block in both articles equals a file in `examples/`, and every example is used.
- **Schemas.** Each manifest is checked against its project's CRD schema at the version the article names, with unknown fields rejected. Core types are checked against mk4's Kubernetes v1.37 OpenAPI. Injected typos are rejected, so the check is not vacuous.
- **Kustomize.** `kubectl kustomize` builds the overlay with 3 replicas, tag 1.5.0, namespace `shop`, a hashed ConfigMap and `LOG_LEVEL=warn`.
- **KEDA.** Trigger metadata matches KEDA 2.21's scaler schema.
- **Kyverno.** Both policies' CEL expressions reject `tests/pod-privileged.yaml` and accept `tests/pod-good.yaml`, evaluated with cel-python, not with Kyverno itself.
- **PromQL.** Every query runs against mk4's Prometheus through read-only GETs.
- **Shell and metadata.** Shell blocks pass `bash -n`; front-matter lengths, images, `related` and `/blog` links all resolve.

Also run: `npx vitest run`. Before another session added `system-design-evolution-1990s-to-microservices.mdx`, the only failures were these two posts' editor round-trips, caused by bold around links. That is fixed, and both now pass `-t "15-essential"`. The full suite currently fails on that other draft's missing `related` post, not on these files. Not run: lint, typecheck and build (no code changed).

Not run against real systems: installs of Flux, Karpenter, KEDA, Istio, Linkerd, Cilium, Kyverno and Velero, and the Velero, Karpenter and Istio troubleshooting commands. Schema validation proves field names and types, not runtime behaviour.

## Facts to recheck before publishing

- **Versions** (latest stable on 2026-11-08): Helm 4.3.1, Argo CD 3.6.1, Flux 2.10.0, Kustomize 5.8.3, K9s 0.51.0, Karpenter 1.15.1, KEDA 2.21.0, Istio 1.31.4, Linkerd edge-26.11.1 (2.20 announced 2026-06-23), Cilium 1.20.4, cert-manager 1.21.3, Velero 1.18.4, Kyverno 1.19.2, Prometheus 3.16.0, Gateway API 1.7.0, kube-prometheus-stack 93.1.0.
- **Kyverno 1.20** (estimated November 2026) removes `ClusterPolicy`. If it ships before publishing, say "removed" instead of "deprecated".
- **Lens pricing** (lenshq.io/pricing): free Personal plan below $10M revenue or funding; Plus $25 a month billed yearly.
- **CNCF status**: Kyverno graduated 2026-03-24; Velero CNCF Sandbox (Velero blog 2026-07-30).
- **Istio Helm chart lag**: the `istiod` chart index stopped at 1.30.8 while Istio 1.31.4 was released.
- **mk4 facts** (Part 1 lab, Part 2 lab), all from read-only `kubectl` and `helm` on 2026-11-08:
  - 8 nodes, v1.37.0, kindnet, about 1.6 cores and 16 GiB in use, 80 pods.
  - Argo CD v3.5.5 with 35 live and 29 stale `roboshop-demo-*` Applications.
  - The `argocd` Helm release is `pending-install` and Traefik revision 2 is `failed`.
  - Prometheus v3.15.0 has no Alertmanager or kube-state-metrics, and `status` labels hold classes such as `5xx`.
  - cert-manager v1.20.4 with 4 Certificates Ready.
  - Velero CRDs, the R2 location and the schedule exist with no server; the last completed backup is `daily-20261101020035`, and 7 MOKS backups have no phase.
  - `tools` e18e0e6 plans Istio 1.30.7 through Terraform, unapplied, and Istio 1.30 does not list Kubernetes 1.37.

## Issues found in the repositories (not fixed)

1. `tools/minikube-infrastructure/istio.tf` pins Istio 1.30.7; Istio 1.30 supports Kubernetes 1.32–1.36 and mk4 runs 1.37.0.
2. Velero objects on mk4 without a server. MOKS backup requests since 1 November were never processed.
3. 29 `roboshop-demo-*` Argo CD Applications point at the deleted EKS cluster.
4. The `argocd` Helm release is stuck in `pending-install`, so the next `helm upgrade` will be refused.
5. `tools/devops-tools/k9s.sh` installs K9s v0.24.15 on CentOS 8 only.
6. No Alertmanager and no kube-state-metrics on mk4, so the restart alert pattern returns nothing.

## LinkedIn post

> You do not need 15 Kubernetes tools. You need to know which problem each one solves.
>
> I wrote a two-part guide to the tools I see in real platforms: Helm, Argo CD, Flux, Kustomize, K9s, Lens and Prometheus in Part 1; Karpenter, KEDA, Istio, Linkerd, Cilium, cert-manager, Velero and Kyverno in Part 2.
>
> Every manifest is validated against the project's own schema at the November 2026 release, the PromQL ran against my lab's Prometheus, and the lab section shows what really runs on my 8-node Minikube cluster, including what is broken.
>
> Two things that surprised me while checking:
> • Kyverno 1.19 deprecated ClusterPolicy. New policies use CEL-based ValidatingPolicy.
> • A 5xx alert written as status=~"5.." matched nothing on my site, because the label holds "5xx".
>
> Part 1: https://jithendar.com/blog/15-essential-kubernetes-tools-devops-engineers-2026
> Part 2: https://jithendar.com/blog/15-essential-kubernetes-tools-devops-engineers-2026-part-2
>
> #Kubernetes #DevOps #PlatformEngineering #GitOps #SRE
