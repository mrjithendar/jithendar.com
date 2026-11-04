import { log } from "./log";

/**
 * One JSON line per finished request, from the `BaseServer.handleRequest` span Next.js ends when the response is
 * sent: final status, duration and the route *pattern*, with the trace id that links it to the proxy's access
 * line (same trace), the app's own log lines and the trace in Jaeger. All of `event`, `method`, `route`,
 * `status`, `durationMs`, `outcome` and `traceId` survive the cluster's log collector (see lib/log.ts), so
 * Loki can answer "which routes fail or are slow" without the metrics.
 *
 * Health probes are skipped (two per pod every 10 s). REQUEST_LOG=false turns the lines off.
 */

type EndedSpan = {
  attributes: Record<string, unknown>;
  duration: [number, number];
  spanContext(): { traceId: string; spanId: string };
  parentSpanContext?: { spanId: string; isRemote?: boolean };
};

const HEALTH = /^\/api\/health(?:$|\?)/;

/**
 * Paths that carry a secret in a segment are logged without it: Better Auth's password-reset link
 * (/api/auth/reset-password/<token>, a bearer credential until used) and draft previews (/preview/<token>).
 * Used by the proxy's access line and onRequestError; the log collector keeps `route` as it is.
 */
const SECRET_SEGMENT = /^(\/api\/auth\/reset-password|\/preview)\/[^/?]+/;
export const loggedPath = (pathname: string) => pathname.replace(SECRET_SEGMENT, "$1/:token");

/** Kubelet probes (/api/health): no trace, no request line, no access line, no request metric. */
export const isHealthProbe = (target: unknown) => typeof target === "string" && HEALTH.test(target);

/**
 * Next.js runs the proxy in a handleRequest pass of its own (`next.bubble`), before the render pass of the same
 * trace. That span always says 200 (even when the proxy answered with a redirect, 410 or 503) and lasts only as
 * long as the proxy, so it is neither a request line nor a request metric. Proxy-decided responses get their
 * real status in the proxy's access line and metrics (src/proxy.ts).
 */
export const isProxyPass = (attributes: Record<string, unknown>) => attributes["next.bubble"] === true;

export function outcomeOf(status: number): "success" | "redirect" | "client_error" | "server_error" {
  if (status >= 500) return "server_error";
  if (status >= 400) return "client_error";
  if (status >= 300) return "redirect";
  return "success";
}

/**
 * Uncaught exceptions as JSON lines with the stack. Next.js already logs unhandled rejections through console.error
 * (JSON once jsonConsole() is on). The monitor only observes: what Node or Next does afterwards is unchanged.
 */
export function logUncaughtExceptions() {
  const g = globalThis as { __uncaughtLogged?: boolean };
  if (g.__uncaughtLogged) return;
  g.__uncaughtLogged = true;
  process.on("uncaughtExceptionMonitor", (err, origin) => log.error("uncaught exception", { err, origin, event: "uncaught_exception" }));
}

export const requestLogSpanProcessor = {
  onStart() {},
  onEnd(span: EndedSpan) {
    if (process.env.REQUEST_LOG === "false") return;
    const a = span.attributes;
    if (a["next.span_type"] !== "BaseServer.handleRequest" || isProxyPass(a)) return;
    const target = typeof a["http.target"] === "string" ? a["http.target"] : "";
    if (isHealthProbe(target)) return;
    const status = Number(a["http.status_code"] ?? 0);
    const [s, ns] = span.duration;
    const { traceId, spanId } = span.spanContext();
    const fields = {
      event: "http_request_completed",
      method: String(a["http.method"] ?? "OTHER"),
      // The pattern (/blog/[slug]) when Next matched a route, else the path without its query.
      route: String(a["next.route"] ?? a["http.route"] ?? (loggedPath(target.split("?")[0] ?? "") || "unknown")),
      status,
      durationMs: Math.round(s * 1000 + ns / 1e6),
      outcome: outcomeOf(status),
      rsc: a["next.rsc"] === true || undefined,
      traceId,
      spanId,
    };
    if (status >= 500) log.error("request completed", fields);
    else log.info("request completed", fields);
  },
  async shutdown() {},
  async forceFlush() {},
};
