import { runtimeAdsTxt } from "@/lib/runtime-settings";

export const dynamic = "force-dynamic";

/** /ads.txt: exactly the line(s) AdSense gives for this account (Admin → Advanced settings, or ADS_TXT), or 404 when not configured. */
export async function GET() {
  const body = await runtimeAdsTxt();
  if (!body) return new Response("Not found\n", { status: 404, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  return new Response(body, { headers: { "Content-Type": "text/plain; charset=utf-8", "Cache-Control": "public, max-age=3600" } });
}
