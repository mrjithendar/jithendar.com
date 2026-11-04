import { afterEach, describe, expect, it, vi } from "vitest";
import { NextRequest } from "next/server";

vi.mock("server-only", () => ({}));

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllEnvs();
});

/** Every JSON line written through console.error / console.log during `fn`. */
async function captureLogs(fn: () => unknown | Promise<unknown>) {
  const lines: Record<string, unknown>[] = [];
  const grab = (line: unknown) => {
    if (typeof line === "string" && line.startsWith("{")) lines.push(JSON.parse(line));
  };
  vi.spyOn(console, "error").mockImplementation(grab);
  vi.spyOn(console, "log").mockImplementation(grab);
  vi.spyOn(process.stdout, "write").mockImplementation((chunk) => (grab(String(chunk).trim()), true));
  await fn();
  return lines;
}

describe("route handler errors", () => {
  it("turns an unexpected error into a logged JSON 500 with a reference, never the internals", async () => {
    const { handleErrors } = await import("@/lib/http-errors");
    const GET = handleErrors("thing export", async (req: Request) => {
      void req;
      throw new Error("connection to 10.0.0.5 refused");
    });
    let res!: Response;
    const lines = await captureLogs(async () => {
      res = await GET(new Request("https://jithendar.com/api/admin/thing?x=1", { headers: { "x-request-id": "req-12345678" } }));
    });
    expect(res.status).toBe(500);
    const body = await res.json();
    expect(body).toEqual({ error: "Something went wrong. The error has been logged.", code: "internal", reference: "req-12345678" });
    expect(JSON.stringify(body)).not.toContain("10.0.0.5");
    expect(res.headers.get("x-request-id")).toBe("req-12345678");
    expect(lines).toHaveLength(1);
    expect(lines[0]).toMatchObject({
      level: "error",
      event: "thing_export_failed",
      route: "/api/admin/thing",
      method: "GET",
      status: 500,
      outcome: "error",
      requestId: "req-12345678",
      errorType: "Error",
    });
    expect((lines[0]!.error as { stack: string }).stack).toContain("connection to 10.0.0.5 refused");
  });

  it("answers known 4xx errors with their own message and does not log them as failures", async () => {
    const { handleErrors } = await import("@/lib/http-errors");
    const { PostError } = await import("@/lib/posts");
    const POST = handleErrors("thing", async (req: Request) => {
      void req;
      throw new PostError("Title is required.", 422);
    });
    let res!: Response;
    const lines = await captureLogs(async () => {
      res = await POST(new Request("https://jithendar.com/api/thing", { method: "POST" }));
    });
    expect(res.status).toBe(422);
    expect(await res.json()).toEqual({ error: "Title is required." });
    expect(lines).toHaveLength(0);
  });

  it("lets redirect() and notFound() through untouched", async () => {
    const { handleErrors } = await import("@/lib/http-errors");
    const redirect = Object.assign(new Error("NEXT_REDIRECT"), { digest: "NEXT_REDIRECT;replace;/;307;" });
    const GET = handleErrors("thing", async (req: Request) => {
      void req;
      throw redirect;
    });
    await expect(GET(new Request("https://jithendar.com/x"))).rejects.toBe(redirect);
  });

  it("adds the reference to messages shown in the UI", async () => {
    const { withReference } = await import("@/lib/http-errors");
    expect(withReference("Something went wrong.", { reference: "abc", requestId: undefined, traceId: undefined })).toBe("Something went wrong. Reference: abc");
    expect(withReference("Something went wrong.", { reference: undefined, requestId: undefined, traceId: undefined })).toBe("Something went wrong.");
  });
});

