"use client";

import { useQuery } from "@tanstack/react-query";
import { Bookmark } from "lucide-react";
import Link from "next/link";

import { PageHeader, QueryError } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState, Skeleton } from "@/components/ui/feedback";
import { api } from "@/lib/api";
import type { JobSummary } from "@/types/api";

import { JobCard } from "./job-card";

export function SavedJobs() {
  const saved = useQuery({ queryKey: ["saved"], queryFn: () => api.get<JobSummary[]>("/jobs/saved") });
  return (
    <>
      <PageHeader title="Bewaarde vacatures" description="Vacatures die je bewaarde om later te bekijken." />
      {saved.error ? <QueryError error={saved.error} onRetry={() => saved.refetch()} /> : !saved.data ? <Skeleton className="h-40" /> :
        saved.data.length === 0 ? (
          <EmptyState icon={Bookmark} title="Nog niets bewaard" description="Bewaar vacatures met het bladwijzer-icoon om ze hier terug te vinden."
            action={<Button asChild variant="secondary"><Link href="/jobs">Vacatures zoeken</Link></Button>} />
        ) : <div className="flex flex-col gap-3">{saved.data.map((j) => <JobCard key={j.id} job={j} />)}</div>}
    </>
  );
}
