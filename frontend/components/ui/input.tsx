"use client";

import * as React from "react";

import { cn } from "@/lib/utils";

const fieldBase =
  "w-full rounded-lg border border-border bg-surface px-3 text-sm text-text shadow-card placeholder:text-muted focus:border-accent focus:outline-none focus:ring-2 focus:ring-ring/40 disabled:opacity-60 aria-[invalid=true]:border-danger";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return <input className={cn(fieldBase, "h-10", className)} {...props} />;
}

export function Textarea({ className, ...props }: React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={cn(fieldBase, "min-h-24 py-2 leading-relaxed", className)} {...props} />;
}

export function Select({ className, children, ...props }: React.SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select className={cn(fieldBase, "h-10 appearance-none bg-[length:16px] bg-[right_10px_center] bg-no-repeat pr-9", className)}
      style={{ backgroundImage: "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23667085' stroke-width='2'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E\")" }}
      {...props}>
      {children}
    </select>
  );
}

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={cn("text-sm font-medium text-text-2", className)} {...props} />;
}

export function Checkbox({ className, label, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { label: React.ReactNode }) {
  return (
    <label className={cn("flex cursor-pointer items-start gap-2.5 text-sm text-text-2", className)}>
      <input type="checkbox" className="mt-0.5 size-4 shrink-0 rounded border-border-strong accent-[var(--accent)]" {...props} />
      <span>{label}</span>
    </label>
  );
}

export function Field({ label, error, hint, htmlFor, children, className }: {
  label?: React.ReactNode; error?: string; hint?: React.ReactNode; htmlFor?: string; children: React.ReactNode; className?: string;
}) {
  // Associate the label (and hint/error) with the control, also when the caller didn't pass an id.
  const generated = React.useId();
  const child = React.isValidElement<{ id?: string; "aria-describedby"?: string }>(children) ? children : null;
  const id = htmlFor ?? child?.props.id ?? generated;
  const describedBy = error || hint ? `${id}-desc` : undefined;
  const control = child && typeof child.type === "string" || (child && [Input, Textarea, Select].includes(child.type as never))
    ? React.cloneElement(child!, { id, "aria-describedby": describedBy })
    : children;
  return (
    <div className={cn("flex flex-col gap-1.5", className)}>
      {label && <Label htmlFor={id}>{label}</Label>}
      {control}
      {error ? <p id={describedBy} className="text-xs text-danger" role="alert">{error}</p> : hint ? <p id={describedBy} className="text-xs text-muted">{hint}</p> : null}
    </div>
  );
}
