import { json, readJson, withUser } from "@/lib/practice/http";
import { createSession } from "@/lib/practice/sessions";

export const dynamic = "force-dynamic";

/** POST { mode, roles, difficulties, topics, count, durationMinutes, includeFailed, excludeSolved } → { id }. */
export async function POST(req: Request) {
  return withUser(req, async (user) => json(await createSession(user.id, await readJson(req)), 201), { mutating: true });
}
