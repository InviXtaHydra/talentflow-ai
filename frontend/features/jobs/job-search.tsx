"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Columns3, Search, SlidersHorizontal, X } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";

import { PageHeader, QueryError } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { EmptyState, Skeleton } from "@/components/ui/feedback";
import { Checkbox, Field, Input, Select } from "@/components/ui/input";
import { useMe } from "@/hooks/use-auth";
import { api, query } from "@/lib/api";
import { t } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { EmploymentType, ExperienceLevel, Facets, JobSummary, Page, RemotePolicy } from "@/types/api";

import { JobCard } from "./job-card";

const REMOTE: RemotePolicy[] = ["onsite", "hybrid", "remote"];
const TYPES: EmploymentType[] = ["full_time", "part_time", "contract", "freelance", "internship", "temporary"];
const LEVELS: ExperienceLevel[] = ["junior", "medior", "senior", "lead"];
const LIST_KEYS = ["remote", "employment_type", "experience_level", "industry", "skills", "language"] as const;

function useFilters() {
  const params = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();
  const get = (k: string) => params.get(k) ?? "";
  const list = (k: string) => params.getAll(k);
  const update = React.useCallback((changes: Record<string, string | string[] | null>, resetPage = true) => {
    const next = new URLSearchParams(params.toString());
    for (const [key, value] of Object.entries(changes)) {
      next.delete(key);
      if (Array.isArray(value)) value.forEach((v) => next.append(key, v));
      else if (value) next.set(key, value);
    }
    if (resetPage) next.delete("page");
    router.replace(`${pathname}?${next.toString()}`, { scroll: false });
  }, [params, router, pathname]);
  return { params, get, list, update };
}

function CheckGroup<T extends string>({ legend, options, selected, label, onChange }: {
  legend: string; options: readonly T[]; selected: string[]; label: (v: T) => string; onChange: (v: string[]) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-sm font-medium text-text-2">{legend}</legend>
      <div className="flex flex-col gap-1.5">
        {options.map((o) => (
          <Checkbox key={o} label={label(o)} checked={selected.includes(o)} onChange={(e) => onChange(e.target.checked ? [...selected, o] : selected.filter((x) => x !== o))} />
        ))}
      </div>
    </fieldset>
  );
}

