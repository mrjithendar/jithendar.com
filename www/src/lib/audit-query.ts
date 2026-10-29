import "server-only";
import { and, count, desc, eq, gt, ilike, inArray, like, or, type SQL } from "drizzle-orm";
import { getDb, schema } from "@/db";
import { SEVERITIES, type Severity } from "./audit";

/** Groups of actions for the audit log filter (prefixes of `action`). */
export const AUDIT_CATEGORIES = {
  auth: { label: "Sign-ins & accounts", prefixes: ["auth."] },
  users: { label: "Users & roles", prefixes: ["user.", "profile."] },
  content: { label: "Posts, pages & comments", prefixes: ["post.", "page.", "comment.", "category.", "tag."] },
  media: { label: "Media", prefixes: ["media."] },
  settings: { label: "Settings & integrations", prefixes: ["site-config.", "integrations.", "storage.", "email.", "backup.", "apikey.", "database."] },
} as const;
export type AuditCategory = keyof typeof AUDIT_CATEGORIES;

export const AUDIT_PERIODS = { "1": "Last 24 hours", "7": "Last 7 days", "30": "Last 30 days", "90": "Last 90 days", all: "All time" } as const;

export type AuditFilter = { q: string; severity: Severity | ""; category: AuditCategory | ""; ip: string; days: keyof typeof AUDIT_PERIODS; page: number };

export function parseAuditFilter(sp: Record<string, string | undefined>): AuditFilter {
  const severity = SEVERITIES.find((s) => s === sp.severity) ?? "";
  const category = (Object.keys(AUDIT_CATEGORIES) as AuditCategory[]).find((c) => c === sp.category) ?? "";
  const days = (Object.keys(AUDIT_PERIODS) as (keyof typeof AUDIT_PERIODS)[]).find((d) => d === sp.days) ?? "30";
  return { q: (sp.q ?? "").trim().slice(0, 100), severity, category, ip: (sp.ip ?? "").trim().slice(0, 64), days, page: Math.max(1, Math.floor(Number(sp.page) || 1)) };
}

/** "warning" shows warnings and criticals; "notice" adds notices; and so on. */
const atLeast = (s: Severity) => SEVERITIES.slice(SEVERITIES.indexOf(s));

function where(f: AuditFilter): SQL | undefined {
  const a = schema.auditLog;
  const text = f.q ? `%${f.q.replace(/[%_\\]/g, "\\$&")}%` : undefined;
  return and(
    text ? or(ilike(a.action, text), ilike(a.actor, text), ilike(a.target, text), ilike(a.ip, text)) : undefined,
    f.severity ? inArray(a.severity, atLeast(f.severity)) : undefined,
    f.category ? or(...AUDIT_CATEGORIES[f.category].prefixes.map((p) => like(a.action, `${p}%`))) : undefined,
    f.ip ? eq(a.ip, f.ip) : undefined,
    f.days !== "all" ? gt(a.createdAt, new Date(Date.now() - Number(f.days) * 86_400_000)) : undefined,
  );
}

export async function queryAudit(f: AuditFilter, pageSize = 100) {
  const db = await getDb();
  const w = where(f);
  const [rows, [total]] = await Promise.all([
    db.select().from(schema.auditLog).where(w).orderBy(desc(schema.auditLog.createdAt)).limit(pageSize).offset((f.page - 1) * pageSize),
    db.select({ n: count() }).from(schema.auditLog).where(w),
  ]);
  return { rows, total: Number(total?.n ?? 0) };
}

/** Matching entries for export (newest first, capped). */
export async function exportAudit(f: AuditFilter, max = 50_000) {
  const db = await getDb();
  return db.select().from(schema.auditLog).where(where(f)).orderBy(desc(schema.auditLog.createdAt)).limit(max);
}
