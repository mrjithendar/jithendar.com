import { redirect } from "next/navigation";
import { PostError } from "./posts";

/** Server-action helper: run, then redirect back with ?ok= or ?error= (+ issues) for the page to show. */
export async function flash(path: string, fn: () => Promise<string | void>): Promise<never> {
  let target: string;
  try {
    const message = (await fn()) || "Saved.";
    target = `${path}${path.includes("?") ? "&" : "?"}ok=${encodeURIComponent(message)}`;
  } catch (error) {
    const { isNextControlFlow } = await import("./trace");
    if (isNextControlFlow(error)) throw error;
    let text: string;
    if (error instanceof PostError) text = [error.message, ...error.issues].join(" · ");
    else {
      const { currentRequestId, reportError, withReference } = await import("./http-errors");
      const ref = reportError("admin action failed", error, { route: path.split("?")[0], requestId: await currentRequestId() });
      text = withReference("Something went wrong. The error has been logged.", ref);
    }
    target = `${path}${path.includes("?") ? "&" : "?"}error=${encodeURIComponent(text)}`;
  }
  redirect(target);
}
