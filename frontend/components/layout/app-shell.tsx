"use client";

import { useQuery } from "@tanstack/react-query";
import {
  Bell, BarChart3, Bookmark, Briefcase, Building2, FileText, LayoutDashboard, LogOut, Menu, MessageSquareText, Moon, Search,
  Settings, Shield, Sun, User as UserIcon, Users, X,
} from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import * as React from "react";

import { Logo } from "@/components/logo";
import { Alert, Spinner } from "@/components/ui/feedback";
import { useLogout, useMe } from "@/hooks/use-auth";
import { useTheme } from "@/hooks/use-theme";
import { api } from "@/lib/api";
import { t } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { Role, User } from "@/types/api";

type NavItem = { href: string; label: string; icon: React.ComponentType<{ className?: string }> };

const NAV: Record<Role, NavItem[]> = {
  candidate: [
    { href: "/dashboard", label: t("nav.dashboard"), icon: LayoutDashboard },
    { href: "/jobs", label: t("nav.jobs"), icon: Search },
    { href: "/saved", label: t("nav.saved"), icon: Bookmark },
    { href: "/applications", label: t("nav.applications"), icon: Briefcase },
    { href: "/cv", label: t("nav.cv"), icon: FileText },
    { href: "/profile", label: t("nav.profile"), icon: UserIcon },
    { href: "/assistant", label: t("nav.assistant"), icon: MessageSquareText },
    { href: "/companies", label: t("nav.companies"), icon: Building2 },
  ],
  employer: [
    { href: "/employer", label: t("nav.employerDashboard"), icon: LayoutDashboard },
    { href: "/employer/jobs", label: t("nav.employerJobs"), icon: Briefcase },
    { href: "/employer/applications", label: t("nav.employerApplicants"), icon: Users },
    { href: "/employer/company", label: t("nav.employerCompany"), icon: Building2 },
    { href: "/jobs", label: "Alle vacatures", icon: Search },
  ],
  admin: [
    { href: "/admin", label: t("nav.admin"), icon: BarChart3 },
    { href: "/jobs", label: t("nav.jobs"), icon: Search },
    { href: "/companies", label: t("nav.companies"), icon: Building2 },
  ],
};

const FOOTER: NavItem[] = [
  { href: "/notifications", label: t("nav.notifications"), icon: Bell },
  { href: "/settings", label: t("nav.settings"), icon: Settings },
  { href: "/privacy/data", label: t("nav.privacy"), icon: Shield },
];

function NavLinks({ items, onNavigate, unread }: { items: NavItem[]; onNavigate?: () => void; unread?: number }) {
  const pathname = usePathname();
  return (
    <ul className="flex flex-col gap-0.5">
      {items.map(({ href, label, icon: Icon }) => {
        const active = pathname === href || (href !== "/employer" && href !== "/dashboard" && pathname.startsWith(`${href}/`));
        return (
          <li key={href}>
            <Link href={href} onClick={onNavigate} aria-current={active ? "page" : undefined}
              className={cn("flex items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-accent-soft text-accent" : "text-text-2 hover:bg-surface-2 hover:text-text")}>
              <Icon className="size-4 shrink-0" />
              <span className="flex-1">{label}</span>
              {href === "/notifications" && !!unread && (
                <span className="rounded-full bg-accent px-1.5 text-[11px] font-semibold text-accent-fg">{unread}</span>
              )}
            </Link>
          </li>
        );
      })}
    </ul>
  );
}

