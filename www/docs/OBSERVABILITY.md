# Observability: traces, logs, metrics and Grafana dashboards

jithendar.com uses the cluster's shared monitoring stack (configured in the `tools` repo, synced by Argo CD from
`roboshop-ai/argocd`): OpenTelemetry collector + Jaeger (traces), Alloy + Loki (logs), Prometheus (metrics) and
Grafana at `https://jithendar.com/grafana/` (folder **Jithendar.com**).

| Signal | From the site | Collected by | Where to look |
|---|---|---|---|
| Traces | Next.js spans via `@vercel/otel` (`src/instrumentation.ts`), OTLP/HTTP to `otel-collector.observability:4318` | collector → Jaeger (privacy filter drops URLs, queries, SQL, exception text, health checks) | Jaeger UI (not public): `kubectl -n observability port-forward svc/jaeger 16686`, then http://localhost:16686, service `jithendar-com` |
| Logs | JSON lines on stdout (`src/lib/log.ts`, access log in `src/proxy.ts`) | Alloy reads namespace `jithendar` (Role `alloy-logs`, `k8s/70-observability.yaml`) → Loki | Dashboard **Jithendar.com · Logs** |
| Metrics | `src/lib/metrics.ts` on port **9464** `/metrics` (cluster-internal) | Prometheus job `jithendar-com` (headless Service `jithendar-com-metrics`) | Dashboard **Jithendar.com · Overview**; alerts `JithendarCom*` |

## Metrics

- `http_server_requests_total{method, route, status}` and `http_server_request_duration_seconds{method, route}` —
  derived from the `BaseServer.handleRequest` span Next.js creates for every request; `route` is the route
  *pattern* (`/blog/[slug]`), `status` the class (`2xx`…`5xx`), so series stay bounded. Requests without a route
  (static files, internals) are `route="other"`.
- `process_*`, `nodejs_heap_*`, `nodejs_eventloop_delay_{p99,max}_seconds`, `jithendar_build_info{version}`.
- `jithendar_mail_sent_total{provider, outcome}`, `jithendar_comments_submitted_total{status}`.
- From the database at scrape time (cached 30 s): `jithendar_posts_published`, `jithendar_users`,
  `jithendar_comments_pending`, `jithendar_comments_reported`, `jithendar_jobs{status}`, `jithendar_database_up`.

Port 9464 is not in the public Service or ingress; the NetworkPolicy admits only the Prometheus pod
(`monitoring`, `app=roboshop-prometheus`). `METRICS_PORT=0` turns the listener off. Counters are per pod and reset
on restart (Prometheus `rate()`/`increase()` handle that).

## Logs

The collector stores only allowlisted fields with strict formats and drops everything else, **including `msg`**
(privacy by design). Fields that reach Loki: `event`, `level`, `route`, `method`, `status`, `durationMs`,
`dependency`, `operation`, `errorType`, `errorCode`, `outcome`, `traceId`. So:

- every line gets `event`, a stable slug of the message (`comment submitted` → `comment_submitted`), unless the
  caller passes its own;
- errors get `errorType` (class name) and `errorCode` (when the error has a short `code`);
- the proxy's access log is `event=http_request` with `route` (the path) and `method`;
- full JSON (with `msg`, stack traces) is still in `kubectl -n jithendar logs deploy/jithendar-com`.

Log lines in Grafana show `trace_id`; the line details link to Jaeger (needs the port-forward above). Grafana has no
Jaeger data source: Jaeger 2.x no longer serves the legacy query API that data source uses.

## Alerts (Prometheus, `tools/observability/prometheus/files/alerts.yml`)

`JithendarComDown` (no pod scraped for 5 min), `JithendarComHighErrorRatio` (> 5 % 5xx for 5 min),
`JithendarComSlow` (p95 > 2 s for 10 min). They show in Prometheus → Alerts; no Alertmanager delivers them.

## Rolling it out

1. Deploy the site (`./deploy.sh`: new image + `k8s/` metrics port, NetworkPolicy rule, `70-observability.yaml`).
2. Push the `tools` repo: Argo CD then updates Alloy (namespace `jithendar`), Prometheus (scrape job, alerts) and
   Grafana (folder, dashboards, Loki trace links).
3. Check: Prometheus → Status → Targets shows `jithendar-com` (2 up); Grafana → Jithendar.com dashboards.
