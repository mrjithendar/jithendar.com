import { z } from "zod";
import { PracticeError } from "@/lib/practice/errors";
import { json, readJson, withUser } from "@/lib/practice/http";
import { saveDraft, saveNote, setBookmark, userProblemView } from "@/lib/practice/progress";

export const dynamic = "force-dynamic";

/** GET: the signed-in user's state on this problem (status, revealed hints, draft, note, bookmark, recent submissions). */
export async function GET(req: Request, { params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return withUser(req, async (user) => json(await userProblemView(user.id, slug)));
}

const input = z.union([z.object({ draft: z.string() }), z.object({ note: z.string() }), z.object({ bookmarked: z.boolean() })]);

/** PUT { draft } | { note } | { bookmarked }. */
export async function PUT(req: Request, { params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return withUser(
    req,
    async (user) => {
      const parsed = input.safeParse(await readJson(req));
      if (!parsed.success) throw new PracticeError("Invalid request.", 400, "invalid");
      const body = parsed.data;
      if ("draft" in body) await saveDraft(user.id, slug, body.draft);
      else if ("note" in body) await saveNote(user.id, slug, body.note);
      else await setBookmark(user.id, slug, body.bookmarked);
      return json({ ok: true });
    },
    { mutating: true },
  );
}
