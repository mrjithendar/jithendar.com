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

## Alerts (Prometheus, `tools/deploy/minikube/observability/prometheus/files/alerts.yml`)

Site: `JithendarComDown` (no pod scraped for 5 min), `JithendarComHighErrorRatio` (> 5 % 5xx for 5 min **and** at
least 3 failures), `JithendarComSlow` (p95 > 2 s for 10 min). `/api/health` is excluded from both ratios.
Pipeline: `ObservabilityTargetDown` (Loki, Alloy, collector or Jaeger not scraped), `LogShippingDropped` (Alloy gave
up on log lines), `TraceSpansLost` (collector or Jaeger refusing/failing spans), `JaegerMemoryNearLimit` (> 90 %).
They show in Prometheus → Alerts; no Alertmanager delivers them. Each has a `runbook_url` pointing at a section below.

## Runbooks

### Site down

1. `kubectl --context mk4 -n jithendar get pods -l app=jithendar-com` — `ImagePullBackOff` with ECR 403 means the
   `ecr-pull` Secret expired (see `docs/DEPLOYMENT.md`); `OOMKilled` means memory (limit 1Gi).
2. `curl -s https://jithendar.com/api/health` — answers `{status, version}`; `version` is the running commit.
3. If pods are up but the alert fires, the metrics port is the problem: Prometheus → Status → Targets, job
   `jithendar-com`; the NetworkPolicy admits only `monitoring/app=roboshop-prometheus` on 9464.

### 5xx errors

1. Dashboard **Jithendar.com · Overview** → *5xx by route* shows which route pattern fails.
2. Loki: `{namespace="jithendar", container="web", level="error"} | logfmt` — `error_type`, `error_code` (the
   digest a visitor sees) and `trace_id`. A visitor's "Reference: <id>" is the trace id:
   `{namespace="jithendar"} |= "trace_id=<id>"`.
3. The full line with `msg` and the stack is only in the pod: `kubectl --context mk4 -n jithendar logs
   deploy/jithendar-com | grep <trace id>` (try both pods: `-l app=jithendar-com --max-log-requests=4`).
4. The trace: `kubectl --context mk4 -n observability port-forward svc/jaeger 16686`, then
   http://localhost:16686/trace/<id>. Exception text is removed by the collector; the failing span has
   `error.type` and status ERROR. Jaeger keeps the newest 5000 traces in memory, so look soon.

### Slow responses

1. Overview → *Slowest routes (p95)*; Logs → *Failed or slow requests* lists completion lines over 2 s with their
   `trace_id`.
2. Open the trace: the long child spans say where the time went (`r2.*`, `fetch POST <host>`, `job …`,
   `render route (app) …`). Database queries have no spans, so time inside a render span with no children is often
   SQL; compare with `jithendar_database_up` and the Postgres pod's CPU.
3. Check the pod: *Event-loop delay (p99)* and *CPU throttling* panels.

## Rolling it out

1. Deploy the site: `./deploy.sh` (new image + `k8s/`, including the `strip-trace-headers` middleware on the
   `jithendar-com` Ingress).
2. Push the `tools` repo, then sync `loki`, `prometheus` and `grafana` in Argo CD (Alloy patterns, scrape jobs,
   alerts, dashboards).
3. The collector and Jaeger have no Argo CD Application: `kubectl --context mk4 apply -k
   deploy/minikube/observability/otel-collector` and `… -k deploy/minikube/observability/jaeger` from `tools`.
   Jaeger restarts with an empty store (it is in memory).
4. Check: Prometheus → Targets shows `jithendar-com` (2 up), `otel-collector` and `jaeger` up; Jaeger has no new
   `GET /api/health` traces; `{namespace="jithendar"} |= "route=/api/health"` returns nothing new; completion lines
   for `/blog/[slug]` carry `route=`.

## Review fixes (2026-11-04, second round)

Found on mk4 and fixed in code (the site fixes need a deploy; the `tools` ones a push/sync, see "Rolling it out"):

- **Health probes were most of the telemetry.** About 1,080 of ~2,300 requests an hour were kubelet probes: one
  8-span trace each in Jaeger, one access line each in Loki, and half of every request-rate and p95 figure. Now
  `requestSampler` (`src/lib/tracing-config.ts`) does not trace `/api/health`, so it has no spans, metrics or
  completion line, and the proxy writes no access line for it.
- **Visitors could steer tracing.** Next.js continues any incoming `traceparent`: a request with
  `traceparent: 00-<id>-…-01` got that trace id (and it became the visitor's error reference); `…-00` would have
  turned off the trace, the request metric and the completion line. The ingress now strips
  `traceparent`/`tracestate`/`baggage` (`k8s/40-middlewares.yaml`, `strip-trace-headers`), and the sampler ignores
  remote sampling flags.
- **Outgoing span names held full URLs:** `http GET https://<account>.r2.cloudflarestorage.com/<bucket>/<key>?…`,
  and a ~95 kB `fetch GET data:…base64` name from the OG image renderer. Names are now `<kind> <METHOD> <host>`
  (`outboundSpanNames`), `resource.name` is the host, `data:` URLs are not traced.
- **Trace context to the practice executor.** Only `PRACTICE_EXECUTOR_URL` receives `traceparent`; the executor
  writes its `trace_id` on `job.submitted`/`job.cancel_requested` audit lines, so one Loki search covers both.
- **Password-reset tokens in logs.** `/api/auth/reset-password/<token>` was logged as the access line's `route`
  (which reaches Loki) and as `path` in `request_failed`. Both, and draft preview tokens, are now `…/:token`
  (`loggedPath`). None were found in the last 72 h of pod logs.
- **Collector side (`tools`):** Alloy dropped `route` for every pattern with brackets (`/blog/[slug]`) and every
  `outcome` except `success`; Jaeger was OOMKilled 11 times at 256Mi with no trace cap (now `max_traces: 5000`,
  384Mi); the collector's own metrics were unreachable; Alloy dropped 541,189 log lines on 2026-11-02 (Loki: "Ingester
  is shutting down") with no alert. See the alerts above.

`route="other"` is mostly static files and the image optimizer: `/_next/image` fetches `/media/[id]/[name]` inside
the same process, so one image is one `other` request plus one `/media/[id]/[name]` request in the same trace.
