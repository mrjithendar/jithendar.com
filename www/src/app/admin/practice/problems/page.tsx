import Link from "next/link";
import { AdminHeader, Card, StatusPill } from "@/components/admin/ui";
import { buttonClass, Input, Select } from "@/components/ui/form";
import { listAdminProblems } from "@/lib/practice/admin";
import { requireRole } from "@/lib/session";

export const metadata = { title: "Practice problems" };

export default async function AdminProblems({ searchParams }: { searchParams: Promise<{ status?: string; q?: string }> }) {
  await requireRole("admin", "author");
  const sp = await searchParams;
  const rows = await listAdminProblems({ status: sp.status || undefined, q: sp.q });
  return (
    <>
      <AdminHeader title="Practice problems" description="Every save creates a new version; old submissions keep pointing at the version they were graded against." actions={<Link href="/admin/practice/problems/new" className={buttonClass("primary", "sm")}>New problem</Link>} />
      <form className="mb-4 flex flex-wrap gap-2">
        <Select name="status" defaultValue={sp.status ?? ""} className="!w-auto" aria-label="Status">
          <option value="">All statuses</option>
          <option value="published">Published</option>
          <option value="draft">Draft</option>
          <option value="archived">Archived</option>
        </Select>
        <Input name="q" defaultValue={sp.q ?? ""} placeholder="Search" className="!w-64" aria-label="Search" />
        <button className={buttonClass("secondary")}>Filter</button>
      </form>
      <Card className="!p-0">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-line text-fg-subtle">
            <tr>
              <th className="px-4 py-2 font-medium">Title</th>
              <th className="px-4 py-2 font-medium">Difficulty</th>
              <th className="px-4 py-2 font-medium">Status</th>
              <th className="px-4 py-2 font-medium">Version</th>
              <th className="px-4 py-2 font-medium">Source</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-line">
            {rows.map((r) => (
              <tr key={r.id}>
                <td className="px-4 py-2">
                  <Link href={`/admin/practice/problems/${r.id}`} className="font-medium text-fg hover:underline">{r.title}</Link>
                  <div className="text-xs text-fg-subtle">{r.slug}</div>
                </td>
                <td className="px-4 py-2 capitalize">{r.difficulty}</td>
                <td className="px-4 py-2"><StatusPill status={r.status} /></td>
                <td className="px-4 py-2 tabular-nums">v{r.version}</td>
                <td className="px-4 py-2 text-fg-muted">{r.source === "seed" ? "Repository" : "Admin"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}
