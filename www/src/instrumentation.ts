import type { Instrumentation } from "next";

/** Runs once per server start, before requests are served. */
export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;
  const { log } = await import("./lib/log");

  // Spans are always recorded: request metrics are derived from them. They are exported to the
  // OpenTelemetry collector (OTLP/HTTP, e.g. http://otel-collector.observability:4318) when configured.
  const { registerOTel } = await import("@vercel/otel");
  const { metricsSpanProcessor, startMetricsServer } = await import("./lib/metrics");
  registerOTel({ serviceName: process.env.OTEL_SERVICE_NAME ?? "jithendar-com", spanProcessors: ["auto", metricsSpanProcessor] });
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
  const started = Date.now();
  const applied = await migrateDb(await getDb());
  log.info("database ready", { migrationsApplied: applied, ms: Date.now() - started });

  const { startBackupScheduler } = await import("./lib/backups");
  startBackupScheduler();

  // Scheduled publishing and the job queue (IndexNow submissions with retries).
  const { startWorker } = await import("./lib/scheduler");
  startWorker();

  // Warm the caches so the first visitor gets a fast page, not a cold one.
  const { warmCaches } = await import("./lib/warm");
  void warmCaches().catch((err) => log.warn("cache warm-up failed", { err }));
}

/** Every unhandled server error, as one structured log line with route and trace ids. */
export const onRequestError: Instrumentation.onRequestError = async (error, request, context) => {
  const { log } = await import("./lib/log");
  const digest = (error as { digest?: string }).digest;
  log.error("request failed", {
    err: error,
    digest,
    method: request.method,
    path: request.path,
    route: context.routePath,
    requestId: (request.headers["x-request-id"] as string | undefined) ?? undefined,
    routePath: context.routePath,
    routeType: context.routeType,
    renderSource: context.renderSource,
  });
};
