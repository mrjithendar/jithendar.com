import { json, readJson, withUser } from "@/lib/practice/http";
import { deletePracticeData, exportPracticeData, getPreferences, updatePreferences } from "@/lib/practice/profile";

export const dynamic = "force-dynamic";

/** GET ?export=1 → all practice data as a JSON download; otherwise preferences. */
export async function GET(req: Request) {
  return withUser(req, async (user) => {
    if (new URL(req.url).searchParams.get("export") === "1") {
      return json(await exportPracticeData(user.id), 200, { "Content-Disposition": `attachment; filename="python-practice-${new Date().toISOString().slice(0, 10)}.json"` });
    }
    return json(await getPreferences(user.id));
  });
}

/** PUT { roles?, leaderboardOptIn?, publicName?, editor? }. */
export async function PUT(req: Request) {
  return withUser(
    req,
    async (user) => {
      await updatePreferences(user.id, await readJson(req));
      return json(await getPreferences(user.id));
    },
    { mutating: true },
  );
}

/** DELETE: remove this module's data for the signed-in user (the account itself is kept). */
export async function DELETE(req: Request) {
  return withUser(
    req,
    async (user) => {
      await deletePracticeData(user.id);
      return json({ ok: true });
    },
    { mutating: true },
  );
}
