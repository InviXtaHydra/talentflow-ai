import Link from "next/link";

import { brand } from "@/lib/config";
import { cn } from "@/lib/utils";

export function Logo({ className, href = "/" }: { className?: string; href?: string }) {
  return (
    <Link href={href} className={cn("inline-flex items-center gap-2 font-semibold tracking-tight text-text", className)}>
      <svg viewBox="0 0 32 32" className="size-7" aria-hidden>
        <rect width="32" height="32" rx="8" className="fill-accent" />
        <path d="M9 11h14M16 11v12M11 17.5c3.5 0 6.5 2 10 2" stroke="var(--accent-fg)" strokeWidth="2.4" strokeLinecap="round" fill="none" />
      </svg>
      <span>{brand.name}</span>
    </Link>
  );
}
