import type { Instrumentation } from "next";

/** Runs once per server start, before requests are served. */
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  const { jsonConsole, log } = await import("./lib/log");
  // Every stdout/stderr line as JSON in production (Next's own "⨯ Error" output included).
  if (process.env.NODE_ENV === "production") jsonConsole();
  const { logUncaughtExceptions } = await import("./lib/request-log");
  logUncaughtExceptions();

  // Spans are always recorded: request metrics are derived from them. They are exported to the
  // OpenTelemetry collector (OTLP/HTTP, e.g. http://otel-collector.observability:4318) when configured.
  const { registerOTel } = await import("@vercel/otel");
  const { metricsSpanProcessor, startMetricsServer } = await import("./lib/metrics");
  const { requestLogSpanProcessor } = await import("./lib/request-log");
  registerOTel({
    serviceName: process.env.OTEL_SERVICE_NAME ?? "jithendar-com",
    attributes: { "service.version": process.env.GIT_SHA ?? "dev", "deployment.environment": process.env.APP_ENV ?? process.env.NODE_ENV ?? "development" },
    spanProcessors: ["auto", metricsSpanProcessor, requestLogSpanProcessor],
  });
  if (process.env.OTEL_EXPORTER_OTLP_ENDPOINT) log.info("tracing enabled", { event: "tracing_enabled", endpoint: process.env.OTEL_EXPORTER_OTLP_ENDPOINT });

  // Prometheus metrics on a separate, cluster-internal port (METRICS_PORT, default 9464; 0 = off).
  const metricsPort = await startMetricsServer().catch((err) => {
    log.warn("metrics listener unavailable", { err });
    return null;
  });
  if (metricsPort) log.info("metrics listening", { event: "metrics_listening", port: metricsPort });

  const { listenForInvalidations } = await import("./lib/cache-bus");
  await listenForInvalidations().catch((err) => log.warn("cache invalidation listener unavailable", { err }));

  if (!process.env.DATABASE_URL) return;
  const { getDb } = await import("./db");
  const { migrateDb } = await import("./db/migrate");
  const { withSpan } = await import("./lib/trace");
  const started = Date.now();
  const applied = await withSpan("startup.migrate", {}, async () => migrateDb(await getDb()));
  log.info("database ready", { migrationsApplied: applied, ms: Date.now() - started });

  // Python practice catalog (content/python-practice/catalog.generated.json): new and changed problems.
  const { ensurePracticeSeeded } = await import("./lib/practice/seed");
  await ensurePracticeSeeded().catch((err) => log.warn("practice catalog seed failed", { err }));

  const { startBackupScheduler } = await import("./lib/backups");
  startBackupScheduler();

  // Scheduled publishing and the job queue (IndexNow submissions with retries).
  const { startWorker } = await import("./lib/scheduler");
  startWorker();

  // Warm the caches so the first visitor gets a fast page, not a cold one.
  const { warmCaches } = await import("./lib/warm");
  void warmCaches().catch((err) => log.warn("cache warm-up failed", { err }));
}

/**
 * Every unhandled server error (pages, layouts, route handlers, server actions), as one structured log line.
 * `digest` is the reference error.tsx/global-error.tsx show the visitor; the line also carries the request id
 * (set by the proxy) and the trace id, and the active span is marked failed.
 */
export const onRequestError: Instrumentation.onRequestError = async (error, request, context) => {
  const { log } = await import("./lib/log");
  const digest = (error as { digest?: string }).digest;
  const requestId = request.headers["x-request-id"];
  log.error("request failed", {
    err: error,
    errorCode: digest && /^[A-Za-z0-9_.]{1,80}$/.test(digest) ? digest : undefined,
    digest,
    method: request.method,
    path: request.path.split("?")[0],
    route: context.routePath,
    status: 500,
    outcome: "error",
    requestId: typeof requestId === "string" ? requestId : undefined,
    routeType: context.routeType,
    renderSource: context.renderSource,
    revalidateReason: context.revalidateReason,
  });
};
