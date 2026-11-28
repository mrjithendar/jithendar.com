# worker1 out of memory (28 November 2026)

Evidence and figures for `content/blog/kubernetes-node-out-of-memory-postmortem-mk4.mdx`: a `kubectl rollout restart`
put a second LiteLLM pod on mk4's worker1, which ran out of memory and was NotReady from 11:10:22 to 11:21:05 UTC.

## evidence/

Everything was collected read-only from the cluster between 11:39 and 11:45 UTC the same day.

| File | What | How |
|---|---|---|
| `events.tsv` | Kubernetes events, 10:50–11:30 UTC (pod IPs and image digests replaced, the per-minute seo-flow-dispatcher CronJob noise removed) | `kubectl get events -A -o json` (events expire after an hour) |
| `memory.txt` | Raw `container_memory_working_set_bytes` samples: worker1's root cgroup, the LiteLLM pods, docling-serve | Prometheus (port-forward, route prefix `/prometheus`), `[70m]` range at 11:35 |
| `kubelet.txt` | `evictionHard`, `systemReserved`, `kubeReserved` on every node; requests and limits per node | `kubectl get --raw /api/v1/nodes/<node>/proxy/configz`, `kubectl describe nodes` |
| `alerts.txt` | Every alert series in the window: none for the node, and no Alertmanager | `ALERTS[70m]` in Prometheus |
| `site.txt` | The site's own request log during the outage, and the public checks | Loki (`container="web"`), curl |

## diagrams/

`build_diagrams.py` writes the four `.drawio` files from the numbers above (`drawio_model.py` is the shared writer from
`../home-page-520`); `export.sh` renders them with the draw.io desktop CLI into `public/images/worker1-oom/`:

```bash
python3 docs/knowledge-sharing/worker1-oom/diagrams/build_diagrams.py
DRAWIO=/Applications/draw.io.app/Contents/MacOS/draw.io bash docs/knowledge-sharing/worker1-oom/diagrams/export.sh
```

| Figure | Shows |
|---|---|
| `worker1-oom-memory` (cover) | Requests against working set on worker1 at 11:10:23: why the scheduler said "fits" |
| `worker1-oom-timeline` | Four lanes, twelve numbered events |
| `worker1-oom-recovery` | The seven recovery steps |
| `worker1-oom-followups` | Causes and the follow-up for each |

When a follow-up lands, update the article's table and `FIXES` in `build_diagrams.py`, then rebuild.
