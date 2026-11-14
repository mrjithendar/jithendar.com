# One Redis for Every App: Valkey on Minikube (9 November 2026)

Article: `content/blog/valkey-redis-sentinel-minikube-terraform.mdx` (`status: review`, uncommitted). Companion to
`cloudnativepg-postgres-cluster-minikube-terraform.mdx`.

## Sources of truth

- miniKube repository: `minikube-infrastructure/redis.tf`, `_variables.tf` (`redis_tenants`, `redis_allowed_ips`),
  `vars/mk4.tfvars`, `deploy/minikube/redis/` (values, post-renderer, access chart), `tests/test_redis.py`,
  Prometheus alerts, and the "Redis (Valkey)" section of `minikube-infrastructure/README.md`.
- This repository: `kubernetes/practice-executor-40-executor.yaml`, `kubernetes/practice-executor-50-networkpolicies.yaml`.
- Live mk4, read only, on 9 November 2026: pods and nodes, PVCs, PDB, Sentinel master and `ckquorum`, `info
  replication`, `info keyspace`, `client list` per user, `acl getuser` / `acl dryrun` for user `practice`, images,
  Helm releases, and `redis.jithendar.com` (DNS, wildcard certificate, `NOAUTH` reply to an unauthenticated `PING`).
- The failover figure (2 failed writes over about 4 s) is from the miniKube README, not re-measured for the article.

## Figures

```bash
python3 sites/jithendar.com/docs/knowledge-sharing/valkey-minikube/diagrams/build_diagrams.py   # writes the .drawio files
bash sites/jithendar.com/docs/knowledge-sharing/valkey-minikube/diagrams/export.sh              # draw.io CLI → public/images/valkey-minikube/
```

| Figure | Used in |
|---|---|
| `valkey-architecture` | section 3 (replaces the Mermaid diagram) |
| `valkey-failover` | section 4.2 |
| `valkey-tenancy-security` | section 4.5 |

`drawio_model.py` is a copy of the istio-minikube one, with one extra arrow kind (`replicate`). After editing a
`.drawio` file by hand, run only `export.sh`.

## Recheck before publishing

- Which pod is primary (the figures show `valkey-1` on `mk4-m03`; a failover changes it).
- Whether the `jithendar` tenant removal has been applied (ACL user still on the server on 9 November 2026).
- Chart, Valkey and RedisInsight versions, if mk4 has been upgraded.
