import Link from "next/link";
import { notFound } from "next/navigation";
import { Flash, type FlashParams } from "@/components/admin/Flash";
import { AdminHeader, Card, StatusPill } from "@/components/admin/ui";
import { Button } from "@/components/ui/form";
import { getAdminProblem } from "@/lib/practice/admin";
import { listRoles, listTopics } from "@/lib/practice/catalog";
import { PracticeError } from "@/lib/practice/errors";
import { requireRole } from "@/lib/session";
import { statusAction, validateAction } from "../actions";
import { ProblemForm } from "../ProblemForm";

export const metadata = { title: "Edit practice problem" };

export default async function EditProblem({ params, searchParams }: { params: Promise<{ id: string }>; searchParams: FlashParams }) {
  await requireRole("admin", "author");
  const { id } = await params;
  let data;
  try {
    data = await getAdminProblem(id);
  } catch (e) {
    if (e instanceof PracticeError) notFound();
    throw e;
  }
  const [roles, topics, sp] = await Promise.all([listRoles({ includeHidden: true }), listTopics(), searchParams]);
  const { problem, versions, stats } = data;
  return (
    <>
      <AdminHeader
        title={problem.title}
        description={<>/{problem.slug} · v{problem.currentVersion} · {problem.source === "seed" ? "from the repository catalog (editing here takes it over)" : "admin-managed"}</>}
        actions={<Link href={`/python-practice/problems/${problem.slug}`} className="text-sm underline">View</Link>}
      />
      <Flash ok={sp.ok} error={sp.error} />
      <div className="mb-6 grid gap-4 lg:grid-cols-3">
        <Card>
          <p className="text-sm text-fg-subtle">Status</p>
          <div className="mt-2"><StatusPill status={problem.status} /></div>
          <div className="mt-4 flex flex-wrap gap-2">
            {(["published", "draft", "archived"] as const).filter((s) => s !== problem.status).map((s) => (
              <form key={s} action={statusAction}>
                <input type="hidden" name="id" value={problem.id} />
                <input type="hidden" name="status" value={s} />
                <Button size="sm" variant={s === "published" ? "primary" : "secondary"}>{s === "published" ? "Publish" : s === "draft" ? "Unpublish" : "Archive"}</Button>
              </form>
            ))}
          </div>
        </Card>
        <Card>
          <p className="text-sm text-fg-subtle">Validate in the sandbox</p>
          <p className="mt-1 text-sm text-fg-muted">Runs the reference solution against every test.</p>
          <div className="mt-3 flex flex-wrap gap-2">
            <form action={validateAction}><input type="hidden" name="id" value={problem.id} /><Button size="sm" variant="secondary">Validate</Button></form>
            <form action={validateAction}><input type="hidden" name="id" value={problem.id} /><input type="hidden" name="fill" value="1" /><Button size="sm" variant="secondary">Validate and fill expected outputs</Button></form>
          </div>
        </Card>
        <Card>
          <p className="text-sm text-fg-subtle">Usage</p>
          <p className="mt-1 text-sm text-fg">{stats?.submits ?? 0} submissions by {stats?.users ?? 0} people · {stats?.submits ? Math.round(((stats.accepted ?? 0) / stats.submits) * 100) : 0}% accepted</p>
          <details className="mt-2 text-sm">
            <summary className="cursor-pointer text-fg-muted">{versions.length} version(s)</summary>
            <ul className="mt-1 space-y-0.5 text-fg-muted">{versions.map((v) => <li key={v.version}>v{v.version} · {v.createdAt.toISOString().slice(0, 10)} · {v.note}</li>)}</ul>
          </details>
        </Card>
      </div>
      <ProblemForm data={data} roles={roles} topics={topics} />
    </>
  );
}