function Filters({ facets, onClose }: { facets?: Facets; onClose?: () => void }) {
  const { get, list, update } = useFilters();
  const [city, setCity] = React.useState(get("city"));
  const [salary, setSalary] = React.useState(get("salary_min_annual"));
  const active = ["city", "salary_min_annual", "max_distance_km", ...LIST_KEYS].some((k) => list(k).length);
  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <p className="font-semibold text-text">Filters</p>
        <div className="flex items-center gap-1">
          {active && <Button size="sm" variant="ghost" onClick={() => { setCity(""); setSalary(""); update(Object.fromEntries(["city", "salary_min_annual", "max_distance_km", ...LIST_KEYS].map((k) => [k, null]))); }}>Wissen</Button>}
          {onClose && <Button size="icon" variant="ghost" onClick={onClose} aria-label="Filters sluiten"><X /></Button>}
        </div>
      </div>
      <form className="flex flex-col gap-3" onSubmit={(e) => { e.preventDefault(); update({ city: city || null }); }}>
        <Field label="Locatie" htmlFor="f-city">
          <Input id="f-city" list="cities" value={city} placeholder="bv. Gent" onChange={(e) => setCity(e.target.value)} onBlur={() => city !== get("city") && update({ city: city || null })} />
          <datalist id="cities">{facets?.cities.map((c) => <option key={c} value={c} />)}</datalist>
        </Field>
        <Field label="Binnen" htmlFor="f-dist">
          <Select id="f-dist" value={get("max_distance_km")} disabled={!get("city")} onChange={(e) => update({ max_distance_km: e.target.value || null })}>
            <option value="">Alleen deze plaats</option>
            {[10, 25, 50, 75, 100].map((km) => <option key={km} value={km}>{km} km</option>)}
          </Select>
        </Field>
      </form>
      <CheckGroup legend="Thuiswerk" options={REMOTE} selected={list("remote")} label={(v) => t(`enums.remote.${v}`)} onChange={(v) => update({ remote: v })} />
      <CheckGroup legend="Contracttype" options={TYPES} selected={list("employment_type")} label={(v) => t(`enums.employmentType.${v}`)} onChange={(v) => update({ employment_type: v })} />
      <CheckGroup legend="Ervaringsniveau" options={LEVELS} selected={list("experience_level")} label={(v) => t(`enums.experienceLevel.${v}`)} onChange={(v) => update({ experience_level: v })} />
      <Field label="Minimumloon (bruto per jaar)" htmlFor="f-sal" hint="Vacatures zonder vermeld loon worden dan niet getoond.">
        <Input id="f-sal" type="number" min={0} step={1000} value={salary} placeholder="bv. 45000" onChange={(e) => setSalary(e.target.value)} onBlur={() => salary !== get("salary_min_annual") && update({ salary_min_annual: salary || null })} />
      </Field>
      {facets && facets.industries.length > 0 && (
        <CheckGroup legend="Sector" options={facets.industries} selected={list("industry")} label={(v) => v} onChange={(v) => update({ industry: v })} />
      )}
      <CheckGroup legend="Taal van de vacature" options={["nl", "fr", "en"] as const} selected={list("language")} label={(v) => t(`enums.languages.${v}`)} onChange={(v) => update({ language: v })} />
      {facets && facets.skills.length > 0 && (
        <fieldset>
          <legend className="mb-2 text-sm font-medium text-text-2">Vaardigheden</legend>
          <div className="flex flex-wrap gap-1.5">
            {facets.skills.slice(0, 20).map((s) => {
              const on = list("skills").includes(s);
              return (
                <button key={s} type="button" aria-pressed={on} onClick={() => update({ skills: on ? list("skills").filter((x) => x !== s) : [...list("skills"), s] })}
                  className={cn("rounded-md border px-2 py-1 text-xs font-medium", on ? "border-accent bg-accent-soft text-accent" : "border-border text-text-2 hover:bg-surface-2")}>
                  {s}
                </button>
              );
            })}
          </div>
        </fieldset>
      )}
    </div>
  );
}