describe("request completion log from the Next.js server span", () => {
  const span = (attributes: Record<string, unknown>, seconds: number) => ({
    attributes,
    duration: [Math.floor(seconds), Math.round((seconds % 1) * 1e9)] as [number, number],
    spanContext: () => ({ traceId: "0af7651916cd43dd8448eb211c80319c", spanId: "b7ad6b7169203331" }),
  });

  it("writes one line per request with status, duration, outcome and trace id", async () => {
    const { requestLogSpanProcessor } = await import("@/lib/request-log");
    const root = { "next.span_type": "BaseServer.handleRequest", "http.method": "GET", "next.route": "/blog/[slug]", "http.target": "/blog/hello?utm=x" };
    const lines = await captureLogs(() => {
      requestLogSpanProcessor.onEnd(span({ ...root, "http.status_code": 200 }, 0.125));
      requestLogSpanProcessor.onEnd(span({ ...root, "http.status_code": 503 }, 1.5));
      // Child spans, the proxy's own pass (always "200") and health probes are not request lines.
      requestLogSpanProcessor.onEnd(span({ "next.span_type": "AppRender.getBodyResult" }, 1));
      requestLogSpanProcessor.onEnd(span({ "next.span_type": "BaseServer.handleRequest", "next.bubble": true, "http.method": "GET", "http.target": "/blog/hello", "http.status_code": 200 }, 0.001));
      requestLogSpanProcessor.onEnd(span({ ...root, "next.route": undefined, "http.target": "/api/health", "http.status_code": 200 }, 0.001));
    });
    expect(lines).toHaveLength(2);
    expect(lines[0]).toMatchObject({ level: "info", event: "http_request_completed", method: "GET", route: "/blog/[slug]", status: 200, durationMs: 125, outcome: "success", traceId: "0af7651916cd43dd8448eb211c80319c" });
    expect(lines[1]).toMatchObject({ level: "error", status: 503, durationMs: 1500, outcome: "server_error" });
  });

  it("falls back to the path without the query when Next matched no route, and can be turned off", async () => {
    const { requestLogSpanProcessor } = await import("@/lib/request-log");
    const attrs = { "next.span_type": "BaseServer.handleRequest", "http.method": "GET", "http.target": "/wp-login.php?x=1", "http.status_code": 404 };
    const lines = await captureLogs(() => requestLogSpanProcessor.onEnd(span(attrs, 0.01)));
    expect(lines[0]).toMatchObject({ route: "/wp-login.php", outcome: "client_error" });
    vi.stubEnv("REQUEST_LOG", "false");
    expect(await captureLogs(() => requestLogSpanProcessor.onEnd(span(attrs, 0.01)))).toHaveLength(0);
  });
});

describe("JSON console", () => {
  it("rewrites plain console output from Next and libraries as JSON lines and passes JSON through", async () => {
    const written: string[] = [];
    vi.spyOn(console, "error").mockImplementation((line: unknown) => void written.push(String(line)));
    vi.spyOn(console, "log").mockImplementation((line: unknown) => void written.push(String(line)));
    const saved = { log: console.log, info: console.info, debug: console.debug, warn: console.warn, error: console.error };
    const { jsonConsole } = await import("@/lib/log");
    try {
      jsonConsole();
      console.error(" ⨯ \u001b[31mError: boom\u001b[39m", new TypeError("boom"));
      console.warn("deprecated option");
      console.log('{"already":"json"}');
    } finally {
      Object.assign(console, saved);
      delete (console as { __json?: boolean }).__json;
    }
    expect(written).toHaveLength(3);
    const [err, warn, passthrough] = written.map((l) => JSON.parse(l));
    expect(err).toMatchObject({ level: "error", event: "console_error", msg: "Error: boom", errorType: "TypeError" });
    expect(warn).toMatchObject({ level: "warn", event: "console_warn", msg: "deprecated option" });
    expect(passthrough).toEqual({ already: "json" });
  });
});

describe("proxy request ids", () => {
  it("forwards the request id to the app and echoes it, replacing unsafe upstream values", async () => {
    vi.stubEnv("ACCESS_LOG", "false");
    vi.doMock("@/lib/site-config/maintenance", async (orig) => ({ ...(await orig<object>()), maintenanceState: async () => ({ enabled: false }) }));
    const { proxy } = await import("@/proxy");
    const ok = await proxy(new NextRequest("https://jithendar.com/blog", { headers: { "x-request-id": "edge-abcdef12" } }));
    expect(ok.headers.get("x-request-id")).toBe("edge-abcdef12");
    // NextResponse.next({ request: { headers } }) passes overridden request headers to the app this way.
    expect(ok.headers.get("x-middleware-request-x-request-id")).toBe("edge-abcdef12");

    const forged = await proxy(new NextRequest("https://jithendar.com/blog", { headers: { "x-request-id": '"},"level":"error' } }));
    expect(forged.headers.get("x-request-id")).toMatch(/^[0-9a-f-]{36}$/);
    // Proxy-decided answers are counted with their real status (Next's span for that pass says 200).
    delete (globalThis as { __metrics?: unknown }).__metrics;
    await proxy(new NextRequest("https://jithendar.com/blog/"));
    const { renderMetrics } = await import("@/lib/metrics");
    expect(await renderMetrics()).toContain('http_server_requests_total{method="GET",route="proxy",status="3xx"} 1');
    vi.doUnmock("@/lib/site-config/maintenance");
  });
});
