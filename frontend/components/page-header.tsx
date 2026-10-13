import * as React from "react";

import { cn } from "@/lib/utils";

export function PageHeader({ title, description, actions, className, eyebrow }: {
  title: React.ReactNode; description?: React.ReactNode; actions?: React.ReactNode; className?: string; eyebrow?: React.ReactNode;
}) {
  return (
    <div className={cn("mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between", className)}>
      <div className="min-w-0">
        {eyebrow && <div className="mb-1.5 text-sm text-muted">{eyebrow}</div>}
        <h1 className="text-2xl font-semibold tracking-tight text-text">{title}</h1>
        {description && <p className="mt-1 max-w-2xl text-[15px] text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function QueryError({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "Er ging iets mis.";
  return (
    <div role="alert" className="flex flex-col items-start gap-3 rounded-xl border border-danger/30 bg-danger-soft px-5 py-4 text-sm text-danger">
      <p><span className="font-medium">Er ging iets mis.</span> {message}</p>
      {onRetry && <button onClick={onRetry} className="font-medium underline underline-offset-4">Opnieuw proberen</button>}
    </div>
  );
}
