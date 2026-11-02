import { json, readJson, withUser } from "@/lib/practice/http";
import { createSubmission } from "@/lib/practice/submissions";

export const dynamic = "force-dynamic";

/** POST /api/practice/run — { slug, code, kind: "run" | "submit", runtime?, sessionId?, idempotencyKey, custom? } → submission (queued). */
export async function POST(req: Request) {
  return withUser(req, async (user) => json(await createSubmission(user.id, await readJson(req)), 202), { mutating: true });
}
