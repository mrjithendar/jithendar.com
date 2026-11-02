import "server-only";
import type { PracticeSettings } from "../settings";

/**
 * Model providers for the tutor. Each takes a system prompt, a user prompt and a JSON schema, and returns raw
 * text plus token usage. The model id is always configuration (Admin → Python practice → Settings); nothing
 * here assumes a particular model.
 *
 * - openai: OpenAI Chat Completions or any OpenAI-compatible endpoint (base URL), structured output via json_schema
 * - gemini: Gemini API generateContent with responseSchema (reuses GEMINI_API_KEY when no key is saved)
 * - bedrock: Amazon Bedrock Converse API with the pod's AWS credentials (env or IRSA); JSON requested in the prompt
 */
export type ModelCall = { system: string; user: string; schema: Record<string, unknown>; maxTokens: number; signal: AbortSignal };
export type ModelResult = { text: string; inputTokens: number; outputTokens: number };

export class ProviderError extends Error {
  constructor(
    message: string,
    readonly code: "timeout" | "rate_limited" | "auth" | "unavailable" | "bad_response",
    readonly retryable: boolean,
  ) {
    super(message);
  }
}

function fromStatus(status: number, provider: string): ProviderError {
  if (status === 429) return new ProviderError(`${provider} rate limit`, "rate_limited", true);
  if (status === 401 || status === 403) return new ProviderError(`${provider} rejected the credentials`, "auth", false);
  if (status >= 500) return new ProviderError(`${provider} HTTP ${status}`, "unavailable", true);
  return new ProviderError(`${provider} HTTP ${status}`, "bad_response", false);
}

async function post(url: string, headers: Record<string, string>, body: unknown, signal: AbortSignal, provider: string, fetchImpl: typeof fetch): Promise<Record<string, unknown>> {
  let res: Response;
  try {
    res = await fetchImpl(url, { method: "POST", headers: { "Content-Type": "application/json", ...headers }, body: JSON.stringify(body), signal });
  } catch (e) {
    if ((e as Error).name === "TimeoutError" || signal.aborted) throw new ProviderError(`${provider} timed out`, "timeout", true);
    throw new ProviderError(`${provider} unreachable`, "unavailable", true);
  }
  if (!res.ok) throw fromStatus(res.status, provider);
  try {
    return (await res.json()) as Record<string, unknown>;
  } catch {
    throw new ProviderError(`${provider} returned invalid JSON`, "bad_response", true);
  }
}

export async function callModel(settings: PracticeSettings["ai"], apiKey: string | null, call: ModelCall, fetchImpl: typeof fetch = fetch): Promise<ModelResult> {
  if (settings.provider === "openai") {
    const base = settings.baseUrl || "https://api.openai.com/v1";
    const official = !settings.baseUrl;
    const data = await post(
      `${base.replace(/\/+$/, "")}/chat/completions`,
      { Authorization: `Bearer ${apiKey}` },
      {
        model: settings.model,
        messages: [
          { role: "system", content: call.system },
          { role: "user", content: call.user },
        ],
        ...(official ? { max_completion_tokens: call.maxTokens } : { max_tokens: call.maxTokens }),
        response_format: { type: "json_schema", json_schema: { name: "tutor_answer", schema: call.schema, strict: true } },
      },
      call.signal,
      "OpenAI",
      fetchImpl,
    );
    const choice = (data.choices as { message?: { content?: string; refusal?: string } }[] | undefined)?.[0]?.message;
    const usage = data.usage as { prompt_tokens?: number; completion_tokens?: number } | undefined;
    if (!choice?.content) throw new ProviderError(choice?.refusal ? "The model declined to answer." : "Empty answer", "bad_response", false);
    return { text: choice.content, inputTokens: usage?.prompt_tokens ?? 0, outputTokens: usage?.completion_tokens ?? 0 };
  }
  if (settings.provider === "gemini") {
    const data = await post(
      `https://generativelanguage.googleapis.com/v1beta/models/${encodeURIComponent(settings.model)}:generateContent`,
      { "x-goog-api-key": apiKey ?? "" },
      {
        systemInstruction: { parts: [{ text: call.system }] },
        contents: [{ role: "user", parts: [{ text: call.user }] }],
        generationConfig: { maxOutputTokens: call.maxTokens, responseMimeType: "application/json", responseSchema: geminiSchema(call.schema) },
      },
      call.signal,
      "Gemini",
      fetchImpl,
    );
    const parts = (data.candidates as { content?: { parts?: { text?: string }[] } }[] | undefined)?.[0]?.content?.parts ?? [];
    const usage = data.usageMetadata as { promptTokenCount?: number; candidatesTokenCount?: number } | undefined;
    const text = parts.map((p) => p.text ?? "").join("");
    if (!text) throw new ProviderError("Empty answer", "bad_response", false);
    return { text, inputTokens: usage?.promptTokenCount ?? 0, outputTokens: usage?.candidatesTokenCount ?? 0 };
  }
  // Bedrock Converse.
  const { BedrockRuntimeClient, ConverseCommand } = await import("@aws-sdk/client-bedrock-runtime");
  const client = new BedrockRuntimeClient({ region: settings.region, maxAttempts: 1 });
  try {
    const out = await client.send(
      new ConverseCommand({
        modelId: settings.model,
        system: [{ text: `${call.system}\n\nAnswer with a single JSON object matching this JSON Schema, and nothing else:\n${JSON.stringify(call.schema)}` }],
        messages: [{ role: "user", content: [{ text: call.user }] }],
        inferenceConfig: { maxTokens: call.maxTokens },
      }),
      { abortSignal: call.signal },
    );
    const text = (out.output?.message?.content ?? []).map((c) => ("text" in c ? (c.text ?? "") : "")).join("");
    if (!text) throw new ProviderError("Empty answer", "bad_response", false);
    return { text, inputTokens: out.usage?.inputTokens ?? 0, outputTokens: out.usage?.outputTokens ?? 0 };
  } catch (e) {
    if (e instanceof ProviderError) throw e;
    const name = (e as { name?: string }).name ?? "";
    if (call.signal.aborted || name === "AbortError" || name === "TimeoutError") throw new ProviderError("Bedrock timed out", "timeout", true);
    if (name === "ThrottlingException" || name === "ServiceQuotaExceededException") throw new ProviderError("Bedrock throttled", "rate_limited", true);
    if (name === "AccessDeniedException" || name === "UnrecognizedClientException" || name === "CredentialsProviderError") throw new ProviderError("Bedrock denied access", "auth", false);
    throw new ProviderError(`Bedrock error ${name}`, "unavailable", true);
  }
}

/** Gemini's responseSchema is an OpenAPI subset: drop keywords it rejects. */
function geminiSchema(schema: Record<string, unknown>): Record<string, unknown> {
  const out: Record<string, unknown> = {};
  for (const [k, v] of Object.entries(schema)) {
    if (k === "additionalProperties" || k === "$schema") continue;
    if (k === "properties" && v && typeof v === "object") out[k] = Object.fromEntries(Object.entries(v).map(([pk, pv]) => [pk, geminiSchema(pv as Record<string, unknown>)]));
    else if (k === "items" && v && typeof v === "object") out[k] = geminiSchema(v as Record<string, unknown>);
    else out[k] = v;
  }
  return out;
}