function Sidebar({ user, onNavigate }: { user: User; onNavigate?: () => void }) {
  const logout = useLogout();
  const { theme, toggle } = useTheme();
  const unread = useQuery({ queryKey: ["unread"], queryFn: () => api.get<{ count: number }>("/notifications/unread-count"), refetchInterval: 30_000 });
  return (
    <div className="flex h-full flex-col gap-6 px-3 py-4">
      <Logo href="/" className="px-2" />
      <nav aria-label="Hoofdmenu" className="flex-1">
        <React.Suspense fallback={null}>
          <NavLinks items={NAV[user.role]} onNavigate={onNavigate} />
        </React.Suspense>
      </nav>
      <div className="flex flex-col gap-3 border-t border-border pt-4">
        <React.Suspense fallback={null}>
          <NavLinks items={FOOTER} onNavigate={onNavigate} unread={unread.data?.count} />
        </React.Suspense>
        <div className="flex items-center gap-2 rounded-lg px-3 py-2">
          <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-accent-soft text-sm font-semibold text-accent">
            {user.full_name.slice(0, 1).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-text">{user.full_name}</p>
            <p className="truncate text-xs text-muted">{t(`enums.role.${user.role}`)}</p>
          </div>
          <button onClick={toggle} className="rounded-md p-1.5 text-muted hover:bg-surface-2 hover:text-text" aria-label={t("nav.theme")}>
            {theme === "dark" ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
          <button onClick={logout} className="rounded-md p-1.5 text-muted hover:bg-surface-2 hover:text-text" aria-label={t("nav.logout")}>
            <LogOut className="size-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export function AppShell({ children, roles }: { children: React.ReactNode; roles?: Role[] }) {
  const { data: user, isLoading, error } = useMe();
  const router = useRouter();
  const [open, setOpen] = React.useState(false);

  React.useEffect(() => {
    if (!isLoading && user === null) router.replace(`/login?next=${encodeURIComponent(window.location.pathname + window.location.search)}`);
  }, [isLoading, user, router]);

  if (error) return <div className="p-8"><Alert tone="danger" title="De app kon niet laden.">{(error as Error).message}</Alert></div>;
  if (isLoading || !user) return <div className="flex min-h-dvh items-center justify-center"><Spinner /></div>;
  if (roles && !roles.includes(user.role)) {
    return (
      <div className="flex min-h-dvh items-center justify-center p-6">
        <Alert tone="warning" title="Geen toegang">Deze pagina is niet beschikbaar voor jouw accounttype. <Link className="underline" href="/">Naar de startpagina</Link></Alert>
      </div>
    );
  }

  return (
    <div className="min-h-dvh lg:grid lg:grid-cols-[256px_1fr]">
      <aside className="sticky top-0 hidden h-dvh border-r border-border bg-surface lg:block">
        <Sidebar user={user} />
      </aside>
      <div className="flex items-center justify-between border-b border-border bg-surface px-4 py-3 lg:hidden">
        <Logo />
        <button onClick={() => setOpen(true)} className="rounded-md p-2 hover:bg-surface-2" aria-label={t("nav.menu")}><Menu className="size-5" /></button>
      </div>
      {open && (
        <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label={t("nav.menu")}>
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpen(false)} />
          <div className="absolute inset-y-0 left-0 w-72 max-w-[85vw] bg-surface shadow-pop">
            <button onClick={() => setOpen(false)} className="absolute right-3 top-4 rounded-md p-1.5 hover:bg-surface-2" aria-label={t("common.close")}><X className="size-4" /></button>
            <Sidebar user={user} onNavigate={() => setOpen(false)} />
          </div>
        </div>
      )}
      <main id="main" className="min-w-0 px-4 py-6 sm:px-6 lg:px-10 lg:py-8">
        {!user.email_verified && <VerifyBanner />}
        <div className="mx-auto max-w-6xl">{children}</div>
      </main>
    </div>
  );
}

function VerifyBanner() {
  const [state, setState] = React.useState<"idle" | "sending" | "sent" | "error">("idle");
  return (
    <div className="mx-auto mb-6 max-w-6xl">
      <Alert tone="warning" title="Bevestig je e-mailadres"
        action={state === "sent" ? <span className="text-sm">Verstuurd</span> : (
          <button className="text-sm font-medium underline underline-offset-4" disabled={state === "sending"}
            onClick={async () => {
              setState("sending");
              try { await api.post("/auth/resend-verification"); setState("sent"); } catch { setState("error"); }
            }}>
            Opnieuw versturen
          </button>
        )}>
        We stuurden je een link. Werkgevers kunnen pas vacatures publiceren na bevestiging.
        {state === "error" && " Versturen lukte niet; probeer het later opnieuw."}
      </Alert>
    </div>
  );
}
