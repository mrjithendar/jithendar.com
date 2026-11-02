import { Flash, type FlashParams } from "@/components/admin/Flash";
import { AdminHeader } from "@/components/admin/ui";
import { listRoles, listTopics } from "@/lib/practice/catalog";
import { requireRole } from "@/lib/session";
import { ProblemForm } from "../ProblemForm";

export const metadata = { title: "New practice problem" };

export default async function NewProblem({ searchParams }: { searchParams: FlashParams }) {
  await requireRole("admin", "author");
  const [roles, topics, sp] = await Promise.all([listRoles({ includeHidden: true }), listTopics(), searchParams]);
  return (
    <>
      <AdminHeader title="New practice problem" description="Saved as a draft. Quality checks and duplicate detection run on save; publish when it validates." />
      <Flash ok={sp.ok} error={sp.error} />
      <ProblemForm data={null} roles={roles} topics={topics} />
    </>
  );
}
