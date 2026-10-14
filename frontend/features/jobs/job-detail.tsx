"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowLeft, ArrowUpRight, Briefcase, Building2, CalendarDays, CircleCheck, Clock, ExternalLink, Eye, Globe, GraduationCap, Hourglass,
  Languages, Layers, MapPin, MessageSquareText, Pencil, Send, Sparkles, Timer, Users, Wallet,
} from "lucide-react";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { QueryError } from "@/components/page-header";
import { PageSkeleton } from "@/components/page-suspense";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Dialog } from "@/components/ui/dialog";
import { Alert, Badge, Skeleton } from "@/components/ui/feedback";
import { Checkbox, Field, Select, Textarea } from "@/components/ui/input";
import { useMe, usePublicConfig } from "@/hooks/use-auth";
import { api, ApiError, errorMessage } from "@/lib/api";
import { formatDate, formatMonths, formatSalary, languageName, relativeTime } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { CvLanguage, CvTemplate, CvVersionSummary, JobDetail, JobSummary, MatchOut } from "@/types/api";

import { CompanyLogo } from "./company-logo";
import { DemoBadge, JobCard, SaveJobButton } from "./job-card";
import { MatchBreakdown } from "./match-breakdown";

function OptimizeDialog({ job, open, onOpenChange }: { job: JobDetail; open: boolean; onOpenChange: (o: boolean) => void }) {
  const router = useRouter();
  const config = usePublicConfig();
  const versions = useQuery({ queryKey: ["cv-versions"], queryFn: () => api.get<CvVersionSummary[]>("/cv-versions"), enabled: open });
  const [source, setSource] = React.useState("");
  const [language, setLanguage] = React.useState<CvLanguage>(job.language === "fr" ? "fr" : job.language === "en" ? "en" : "nl");
  const [template, setTemplate] = React.useState<CvTemplate>("modern");
  const start = useMutation({
    mutationFn: () => api.post<{ optimization_id: string }>(`/jobs/${job.id}/optimize-cv`, { source_version_id: source || null, language, template }),
    onSuccess: (data) => router.push(`/cv/optimizations/${data.optimization_id}`),
  });
  const sources = (versions.data ?? []).filter((v) => v.status === "ready" && v.kind !== "optimized");
  const notConfigured = config.data && !config.data.ai_configured;
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title="Optimaliseer mijn cv voor deze vacature"
      description="We stemmen je cv af op deze vacature met alleen feiten uit je profiel. Jij controleert het resultaat voordat je het downloadt."
      footer={<><Button variant="secondary" onClick={() => onOpenChange(false)}>Annuleren</Button><Button loading={start.isPending} onClick={() => start.mutate()}><Sparkles />Start optimalisatie</Button></>}>
      <div className="flex flex-col gap-4">
        {notConfigured && <Alert tone="warning" title="Geen AI-model ingesteld">Alleen voor de demo-gegevens is een gesimuleerde, duidelijk gelabelde versie beschikbaar. Voor je eigen cv moet de beheerder een AI-model instellen.</Alert>}
        {start.error && <Alert tone="danger">{errorMessage(start.error)}{start.error instanceof ApiError && start.error.code === "profile_empty" && <> <Link href="/profile" className="underline">Naar je profiel</Link></>}</Alert>}
        <Field label="Vertrek van">
          <Select value={source} onChange={(e) => setSource(e.target.value)}>
            <option value="">Mijn bevestigde profiel</option>
            {sources.map((v) => <option key={v.id} value={v.id}>{v.title}</option>)}
          </Select>
        </Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Taal van het cv">
            <Select value={language} onChange={(e) => setLanguage(e.target.value as CvLanguage)}>
              {(["nl", "fr", "en"] as CvLanguage[]).map((l) => <option key={l} value={l}>{t(`enums.languages.${l}`)}</option>)}
            </Select>
          </Field>
          <Field label="Sjabloon">
            <Select value={template} onChange={(e) => setTemplate(e.target.value as CvTemplate)}>
              {(["modern", "minimal", "technical"] as CvTemplate[]).map((x) => <option key={x} value={x}>{t(`enums.template.${x}`)}</option>)}
            </Select>
          </Field>
        </div>
        {config.data?.ai_is_local && <p className="text-xs text-muted">Het AI-model draait lokaal; je cv verlaat de server niet. Dit duurt meestal 30 seconden tot 2 minuten.</p>}
      </div>
    </Dialog>
  );
}

