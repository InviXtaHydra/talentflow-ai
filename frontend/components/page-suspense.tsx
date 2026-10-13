import * as React from "react";

import { Skeleton } from "@/components/ui/feedback";

export function PageSkeleton() {
  return (
    <div className="flex flex-col gap-4" aria-busy="true">
      <Skeleton className="h-8 w-64" />
      <Skeleton className="h-4 w-96 max-w-full" />
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <Skeleton className="h-40" />
        <Skeleton className="h-40" />
      </div>
    </div>
  );
}

/** Pages render their client component inside Suspense: URL hooks (useSearchParams, useParams) need a boundary with Cache Components. */
export function PageSuspense({ children }: { children: React.ReactNode }) {
  return <React.Suspense fallback={<PageSkeleton />}>{children}</React.Suspense>;
}
