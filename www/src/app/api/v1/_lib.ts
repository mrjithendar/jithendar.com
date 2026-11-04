import { authenticateApiKey, type ApiAuth, type Scope } from "@/lib/api-keys";
import { toIsoOffset } from "@/lib/dates-iso";
import { reportError, routeFields } from "@/lib/http-errors";
import { PostError, type PostRow } from "@/lib/posts";

/** JSON responses and errors for /api/v1. Unknown errors are logged and never leak details. */
export async function api(request: Request, scope: Scope, fn: (auth: ApiAuth) => Promise<unknown>, status = 200): Promise<Response> {
  try {
    const auth = await authenticateApiKey(request.headers.get("authorization"));
    if (!auth.scopes.includes(scope)) throw new PostError(`This key lacks the ${scope} scope.`, 403);
    const data = await fn(auth);
    return data === undefined ? new Response(null, { status: 204 }) : Response.json({ data }, { status, headers: { "Cache-Control": "no-store" } });
  } catch (error) {
    if (error instanceof PostError) {
      const code = error.message.startsWith("Rate limit") ? 429 : error.status;
      return Response.json({ error: { message: error.message, issues: error.issues } }, { status: code });
    }
    const ref = reportError("api request failed", error, routeFields(request));
    return Response.json({ error: { message: "Internal error.", code: "internal", reference: ref.reference } }, { status: 500, headers: { "Cache-Control": "no-store" } });
  }
}

export async function json(request: Request): Promise<unknown> {
  try {
    return await request.json();
  } catch {
    throw new PostError("The request body must be JSON.", 400);
  }
}

/** Public representation of a post row (ISO 8601 dates with offset). */
export function serialize(p: PostRow) {
  const iso = (d: Date | null) => (d ? toIsoOffset(d) : null);
  return {
    id: p.id,
    collection: p.collection,
    slug: p.slug,
    url: `/${p.collection}/${p.slug}`,
    title: p.title,
    description: p.description,
    body: p.body,
    category: p.category,
    tags: p.tags,
    contentType: p.contentType,
    status: p.status,
    publishedAt: iso(p.publishedAt),
    updatedAt: iso(p.updatedAt),
    canonicalUrl: p.canonicalUrl,
    featuredImage: p.featuredImage,
    sources: p.sources,
    corrections: p.corrections,
    sponsored: p.sponsored,
    sponsor: p.sponsor,
    related: p.related,
    authorId: p.authorId,
    createdAt: iso(p.createdAt),
    savedAt: iso(p.savedAt),
  };
}
