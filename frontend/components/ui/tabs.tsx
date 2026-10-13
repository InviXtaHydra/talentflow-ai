"use client";

import { Tabs as T } from "radix-ui";
import * as React from "react";

import { cn } from "@/lib/utils";

export const Tabs = T.Root;

export function TabsList({ className, ...props }: React.ComponentProps<typeof T.List>) {
  return <T.List className={cn("inline-flex flex-wrap gap-1 rounded-lg border border-border bg-surface-2 p-1", className)} {...props} />;
}

export function TabsTrigger({ className, ...props }: React.ComponentProps<typeof T.Trigger>) {
  return (
    <T.Trigger className={cn("rounded-md px-3 py-1.5 text-sm font-medium text-muted transition-colors hover:text-text data-[state=active]:bg-surface data-[state=active]:text-text data-[state=active]:shadow-card", className)} {...props} />
  );
}

export const TabsContent = T.Content;
