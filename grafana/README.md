# Grafana dashboards for jithendar.com

Grafana at `https://jithendar.com/grafana/`, folder **Jithendar.com**. The JSON here is the source; Argo CD's
`grafana` Application (tools repo, `deploy/minikube/applications/grafana.yaml`) turns this folder into the ConfigMap
`monitoring/grafana-dashboards-jithendar`, which Grafana loads read-only.

| Dashboard | uid | What it answers |
|---|---|---|
| **Jithendar.com · Observability** | `jithendar-com-observability` | Metrics, logs and traces on one page: find a slow or failing request, open its trace and its log lines |
| **Jithendar.com · Overview** | `jithendar-com-overview` | Traffic, latency, site counters (posts, comments, jobs), runtime |
| **Jithendar.com · Logs** | `jithendar-com-logs` | Log volume, top events, errors by type, raw lines |

## Data sources (provisioned by tools, `deploy/minikube/observability/grafana/values.yaml`)

| uid | Type | Holds |
|---|---|---|
| `roboshop-prometheus` | Prometheus | Job `jithendar-com` (`/metrics` on 9464), collector, Jaeger, Loki, Alloy, cAdvisor |
| `roboshop-loki` | Loki | Namespace `jithendar`; lines are logfmt with only allowlisted fields (`www/docs/OBSERVABILITY.md`) |
| `jaeger` | Jaeger | `jaeger.observability:16686`, services `jithendar-com`, `moks-worker` |

Jaeger 2.x serves only its `/api/v3` query API. Grafana reaches it through feature toggle
`jaegerEnableGrpcEndpoint`, which covers trace-by-id, services and operations. **Search** (by service, tags or
duration) and the **dependency graph** still use Jaeger's old REST API, so they fail in Grafana. That is why the
Observability dashboard finds requests from their completion log lines in Loki (each one carries `trace_id`,
`route`, `status` and `duration_ms`), not by Jaeger search.

## How the Observability dashboard connects the three signals

1. **Route**, **Status** and **Min duration (ms)** filter the metrics panels and the requests table.
2. The requests table lists completion lines (`event=http_request_completed`). Clicking a trace id sets the
   **Trace id** variable: the trace panel shows that trace from Jaeger, and *Log lines of this trace* shows every Loki
   line with the same id (access line, app lines, completion line, practice-executor audit lines).
3. Each trace id cell also opens the trace in Explore. In any logs panel, a line's details have a *TraceID* link that
   opens the trace in Grafana. Span details in the trace view link back to the logs (trace to logs, set on the Jaeger
   data source).
4. *Telemetry pipeline* shows whether data is arriving: spans received, sent and stored, lines shipped or dropped
   by Alloy, scrape targets, Jaeger's memory.

A visitor's "Reference: …" on an error page is the trace id: paste it into **Trace id**.

Jaeger keeps the newest 5000 traces in memory and loses all of them on a restart, so trace links on old log lines
stop resolving. The logs and metrics stay.

## Editing

Grafana loads these dashboards read-only (`editable: false`, `allowUiUpdates: false`). To change one: edit it in
Grafana (Save is refused, but **Export → Save to file** works), replace the JSON here, then run
`python3 scripts/check-dashboards.py`. After the push, sync the `grafana` app in Argo CD.
