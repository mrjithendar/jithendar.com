import { z } from "zod";
import { PracticeError } from "@/lib/practice/errors";
import { json, readJson, withUser } from "@/lib/practice/http";
import { revealHint, revealSolution } from "@/lib/practice/progress";

export const dynamic = "force-dynamic";

const input = z.union([
  z.object({ action: z.literal("hint"), level: z.number().int().min(1).max(10), sessionId: z.uuid().nullish() }),
  z.object({ action: z.literal("solution"), confirm: z.literal(true), sessionId: z.uuid().nullish() }),
]);

/** POST { action: "hint", level } → { hints }; { action: "solution", confirm: true } → { solution }. Signed-in users only. */
export async function POST(req: Request, { params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return withUser(
    req,
    async (user) => {
      const parsed = input.safeParse(await readJson(req));
      if (!parsed.success) throw new PracticeError("Invalid request.", 400, "invalid");
      const body = parsed.data;
      if (body.action === "hint") return json({ hints: await revealHint(user.id, slug, body.level, body.sessionId) });
      return json({ solution: await revealSolution(user.id, slug, body.sessionId) });
    },
    { mutating: true },
  );
}