function ApplyDialog({ job, open, onOpenChange }: { job: JobDetail; open: boolean; onOpenChange: (o: boolean) => void }) {
  const qc = useQueryClient();
  const versions = useQuery({ queryKey: ["cv-versions"], queryFn: () => api.get<CvVersionSummary[]>("/cv-versions"), enabled: open });
  const ready = (versions.data ?? []).filter((v) => v.status === "ready");
  const preferred = ready.find((v) => v.target_job_id === job.id) ?? ready[0];
  const [chosen, setCv] = React.useState("");
  const cv = chosen || preferred?.id || "";
  const [letter, setLetter] = React.useState("");
  const [consent, setConsent] = React.useState(false);
  const apply = useMutation({
    mutationFn: () => api.post("/applications", { job_id: job.id, channel: "platform", cv_version_id: cv || null, cover_letter: letter || null, share_consent: consent }),
    onSuccess: () => {
      toast.success("Je sollicitatie is verstuurd");
      qc.invalidateQueries({ queryKey: ["job", job.id] });
      qc.invalidateQueries({ queryKey: ["applications"] });
      onOpenChange(false);
    },
  });
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={`Solliciteren bij ${job.company.name}`}
      footer={<><Button variant="secondary" onClick={() => onOpenChange(false)}>Annuleren</Button><Button disabled={!cv || !consent} loading={apply.isPending} onClick={() => apply.mutate()}><Send />Sollicitatie versturen</Button></>}>
      <div className="flex flex-col gap-4">
        {apply.error && <Alert tone="danger">{errorMessage(apply.error)}</Alert>}
        {versions.data && ready.length === 0 ? (
          <Alert tone="warning">Je hebt nog geen cv-versie. <Link href="/cv" className="underline">Maak er een</Link> of optimaliseer je cv voor deze vacature.</Alert>
        ) : (
          <Field label="Welk cv stuur je mee?">
            <Select value={cv} onChange={(e) => setCv(e.target.value)}>
              {ready.map((v) => <option key={v.id} value={v.id}>{v.title}{v.target_job_id === job.id ? " (voor deze vacature)" : ""}</option>)}
            </Select>
          </Field>
        )}
        <Field label="Motivatie" hint="Optioneel. De carrière-assistent kan je helpen met een eerste versie.">
          <Textarea rows={5} value={letter} onChange={(e) => setLetter(e.target.value)} maxLength={10000} />
        </Field>
        <Checkbox checked={consent} onChange={(e) => setConsent(e.target.checked)}
          label={<>Ik geef toestemming om mijn naam, e-mailadres en het gekozen cv te delen met {job.company.name} voor deze vacature.</>} />
      </div>
    </Dialog>
  );
}

