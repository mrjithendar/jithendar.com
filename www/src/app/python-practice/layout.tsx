import type { Metadata } from "next";
import Link from "next/link";
import { Suspense, type ReactNode } from "react";
import { PracticeAuthProvider } from "@/components/practice/AuthGate";
import { PracticeNav } from "@/components/practice/PracticeNav";
import { getSessionUser } from "@/lib/session";

export const metadata: Metadata = {
  title: { default: "Python practice", template: "%s · Python practice" },
  description: "Role-based Python coding practice and interview preparation for DevOps, SRE, platform, cloud, AI and data engineers.",
};
export const dynamic = "force-dynamic";

export default async function PracticeLayout({ children }: { children: ReactNode }) {
  const user = await getSessionUser();
  return (
    <Suspense>
      <PracticeAuthProvider signedIn={Boolean(user)}>
        <div className="border-b border-line bg-surface">
          <div className="mx-auto flex max-w-[calc(var(--container-page)+4rem)] items-center gap-4 overflow-x-auto px-4 sm:px-6 lg:px-8">
            <Link href="/python-practice" className="shrink-0 py-3 text-sm font-semibold text-fg">
              Python practice
            </Link>
            <PracticeNav signedIn={Boolean(user)} />
          </div>
        </div>
        {children}
      </PracticeAuthProvider>
    </Suspense>
  );
}
