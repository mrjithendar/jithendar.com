import { monitorEventLoopDelay } from "node:perf_hooks";

/**
 * Prometheus metrics for the site, without extra dependencies.
 *
 * - HTTP request rate, errors and latency per route come from the server spans Next.js already creates
 *   (one `BaseServer.handleRequest` span per request, with method, status code and the route *pattern*,
 *   e.g. `/blog/[slug]`, so label values stay bounded). See `metricsSpanProcessor`.
 * - Process health (memory, CPU, event-loop delay) and a few counters (emails, comments).
 * - Site gauges read from the database at scrape time (cached 30 s).
 *
 * Served on a separate port (METRICS_PORT, default 9464; 0 = off) that is reachable only inside the
 * cluster (NetworkPolicy), never through the public ingress.
 * No `server-only` import: instrumentation.ts loads this outside the React server layer. The registry lives on
 * globalThis, so the instrumentation bundle and the app bundles share one set of counters.
 */

type Labels = Record<string, string>;
const DURATION_BUCKETS = [0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10];

const key = (labels: Labels) => JSON.stringify(Object.entries(labels).sort(([a], [b]) => a.localeCompare(b)));
const escape = (v: string) => v.replace(/\\/g, "\\\\").replace(/\n/g, "\\n").replace(/"/g, '\\"');
const fmt = (labels: Labels) => {
  const parts = Object.entries(labels).map(([k, v]) => `${k}="${escape(v)}"`);
  return parts.length ? `{${parts.join(",")}}` : "";
};

class Counter {
  private values = new Map<string, { labels: Labels; value: number }>();
  constructor(
    readonly name: string,
    readonly help: string,
  ) {}
  inc(labels: Labels = {}, by = 1) {
    const k = key(labels);
    const v = this.values.get(k) ?? { labels, value: 0 };
    v.value += by;
    this.values.set(k, v);
  }
  render(): string {
    const lines = [`# HELP ${this.name} ${this.help}`, `# TYPE ${this.name} counter`];
    for (const { labels, value } of this.values.values()) lines.push(`${this.name}${fmt(labels)} ${value}`);
    return lines.join("\n");
  }
}

class Histogram {
  private values = new Map<string, { labels: Labels; buckets: number[]; sum: number; count: number }>();
  constructor(
    readonly name: string,
    readonly help: string,
    readonly bounds: number[],
  ) {}
  observe(labels: Labels, value: number) {
    const k = key(labels);
    const v = this.values.get(k) ?? { labels, buckets: this.bounds.map(() => 0), sum: 0, count: 0 };
    this.bounds.forEach((b, i) => {
      if (value <= b) v.buckets[i]! += 1;
    });
    v.sum += value;
    v.count += 1;
    this.values.set(k, v);
  }
  render(): string {
    const lines = [`# HELP ${this.name} ${this.help}`, `# TYPE ${this.name} histogram`];
    for (const { labels, buckets, sum, count } of this.values.values()) {
      this.bounds.forEach((b, i) => lines.push(`${this.name}_bucket${fmt({ ...labels, le: String(b) })} ${buckets[i]}`));
      lines.push(`${this.name}_bucket${fmt({ ...labels, le: "+Inf" })} ${count}`);
      lines.push(`${this.name}_sum${fmt(labels)} ${sum}`);
      lines.push(`${this.name}_count${fmt(labels)} ${count}`);
    }
    return lines.join("\n");
  }
}

const gauge = (name: string, help: string, samples: { labels?: Labels; value: number }[]) =>
  [`# HELP ${name} ${help}`, `# TYPE ${name} gauge`, ...samples.map((s) => `${name}${fmt(s.labels ?? {})} ${s.value}`)].join("\n");

// One registry per process (survives hot reloads in development).
type Registry = {
  requests: Counter;
  duration: Histogram;
  mail: Counter;
  comments: Counter;
  loop: ReturnType<typeof monitorEventLoopDelay>;
};
const g = globalThis as unknown as { __metrics?: Registry };
function registry(): Registry {
  if (!g.__metrics) {
    const loop = monitorEventLoopDelay({ resolution: 20 });
    loop.enable();
    g.__metrics = {
      requests: new Counter("http_server_requests_total", "HTTP requests handled by Next.js, by method, route pattern and status code."),
      duration: new Histogram("http_server_request_duration_seconds", "Time to handle an HTTP request, by method and route pattern.", DURATION_BUCKETS),
      mail: new Counter("jithendar_mail_sent_total", "Transactional emails by provider and outcome."),
      comments: new Counter("jithendar_comments_submitted_total", "Comments and replies submitted, by resulting status."),
      loop,
    };
  }
  return g.__metrics;
}

/** Status code → class label ("2xx"…"5xx") keeps one series per class instead of per code. */
const statusClass = (code: unknown) => (typeof code === "number" && code >= 100 && code < 600 ? `${Math.floor(code / 100)}xx` : "unknown");

/** Route patterns only; anything else (e.g. static files without a route) is grouped. */
function routeLabel(route: unknown): string {
  if (typeof route !== "string" || !route.startsWith("/") || route.length > 120) return "other";
  return route;
}

export function recordRequest(method: string, route: unknown, status: unknown, seconds: number) {
  const r = registry();
  const m = /^(GET|HEAD|POST|PUT|PATCH|DELETE|OPTIONS)$/.test(method) ? method : "OTHER";
  const labels = { method: m, route: routeLabel(route) };
  r.requests.inc({ ...labels, status: statusClass(status) });
  r.duration.observe(labels, seconds);
}

export function recordMail(provider: string, outcome: "sent" | "failed" | "skipped") {
  registry().mail.inc({ provider, outcome });
}

export function recordComment(status: "approved" | "pending") {
  registry().comments.inc({ status });
}

/** The minimal SpanProcessor shape (avoids depending on @opentelemetry/sdk-trace-base directly). */
type EndedSpan = { attributes: Record<string, unknown>; duration: [number, number] };
export const metricsSpanProcessor = {
  onStart() {},
  onEnd(span: EndedSpan) {
    if (span.attributes["next.span_type"] !== "BaseServer.handleRequest") return;
    const [s, ns] = span.duration;
    recordRequest(String(span.attributes["http.method"] ?? "OTHER"), span.attributes["next.route"] ?? span.attributes["http.route"], span.attributes["http.status_code"], s + ns / 1e9);
  },
  async shutdown() {},
  async forceFlush() {},
};

// --- Database gauges (cached) ---------------------------------------------------------------------

let dbCache: { at: number; text: string } | null = null;
async function databaseGauges(): Promise<string> {
  if (dbCache && Date.now() - dbCache.at < 30_000) return dbCache.text;
  try {
    const { sql } = await import("drizzle-orm");
    const { getDb } = await import("@/db");
    const { rowsOf } = await import("@/db/rows");
    const db = await getDb();
    const one = async (q: ReturnType<typeof sql>) => Number(rowsOf<{ n: number }>(await db.execute(q))[0]?.n ?? 0);
    const [published, users, pending, reported] = await Promise.all([
      one(sql`select count(*)::int as n from post where status = 'published' and deleted_at is null`),
      one(sql`select count(*)::int as n from "user"`),
      one(sql`select count(*)::int as n from comment where status = 'pending' and deleted_at is null`),
      one(sql`select count(distinct comment_id)::int as n from comment_report where resolved_at is null`),
    ]);
    const jobs = rowsOf<{ status: string; n: number }>(await db.execute(sql`select status, count(*)::int as n from job group by status`));
    const text = [
      gauge("jithendar_posts_published", "Published posts.", [{ value: published }]),
      gauge("jithendar_users", "Registered accounts.", [{ value: users }]),
      gauge("jithendar_comments_pending", "Comments waiting for moderation.", [{ value: pending }]),
      gauge("jithendar_comments_reported", "Comments with open reports.", [{ value: reported }]),
      gauge("jithendar_jobs", "Background jobs by status.", jobs.map((j) => ({ labels: { status: j.status }, value: Number(j.n) }))),
      gauge("jithendar_database_up", "1 when the database answered the last metrics query.", [{ value: 1 }]),
    ].join("\n");
    dbCache = { at: Date.now(), text };
    return text;
  } catch {
    return gauge("jithendar_database_up", "1 when the database answered the last metrics query.", [{ value: 0 }]);
  }
}

// --- Exposition --------------------------------------------------------------------------------------

export async function renderMetrics(): Promise<string> {
  const r = registry();
  const mem = process.memoryUsage();
  const cpu = process.cpuUsage();
  const parts = [
    gauge("jithendar_build_info", "Running version (commit).", [{ labels: { version: process.env.GIT_SHA ?? "dev", node: process.version }, value: 1 }]),
    gauge("process_start_time_seconds", "Process start time (Unix seconds).", [{ value: Math.round(Date.now() / 1000 - process.uptime()) }]),
    `# HELP process_cpu_seconds_total CPU time used by the process.\n# TYPE process_cpu_seconds_total counter\nprocess_cpu_seconds_total ${(cpu.user + cpu.system) / 1e6}`,
    gauge("process_resident_memory_bytes", "Resident memory.", [{ value: mem.rss }]),
    gauge("nodejs_heap_used_bytes", "V8 heap in use.", [{ value: mem.heapUsed }]),
    gauge("nodejs_heap_total_bytes", "V8 heap allocated.", [{ value: mem.heapTotal }]),
    gauge("nodejs_eventloop_delay_p99_seconds", "Event-loop delay, 99th percentile since the last scrape.", [{ value: r.loop.percentile(99) / 1e9 }]),
    gauge("nodejs_eventloop_delay_max_seconds", "Event-loop delay, maximum since the last scrape.", [{ value: r.loop.max / 1e9 }]),
    r.requests.render(),
    r.duration.render(),
    r.mail.render(),
    r.comments.render(),
    await databaseGauges(),
  ];
  r.loop.reset();
  return parts.join("\n") + "\n";
}

/** Start the in-cluster metrics listener once per process. */
export async function startMetricsServer(): Promise<number | null> {
  const port = Number(process.env.METRICS_PORT ?? 9464);
  if (!Number.isInteger(port) || port <= 0) return null;
  const http = await import("node:http");
  const server = http.createServer((req, res) => {
    if (req.method !== "GET" || req.url?.split("?")[0] !== "/metrics") {
      res.writeHead(404).end();
      return;
    }
    renderMetrics().then(
      (body) => res.writeHead(200, { "Content-Type": "text/plain; version=0.0.4; charset=utf-8", "Cache-Control": "no-store" }).end(body),
      () => res.writeHead(500).end(),
    );
  });
  await new Promise<void>((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "0.0.0.0", () => resolve());
  });
  server.unref();
  return port;
}
