"use client";

import { useQuery } from "@tanstack/react-query";
import type * as React from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { PageHeader, QueryError } from "@/components/page-header";
import { PageSkeleton } from "@/components/page-suspense";
import { Badge } from "@/components/ui/feedback";
import { api, query } from "@/lib/api";
import { formatSalary, languageName } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { JobDetail } from "@/types/api";

import { MatchScore } from "./match-score";

export function JobCompare() {
  const ids = useSearchParams().getAll("ids");
  const jobs = useQuery({ queryKey: ["compare", ids], queryFn: () => api.get<JobDetail[]>(`/jobs/compare${query({ ids })}`), enabled: ids.length >= 2 });
  if (ids.length < 2) return <QueryError error={new Error("Kies twee tot vier vacatures om te vergelijken.")} />;
  if (jobs.error) return <QueryError error={jobs.error} onRetry={() => jobs.refetch()} />;
  if (!jobs.data) return <PageSkeleton />;
  const rows: [string, (j: JobDetail) => React.ReactNode][] = [
    ["Bedrijf", (j) => <Link href={`/companies/${j.company.id}`} className="hover:text-accent">{j.company.name}</Link>],
    ["Match", (j) => (j.match ? <MatchScore score={j.match.score} size={44} /> : "—")],
    ["Locatie", (j) => `${j.city ?? "—"} · ${t(`enums.remote.${j.remote_policy}`)}`],
    ["Contract", (j) => t(`enums.employmentType.${j.employment_type}`)],
    ["Loon", (j) => formatSalary(j.salary_min, j.salary_max, j.salary_currency, j.salary_period) ?? <span className="italic text-muted">Niet vermeld</span>],
    ["Niveau", (j) => (j.experience_level ? t(`enums.experienceLevel.${j.experience_level}`) : "—")],
    ["Ervaring", (j) => (j.min_years_experience != null ? `${j.min_years_experience} jaar` : "—")],
    ["Opleiding", (j) => (j.education_level ? t(`enums.education.${j.education_level}`) : "—")],
    ["Talen", (j) => j.required_languages.map(languageName).join(", ") || "—"],
    ["Jouw vaardigheden", (j) => <div className="flex flex-wrap gap-1">{j.match?.matching_skills.map((s) => <Badge key={s} tone="success">{s}</Badge>) ?? "—"}</div>],
    ["Ontbreekt", (j) => <div className="flex flex-wrap gap-1">{j.match?.missing_required_skills.map((s) => <Badge key={s} tone="warning">{s}</Badge>) ?? "—"}</div>],
  ];
  return (
    <>
      <PageHeader title="Vacatures vergelijken" />
      <div className="overflow-x-auto rounded-xl border border-border bg-surface shadow-card">
        <table className="w-full min-w-[640px] text-sm">
          <thead>
            <tr className="border-b border-border">
              <th className="w-40 px-4 py-3 text-left font-medium text-muted" scope="col"><span className="sr-only">Kenmerk</span></th>
              {jobs.data.map((j) => <th key={j.id} scope="col" className="px-4 py-3 text-left align-top font-semibold text-text"><Link href={`/jobs/${j.id}`} className="hover:text-accent">{j.title}</Link></th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map(([label, render]) => (
              <tr key={label} className="border-b border-border last:border-0">
                <th scope="row" className="px-4 py-3 text-left align-top font-medium text-muted">{label}</th>
                {jobs.data.map((j) => <td key={j.id} className="px-4 py-3 align-top text-text-2">{render(j)}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
