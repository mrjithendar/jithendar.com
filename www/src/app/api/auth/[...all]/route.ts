import { getAuth } from "@/lib/auth";
import { auditAuthResponse, emailFromRequest } from "@/lib/auth-audit";

export const dynamic = "force-dynamic";

async function handle(request: Request) {
  const path = new URL(request.url).pathname.replace(/^\/api\/auth/, "");
  const email = await emailFromRequest(request, path);
  const response = await (await getAuth()).handler(request);
  // Failed, blocked and sensitive requests go to the audit log (Admin → Audit log). Never fails the request.
  await auditAuthResponse({ path, method: request.method, request, response, email });
  return response;
}

export { handle as GET, handle as POST };
