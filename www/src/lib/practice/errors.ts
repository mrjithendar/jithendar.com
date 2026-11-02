/** A practice error with an HTTP status and a stable code the browser can act on (e.g. "auth_required"). */
export class PracticeError extends Error {
  constructor(
    message: string,
    readonly status = 400,
    readonly code = "bad_request",
    readonly retryAfter?: number,
  ) {
    super(message);
  }
}

export const authRequired = () => new PracticeError("Sign in to use this feature.", 401, "auth_required");
export const notFound = (what = "Problem") => new PracticeError(`${what} not found.`, 404, "not_found");
