"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Building2, ExternalLink, MapPin, Search, Users } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import * as React from "react";

import { PageHeader, QueryError } from "@/components/page-header";
import { PageSkeleton } from "@/components/page-suspense";
import { Card, CardBody } from "@/components/ui/card";
import { EmptyState, Skeleton } from "@/components/ui/feedback";
import { Input } from "@/components/ui/input";
import { CompanyLogo } from "@/features/jobs/company-logo";
import { DemoBadge, JobCard } from "@/features/jobs/job-card";
import { api, query } from "@/lib/api";
import type { Company, JobSummary, Page } from "@/types/api";

export function CompanyDirectory() {
  const [q, setQ] = React.useState("");
  const [search, setSearch] = React.useState("");
  const companies = useQuery({ queryKey: ["companies", search], queryFn: () => api.get<Page<Company>>(`/companies${query({ q: search })}`), placeholderData: keepPreviousData });
  return (
    <>
      <PageHeader title="Bedrijven" description="Werkgevers met open vacatures." />
      <form className="mb-6 max-w-md" role="search" onSubmit={(e) => { e.preventDefault(); setSearch(q); }}>
        <div className="relative"><Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} onBlur={() => setSearch(q)} placeholder="Zoek op naam of sector" className="pl-9" aria-label="Zoek bedrijven" /></div>
      </form>
      {companies.error ? <QueryError error={companies.error} /> : !companies.data ? <Skeleton className="h-40" /> : companies.data.items.length === 0 ? (
        <EmptyState icon={Building2} title="Geen bedrijven gevonden" />
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {companies.data.items.map((c) => (
            <Link key={c.id} href={`/companies/${c.id}`} className="rounded-xl border border-border bg-surface p-5 shadow-card transition hover:border-accent">
              <div className="flex items-center gap-3"><CompanyLogo company={c} size={44} /><div className="min-w-0"><p className="truncate font-semibold text-text">{c.name}</p><p className="text-sm text-muted">{c.industry ?? "Sector onbekend"}</p></div></div>
              <p className="mt-3 line-clamp-2 text-sm text-text-2">{c.description}</p>
              <div className="mt-3 flex items-center justify-between text-sm"><span className="text-accent">{c.open_jobs} open vacature{c.open_jobs === 1 ? "" : "s"}</span>{c.is_demo && <DemoBadge />}</div>
            </Link>
          ))}
        </div>
      )}
    </>
  );
}

export function CompanyProfile() {
  const { id } = useParams<{ id: string }>();
  const company = useQuery({ queryKey: ["company", id], queryFn: () => api.get<Company>(`/companies/${id}`) });
  const jobs = useQuery({ queryKey: ["company-jobs", id], queryFn: () => api.get<JobSummary[]>(`/companies/${id}/jobs`) });
  if (company.error) return <QueryError error={company.error} />;
  if (!company.data) return <PageSkeleton />;
  const c = company.data;
  return (
    <div className="flex flex-col gap-6">
      <Card>
        <CardBody className="flex flex-col gap-4 p-6 sm:flex-row sm:items-start">
          <CompanyLogo company={c} size={72} />
          <div className="min-w-0 flex-1">
            <h1 className="flex flex-wrap items-center gap-2 text-2xl font-semibold tracking-tight text-text">{c.name}{c.is_demo && <DemoBadge />}</h1>
            <div className="mt-2 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
              {c.industry && <span className="inline-flex items-center gap-1.5"><Building2 className="size-4" />{c.industry}</span>}
              {c.city && <span className="inline-flex items-center gap-1.5"><MapPin className="size-4" />{c.city}</span>}
              {c.size && <span className="inline-flex items-center gap-1.5"><Users className="size-4" />{c.size} medewerkers</span>}
              {c.website_url && <a href={c.website_url} target="_blank" rel="noopener noreferrer" className="inline-flex items-center gap-1.5 text-accent hover:underline"><ExternalLink className="size-4" />Website</a>}
            </div>
            {c.description && <p className="mt-4 whitespace-pre-line text-text-2">{c.description}</p>}
          </div>
        </CardBody>
      </Card>
      <section>
        <h2 className="mb-3 text-[15px] font-semibold text-text">Open vacatures ({c.open_jobs})</h2>
        {!jobs.data ? <Skeleton className="h-32" /> : jobs.data.length === 0 ? <p className="text-sm text-muted">Momenteel geen open vacatures.</p> : (
          <div className="flex flex-col gap-3">{jobs.data.map((j) => <JobCard key={j.id} job={j} showActions={false} />)}</div>
        )}
      </section>
    </div>
  );
}
