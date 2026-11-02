import { json, readJson, withUser } from "@/lib/practice/http";
import { getSession, sessionAction } from "@/lib/practice/sessions";

export const dynamic = "force-dynamic";

/** GET: session state with the server-computed remaining time. POST { action: goto | skip | finish | abandon, position? }. */
export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return withUser(req, async (user) => json(await getSession(user.id, id)));
}

export async function POST(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return withUser(req, async (user) => json(await sessionAction(user.id, id, await readJson(req))), { mutating: true });
}
