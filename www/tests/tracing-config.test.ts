import { describe, expect, it } from "vitest";
import { context, trace, TraceFlags, type SpanContext } from "@opentelemetry/api";
import { fetchInstrumentationConfig, outboundHost, outboundSpanNames, requestSampler } from "@/lib/tracing-config";
import { loggedPath } from "@/lib/request-log";

const SAMPLED = 2;
const NOT_RECORD = 0;
const parent = (flags: number, isRemote: boolean): SpanContext => ({ traceId: "4bf92f3577b34da6a3ce929d0e0e4736", spanId: "00f067aa0ba902b7", traceFlags: flags, isRemote });
const decide = (attributes: Record<string, unknown>, ctx = context.active()) => requestSampler.shouldSample(ctx, "t", "GET", 1, attributes as never).decision;

describe("request sampler", () => {
  it("drops health probes and traces everything else", () => {
    expect(decide({ "http.target": "/api/health" })).toBe(NOT_RECORD);
    expect(decide({ "http.target": "/api/health?x=1" })).toBe(NOT_RECORD);
    expect(decide({ "http.target": "/api/healthz" })).toBe(SAMPLED);
    expect(decide({ "http.target": "/blog/hello" })).toBe(SAMPLED);
    expect(decide({})).toBe(SAMPLED); // background jobs, startup
  });

  it("follows a local parent but never lets a remote traceparent switch tracing off", () => {
    const local = (flags: number) => trace.setSpanContext(context.active(), parent(flags, false));
    expect(decide({}, local(TraceFlags.NONE))).toBe(NOT_RECORD);
    expect(decide({}, local(TraceFlags.SAMPLED))).toBe(SAMPLED);
    const remote = trace.setSpanContext(context.active(), parent(TraceFlags.NONE, true));
    expect(decide({ "http.target": "/blog/hello" }, remote)).toBe(SAMPLED);
  });
});

describe("outgoing call spans", () => {
  const rename = (name: string) => {
    const span = { name, updateName(n: string) { this.name = n; } };
    outboundSpanNames.onStart(span);
    return span.name;
  };

  it("keeps only the method and host, without object keys, queries or the R2 account", () => {
    expect(rename("http GET https://a5f17e1bb4331919a2c03c1798ab055b.r2.cloudflarestorage.com/jithendar/www/media/images/2026/11/x.jpg?x-id=GetObject")).toBe(
      "http GET r2.cloudflarestorage.com",
    );
    expect(rename("fetch POST https://api.indexnow.org/indexnow?url=https://jithendar.com/x")).toBe("fetch POST api.indexnow.org");
    expect(rename(`fetch GET data:application/octet-stream;base64,${"A".repeat(5000)}`)).toBe("fetch GET data");
    expect(rename("GET /blog/[slug]")).toBe("GET /blog/[slug]");
    expect(outboundHost("not a url")).toBe("unknown");
  });

  it("propagates trace context to the practice executor only", () => {
    expect(fetchInstrumentationConfig({ PRACTICE_EXECUTOR_URL: "http://practice-executor.jithendar/" })).toMatchObject({
      propagateContextUrls: ["http://practice-executor.jithendar/"],
      resourceNameTemplate: "{http.host}",
    });
    expect(fetchInstrumentationConfig({}).propagateContextUrls).toEqual([]);
    expect(fetchInstrumentationConfig({}).ignoreUrls[0]!.test("data:application/wasm;base64,AAAA")).toBe(true);
  });
});

describe("access log paths", () => {
  it("removes secrets carried in path segments", () => {
    expect(loggedPath("/api/auth/reset-password/AbC123_token-xyz")).toBe("/api/auth/reset-password/:token");
    expect(loggedPath("/preview/abcdefghijklmnopqrstuvwx")).toBe("/preview/:token");
    expect(loggedPath("/blog/reset-password")).toBe("/blog/reset-password");
    expect(loggedPath("/api/auth/get-session")).toBe("/api/auth/get-session");
  });
});
