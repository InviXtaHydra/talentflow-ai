"use client";

import { X } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

/** Editable list of short values (skills, cities, titles). Enter or comma adds a value. */
export function TagInput({ value, onChange, placeholder, id, max = 60, className, suggestions }: {
  value: string[]; onChange: (value: string[]) => void; placeholder?: string; id?: string; max?: number; className?: string; suggestions?: string[];
}) {
  const [draft, setDraft] = React.useState("");
  const listId = React.useId();
  const add = (raw: string) => {
    const items = raw.split(",").map((s) => s.trim()).filter(Boolean);
    const next = [...value];
    for (const item of items) if (!next.some((v) => v.toLowerCase() === item.toLowerCase()) && next.length < max) next.push(item);
    onChange(next);
    setDraft("");
  };
  return (
    <div className={cn("flex min-h-10 flex-wrap items-center gap-1.5 rounded-lg border border-border bg-surface px-2 py-1.5 shadow-card focus-within:border-accent focus-within:ring-2 focus-within:ring-ring/40", className)}>
      {value.map((tag) => (
        <span key={tag} className="inline-flex items-center gap-1 rounded-md bg-surface-2 px-2 py-0.5 text-sm text-text-2">
          {tag}
          <button type="button" aria-label={`${tag} verwijderen`} className="rounded text-muted hover:text-danger" onClick={() => onChange(value.filter((v) => v !== tag))}>
            <X className="size-3.5" />
          </button>
        </span>
      ))}
      <input id={id} list={suggestions ? listId : undefined} value={draft} placeholder={value.length ? "" : placeholder}
        className="min-w-[8rem] flex-1 bg-transparent px-1 py-0.5 text-sm outline-none placeholder:text-muted"
        onChange={(e) => (e.target.value.endsWith(",") ? add(e.target.value) : setDraft(e.target.value))}
        onKeyDown={(e) => {
          if (e.key === "Enter" && draft.trim()) { e.preventDefault(); add(draft); }
          if (e.key === "Backspace" && !draft && value.length) onChange(value.slice(0, -1));
        }}
        onBlur={() => draft.trim() && add(draft)} />
      {suggestions && <datalist id={listId}>{suggestions.map((s) => <option key={s} value={s} />)}</datalist>}
    </div>
  );
}
