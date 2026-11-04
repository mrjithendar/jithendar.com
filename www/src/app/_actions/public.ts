"use server";

import { headers } from "next/headers";
import { submitContact } from "@/lib/contact";
import { PostError } from "@/lib/posts";
import { getSessionUser } from "@/lib/session";

export type PublicResult = { ok: true; message: string } | { ok: false; error: string; issues?: string[] };

async function clientIp() {
  return (await headers()).get("x-forwarded-for")?.split(",")[0]?.trim() ?? null;
}

async function guard(fn: () => Promise<string>): Promise<PublicResult> {
  try {
    return { ok: true, message: await fn() };
  } catch (error) {
    if (error instanceof PostError) return { ok: false, error: error.message, issues: error.issues };
    const { currentRequestId, reportError, withReference } = await import("@/lib/http-errors");
    const ref = reportError("public form failed", error, { requestId: await currentRequestId() });
    return { ok: false, error: withReference("Something went wrong. Please try again later.", ref) };
  }
}

export async function submitContactAction(data: { name: string; email: string; subject: string; message: string }, token: string | null): Promise<PublicResult> {
  return guard(async () => {
    await submitContact(data, token, await clientIp(), { signedIn: !!(await getSessionUser()) });
    return "Thanks for getting in touch. Your message has been received.";
  });
}
