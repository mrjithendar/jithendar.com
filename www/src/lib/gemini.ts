/**
 * Gemini image generation through the Gemini API's Interactions endpoint (REST, API key in the
 * x-goog-api-key header). Request and response shapes follow Google's published OpenAPI description
 * (ai.google.dev/static/api/interactions.openapi.json, checked 2026-10-29):
 *
 *   POST https://generativelanguage.googleapis.com/v1beta/interactions
 *   { model, input, response_format: { type: "image", mime_type, aspect_ratio, image_size }, store: false }
 *   → { id, status, steps: [{ type: "model_output", content: [{ type: "image", data, mime_type }, …] }], errors? }
 *
 * The models are configuration (GEMINI_IMAGE_MODEL for "Fast", optional GEMINI_IMAGE_PRO_MODEL for "Pro");
 * nothing here assumes a particular model name.
 * The API key never leaves the server.
 */

/** A subset of the API's aspect_ratio enum that suits article covers and inline images. */
export const ASPECT_RATIOS = ["16:9", "4:3", "3:2", "1:1", "21:9"] as const;
export type AspectRatio = (typeof ASPECT_RATIOS)[number];
/** Smallest to largest: larger sizes cost more and take longer. */
export const IMAGE_SIZES = ["512", "1K", "2K", "4K"] as const;
export type ImageSize = (typeof IMAGE_SIZES)[number];
/** "fast" uses GEMINI_IMAGE_MODEL; "pro" uses GEMINI_IMAGE_PRO_MODEL (offered only when set). */
export const QUALITIES = ["fast", "pro"] as const;
export type Quality = (typeof QUALITIES)[number];
const ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/interactions";

export type GeminiImageConfig = {
  apiKey: string;
  model: string;
  /** Higher-quality model offered as "Pro" in the editor; none when unset. */
  proModel?: string;
  /** Default size in the editor. */
  imageSize: ImageSize;
  /** Largest size authors may choose (cost cap); defaults to the larger of imageSize and 2K. */
  maxImageSize?: ImageSize;
  timeoutMs: number;
  endpoint: string;
};

const sizeRank = (s: ImageSize) => IMAGE_SIZES.indexOf(s);
const asSize = (v: string | undefined): ImageSize | undefined => IMAGE_SIZES.find((s) => s === v?.trim());

/** Sizes authors may choose, smallest first: up to maxImageSize, always including the default size. */
export function allowedImageSizes(config: GeminiImageConfig): ImageSize[] {
  const max = config.maxImageSize ?? (sizeRank(config.imageSize) > sizeRank("2K") ? config.imageSize : "2K");
  const cap = Math.max(sizeRank(max), sizeRank(config.imageSize));
  return IMAGE_SIZES.filter((s) => sizeRank(s) <= cap);
}

/** Qualities authors may choose, with the model each one uses. */
export function availableQualities(config: GeminiImageConfig): { id: Quality; model: string }[] {
  return [{ id: "fast", model: config.model }, ...(config.proModel && config.proModel !== config.model ? [{ id: "pro" as const, model: config.proModel }] : [])];
}

/**
 * From environment variables only. Code paths that generate images use resolveGeminiImageConfig() (lib/integrations),
 * which prefers the key saved in Admin → Integrations. null when not configured (the editor then hides the button).
 */
export function geminiImageConfig(env: Record<string, string | undefined> = process.env): GeminiImageConfig | null {
  const apiKey = env.GEMINI_API_KEY?.trim();
  const model = env.GEMINI_IMAGE_MODEL?.trim();
  if (!apiKey || !model) return null;
  const proModel = env.GEMINI_IMAGE_PRO_MODEL?.trim();
  const maxImageSize = asSize(env.GEMINI_IMAGE_MAX_SIZE);
  return {
    apiKey,
    model,
    ...(proModel ? { proModel } : {}),
    imageSize: asSize(env.GEMINI_IMAGE_SIZE) ?? "1K",
    ...(maxImageSize ? { maxImageSize } : {}),
    timeoutMs: Math.min(Math.max(Number(env.GEMINI_IMAGE_TIMEOUT_MS) || 90_000, 5_000), 300_000),
    endpoint: env.GEMINI_API_ENDPOINT?.trim() || ENDPOINT,
  };
}

export type ImageGenErrorCode =
  | "refused"
  | "quota"
  | "timeout"
  | "cancelled"
  | "unsupported"
  | "auth"
  | "model"
  | "unavailable"
  | "empty"
  | "invalid_image";

const MESSAGES: Record<ImageGenErrorCode, string> = {
  refused: "The image service declined this prompt under its content policy. Rephrase the prompt and try again.",
  quota: "The image service's quota or rate limit has been reached. Try again later.",
  timeout: "Image generation took too long and was stopped. Try again, or simplify the prompt.",
  cancelled: "Generation cancelled.",
  unsupported: "The image service rejected these options for this model. Try another aspect ratio, size or quality.",
  auth: "The Gemini API key was rejected. An admin must check the key in Admin → Integrations.",
  model: "The configured image model is not available. An admin must check the model in Admin → Integrations.",
  unavailable: "The image service is unavailable right now. Try again in a minute.",
  empty: "The model did not return an image. Try rephrasing the prompt.",
  invalid_image: "The image service returned data that is not a valid image. Try again.",
};

