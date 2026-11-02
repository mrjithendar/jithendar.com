"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const ITEMS = [
  { href: "/python-practice/roles", label: "Roles" },
  { href: "/python-practice/problems", label: "Problems" },
  { href: "/python-practice/dashboard", label: "Dashboard", private: true },
  { href: "/python-practice/history", label: "History", private: true },
  { href: "/python-practice/leaderboard", label: "Leaderboard" },
  { href: "/python-practice/achievements", label: "Achievements" },
];

export function PracticeNav({ signedIn }: { signedIn: boolean }) {
  const path = usePathname();
  return (
    <nav aria-label="Python practice" className="flex gap-1">
      {ITEMS.filter((i) => signedIn || !i.private).map((i) => {
        const active = path === i.href || path.startsWith(`${i.href}/`);
        return (
          <Link key={i.href} href={i.href} aria-current={active ? "page" : undefined} className={`whitespace-nowrap rounded-md px-3 py-1.5 text-sm ${active ? "bg-accent-soft font-medium text-accent-text" : "text-fg-muted hover:bg-surface-sunken hover:text-fg"}`}>
            {i.label}
          </Link>
        );
      })}
    </nav>
  );
}
