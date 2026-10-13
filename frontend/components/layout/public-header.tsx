"use client";

import Link from "next/link";

import { Logo } from "@/components/logo";
import { Button } from "@/components/ui/button";
import { homeFor, useMe } from "@/hooks/use-auth";
import { brand } from "@/lib/config";

export function PublicHeader() {
  const { data: user } = useMe();
  return (
    <header className="sticky top-0 z-30 border-b border-border bg-surface/85 backdrop-blur">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between gap-4 px-4 sm:px-6">
        <Logo />
        <nav className="flex items-center gap-1 sm:gap-2" aria-label="Hoofdmenu">
          <Link href="/jobs" className="hidden rounded-md px-3 py-2 text-sm font-medium text-text-2 hover:text-text sm:block">Vacatures</Link>
          <Link href="/companies" className="hidden rounded-md px-3 py-2 text-sm font-medium text-text-2 hover:text-text sm:block">Bedrijven</Link>
          {user ? (
            <Button asChild size="sm"><Link href={homeFor(user)}>Naar mijn omgeving</Link></Button>
          ) : (
            <>
              <Button asChild size="sm" variant="ghost"><Link href="/login">Inloggen</Link></Button>
              <Button asChild size="sm"><Link href="/register">Gratis starten</Link></Button>
            </>
          )}
        </nav>
      </div>
    </header>
  );
}

export function PublicFooter() {
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto flex max-w-6xl flex-col gap-3 px-4 py-8 text-sm text-muted sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p>© {brand.name}</p>
        <nav className="flex gap-5" aria-label="Voettekst">
          <Link href="/privacy" className="hover:text-text">Privacyverklaring</Link>
          <Link href="/terms" className="hover:text-text">Voorwaarden</Link>
          <Link href="/jobs" className="hover:text-text">Vacatures</Link>
        </nav>
      </div>
    </footer>
  );
}