export class ImageGenError extends Error {
  constructor(
    readonly code: ImageGenErrorCode,
    readonly status: number,
    /** Short provider detail for logs (never the prompt). */
    readonly detail?: string,
  ) {
    super(MESSAGES[code]);
  }
}

const POLICY = /safety|blocked|block_reason|prohibited|policy|responsible ai|harm/i;

type ImageBlock = { type: "image"; data?: string; mime_type?: string };
type TextBlock = { type: "text"; text?: string };
type Interaction = {
  id?: string;
  status?: string;
  steps?: { type?: string; content?: (ImageBlock | TextBlock | { type: string })[] }[];
  errors?: { code?: string; message?: string }[];
};

function fromHttp(status: number, body: string): ImageGenError {
  let message = "";
  try {
    message = String((JSON.parse(body) as { error?: { message?: string; status?: string } }).error?.message ?? "");
  } catch {
    message = body.slice(0, 200);
  }
  const detail = `${status} ${message}`.slice(0, 300);
  if (status === 429) return new ImageGenError("quota", 429, detail);
  if (status === 401 || status === 403) return new ImageGenError(POLICY.test(message) ? "refused" : "auth", status === 401 ? 502 : 422, detail);
  if (status === 404) return new ImageGenError("model", 502, detail);
  if (status === 408 || status === 504) return new ImageGenError("timeout", 504, detail);
  if (status === 400 || status === 422) return new ImageGenError(POLICY.test(message) ? "refused" : "unsupported", 422, detail);
  return new ImageGenError("unavailable", 503, detail);
}

export type GeneratedImage = { bytes: Buffer; mimeType: string; interactionId?: string };

/**
 * Generate one image. `model` and `imageSize` default to the configured ones (the caller validates
 * overrides against availableQualities/allowedImageSizes). `signal` aborts the upstream request (the
 * author pressed Cancel or closed the dialog); the configured timeout aborts it too. Throws
 * ImageGenError for every failure.
 */
export async function generateImage(
  config: GeminiImageConfig,
  input: { prompt: string; aspectRatio: AspectRatio; model?: string; imageSize?: ImageSize; signal?: AbortSignal },
  fetchImpl: typeof fetch = fetch,
): Promise<GeneratedImage> {
  const timeout = AbortSignal.timeout(config.timeoutMs);
  const signal = input.signal ? AbortSignal.any([input.signal, timeout]) : timeout;
  let res: Response;
  try {
    res = await fetchImpl(config.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", "x-goog-api-key": config.apiKey },
      body: JSON.stringify({
        model: input.model ?? config.model,
        input: input.prompt,
        response_format: { type: "image", mime_type: "image/jpeg", aspect_ratio: input.aspectRatio, image_size: input.imageSize ?? config.imageSize },
        // Do not keep the prompt or result on Google's side for later retrieval.
        store: false,
      }),
      signal,
    });
  } catch (e) {
    if (input.signal?.aborted) throw new ImageGenError("cancelled", 499);
    if (timeout.aborted || (e as Error).name === "TimeoutError") throw new ImageGenError("timeout", 504);
    throw new ImageGenError("unavailable", 503, (e as Error).message);
  }
  const text = await res.text().catch(() => "");
  if (!res.ok) throw fromHttp(res.status, text);

  let body: Interaction;
  try {
    body = JSON.parse(text) as Interaction;
  } catch {
    throw new ImageGenError("invalid_image", 502, "response was not JSON");
  }
  const errors = (body.errors ?? []).map((e) => `${e.code ?? ""} ${e.message ?? ""}`).join("; ");
  if (body.status === "cancelled") throw new ImageGenError("cancelled", 499);
  if (body.status === "failed") throw new ImageGenError(POLICY.test(errors) ? "refused" : "unavailable", POLICY.test(errors) ? 422 : 503, errors.slice(0, 300));

  const blocks = (body.steps ?? []).filter((s) => s.type === "model_output").flatMap((s) => s.content ?? []);
  const image = blocks.find((b): b is ImageBlock => b.type === "image" && typeof (b as ImageBlock).data === "string" && (b as ImageBlock).data!.length > 0);
  if (!image) {
    const said = blocks.filter((b): b is TextBlock => b.type === "text").map((b) => b.text ?? "").join(" ");
    // No image: a refusal is usually explained in text or errors; otherwise the model just produced nothing.
    if (POLICY.test(`${said} ${errors}`)) throw new ImageGenError("refused", 422, `${body.status ?? ""} ${errors}`.trim().slice(0, 300));
    throw new ImageGenError("empty", 502, `status=${body.status ?? "?"}`);
  }
  const bytes = Buffer.from(image.data!, "base64");
  if (bytes.length === 0) throw new ImageGenError("invalid_image", 502, "empty image data");
  return { bytes, mimeType: image.mime_type ?? "image/jpeg", interactionId: body.id };
}
