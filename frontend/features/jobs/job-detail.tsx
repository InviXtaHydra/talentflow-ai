"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Building2, ExternalLink, GraduationCap, Languages, MessageSquareText, Pencil, Send, Sparkles } from "lucide-react";
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
import { formatDate, languageName } from "@/lib/format";
import { t } from "@/lib/i18n";
import type { CvLanguage, CvTemplate, CvVersionSummary, JobDetail, JobSummary, MatchOut } from "@/types/api";

import { CompanyLogo } from "./company-logo";
import { DemoBadge, JobCard, JobMeta, SaveJobButton } from "./job-card";
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

  return (
    <div className="flex flex-col gap-6">
      <Link href="/jobs" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-text"><ArrowLeft className="size-4" />Alle vacatures</Link>
      {j.status === "closed" && <Alert tone="warning">Deze vacature is gesloten. Solliciteren kan niet meer.</Alert>}
      {j.status === "draft" && <Alert tone="neutral">Concept: alleen zichtbaar voor jouw bedrijf.</Alert>}

      <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
        <div className="flex flex-col gap-6">
          <Card>
            <CardBody className="flex flex-col gap-5 p-6">
              <div className="flex gap-4">
                <CompanyLogo company={j.company} size={56} />
                <div className="min-w-0">
                  <h1 className="text-2xl font-semibold tracking-tight text-text">{j.title}</h1>
                  <p className="mt-1 flex flex-wrap items-center gap-2 text-text-2">
                    <Link href={`/companies/${j.company.id}`} className="hover:text-accent">{j.company.name}</Link>
                    {j.is_demo && <DemoBadge />}
                  </p>
                </div>
              </div>
              <JobMeta job={j} />
              <div className="flex flex-wrap gap-2">
                {isCandidate && open && <Button onClick={() => setOptimizeOpen(true)}><Sparkles />Optimaliseer mijn cv voor deze vacature</Button>}
                {isCandidate && open && !j.application && <Button variant="secondary" onClick={() => setApplyOpen(true)}><Send />Solliciteren via {j.company.name}</Button>}
                {isCandidate && open && j.application_url && <ExternalApply job={j} />}
                {isCandidate && !j.application && <Button variant="ghost" loading={track.isPending} onClick={() => track.mutate()}>Volgen in sollicitaties</Button>}
                {isCandidate && <SaveJobButton job={j} />}
                {isCandidate && <Button asChild variant="ghost"><Link href={`/assistant?job=${j.id}`}><MessageSquareText />Vraag de assistent</Link></Button>}
                {j.can_edit && <Button asChild variant="secondary"><Link href={`/employer/jobs/${j.id}/edit`}><Pencil />Bewerken</Link></Button>}
                {!me.data && <Button asChild><Link href={`/register?next=/jobs/${j.id}`}>Maak een account om je match te zien</Link></Button>}
              </div>
              {j.application && (
                <Alert tone="accent">Je volgt deze vacature: <strong>{t(`enums.applicationStatus.${j.application.status}`)}</strong>. <Link href="/applications" className="underline">Naar je sollicitaties</Link></Alert>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Over de functie" />
            <CardBody className="flex flex-col gap-6 text-[15px] leading-relaxed text-text-2">
              <p className="whitespace-pre-line">{j.description}</p>
              {j.responsibilities.length > 0 && (
                <div><h3 className="mb-2 font-semibold text-text">Wat je doet</h3><ul className="list-disc space-y-1 pl-5">{j.responsibilities.map((r) => <li key={r}>{r}</li>)}</ul></div>
              )}
              {j.qualifications.length > 0 && (
                <div><h3 className="mb-2 font-semibold text-text">Wat we vragen</h3><ul className="list-disc space-y-1 pl-5">{j.qualifications.map((r) => <li key={r}>{r}</li>)}</ul></div>
              )}
              <div className="grid gap-4 sm:grid-cols-2">
                <div>
                  <h3 className="mb-2 font-semibold text-text">Vaardigheden</h3>
                  <div className="flex flex-wrap gap-1.5">
                    {j.skills.map((s) => <Badge key={s.name} tone={s.is_required ? "accent" : "neutral"} title={s.is_required ? t("common.required") : "Pluspunt"}>{s.name}</Badge>)}
                  </div>
                  <p className="mt-1.5 text-xs text-muted">Gekleurd = verplicht, grijs = pluspunt</p>
                </div>
                <dl className="flex flex-col gap-2 text-sm">
                  <div className="flex gap-2"><GraduationCap className="size-4 text-muted" /><dt className="sr-only">Opleiding</dt><dd>{j.education_level ? t(`enums.education.${j.education_level}`) : "Geen opleidingseis vermeld"}</dd></div>
                  <div className="flex gap-2"><Languages className="size-4 text-muted" /><dt className="sr-only">Talen</dt><dd>{j.required_languages.length ? j.required_languages.map(languageName).join(", ") : "Geen taalvereisten vermeld"}</dd></div>
                  <div className="flex gap-2"><Building2 className="size-4 text-muted" /><dt className="sr-only">Ervaring</dt><dd>{j.min_years_experience != null ? `${j.min_years_experience} jaar ervaring` : "Ervaring niet vermeld"}</dd></div>
                  {j.application_deadline && <div className="text-muted">Solliciteren tot {formatDate(j.application_deadline)}</div>}
                </dl>
              </div>
            </CardBody>
          </Card>
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
