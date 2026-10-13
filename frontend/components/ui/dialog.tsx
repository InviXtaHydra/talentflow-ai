"use client";

import { Dialog as D } from "radix-ui";
import { X } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

export function Dialog({ open, onOpenChange, title, description, children, footer, className }: {
  open: boolean; onOpenChange: (open: boolean) => void; title: React.ReactNode; description?: React.ReactNode;
  children?: React.ReactNode; footer?: React.ReactNode; className?: string;
}) {
  return (
    <D.Root open={open} onOpenChange={onOpenChange}>
      <D.Portal>
        <D.Overlay className="fixed inset-0 z-50 bg-black/40 backdrop-blur-[1px] data-[state=open]:animate-in" />
        <D.Content className={cn("fixed left-1/2 top-1/2 z-50 max-h-[90vh] w-[calc(100vw-2rem)] max-w-lg -translate-x-1/2 -translate-y-1/2 overflow-y-auto rounded-xl border border-border bg-surface p-6 shadow-pop", className)}>
          <div className="mb-4 pr-8">
            <D.Title className="text-lg font-semibold text-text">{title}</D.Title>
            {description ? <D.Description className="mt-1 text-sm text-muted">{description}</D.Description> : <D.Description className="sr-only">{String(title)}</D.Description>}
          </div>
          {children}
          {footer && <div className="mt-6 flex flex-wrap justify-end gap-2">{footer}</div>}
          <D.Close className="absolute right-4 top-4 rounded-md p-1 text-muted hover:bg-surface-2 hover:text-text" aria-label="Sluiten">
            <X className="size-4" />
          </D.Close>
        </D.Content>
      </D.Portal>
    </D.Root>
  );
}

/** Confirmation for destructive actions. */
export function ConfirmDialog({ open, onOpenChange, title, description, confirmLabel, onConfirm, loading, tone = "danger" }: {
  open: boolean; onOpenChange: (open: boolean) => void; title: string; description: React.ReactNode; confirmLabel: string;
  onConfirm: () => void; loading?: boolean; tone?: "danger" | "primary";
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={title} description={description}
      footer={
        <>
          <button className="h-10 rounded-lg border border-border bg-surface px-4 text-sm font-medium hover:bg-surface-2" onClick={() => onOpenChange(false)}>Annuleren</button>
          <button className={cn("inline-flex h-10 items-center gap-2 rounded-lg px-4 text-sm font-medium text-white disabled:opacity-60", tone === "danger" ? "bg-danger" : "bg-accent")}
            onClick={onConfirm} disabled={loading}>
            {confirmLabel}
          </button>
        </>
      } />
  );
}
