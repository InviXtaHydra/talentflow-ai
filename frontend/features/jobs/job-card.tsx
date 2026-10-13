"use client";

import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bookmark, BookmarkCheck, Briefcase, Clock, MapPin, Sparkles, Wallet } from "lucide-react";
import Link from "next/link";
import { toast } from "sonner";

import { Badge } from "@/components/ui/feedback";
import { Button } from "@/components/ui/button";
import { api, errorMessage } from "@/lib/api";
import { formatSalary, relativeTime } from "@/lib/format";
import { t } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { JobSummary } from "@/types/api";

import { CompanyLogo } from "./company-logo";
import { MatchScore } from "./match-score";

export function DemoBadge() {
  return <Badge tone="neutral" title={t("app.demoTitle")}>{t("app.demo")}</Badge>;
}

export function SaveJobButton({ job, compact }: { job: Pick<JobSummary, "id" | "saved">; compact?: boolean }) {
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => (job.saved ? api.delete(`/jobs/${job.id}/save`) : api.post(`/jobs/${job.id}/save`)),
    onSuccess: () => {
      toast.success(job.saved ? "Niet meer bewaard" : "Vacature bewaard");
      qc.invalidateQueries({ queryKey: ["jobs"] });
      qc.invalidateQueries({ queryKey: ["job", job.id] });
      qc.invalidateQueries({ queryKey: ["saved"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const Icon = job.saved ? BookmarkCheck : Bookmark;
  return (
    <Button variant={compact ? "ghost" : "secondary"} size={compact ? "icon" : "md"} loading={mutation.isPending} onClick={() => mutation.mutate()}
      aria-pressed={job.saved} aria-label={job.saved ? "Niet meer bewaren" : "Bewaren"}>
      <Icon className={cn(job.saved && "text-accent")} />
      {!compact && (job.saved ? "Bewaard" : "Bewaren")}
    </Button>
  );
}

export function JobMeta({ job, className }: { job: JobSummary; className?: string }) {
  const salary = formatSalary(job.salary_min, job.salary_max, job.salary_currency, job.salary_period);
  return (
    <div className={cn("flex flex-wrap items-center gap-x-4 gap-y-1.5 text-sm text-muted", className)}>
      <span className="inline-flex items-center gap-1.5"><MapPin className="size-3.5" />{job.city ?? t("common.notSpecified")} · {t(`enums.remote.${job.remote_policy}`)}</span>
      <span className="inline-flex items-center gap-1.5"><Briefcase className="size-3.5" />{t(`enums.employmentType.${job.employment_type}`)}{job.experience_level && ` · ${t(`enums.experienceLevel.${job.experience_level}`)}`}</span>
      <span className="inline-flex items-center gap-1.5"><Wallet className="size-3.5" />{salary ?? <span className="italic">Loon niet vermeld</span>}</span>
      {job.published_at && <span className="inline-flex items-center gap-1.5"><Clock className="size-3.5" />{relativeTime(job.published_at)}</span>}
    </div>
  );
}

export function JobCard({ job, showActions = true }: { job: JobSummary; showActions?: boolean }) {
  const match = job.match;
  return (
    <article className="group relative rounded-xl border border-border bg-surface p-5 shadow-card transition-shadow hover:shadow-pop">
      <div className="flex gap-4">
        <CompanyLogo company={job.company} size={44} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <h3 className="text-[15px] font-semibold text-text">
                <Link href={`/jobs/${job.id}`} className="after:absolute after:inset-0 hover:text-accent focus:outline-none">{job.title}</Link>
              </h3>
              <p className="mt-0.5 flex flex-wrap items-center gap-2 text-sm text-text-2">
                {job.company.name}
                {job.is_demo && <DemoBadge />}
                {job.status === "closed" && <Badge tone="danger">Gesloten</Badge>}
              </p>
            </div>
            {match && <MatchScore score={match.score} />}
          </div>
          <JobMeta job={job} className="mt-3" />
          {match && match.score != null && (
            <div className="mt-3 flex flex-wrap items-center gap-1.5">
              {match.matching_skills.map((s) => <Badge key={s} tone="success">{s}</Badge>)}
              {match.missing_required_skills.slice(0, 2).map((s) => <Badge key={s} tone="warning" title="Gevraagd, niet gevonden in je profiel">mist: {s}</Badge>)}
              {match.eligibility === "not_met" && <Badge tone="danger">harde eis niet vervuld</Badge>}
            </div>
          )}
          {match && match.score == null && <p className="mt-3 text-xs text-muted">{t("match.insufficientHelp")}</p>}
          {showActions && (
            <div className="relative z-10 mt-4 flex flex-wrap items-center gap-2">
              <Button asChild size="sm" variant="secondary"><Link href={`/jobs/${job.id}`}>Bekijken</Link></Button>
              {match && (
                <Button asChild size="sm" variant="ghost">
                  <Link href={`/jobs/${job.id}?optimize=1`}><Sparkles />Optimaliseer cv</Link>
                </Button>
              )}
              {match && <div className="ml-auto"><SaveJobButton job={job} compact /></div>}
            </div>
          )}
        </div>
      </div>
    </article>
  );
}
