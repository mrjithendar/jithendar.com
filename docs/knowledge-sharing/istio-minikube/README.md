# Istio Service Mesh on Minikube (rewrite, 9 November 2026)

Article: `content/blog/istio-service-mesh-minikube-features-setup-troubleshooting.mdx` (same slug and title as the
live post, `status: review`, uncommitted). The live body is in the CMS database, so this file is the paste source.

## What changed from the live version

- mk4's design changed: the Istio ingress gateway is the only edge (Traefik uninstalled, the Kong plan dropped from the
  article), every namespace is STRICT mTLS through `istio-system/default`, and each application and platform namespace
  has a dry-run `allow-known-callers` AuthorizationPolicy. New sections 5 (edge design), 6 (mTLS and authorization) and
  four dated incidents in section 8.
- The lab track keeps Bookinfo, now installed with Helm and the CNI chart, and adds a working delegation example.
- Three draw.io figures replace the Mermaid diagram: `istio-architecture`, `mk4-istio-edge`, `mk4-mesh-security`.
- New fact stated: Istio 1.30 supports Kubernetes 1.32–1.36, and mk4 runs 1.37 (Istio 1.31 lists it).
- About 5,700 words (the live version was about 6,700).

## Checked

- Live facts read on mk4 on 9 November 2026: versions, 56 proxies, replicas and PDBs, PeerAuthentications,
  AuthorizationPolicies, EnvoyFilters, a gateway access-log line, `kubectl top` figures, Velero (namespace, no server).
- Every Istio object in the article passed `istioctl analyze --use-kube=false` (istioctl 1.30.7).
- `vitest run tests/content.test.ts tests/links.test.ts tests/responsive-content.test.tsx`: 17 passed.
- Every istio.io source URL returned 200 on 9 November 2026.

## Figures

```bash
python3 sites/jithendar.com/docs/knowledge-sharing/istio-minikube/diagrams/build_diagrams.py   # writes the .drawio files
bash sites/jithendar.com/docs/knowledge-sharing/istio-minikube/diagrams/export.sh              # draw.io CLI → public/images/istio-minikube/
```

`drawio_model.py` is a copy of the system-design-evolution one. After editing a `.drawio` file by hand, run only
`export.sh`.

## Publishing

1. Commit, so the image build ships `public/images/istio-minikube/*` (the editor refuses `/images/` paths that 404).
2. Paste the body into the existing post in Admin → Posts and update its description and SEO fields.
3. Recheck before publishing: the moks OpenSearch `:9200` exception (gone after the moks Argo CD sync), whether the
   AuthorizationPolicies still run as dry runs, and the Istio version if mk4 has been upgraded.
