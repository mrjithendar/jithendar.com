import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { setDbForTests } from "@/db";
import { freshDb } from "./db-helpers";

const span = (attributes: Record<string, unknown>, seconds: number) => ({ attributes, duration: [Math.floor(seconds), Math.round((seconds % 1) * 1e9)] as [number, number] });

beforeEach(() => {
  delete (globalThis as { __metrics?: unknown }).__metrics;
});
afterEach(() => {
  vi.restoreAllMocks();
  setDbForTests(undefined);
});

describe("request metrics from Next.js server spans", () => {
  it("counts requests by method, route pattern and status class, with a latency histogram", async () => {
    const { metricsSpanProcessor, renderMetrics } = await import("@/lib/metrics");
    const root = { "next.span_type": "BaseServer.handleRequest", "http.method": "GET", "next.route": "/blog/[slug]" };
    metricsSpanProcessor.onEnd(span({ ...root, "http.status_code": 200 }, 0.08));
    metricsSpanProcessor.onEnd(span({ ...root, "http.status_code": 200 }, 0.3));
    metricsSpanProcessor.onEnd(span({ ...root, "http.status_code": 503 }, 1.2));
    // Child spans and unknown methods/routes are not request metrics / are grouped.
    metricsSpanProcessor.onEnd(span({ "next.span_type": "AppRender.getBodyResult", "http.method": "GET" }, 5));
    metricsSpanProcessor.onEnd(span({ "next.span_type": "BaseServer.handleRequest", "http.method": "BREW", "http.status_code": 404 }, 0.01));

    const text = await renderMetrics();
    expect(text).toContain('http_server_requests_total{method="GET",route="/blog/[slug]",status="2xx"} 2');
    expect(text).toContain('http_server_requests_total{method="GET",route="/blog/[slug]",status="5xx"} 1');
    expect(text).toContain('http_server_requests_total{method="OTHER",route="other",status="4xx"} 1');
    expect(text).toContain('http_server_request_duration_seconds_bucket{method="GET",route="/blog/[slug]",le="0.1"} 1');
    expect(text).toContain('http_server_request_duration_seconds_bucket{method="GET",route="/blog/[slug]",le="+Inf"} 3');
    expect(text).toContain('http_server_request_duration_seconds_count{method="GET",route="/blog/[slug]"} 3');
    expect(text).not.toContain("AppRender");
  });

  it("keeps label values bounded and escaped", async () => {
    const { recordRequest, renderMetrics } = await import("@/lib/metrics");
    recordRequest("GET", "/" + "x".repeat(200), 200, 0.1);
    recordRequest("GET", 'not-a-path"\n', 200, 0.1);
    const text = await renderMetrics();
    expect(text).toContain('route="other",status="2xx"} 2');
    expect(text).not.toMatch(/x{150}/);
  });

  it("exposes process, email, comment and database figures in Prometheus text format", async () => {
    await freshDb();
    const { recordMail, recordComment, renderMetrics } = await import("@/lib/metrics");
    recordMail("mailgun", "sent");
    recordMail("mailgun", "failed");
    recordComment("pending");
    const text = await renderMetrics();
    for (const line of [
      "# TYPE http_server_requests_total counter",
      "# TYPE http_server_request_duration_seconds histogram",
      'jithendar_mail_sent_total{provider="mailgun",outcome="sent"} 1',
      'jithendar_comments_submitted_total{status="pending"} 1',
      "jithendar_posts_published 0",
      "jithendar_comments_pending 0",
      "jithendar_database_up 1",
      "process_resident_memory_bytes ",
      "nodejs_eventloop_delay_p99_seconds ",
    ]) {
      expect(text).toContain(line);
    }
    expect(text).toMatch(/jithendar_build_info\{version="[^"]+",node="v\d+/);
    expect(text.endsWith("\n")).toBe(true);
  });

  it("serves /metrics on its own port and nothing else", async () => {
    vi.stubEnv("METRICS_PORT", "0");
    const { startMetricsServer } = await import("@/lib/metrics");
    expect(await startMetricsServer()).toBeNull();
    vi.stubEnv("METRICS_PORT", "39464");
    expect(await startMetricsServer()).toBe(39464);
    const ok = await fetch("http://127.0.0.1:39464/metrics");
    expect(ok.status).toBe(200);
    expect(ok.headers.get("content-type")).toContain("text/plain; version=0.0.4");
    expect((await fetch("http://127.0.0.1:39464/")).status).toBe(404);
    expect((await fetch("http://127.0.0.1:39464/metrics", { method: "POST" })).status).toBe(404);
    vi.unstubAllEnvs();
  });
});

describe("structured logs for the cluster's log collector", () => {
  it("adds a stable event name and the error type, which the collector keeps", async () => {
    const lines: string[] = [];
    vi.spyOn(console, "log").mockImplementation((l: string) => void lines.push(l));
    vi.spyOn(console, "error").mockImplementation((l: string) => void lines.push(l));
    const { log, eventOf } = await import("@/lib/log");
    expect(eventOf("comment submitted")).toBe("comment_submitted");
    expect(eventOf("Mail send failed!")).toBe("mail_send_failed");
    expect(eventOf("404 page")).toBe("log_404_page");

    log.info("post published", { route: "/blog/[slug]" });
    class PostError extends Error {}
    const err = Object.assign(new PostError("nope"), { code: "ECONNREFUSED" });
    log.error("mail send failed", { err });
    log.info("custom", { event: "http_request" });

    const [a, b, c] = lines.map((l) => JSON.parse(l) as Record<string, unknown>);
    expect(a).toMatchObject({ event: "post_published", level: "info", route: "/blog/[slug]", service: "jithendar-com" });
    expect(b).toMatchObject({ event: "mail_send_failed", level: "error", errorType: "PostError", errorCode: "ECONNREFUSED" });
    expect(c).toMatchObject({ event: "http_request" });
    // The collector's patterns: event [A-Za-z][A-Za-z0-9_.:/-]{0,119}, error type [A-Za-z0-9_.$]{1,80}.
    for (const l of [a, b, c]) expect(String(l!.event)).toMatch(/^[A-Za-z][A-Za-z0-9_.:/-]{0,119}$/);
    expect(String(b!.errorType)).toMatch(/^[A-Za-z0-9_.$]{1,80}$/);
  });
});
