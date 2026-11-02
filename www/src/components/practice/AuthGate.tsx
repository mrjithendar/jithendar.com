"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";
import { Dialog } from "@/components/admin/Dialog";
import { buttonClass } from "@/components/ui/form";

/**
 * Guests can read everything public; protected actions (editing, running, hints, solutions, AI, bookmarks,
 * notes, sessions) open this dialog instead. The server enforces the same rule (401 auth_required), and the
 * client opens the dialog for that response too. After signing in, /login returns to this exact page.
 */
type Gate = { signedIn: boolean; requireAuth: (reason: string) => boolean };
const Ctx = createContext<Gate>({ signedIn: false, requireAuth: () => false });

export function usePracticeAuth() {
  return useContext(Ctx);
}

export function PracticeAuthProvider({ signedIn, children }: { signedIn: boolean; children: ReactNode }) {
  const [reason, setReason] = useState<string | null>(null);
  const pathname = usePathname();
  const params = useSearchParams();
  const requireAuth = useCallback(
    (why: string) => {
      if (signedIn) return true;
      setReason(why);
      return false;
    },
    [signedIn],
  );
  const here = `${pathname}${params.size ? `?${params.toString()}` : ""}`;
  const next = encodeURIComponent(here);
  return (
    <Ctx.Provider value={{ signedIn, requireAuth }}>
      {children}
      <Dialog open={reason !== null} onClose={() => setReason(null)} title="Sign in to keep going" size="md">
        <div className="space-y-4 text-[0.9375rem] leading-7 text-fg-muted">
          <p className="text-fg">{reason}</p>
          <p>
            A free account lets you write and run Python in the browser, submit solutions for grading, open hints, and track progress, streaks and achievements. Your code
            runs in an isolated sandbox and your history is private to you.
          </p>
          <p className="text-sm text-fg-subtle">Browsing problems, roles and learning paths never needs an account.</p>
          <div className="flex flex-col gap-2 pt-2 sm:flex-row">
            <Link href={`/login?next=${next}`} className={buttonClass("primary")} data-autofocus>
              Sign in
            </Link>
            <Link href={`/login?mode=signup&next=${next}`} className={buttonClass("secondary")}>
              Create an account
            </Link>
            <button type="button" onClick={() => setReason(null)} className={buttonClass("ghost")}>
              Return to browsing
            </button>
          </div>
        </div>
      </Dialog>
    </Ctx.Provider>
  );
}

/** A button that runs `onClick` for signed-in users and opens the sign-in dialog for guests. */
export function GatedButton({ reason, onClick, className, children, disabled }: { reason: string; onClick: () => void; className?: string; children: ReactNode; disabled?: boolean }) {
  const { requireAuth } = usePracticeAuth();
  return (
    <button type="button" className={className} disabled={disabled} onClick={() => requireAuth(reason) && onClick()}>
      {children}
    </button>
  );
}
