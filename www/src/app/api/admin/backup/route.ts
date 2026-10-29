import { actorOf } from "@/lib/admin";
import { audit } from "@/lib/audit";
import { buildBackup, readStoredBackup } from "@/lib/backups";
import { PostError } from "@/lib/posts";
import { getSessionUser } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Download a fresh encrypted backup, or `?file=` one already stored in R2 (admins only). */
export async function GET(request?: Request) {
  const user = await getSessionUser();
  if (!user || user.role !== "admin") return new Response("Forbidden", { status: 403 });
  try {
    const stored = request ? new URL(request.url).searchParams.get("file") : null;
    const { filename, data } = stored ? { filename: stored, data: await readStoredBackup(stored) } : await buildBackup();
    await audit(actorOf(user), "backup.download", filename, { stored: Boolean(stored) });
    return new Response(new Uint8Array(data), {
      headers: {
        "Content-Type": "application/octet-stream",
        "Content-Disposition": `attachment; filename="${filename}"`,
        "Cache-Control": "no-store",
      },
    });
  } catch (error) {
    if (error instanceof PostError) return new Response(error.message, { status: error.status ?? 400 });
    throw error;
  }
}
