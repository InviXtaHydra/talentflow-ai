"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowRight, Bookmark, Briefcase, Eye, FileText, Lightbulb, MessageSquareText, Search, Sparkles } from "lucide-react";
import Link from "next/link";

import { PageHeader, QueryError } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Alert, Badge, EmptyState, Skeleton } from "@/components/ui/feedback";
import { JobCard } from "@/features/jobs/job-card";
import { scoreTone } from "@/features/jobs/match-score";
import { useMe } from "@/hooks/use-auth";
import { api } from "@/lib/api";
import { languageName, relativeTime } from "@/lib/format";
import { t } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { ApplicationStatus, JobSummary } from "@/types/api";

interface Dashboard {
  profile: { headline: string | null; confirmed: boolean; onboarding_completed: boolean; has_content: boolean };
  recommendations: JobSummary[];
  recommendation_count: number;
  cv: {
    latest: { id: string; filename: string; status: string; confirmed: boolean; uploaded_at: string } | null;
    analysis: { id: string; quality_score: number | null; method: string; created_at: string; suggestions: string[]; failed_checks: string[] } | null;
    generated_versions: number;
  };
  applications: Partial<Record<ApplicationStatus, number>>;
  insights: { type: string; [k: string]: unknown }[];
  activity: { type: string; at: string; title: string; link: string; status?: string }[];
}

const CHECK_LABELS: Record<string, string> = {
  contact: "Contactgegevens aanvullen", headline: "Een titel toevoegen", summary: "Een samenvatting van 30-150 woorden schrijven",
  experience: "Werkervaring toevoegen", experience_dates: "Data bij elke functie vermelden", bullets: "Minstens 2 punten per functie",
  quantified: "Resultaten met cijfers onderbouwen (als je ze hebt)", skills: "Minstens 6 vaardigheden vermelden", education: "Opleiding toevoegen",
  languages: "Talenkennis vermelden",
};

function insightText(insight: Dashboard["insights"][number]): string {
  switch (insight.type) {
    case "skill_gap":
      return `${insight.skill} wordt gevraagd in ${insight.jobs} van je ${insight.sample} best passende vacatures en staat niet in je profiel.`;
    case "language_gap":
      return `${languageName(String(insight.language))} is vereist in ${insight.jobs} van je ${insight.sample} best passende vacatures.`;
    case "remote_share":
      return `${insight.share}% van je best passende vacatures biedt hybride of volledig thuiswerk.`;
    case "jobs_in_area":
      return `${insight.count} van de ${insight.total} open vacatures liggen binnen je pendelafstand.`;
    default:
      return "";
  }
}

const ACTIVITY_ICON = { saved_job: Bookmark, viewed_job: Eye, cv_version: FileText, application: Briefcase } as const;
const ACTIVITY_LABEL: Record<string, string> = { saved_job: "Bewaard", viewed_job: "Bekeken", cv_version: "Cv-versie", application: "Sollicitatie" };

