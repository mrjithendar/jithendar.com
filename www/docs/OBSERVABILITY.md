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

## Errors, request lines and traces (2026-11-04)

**One trace id per request ties everything together.** The proxy runs inside Next's request span, so the access
line (`event=http_request`), the app's own lines, the completion line and the Jaeger trace share `traceId`.

| Line | `event` | Carries |
|---|---|---|
| Access (proxy) | `http_request` | `requestId`, `traceId`, path, IP, user agent; `status` only when the proxy answered (redirect, 410, 503) |
| Completion (span processor, `src/lib/request-log.ts`) | `http_request_completed` | `method`, `route` (pattern), `status`, `durationMs`, `outcome` (`success`/`redirect`/`client_error`/`server_error`), `traceId`; level `error` for 5xx. Health probes skipped; `REQUEST_LOG=false` turns it off |
| Unhandled render/route error (`onRequestError`) | `request_failed` | `digest` (also as `errorCode`, so Loki can find it), `route`, `requestId`, stack |
| Handled unexpected error (`reportError`, `src/lib/http-errors.ts`) | `<name>_failed` | `status`, `outcome=error`, `errorType`, stack, `requestId` |
| Plain console output from Next and libraries | `console_error`, `console_warn`, `console_info` | rewritten as JSON in production (`jsonConsole()` in `log.ts`; `LOG_FORMAT=text` keeps plain output) |
| Uncaught exception | `uncaught_exception` | stack (observed only; Node/Next behaviour unchanged) |

Next.js runs the proxy in a `handleRequest` pass of its own (`next.bubble`) that always reports 200. That pass is
not a request line and not a request metric; answers decided by the proxy are counted as `route="proxy"` with
their real status. (Before this change every rendered request was counted twice, once as a ~1 ms 200.)

**Error responses.** Expected failures (`PostError`, `PracticeError`, any error with a 4xx `status`) answer with
their own message. Unexpected ones are logged once and answer without internals:

- `/api/*` JSON: `{ "error": "Something went wrong…", "code": "internal", "reference": "<trace id>" }`
  (`/api/v1` keeps its envelope: `{ "error": { "message", "code", "reference" } }`). Routes without their own
  handling are wrapped in `handleErrors(name, handler)`.
- Server actions (admin `flash`, account, comments, contact): the message ends with `Reference: <trace id>`.
- Pages: `error.tsx` / `global-error.tsx` show the digest; search Loki for `errorCode="<digest>"`.

The reference is the trace id (kept by the collector); without tracing it falls back to the request id. The
proxy forwards `x-request-id` to the app (an upstream value is kept only if it matches `[A-Za-z0-9._:-]{8,128}`).
Errors logged at level `error` also mark the active span failed.

**Custom spans** (`src/lib/trace.ts`): `r2.*`, `s3.*` (legacy), `ses.*`, `bedrock.*` per AWS SDK call;
`mail.send`; `job <kind>` per queued job; `backup.run`; `startup.migrate`. `fetch` (Gemini, Turnstile, IndexNow)
is traced by `@vercel/otel`. Database queries are not traced: Drizzle's built-in tracing would put SQL and
parameters on spans, and postgres.js has no safe hook.

## Alerts (Prometheus, `tools/observability/prometheus/files/alerts.yml`)

`JithendarComDown` (no pod scraped for 5 min), `JithendarComHighErrorRatio` (> 5 % 5xx for 5 min),
`JithendarComSlow` (p95 > 2 s for 10 min). They show in Prometheus → Alerts; no Alertmanager delivers them.

## Rolling it out

1. Deploy the site (`./deploy.sh`: new image + `k8s/` metrics port, NetworkPolicy rule, `70-observability.yaml`).
2. Push the `tools` repo: Argo CD then updates Alloy (namespace `jithendar`), Prometheus (scrape job, alerts) and
   Grafana (folder, dashboards, Loki trace links).
3. Check: Prometheus → Status → Targets shows `jithendar-com` (2 up); Grafana → Jithendar.com dashboards.
