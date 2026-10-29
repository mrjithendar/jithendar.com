import { actorOf } from "@/lib/admin";
import { audit } from "@/lib/audit";
import { exportAudit, parseAuditFilter } from "@/lib/audit-query";
import { getSessionUser } from "@/lib/session";

export const dynamic = "force-dynamic";

/** Spreadsheet apps execute cells starting with = + - @; prefix those with ' (CSV injection). */
function cell(v: unknown): string {
  let s = v === null || v === undefined ? "" : typeof v === "string" ? v : JSON.stringify(v);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

/** GET /api/admin/audit?{filters} → CSV of matching audit entries (admins only; the export itself is audited). */
export async function GET(request: Request) {
  const user = await getSessionUser();
  if (!user || user.role !== "admin") return new Response("Forbidden", { status: 403 });
  const filter = parseAuditFilter(Object.fromEntries(new URL(request.url).searchParams));
  const rows = await exportAudit(filter);
  await audit(actorOf(user), "audit.export", undefined, { rows: rows.length, filter: { ...filter, page: undefined } });
  const header = ["time_utc", "severity", "action", "actor", "actor_id", "target", "ip", "user_agent", "detail"];
  const lines = rows.map((r) => [r.createdAt.toISOString(), r.severity, r.action, r.actor, r.actorId, r.target, r.ip, r.userAgent, r.detail].map(cell).join(","));
  const stamp = new Date().toISOString().slice(0, 10);
  return new Response([header.join(","), ...lines].join("\r\n"), {
    headers: {
      "Content-Type": "text/csv; charset=utf-8",
      "Content-Disposition": `attachment; filename="jithendar-audit-${stamp}.csv"`,
      "Cache-Control": "no-store",
    },
  });
}