function ExternalApply({ job }: { job: JobDetail }) {
  const qc = useQueryClient();
  const [asked, setAsked] = React.useState(false);
  const confirm = useMutation({
    mutationFn: async () => {
      if (job.application) return api.patch(`/applications/${job.application.id}`, { status: "applied" });
      return api.post("/applications", { job_id: job.id, channel: "external", status: "applied" });
    },
    onSuccess: () => { toast.success("Toegevoegd aan je sollicitaties"); setAsked(false); qc.invalidateQueries({ queryKey: ["job", job.id] }); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  return (
    <>
      <Button asChild variant="secondary" onClick={() => setTimeout(() => setAsked(true), 400)}>
        <a href={job.application_url!} target="_blank" rel="noopener noreferrer"><ExternalLink />Solliciteren op de website</a>
      </Button>
      <Dialog open={asked} onOpenChange={setAsked} title="Heb je gesolliciteerd?"
        description="We houden je sollicitatie alleen bij als je dat bevestigt. Het openen van de link alleen telt niet als sollicitatie."
        footer={<><Button variant="secondary" onClick={() => setAsked(false)}>Nog niet</Button><Button loading={confirm.isPending} onClick={() => confirm.mutate()}>Ja, ik heb gesolliciteerd</Button></>} />
    </>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3">
      <h3 className="text-base font-semibold text-text">{title}</h3>
      {children}
    </section>
  );
}

function Highlight({ icon: Icon, children }: { icon: React.ComponentType<{ className?: string }>; children: React.ReactNode }) {
  return (
    <li className="flex items-start gap-3 text-sm text-text-2">
      <Icon className="mt-0.5 size-4 shrink-0 text-muted" />
      <span>{children}</span>
    </li>
  );
}

function plural(n: number, one: string, many: string) {
  return `${n} ${n === 1 ? one : many}`;
}

/** Practical terms as label/value pairs; rows without a value are left out instead of showing "unknown". */
function detailRows(j: JobDetail): [string, React.ReactNode][] {
  const rows: [string, React.ReactNode | null][] = [
    ["Senioriteitsniveau", j.experience_level && t(`enums.experienceLevel.${j.experience_level}`)],
    ["Dienstverband", t(`enums.employmentType.${j.employment_type}`)],
    ["Werkplek", `${t(`enums.remote.${j.remote_policy}`)}${j.city ? ` · ${j.city}` : ""}`],
    ["Afdeling", j.department],
    ["Sector", j.industry],
    ["Uren per week", j.hours_per_week && `${j.hours_per_week} uur`],
    ["Contractduur", j.contract_duration_months ? formatMonths(j.contract_duration_months) : j.employment_type === "full_time" || j.employment_type === "part_time" ? "Onbepaalde duur" : null],
    ["Startdatum", j.start_date ? formatDate(j.start_date) : "In overleg"],
    ["Aantal vacatures", j.openings > 1 ? j.openings : null],
    ["Ervaring", j.min_years_experience != null && (j.min_years_experience === 0 ? "Geen ervaring vereist" : `Minstens ${plural(j.min_years_experience, "jaar", "jaar")}`)],
    ["Opleiding", j.education_level ? t(`enums.education.${j.education_level}`) : "Geen opleidingseis"],
    ["Talen", j.required_languages.length ? j.required_languages.map(languageName).join(", ") : null],
    ["Taal van de vacature", languageName(j.language)],
    ["Solliciteren tot", j.application_deadline && formatDate(j.application_deadline)],
    ["Gepubliceerd", j.published_at && formatDate(j.published_at)],
  ];
  return rows.filter((r): r is [string, React.ReactNode] => r[1] != null && r[1] !== "" && r[1] !== false && r[1] !== 0);
}

function HiringTeam({ job }: { job: JobDetail }) {
  if (!job.recruiter) return null;
  const initials = job.recruiter.full_name.split(/\s+/).map((p) => p[0]).slice(0, 2).join("").toUpperCase();
  return (
    <Card>
      <CardHeader title="Het wervingsteam" />
      <CardBody className="flex items-center gap-3">
        <span className="grid size-11 shrink-0 place-items-center rounded-full bg-accent-soft text-sm font-semibold text-accent">{initials}</span>
        <div className="min-w-0">
          <p className="font-medium text-text">{job.recruiter.full_name}</p>
          <p className="text-sm text-muted">Plaatste deze vacature voor {job.company.name}</p>
        </div>
      </CardBody>
    </Card>
  );
}

function AboutCompany({ job }: { job: JobDetail }) {
  const c = job.company;
  const p = job.company_profile;
  const facts = [c.industry, p.size && `${p.size} medewerkers`, c.city].filter(Boolean).join(" · ");
  return (
    <Card>
      <CardHeader title="Over het bedrijf" />
      <CardBody className="flex flex-col gap-4">
        <div className="flex items-center gap-4">
          <CompanyLogo company={c} size={48} />
          <div className="min-w-0">
            <Link href={`/companies/${c.id}`} className="font-semibold text-text hover:text-accent">{c.name}</Link>
            {facts && <p className="text-sm text-muted">{facts}</p>}
            <p className="text-sm text-muted">{plural(p.open_jobs, "openstaande vacature", "openstaande vacatures")}</p>
          </div>
        </div>
        {p.description && <p className="whitespace-pre-line text-[15px] leading-relaxed text-text-2">{p.description}</p>}
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="secondary" size="sm"><Link href={`/companies/${c.id}`}><Building2 />Bedrijfspagina en vacatures</Link></Button>
          {p.website_url && <Button asChild variant="ghost" size="sm"><a href={p.website_url} target="_blank" rel="noopener noreferrer"><Globe />Website<ArrowUpRight /></a></Button>}
        </div>
      </CardBody>
    </Card>
  );
}

export function JobDetailPage() {
  const { id } = useParams<{ id: string }>();
  const params = useSearchParams();
  const me = useMe();
  const qc = useQueryClient();
  const isCandidate = me.data?.role === "candidate";
  const job = useQuery({ queryKey: ["job", id], queryFn: () => api.get<JobDetail>(`/jobs/${id}`) });
  const match = useQuery({ queryKey: ["match", id], queryFn: () => api.get<MatchOut>(`/jobs/${id}/match`), enabled: isCandidate && job.data?.status === "published" });
  const related = useQuery({ queryKey: ["related", id], queryFn: () => api.get<JobSummary[]>(`/jobs/${id}/related`), enabled: !!job.data });
  const [optimizeOpen, setOptimizeOpen] = React.useState(params.get("optimize") === "1");
  const [applyOpen, setApplyOpen] = React.useState(false);
  const track = useMutation({
    mutationFn: () => api.post("/applications", { job_id: id, channel: "external", status: "saved" }),
    onSuccess: () => { toast.success("Toegevoegd aan je sollicitaties"); qc.invalidateQueries({ queryKey: ["job", id] }); },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (job.error) return <QueryError error={job.error} onRetry={() => job.refetch()} />;
  if (!job.data) return <PageSkeleton />;
  const j = job.data;
  const open = j.status === "published";
  const salary = formatSalary(j.salary_min, j.salary_max, j.salary_currency, j.salary_period);
  const required = j.skills.filter((s) => s.is_required);
  const niceToHave = j.skills.filter((s) => !s.is_required);
  const matched = new Set((j.match?.matching_skills ?? []).map((s) => s.toLowerCase()));

  return (
    <div className="flex flex-col gap-6">
      <Link href="/jobs" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-text"><ArrowLeft className="size-4" />Alle vacatures</Link>
      {j.status === "closed" && <Alert tone="warning">Deze vacature is gesloten. Solliciteren kan niet meer.</Alert>}
      {j.status === "draft" && <Alert tone="neutral">Concept: alleen zichtbaar voor jouw bedrijf.</Alert>}

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="flex min-w-0 flex-col gap-6">
          <Card>
            <CardBody className="flex flex-col gap-5 p-6">
              <div className="flex items-center gap-3">
                <CompanyLogo company={j.company} size={40} />
                <Link href={`/companies/${j.company.id}`} className="text-sm font-medium text-text-2 hover:text-accent">{j.company.name}</Link>
                {j.is_demo && <DemoBadge />}
              </div>
              <div>
                <h1 className="text-2xl font-semibold tracking-tight text-text sm:text-[28px]">{j.title}</h1>
                <p className="mt-2 flex flex-wrap items-center gap-x-1.5 gap-y-1 text-sm text-muted">
                  <span>{j.city ?? t("common.notSpecified")}</span>
                  {j.published_at && <><span aria-hidden>·</span><span>Geplaatst {relativeTime(j.published_at)}</span></>}
                  <span aria-hidden>·</span>
                  <span className={j.applicant_count > 0 ? "font-medium text-success" : undefined}>
                    {j.applicant_count > 0 ? plural(j.applicant_count, "sollicitant", "sollicitanten") : "Wees een van de eerste sollicitanten"}
                  </span>
                  {j.view_count > 0 && <><span aria-hidden>·</span><span className="inline-flex items-center gap-1"><Eye className="size-3.5" />{plural(j.view_count, "keer", "keer")} bekeken</span></>}
                </p>
              </div>

              <div className="flex flex-wrap gap-2">
                <Badge tone="accent" className="px-2.5 py-1 text-[13px]"><MapPin className="size-3.5" />{t(`enums.remote.${j.remote_policy}`)}</Badge>
                <Badge tone="accent" className="px-2.5 py-1 text-[13px]"><Briefcase className="size-3.5" />{t(`enums.employmentType.${j.employment_type}`)}</Badge>
                {j.experience_level && <Badge tone="neutral" className="px-2.5 py-1 text-[13px]"><Layers className="size-3.5" />{t(`enums.experienceLevel.${j.experience_level}`)}</Badge>}
                {salary && <Badge tone="success" className="px-2.5 py-1 text-[13px]"><Wallet className="size-3.5" />{salary}</Badge>}
              </div>

              <ul className="flex flex-col gap-2.5">
                {j.hours_per_week && <Highlight icon={Clock}>{j.hours_per_week} uur per week{j.contract_duration_months ? ` · contract van ${formatMonths(j.contract_duration_months)}` : ""}</Highlight>}
                <Highlight icon={Building2}>{[j.company_profile.size && `${j.company_profile.size} medewerkers`, j.company.industry ?? j.industry].filter(Boolean).join(" · ") || j.company.name}</Highlight>
                {j.required_languages.length > 0 && <Highlight icon={Languages}>Talen: {j.required_languages.map(languageName).join(", ")}</Highlight>}
                {j.skills.length > 0 && (
                  <Highlight icon={CircleCheck}>
                    Vaardigheden: {j.skills.slice(0, 4).map((s) => s.name).join(", ")}{j.skills.length > 4 && ` en ${j.skills.length - 4} meer`}
                    {isCandidate && j.match && j.match.score != null && <span className="ml-1 font-medium text-success">({j.match.matching_skills.length} van {j.skills.length} in je profiel)</span>}
                  </Highlight>
                )}
                {j.openings > 1 && <Highlight icon={Users}>{j.openings} openstaande plaatsen</Highlight>}
                {j.application_deadline && <Highlight icon={Hourglass}>Solliciteren tot {formatDate(j.application_deadline)}</Highlight>}
              </ul>

              <div className="flex flex-wrap gap-2">
                {isCandidate && open && !j.application && <Button onClick={() => setApplyOpen(true)}><Send />Solliciteren</Button>}
                {isCandidate && open && j.application_url && <ExternalApply job={j} />}
                {isCandidate && <SaveJobButton job={j} />}
                {isCandidate && open && <Button variant="secondary" onClick={() => setOptimizeOpen(true)}><Sparkles />Optimaliseer mijn cv voor deze vacature</Button>}
                {isCandidate && !j.application && <Button variant="ghost" loading={track.isPending} onClick={() => track.mutate()}>Volgen in sollicitaties</Button>}
                {isCandidate && <Button asChild variant="ghost"><Link href={`/assistant?job=${j.id}`}><MessageSquareText />Vraag de assistent</Link></Button>}
                {j.can_edit && <Button asChild variant="secondary"><Link href={`/employer/jobs/${j.id}/edit`}><Pencil />Bewerken</Link></Button>}
                {!me.data && <Button asChild><Link href={`/register?next=/jobs/${j.id}`}>Maak een account om te solliciteren</Link></Button>}
              </div>
              {j.application && (
                <Alert tone="accent">Je volgt deze vacature: <strong>{t(`enums.applicationStatus.${j.application.status}`)}</strong>. <Link href="/applications" className="underline">Naar je sollicitaties</Link></Alert>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Over de vacature" />
            <CardBody className="flex flex-col gap-7 py-5 text-[15px] leading-relaxed text-text-2">
              <p className="whitespace-pre-line">{j.description}</p>
              {j.responsibilities.length > 0 && (
                <Section title="Wat ga je doen?">
                  <ul className="list-disc space-y-1.5 pl-5 marker:text-muted">{j.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul>
                </Section>
              )}
              {j.qualifications.length > 0 && (
                <Section title="Wie zoeken we?">
                  <ul className="list-disc space-y-1.5 pl-5 marker:text-muted">{j.qualifications.map((r) => <li key={r}>{r}</li>)}</ul>
                </Section>
              )}
              {j.skills.length > 0 && (
                <Section title="Vaardigheden">
                  {required.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-sm font-medium text-text">Vereist</p>
                      <div className="flex flex-wrap gap-1.5">{required.map((s) => <Badge key={s.name} tone={matched.has(s.name.toLowerCase()) ? "success" : "accent"}>{matched.has(s.name.toLowerCase()) && <CircleCheck className="size-3" />}{s.name}</Badge>)}</div>
                    </div>
                  )}
                  {niceToHave.length > 0 && (
                    <div>
                      <p className="mb-1.5 text-sm font-medium text-text">Pluspunten</p>
                      <div className="flex flex-wrap gap-1.5">{niceToHave.map((s) => <Badge key={s.name} tone={matched.has(s.name.toLowerCase()) ? "success" : "neutral"}>{matched.has(s.name.toLowerCase()) && <CircleCheck className="size-3" />}{s.name}</Badge>)}</div>
                    </div>
                  )}
                  {matched.size > 0 && <p className="text-xs text-muted">Groen = staat ook in je profiel</p>}
                </Section>
              )}
              {j.benefits.length > 0 && (
                <Section title="Wat bieden we?">
                  {salary && <p className="font-medium text-text">{salary} bruto</p>}
                  <ul className="grid gap-2 sm:grid-cols-2">
                    {j.benefits.map((b) => <li key={b} className="flex items-start gap-2"><CircleCheck className="mt-1 size-4 shrink-0 text-success" />{b}</li>)}
                  </ul>
                </Section>
              )}
              {j.about_team && (
                <Section title="Over het team">
                  <p className="whitespace-pre-line">{j.about_team}</p>
                </Section>
              )}
              {j.hiring_process.length > 0 && (
                <Section title="Sollicitatieprocedure">
                  <ol className="flex flex-col">
                    {j.hiring_process.map((step, i) => (
                      <li key={step} className="relative flex gap-3 pb-4 last:pb-0">
                        {i < j.hiring_process.length - 1 && <span aria-hidden className="absolute left-[13px] top-7 h-[calc(100%-1.75rem)] w-px bg-border" />}
                        <span className="grid size-7 shrink-0 place-items-center rounded-full border border-border bg-surface-2 text-xs font-semibold text-text">{i + 1}</span>
                        <span className="pt-0.5">{step}</span>
                      </li>
                    ))}
                  </ol>
                </Section>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Vacaturedetails" />
            <CardBody>
              <dl className="grid gap-x-6 gap-y-4 sm:grid-cols-2">
                {detailRows(j).map(([label, value]) => (
                  <div key={label} className="min-w-0">
                    <dt className="text-xs font-medium uppercase tracking-wide text-muted">{label}</dt>
                    <dd className="mt-0.5 text-sm text-text">{value}</dd>
                  </div>
                ))}
              </dl>
            </CardBody>
          </Card>

          <AboutCompany job={j} />
        </div>

        <aside className="flex flex-col gap-6">
          {isCandidate && open && (
            <Card>
              <CardHeader title={t("match.title")} />
              <CardBody>
                {match.error ? <QueryError error={match.error} /> : !match.data ? <Skeleton className="h-72" /> : <MatchBreakdown result={match.data.result} calculatedAt={match.data.calculated_at} />}
              </CardBody>
            </Card>
          )}
          {!me.data && (
            <Card><CardBody className="text-sm text-text-2">Met een account zie je hoe goed deze vacature bij je past, en waarom.</CardBody></Card>
          )}
          <HiringTeam job={j} />
          <Card>
            <CardHeader title="In het kort" />
            <CardBody>
              <ul className="flex flex-col gap-2.5">
                <Highlight icon={MapPin}>{j.city ?? t("common.notSpecified")} · {t(`enums.remote.${j.remote_policy}`)}</Highlight>
                <Highlight icon={Wallet}>{salary ?? <span className="italic">Loon niet vermeld</span>}</Highlight>
                {j.hours_per_week && <Highlight icon={Timer}>{j.hours_per_week} uur per week</Highlight>}
                <Highlight icon={GraduationCap}>{j.education_level ? t(`enums.education.${j.education_level}`) : "Geen opleidingseis"}</Highlight>
                <Highlight icon={CalendarDays}>Start: {j.start_date ? formatDate(j.start_date) : "in overleg"}</Highlight>
              </ul>
            </CardBody>
          </Card>
        </aside>
      </div>

      {related.data && related.data.length > 0 && (
        <section>
          <h2 className="mb-3 text-[15px] font-semibold text-text">Gelijkaardige vacatures</h2>
          <div className="grid gap-3 md:grid-cols-2">{related.data.map((r) => <JobCard key={r.id} job={r} showActions={false} />)}</div>
        </section>
      )}

      {isCandidate && open && <OptimizeDialog job={j} open={optimizeOpen} onOpenChange={setOptimizeOpen} />}
      {isCandidate && open && <ApplyDialog job={j} open={applyOpen} onOpenChange={setApplyOpen} />}
    </div>
  );
}