export function JobSearch() {
  const { params, get, update } = useFilters();
  const me = useMe();
  const isCandidate = me.data?.role === "candidate";
  const [q, setQ] = React.useState(get("q"));
  const [showFilters, setShowFilters] = React.useState(false);
  const [compare, setCompare] = React.useState<string[]>([]);
  const page = Number(get("page") || 1);
  const sort = get("sort") || (isCandidate ? "match" : "relevance");

  const queryString = query({
    q: get("q"), city: get("city"), max_distance_km: get("max_distance_km"), salary_min_annual: get("salary_min_annual"), sort, page,
    ...Object.fromEntries(LIST_KEYS.map((k) => [k, params.getAll(k)])),
  });
  const jobs = useQuery({ queryKey: ["jobs", queryString], queryFn: () => api.get<Page<JobSummary>>(`/jobs${queryString}`), placeholderData: keepPreviousData });
  const facets = useQuery({ queryKey: ["facets"], queryFn: () => api.get<Facets>("/jobs/facets"), staleTime: 300_000 });

  return (
    <>
      <PageHeader title="Vacatures" description={jobs.data ? `${jobs.data.total} open vacature${jobs.data.total === 1 ? "" : "s"}` : "Zoek in alle open vacatures"} />
      <form className="mb-6 flex flex-col gap-3 sm:flex-row" role="search" onSubmit={(e) => { e.preventDefault(); update({ q: q || null }); }}>
        <div className="relative flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted" />
          <Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Functie, vaardigheid of bedrijf" className="h-11 pl-9" aria-label="Zoekterm" />
        </div>
        <div className="flex gap-2">
          <Select value={sort} onChange={(e) => update({ sort: e.target.value })} aria-label="Sorteren" className="h-11 w-auto">
            {isCandidate && <option value="match">Beste match</option>}
            <option value="relevance">Relevantie</option>
            <option value="date">Nieuwste</option>
            <option value="salary">Hoogste loon</option>
          </Select>
          <Button type="submit" size="lg">Zoeken</Button>
          <Button type="button" size="lg" variant="secondary" className="lg:hidden" onClick={() => setShowFilters(true)} aria-label="Filters"><SlidersHorizontal /></Button>
        </div>
      </form>

      <div className="grid gap-8 lg:grid-cols-[240px_1fr]">
        <aside className="hidden lg:block"><Filters facets={facets.data} /></aside>
        {showFilters && (
          <div className="fixed inset-0 z-40 lg:hidden" role="dialog" aria-modal="true" aria-label="Filters">
            <div className="absolute inset-0 bg-black/40" onClick={() => setShowFilters(false)} />
            <div className="absolute inset-y-0 right-0 w-80 max-w-[90vw] overflow-y-auto bg-surface p-5 shadow-pop"><Filters facets={facets.data} onClose={() => setShowFilters(false)} /></div>
          </div>
        )}
        <section aria-live="polite" aria-busy={jobs.isFetching}>
          {jobs.error ? <QueryError error={jobs.error} onRetry={() => jobs.refetch()} /> : !jobs.data ? (
            <div className="flex flex-col gap-3">{[0, 1, 2, 3].map((i) => <Skeleton key={i} className="h-36" />)}</div>
          ) : jobs.data.items.length === 0 ? (
            <EmptyState icon={Search} title="Geen vacatures gevonden" description="Probeer een andere zoekterm of verwijder enkele filters." />
          ) : (
            <div className={cn("flex flex-col gap-3 transition-opacity", jobs.isPlaceholderData && "opacity-60")}>
              {jobs.data.items.map((job) => (
                <div key={job.id} className="relative">
                  <JobCard job={job} />
                  <label className="absolute bottom-6 right-16 z-10 hidden items-center gap-1.5 text-xs text-muted sm:flex">
                    <input type="checkbox" className="accent-[var(--accent)]" checked={compare.includes(job.id)} disabled={!compare.includes(job.id) && compare.length >= 4}
                      onChange={(e) => setCompare(e.target.checked ? [...compare, job.id] : compare.filter((id) => id !== job.id))} />
                    Vergelijk
                  </label>
                </div>
              ))}
              {jobs.data.pages > 1 && (
                <nav className="mt-4 flex items-center justify-between" aria-label="Paginering">
                  <Button variant="secondary" disabled={page <= 1} onClick={() => update({ page: String(page - 1) }, false)}>{t("common.previous")}</Button>
                  <span className="text-sm text-muted">{t("common.page", { page, pages: jobs.data.pages })}</span>
                  <Button variant="secondary" disabled={page >= jobs.data.pages} onClick={() => update({ page: String(page + 1) }, false)}>{t("common.next")}</Button>
                </nav>
              )}
            </div>
          )}
        </section>
      </div>

      {compare.length > 0 && (
        <div className="fixed bottom-4 left-1/2 z-30 flex -translate-x-1/2 items-center gap-3 rounded-xl border border-border bg-surface px-4 py-3 shadow-pop">
          <span className="text-sm text-text-2">{compare.length} geselecteerd</span>
          <Button size="sm" disabled={compare.length < 2} asChild={compare.length >= 2}>
            {compare.length >= 2 ? <Link href={`/jobs/compare${query({ ids: compare })}`}><Columns3 />Vergelijken</Link> : <span><Columns3 />Kies er nog één</span>}
          </Button>
          <Button size="sm" variant="ghost" onClick={() => setCompare([])}>Wissen</Button>
        </div>
      )}
    </>
  );
}
