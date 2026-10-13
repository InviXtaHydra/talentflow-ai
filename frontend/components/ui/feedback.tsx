import { AlertTriangle, CheckCircle2, Info, Loader2, XCircle } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

const tones = {
  neutral: "bg-surface-2 text-text-2 border-border",
  accent: "bg-accent-soft text-accent border-transparent",
  success: "bg-success-soft text-success border-transparent",
  warning: "bg-warning-soft text-warning border-transparent",
  danger: "bg-danger-soft text-danger border-transparent",
} as const;
export type Tone = keyof typeof tones;

export function Badge({ tone = "neutral", className, ...props }: React.HTMLAttributes<HTMLSpanElement> & { tone?: Tone }) {
  return <span className={cn("inline-flex items-center gap-1 whitespace-nowrap rounded-md border px-2 py-0.5 text-xs font-medium", tones[tone], className)} {...props} />;
}

const alertIcons = { neutral: Info, accent: Info, success: CheckCircle2, warning: AlertTriangle, danger: XCircle };

export function Alert({ tone = "neutral", title, children, action, className }: {
  tone?: Tone; title?: React.ReactNode; children?: React.ReactNode; action?: React.ReactNode; className?: string;
}) {
  const Icon = alertIcons[tone];
  return (
    <div role={tone === "danger" ? "alert" : "status"} className={cn("flex gap-3 rounded-lg border px-4 py-3 text-sm", tones[tone], className)}>
      <Icon className="mt-0.5 size-4 shrink-0" aria-hidden />
      <div className="min-w-0 flex-1">
        {title && <p className="font-medium">{title}</p>}
        {children && <div className={cn(title && "mt-0.5", "opacity-90")}>{children}</div>}
      </div>
      {action}
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded-md bg-surface-2", className)} aria-hidden />;
}

export function Spinner({ className, label = "Laden…" }: { className?: string; label?: string }) {
  return (
    <span className={cn("inline-flex items-center gap-2 text-sm text-muted", className)} role="status">
      <Loader2 className="size-4 animate-spin" aria-hidden />
      {label}
    </span>
  );
}

export function EmptyState({ icon: Icon, title, description, action, className }: {
  icon?: React.ComponentType<{ className?: string }>; title: string; description?: React.ReactNode; action?: React.ReactNode; className?: string;
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center rounded-xl border border-dashed border-border-strong px-6 py-12 text-center", className)}>
      {Icon && <div className="mb-3 rounded-full bg-surface-2 p-3"><Icon className="size-5 text-muted" /></div>}
      <p className="font-medium text-text">{title}</p>
      {description && <p className="mt-1 max-w-md text-sm text-muted">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

export function Progress({ value, className, label }: { value: number; className?: string; label?: string }) {
  return (
    <div className={cn("h-2 w-full overflow-hidden rounded-full bg-surface-2", className)} role="progressbar" aria-valuenow={value} aria-valuemin={0} aria-valuemax={100} aria-label={label}>
      <div className="h-full rounded-full bg-accent transition-[width] duration-500" style={{ width: `${Math.max(0, Math.min(100, value))}%` }} />
    </div>
  );
}
