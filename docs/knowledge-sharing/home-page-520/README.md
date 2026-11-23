# Home page 520 (23 November 2026): evidence and review notes

Draft (status `review`, written 2026-11-23): `content/blog/cloudflare-520-home-page-postmortem-jithendar-com.mdx`, the
postmortem for the incident in which `https://jithendar.com/` returned Cloudflare 520s, 502s or no response for at least
28 minutes after a deploy, while every other URL worked.

## Sources

| Source | What it gave |
|---|---|
| mk4, namespace `jithendar` (read-only `kubectl`) | ReplicaSets and revisions, Deployment managed fields, probes and strategy, events, the `web` container's JSON log (requests, `pages_warmed`), port-forward checks |
| mk4, namespace `istio-ingress` | the gateway's JSON access log (no path field; used only for error codes and durations) |
| GitHub API | `mrjithendar/jithendar.com` run 45137926193 (both attempts, job and step times, who re-ran it), `mrjithendar/moks-cms` run 45137763032, merge times of moks-cms #192 and jithendar.com #17 |
| curl from a laptop | the checks in `evidence/checks.txt`, through Cloudflare (Singapore edge) and against the origin with `--resolve` |
| The owner's browser | the 520 page at 08:53:44 UTC; the purges in Admin → Cache (09:02–09:06 UTC) |
| Cloudflare docs | [Error 520](https://developers.cloudflare.com/support/troubleshooting/http-status-codes/cloudflare-5xx-errors/error-520/), [purge by single file](https://developers.cloudflare.com/cache/how-to/purge-cache/purge-by-single-file/), [cache rules](https://developers.cloudflare.com/cache/how-to/cache-rules/) |

Raw notes: `evidence/timeline.txt` (times, ReplicaSets, events, log lines) and `evidence/checks.txt` (every curl check
with its result). Nothing in them identifies a visitor: the origin's IP addresses, visitor IPs, cf-ray values and the
Cloudflare zone and account IDs are left out on purpose. Keep it that way when you edit: publishing the origin
address lets anyone go around Cloudflare.

## Not known yet (Todo items in the article)

1. **When it started.** The first failed request I saw was at 08:39:39 UTC. The deploy restarted the pods at 08:22:01 and
   08:30:11. Cloudflare Analytics → Traffic (status codes over time) and **Origin Analytics** (origin status next to
   edge status) for 08:15–09:10 UTC will show the start, which data centres served the errors, and whether the origin
   status was 200. Cloudflare's 520 page reads an origin 200 with an edge 520 as malformed headers or an early close.
2. **Who deleted both pods at 08:41:31–34.** No event, ReplicaSet change or managed field records it. The deletion came
   after the failure had started (08:39:39), so it is not a cause. It cost one warm-up and changed nothing.
3. **Follow-ups.** All five are open. Update the table in the article and the figure when they land.

## Figures

Built with `diagrams/build_diagrams.py` (standard library only, using the shared `drawio_model.py` writer), then
exported with `diagrams/export.sh` (draw.io desktop CLI, light theme) to `public/images/home-page-520/`:

| Figure | Shows |
|---|---|
| `home-page-520-path` | the request path and the three groups of checks; the cover image |
| `home-page-520-timeline` | changes, pods and `GET /` through Cloudflare on one time axis, with the numbered events |
| `home-page-520-narrowing` | the five questions, the command that answered each, and the conclusion |
| `home-page-520-followups` | contributing factors mapped to follow-ups |

```bash
python3 docs/knowledge-sharing/home-page-520/diagrams/build_diagrams.py
bash docs/knowledge-sharing/home-page-520/diagrams/export.sh
```

If you edit a `.drawio` file by hand, run only `export.sh` afterwards. Running the build script overwrites the edits.