export function CandidateDashboard() {
  const me = useMe();
  const query = useQuery({ queryKey: ["dashboard"], queryFn: () => api.get<Dashboard>("/candidates/me/dashboard") });
  const firstName = me.data?.full_name.split(" ")[0];

  if (query.error) return <QueryError error={query.error} onRetry={() => query.refetch()} />;
  const d = query.data;
  const appTotal = d ? Object.values(d.applications).reduce((a, b) => a + (b ?? 0), 0) : 0;

  return (
    <>
      <PageHeader title={firstName ? `Hallo ${firstName}` : "Dashboard"} description="Je persoonlijke overzicht: matches, cv en sollicitaties."
        actions={<Button asChild><Link href="/jobs"><Search />Vacatures zoeken</Link></Button>} />

      {d && !d.profile.has_content && (
        <Alert tone="accent" title="Vul je profiel aan voor betrouwbare matches" className="mb-6"
          action={<Button asChild size="sm"><Link href={d.profile.onboarding_completed ? "/profile" : "/onboarding"}>Profiel aanvullen</Link></Button>}>
          Zonder vaardigheden of werkervaring kunnen we nog geen eerlijke matchscore berekenen.
        </Alert>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
        <section aria-labelledby="recs">
          <div className="mb-3 flex items-center justify-between">
            <h2 id="recs" className="text-[15px] font-semibold text-text">Aanbevolen voor jou</h2>
            {d && d.recommendation_count > 0 && <Link href="/jobs?sort=match" className="text-sm font-medium text-accent hover:underline">Alle {d.recommendation_count} matches</Link>}
          </div>
          {!d ? (
            <div className="flex flex-col gap-3">{[0, 1, 2].map((i) => <Skeleton key={i} className="h-40" />)}</div>
          ) : d.recommendations.length ? (
            <div className="flex flex-col gap-3">{d.recommendations.map((job) => <JobCard key={job.id} job={job} />)}</div>
          ) : (
            <EmptyState icon={Search} title="Nog geen aanbevelingen"
              description={d.profile.has_content ? "Er zijn momenteel geen open vacatures die bij je profiel passen." : "Vul je profiel aan, dan tonen we hier de vacatures die het best passen."}
              action={<Button asChild variant="secondary"><Link href="/jobs">Alle vacatures bekijken</Link></Button>} />
          )}
        </section>

        <aside className="flex flex-col gap-6">
          <Card>
            <CardHeader title="Je cv" action={<Link href="/cv" className="text-sm font-medium text-accent hover:underline">Beheren</Link>} />
            <CardBody className="flex flex-col gap-3 text-sm">
              {!d ? <Skeleton className="h-24" /> : (
                <>
                  {d.cv.latest ? (
                    <p className="text-text-2"><FileText className="mr-1.5 inline size-4 text-muted" />{d.cv.latest.filename} <span className="text-muted">· {relativeTime(d.cv.latest.uploaded_at)}</span></p>
                  ) : <p className="text-muted">Nog geen cv geüpload.</p>}
                  {d.cv.analysis && d.cv.analysis.quality_score != null ? (
                    <div>
                      <p className="flex items-baseline justify-between"><span className="text-text-2">Kwaliteitscontrole</span>
                        <span className={cn("text-lg font-semibold tabular-nums", scoreTone(d.cv.analysis.quality_score))}>{d.cv.analysis.quality_score}/100</span></p>
                      {d.cv.analysis.failed_checks.length > 0 && (
                        <ul className="mt-2 flex flex-col gap-1 text-muted">{d.cv.analysis.failed_checks.map((c) => <li key={c}>• {CHECK_LABELS[c] ?? c}</li>)}</ul>
                      )}
                    </div>
                  ) : <p className="text-muted">Nog geen analyse uitgevoerd.</p>}
                  <p className="text-text-2">{d.cv.generated_versions} afgestemde cv-versie(s)</p>
                  <Button asChild size="sm" variant="secondary" className="self-start"><Link href="/cv/analysis">{d.cv.analysis ? "Analyse bekijken" : "Cv laten analyseren"}</Link></Button>
                </>
              )}
            </CardBody>
          </Card>

          <Card>
            <CardHeader title="Sollicitaties" action={<Link href="/applications" className="text-sm font-medium text-accent hover:underline">Overzicht</Link>} />
            <CardBody>
              {!d ? <Skeleton className="h-20" /> : appTotal === 0 ? <p className="text-sm text-muted">Je volgt nog geen sollicitaties.</p> : (
                <ul className="grid grid-cols-2 gap-2">
                  {(["saved", "applied", "in_review", "interview", "offer", "rejected"] as ApplicationStatus[]).map((s) => (
                    <li key={s} className="rounded-lg bg-surface-2 px-3 py-2">
                      <p className="text-lg font-semibold tabular-nums text-text">{d.applications[s] ?? 0}</p>
                      <p className="text-xs text-muted">{t(`enums.applicationStatus.${s}`)}</p>
                    </li>
                  ))}
                </ul>
              )}
            </CardBody>
          </Card>

          {d && d.insights.length > 0 && (
            <Card>
              <CardHeader title="Inzichten" description="Afgeleid uit je beste matches" />
              <CardBody>
                <ul className="flex flex-col gap-2.5 text-sm text-text-2">
                  {d.insights.map((insight, i) => <li key={i} className="flex gap-2"><Lightbulb className="mt-0.5 size-4 shrink-0 text-warning" />{insightText(insight)}</li>)}
                </ul>
              </CardBody>
            </Card>
          )}

          <Card className="bg-accent-soft/40">
            <CardBody className="flex flex-col gap-2">
              <p className="flex items-center gap-2 font-semibold text-text"><MessageSquareText className="size-4 text-accent" />Carrière-assistent</p>
              <p className="text-sm text-muted">Stel vragen over een vacature, bereid een gesprek voor of laat een motivatiebrief opstellen.</p>
              <Button asChild size="sm" variant="secondary" className="self-start"><Link href="/assistant">Vraag stellen <ArrowRight /></Link></Button>
            </CardBody>
          </Card>

          {d && d.activity.length > 0 && (
            <Card>
              <CardHeader title="Recente activiteit" />
              <CardBody>
                <ul className="flex flex-col gap-3">
                  {d.activity.map((a, i) => {
                    const Icon = ACTIVITY_ICON[a.type as keyof typeof ACTIVITY_ICON] ?? Sparkles;
                    return (
                      <li key={i} className="flex items-start gap-2.5 text-sm">
                        <Icon className="mt-0.5 size-4 shrink-0 text-muted" />
                        <div className="min-w-0">
                          <Link href={a.link} className="line-clamp-1 font-medium text-text hover:text-accent">{a.title}</Link>
                          <p className="text-xs text-muted">
                            {ACTIVITY_LABEL[a.type]}{a.status && <> · <Badge className="px-1 py-0">{t(`enums.applicationStatus.${a.status}`)}</Badge></>} · {relativeTime(a.at)}
                          </p>
                        </div>
                      </li>
                    );
                  })}
                </ul>
              </CardBody>
            </Card>
          )}
        </aside>
      </div>
    </>
  );
}
