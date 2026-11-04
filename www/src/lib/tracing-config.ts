import { trace, TraceFlags, type Attributes, type Context } from "@opentelemetry/api";
import type { SamplingDecision, SamplingResult } from "@opentelemetry/sdk-trace-base";
import { isHealthProbe } from "./request-log";

/**
 * Settings for @vercel/otel in src/instrumentation.ts. Types only from sdk-trace-base: it is a peer of @vercel/otel,
 * not a dependency of the site.
 */

const NOT_RECORD = 0 as SamplingDecision;
const RECORD_AND_SAMPLED = 2 as SamplingDecision;

/**
 * Which requests are traced. Everything except health probes (kubelet asks /api/health about 18 times a minute,
 * which used to be most of the traces Jaeger kept in memory). Request metrics and the completion log line are
 * derived from spans, so probes are not counted there either.
 *
 * A remote parent never decides: Next.js continues any `traceparent` it receives, so a visitor sending
 * `…-00` would otherwise switch off the trace, the request metrics and the completion line for their own
 * request. (The ingress also strips those headers: minikube/40-middlewares.yaml.) The render pass after the proxy
 * reaches here with the proxy pass as a remote parent too; both are sampled, so the trace stays whole.
 */
export const requestSampler = {
  shouldSample(context: Context, _traceId: string, _name: string, _kind: unknown, attributes: Attributes): SamplingResult {
    if (isHealthProbe(attributes["http.target"])) return { decision: NOT_RECORD };
    const parent = trace.getSpanContext(context);
    if (parent && !parent.isRemote) return { decision: parent.traceFlags & TraceFlags.SAMPLED ? RECORD_AND_SAMPLED : NOT_RECORD };
    return { decision: RECORD_AND_SAMPLED };
  },
  toString: () => "JithendarRequestSampler",
};

/** `https://<account>.r2.cloudflarestorage.com/bucket/key?x-id=GetObject` → `<account>`-free host only. */
export function outboundHost(url: string): string {
  if (url.startsWith("data:")) return "data";
  try {
    return new URL(url).hostname.replace(/^[a-z0-9]+\.r2\.cloudflarestorage\.com$/, "r2.cloudflarestorage.com") || "unknown";
  } catch {
    return "unknown";
  }
}

type StartedSpan = { name: string; updateName(name: string): unknown };

/**
 * @vercel/otel names outgoing calls `fetch POST <full URL>` (and `http GET <full URL>` for node:http, which the
 * AWS SDK uses), so object keys, file names and query strings end up in span names, and every key is a new
 * operation in Jaeger. Rename them to `<kind> <METHOD> <host>` as they start, before anything is exported.
 */
export const outboundSpanNames = {
  onStart(span: StartedSpan) {
    const m = /^(http|fetch) ([A-Z]+) (.*)$/s.exec(span.name);
    if (m) span.updateName(`${m[1]} ${m[2]} ${outboundHost(m[3]!)}`);
  },
  onEnd() {},
  async shutdown() {},
  async forceFlush() {},
};

/**
 * Outgoing calls: `resource.name` is the host, not the URL; `data:` URLs (the OG image renderer loads WASM that
 * way, ~95 kB per span name) are not traced; the trace context goes only to the practice executor, never to third
 * parties.
 */
export function fetchInstrumentationConfig(env: Record<string, string | undefined> = process.env) {
  const executor = env.PRACTICE_EXECUTOR_URL?.trim().replace(/\/+$/, "");
  return {
    ignoreUrls: [/^data:/],
    resourceNameTemplate: "{http.host}",
    propagateContextUrls: executor ? [`${executor}/`] : [],
  };
}
