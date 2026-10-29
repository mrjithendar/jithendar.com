"use server";

import { revalidatePath } from "next/cache";
import { adminActor } from "@/lib/admin";
import { EmailSettingsError, saveEmailSettings, sendTestEmail, type EmailSummary } from "@/lib/mail";
import { PostError } from "@/lib/posts";

export type EmailFormState = { ok?: string; error?: string; fieldErrors?: Record<string, string>; summary?: EmailSummary };

const FIELDS = ["fromName", "fromEmail", "replyTo", "host", "port", "security", "username", "password", "domain", "region", "apiKey", "auth", "accessKeyId", "secretAccessKey", "sessionToken"];

function failure(error: unknown): EmailFormState {
  if (error instanceof EmailSettingsError) return { error: error.message, fieldErrors: error.fieldErrors };
  if (error instanceof PostError) return { error: error.message };
  if ((error as { digest?: string })?.digest?.startsWith("NEXT_REDIRECT")) throw error;
  return { error: "Something went wrong. The error has been logged." };
}

/** Save the selected provider and only that provider's fields (the form submits nothing else). */
export async function saveEmailAction(_prev: EmailFormState, form: FormData): Promise<EmailFormState> {
  const actor = await adminActor();
  try {
    const raw: Record<string, unknown> = {};
    for (const k of FIELDS) if (form.has(k)) raw[k] = String(form.get(k) ?? "");
    const provider = String(form.get("provider") ?? "");
    const summary = await saveEmailSettings(actor, provider, raw);
    revalidatePath("/admin/storage");
    return {
      summary,
      ok: provider === "disabled" ? "Email is turned off. Saved provider settings are kept." : "Saved. Send a test email to confirm the settings work.",
    };
  } catch (error) {
    return failure(error);
  }
}

export async function testEmailAction(_prev: EmailFormState, form: FormData): Promise<EmailFormState> {
  const actor = await adminActor();
  try {
    const r = await sendTestEmail(actor, String(form.get("provider") ?? ""), String(form.get("testTo") ?? ""));
    revalidatePath("/admin/storage");
    return r.ok ? { ok: `Test email sent to ${String(form.get("testTo"))}. Check that it arrived (and not in spam).` } : { error: `The test email failed: ${r.error}` };
  } catch (error) {
    return failure(error);
  }
}
