import { askTutor } from "@/lib/practice/ai/tutor";
import { json, readJson, withUser } from "@/lib/practice/http";

export const dynamic = "force-dynamic";
export const maxDuration = 120;

/** POST { feature, slug?, code?, submissionId?, question? } → structured tutor answer (signed-in users, quota-limited). */
export async function POST(req: Request) {
  return withUser(req, async (user) => json(await askTutor(user.id, await readJson(req))), { mutating: true });
}
