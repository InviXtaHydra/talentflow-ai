"use client";

import * as React from "react";

import { Spinner } from "@/components/ui/feedback";
import { useMe } from "@/hooks/use-auth";

import { AppShell } from "./app-shell";
import { PublicFooter, PublicHeader } from "./public-header";

/** Pages that anyone may browse (vacancies, companies): app layout when logged in, public layout otherwise. */
export function BrowseShell({ children }: { children: React.ReactNode }) {
  const { data: user, isLoading } = useMe();
  if (isLoading) return <div className="flex min-h-dvh items-center justify-center"><Spinner /></div>;
  if (user) return <AppShell>{children}</AppShell>;
  return (
    <div className="flex min-h-dvh flex-col">
      <PublicHeader />
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">{children}</main>
      <PublicFooter />
    </div>
  );
}
