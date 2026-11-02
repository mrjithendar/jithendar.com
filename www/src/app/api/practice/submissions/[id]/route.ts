import { json, withUser } from "@/lib/practice/http";
import { cancelSubmission, getSubmission } from "@/lib/practice/submissions";

export const dynamic = "force-dynamic";

/** GET: the submission (collects the result from the executor when it is ready). DELETE: cancel. Owner only. */
export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return withUser(req, async (user) => json(await getSubmission(user.id, id)));
}

export async function DELETE(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return withUser(req, async (user) => json(await cancelSubmission(user.id, id)), { mutating: true });
}
