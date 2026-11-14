# How I Built jithendar.com (draft, 13 November 2026)

Article: `article.md` in this folder (about 2,300 words of prose, plus snippets). Not in `content/blog/` yet, so nothing deploys.

## Figures

Three draw.io figures replace the Mermaid diagram: `platform-architecture`, `crewai-content-pipeline` and `release-pipeline`.

```bash
python3 sites/jithendar.com/docs/knowledge-sharing/how-i-built-jithendar-com/diagrams/build_diagrams.py   # writes the .drawio files
bash sites/jithendar.com/docs/knowledge-sharing/how-i-built-jithendar-com/diagrams/export.sh              # draw.io CLI → public/images/how-i-built-jithendar-com/
```

`drawio_model.py` is a copy of the istio-minikube one. After editing a `.drawio` file by hand, run only `export.sh`.
Commit the images before publishing (the editor refuses `/images/` paths that 404).

## SEO

- **Title (57 chars):** Building jithendar.com: Istio, CrewAI and EKS on Minikube
- **Meta description (141 chars):** How I run my blog on minikube with EKS-style patterns: Istio gateway and STRICT mTLS, CrewAI flows with human review, and PR-tagged releases.
- **Tags:** kubernetes, istio, crewai, platform-engineering, ci-cd

## LinkedIn post

I could have put my blog on WordPress in an afternoon. Instead I built jithendar.com as a small production platform on a multi-node minikube cluster, so I'd have somewhere to practise the platform work I talk about.

The new post walks through what's actually in the repo:

- Istio ingress gateway as the only edge, with STRICT mTLS inside the namespace (after moving off Traefik and dropping a Kong migration)
- EKS habits on minikube: least-privilege CI ServiceAccounts, required topology spread, NetworkPolicies, OpenTelemetry, encrypted backups
- A CrewAI pipeline where agents can only read, and nothing publishes without my approval
- Images tagged with the PR number, built only on merge, with no push trigger

It also covers five things that broke, including CI freezing the host and sidecars that never became ready, and how I fixed each one.

Link in the comments.

#Kubernetes #Istio #CrewAI #PlatformEngineering #DevOps

## Questions for the author

1. **Kong.** The brief says Kong is the edge and replaced Traefik/Istio ingress. The repo says the opposite: the Istio gateway is the only edge, Traefik was uninstalled on 2026-11-09, and the Kong decK file is "NOT APPLIED BY ANYTHING". `DECISIONS.md` D-62 also says "Kong on mk4 runs in DB mode". Is Kong running on mk4 for other apps? Did the cutover happen outside this repo? The article currently says Istio is the edge.
2. **Edge in front of the gateway.** The platform figure shows Cloudflare DNS (DNS only, no proxying) → HAProxy on the host (TCP, PROXY v2) → gateway NodePort, taken from the Istio article (9 November 2026). Is that still true, given that `robots.txt` mentions Cloudflare Access?
3. **Hardware cost.** The repo only has LLM cost estimates. What is the host, how many nodes does mk4 have, and what do power, the domain and R2 cost each month?
4. **Measured LLM spend.** `COSTS.md` says the numbers are estimates made before any live Claude call. Do you have real `seo_llm_usage` totals to replace them?
5. **Helm.** The brief mentions Helm charts, but this repo has none (D-63: "there is no Helm chart here"). Istio is installed with Helm in the cluster repo. Should the article mention that?
6. **ECR vs Harbor.** `infra/` and the root README still describe ECR, while the workflows push to Harbor. Is ECR retired? The article says the release workflows push to Harbor.
7. **The "why".** Is there anything personal to add about the long-term brand goal (audience, consulting, the Hire me page)?
8. **What's next.** The article only lists TODOs found in the repo. Add your own plans.
