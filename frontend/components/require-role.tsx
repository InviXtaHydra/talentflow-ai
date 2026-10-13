"use client";

import Link from "next/link";
import * as React from "react";

import { Alert } from "@/components/ui/feedback";
import { homeFor, useMe } from "@/hooks/use-auth";
import type { Role } from "@/types/api";

/** UI guard for role-specific pages. The API enforces the same rules on every request. */
export function RequireRole({ roles, children }: { roles: Role[]; children: React.ReactNode }) {
  const { data: user } = useMe();
  if (!user) return null;
  if (!roles.includes(user.role)) {
    return (
      <Alert tone="warning" title="Niet beschikbaar voor jouw account">
        Deze pagina is bedoeld voor {roles.map((r) => (r === "candidate" ? "kandidaten" : r === "employer" ? "werkgevers" : "beheerders")).join(" en ")}.{" "}
        <Link href={homeFor(user)} className="underline">Ga naar je startpagina</Link>.
      </Alert>
    );
  }
  return <>{children}</>;
}
