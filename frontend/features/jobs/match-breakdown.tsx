import { AlertTriangle, CheckCircle2, CircleHelp, Info, MinusCircle, XCircle } from "lucide-react";

import { Badge } from "@/components/ui/feedback";
import { formatMoney, languageName } from "@/lib/format";
import { t } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { MatchComponent, MatchResult, PreferenceCheck } from "@/types/api";

import { MatchScore, scoreTone } from "./match-score";

const HARD_CAP = 60;

function issueText(issue: Record<string, unknown>): string {
  const code = String(issue.code);
  const params: Record<string, string | number> = {};
  for (const [k, v] of Object.entries(issue)) params[k] = typeof v === "number" ? v : String(v ?? "");
  if (code.startsWith("language")) params.value = languageName(String(issue.value));
  if (code === "language_level") params.level = t(`enums.languageLevel.${issue.level}`);
  if (code === "education") params.value = t(`enums.education.${issue.value}`);
  return t(`match.issue.${code}`, params);
}

function componentDetail(c: MatchComponent): string | null {
  const d = c.details as Record<string, number | string | null>;
  if (!c.applicable) {
    const reasons: Record<string, string> = {
      no_job_skills: "De vacature vermeldt geen vaardigheden.",
      no_candidate_skills: "Je profiel bevat nog geen vaardigheden of werkervaring.",
      no_candidate_experience: "Je profiel bevat nog geen werkervaring.",
      no_candidate_titles: "Je profiel bevat nog geen functietitels.",
      no_job_requirement: "De vacature stelt geen opleidingseis.",
      no_candidate_education: "Je profiel vermeldt geen opleidingsniveau.",
      no_preferences: "Je hebt nog geen voorkeuren ingesteld.",
    };
    return reasons[String(d.reason)] ?? t("match.notApplicable");
  }
  switch (c.key) {
    case "skills":
      return `${d.matched} van ${d.total} gevraagde vaardigheden gevonden (${d.required_matched}/${d.required_total} verplicht).`;
    case "experience":
      return d.required_years != null
        ? `${d.relevant_years} jaar relevante ervaring gevonden; gevraagd: ${d.required_years} jaar.`
        : `${d.relevant_count} relevante functie(s) gevonden.`;
    case "role":
      return `Vergeleken via ${t(`match.method.${d.method}`)}.`;
    case "qualifications":
      return `Gevraagd: ${t(`enums.education.${d.required}`)}; jouw niveau: ${t(`enums.education.${d.candidate}`)}.`;
    case "preferences":
      return `${d.evaluated} voorkeur(en) vergeleken.`;
  }
  return null;
}

const prefIcon = { match: CheckCircle2, partial: MinusCircle, mismatch: XCircle, unknown: CircleHelp };
const prefTone = { match: "text-success", partial: "text-warning", mismatch: "text-danger", unknown: "text-muted" };

function preferenceText(check: PreferenceCheck): string {
  if (check.key === "location") {
    if (check.reason === "remote_job") return t("match.remoteJob");
    if (check.reason === "no_location") return t("match.noLocation");
    if (check.reason === "unknown_place") return "Afstand kon niet bepaald worden";
    return check.distance_km === 0 ? "In je voorkeurslocatie" : t("match.distance", { km: Number(check.distance_km) });
  }
  if (check.key === "remote") return `Jij: ${t(`enums.remote.${check.wanted}`)} · vacature: ${t(`enums.remote.${check.offered}`)}`;
  if (check.key === "employment_type") return t(`enums.employmentType.${check.offered}`);
  if (check.key === "salary") {
    if (check.reason === "no_salary_in_job") return t("match.noSalary");
    return `Tot ${formatMoney(Number(check.job_annual_max_eur))}/jaar · jouw minimum ${formatMoney(Number(check.wanted_annual_eur))}/jaar`;
  }
  if (check.key === "industry") return String(check.offered);
  return "";
}

export function MatchBreakdown({ result, calculatedAt, compact }: { result: MatchResult; calculatedAt?: string; compact?: boolean }) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-4">
        <MatchScore score={result.score} size={64} />
        <div className="min-w-0">
          <p className="font-semibold text-text">{result.score == null ? t("match.insufficient") : `${result.score}% match`}</p>
          <p className="text-sm text-muted">{result.score == null ? t("match.insufficientHelp") : t(`match.eligibility.${result.eligibility.status}`)}</p>
        </div>
      </div>

      {(result.eligibility.issues.length > 0 || result.eligibility.unknown.length > 0) && (
        <div className={cn("rounded-lg border px-4 py-3 text-sm", result.eligibility.issues.length ? "border-danger/30 bg-danger-soft" : "border-warning/30 bg-warning-soft")}>
          <ul className="flex flex-col gap-1">
            {result.eligibility.issues.map((issue, i) => (
              <li key={`i${i}`} className="flex items-start gap-2 text-danger"><AlertTriangle className="mt-0.5 size-4 shrink-0" />{issueText(issue)}</li>
            ))}
            {result.eligibility.unknown.map((issue, i) => (
              <li key={`u${i}`} className="flex items-start gap-2 text-warning"><CircleHelp className="mt-0.5 size-4 shrink-0" />Niet te controleren: {issueText(issue)}</li>
            ))}
          </ul>
          {result.capped && <p className="mt-2 text-xs text-text-2">{t("match.capped", { cap: HARD_CAP })}</p>}
        </div>
      )}

      <ul className="flex flex-col gap-3" aria-label="Score per onderdeel">
        {result.components.map((c) => (
          <li key={c.key}>
            <div className="flex items-baseline justify-between gap-3 text-sm">
              <span className="font-medium text-text-2">{t(`match.components.${c.key}`)}</span>
              <span className={cn("tabular-nums", c.applicable ? scoreTone(c.score) : "text-muted")}>
                {c.applicable ? `${c.score}%` : t("match.notApplicable")}
                <span className="ml-2 text-xs text-muted">{c.applicable ? t("match.weight", { weight: Math.round(c.effective_weight * 100) }) : ""}</span>
              </span>
            </div>
            <div className="mt-1.5 h-1.5 overflow-hidden rounded-full bg-surface-2">
              {c.applicable && <div className={cn("h-full rounded-full bg-current", scoreTone(c.score))} style={{ width: `${c.score}%` }} />}
            </div>
            {!compact && <p className="mt-1 text-xs text-muted">{componentDetail(c)}</p>}
          </li>
        ))}
      </ul>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <h4 className="mb-2 text-sm font-medium text-text-2">{t("match.matchingSkills")}</h4>
          <div className="flex flex-wrap gap-1.5">
            {result.matching_skills.length ? result.matching_skills.map((s) => (
              <Badge key={s.name} tone="success" title={s.evidence === "experience" ? t("match.evidenceExperience") : undefined}>
                {s.name}{s.evidence === "experience" && " *"}
              </Badge>
            )) : <span className="text-sm text-muted">—</span>}
          </div>
          {result.matching_skills.some((s) => s.evidence === "experience") && <p className="mt-1.5 text-xs text-muted">* {t("match.evidenceExperience")}</p>}
        </div>
        <div>
          <h4 className="mb-2 text-sm font-medium text-text-2">{t("match.missingRequired")}</h4>
          <div className="flex flex-wrap gap-1.5">
            {result.missing_required_skills.length ? result.missing_required_skills.map((s) => <Badge key={s.name} tone="warning">{s.name}</Badge>) : <span className="text-sm text-muted">—</span>}
          </div>
          {result.missing_preferred_skills.length > 0 && (
            <>
              <h4 className="mb-2 mt-3 text-sm font-medium text-text-2">{t("match.missingPreferred")}</h4>
              <div className="flex flex-wrap gap-1.5">{result.missing_preferred_skills.map((s) => <Badge key={s.name}>{s.name}</Badge>)}</div>
            </>
          )}
        </div>
      </div>

      {!compact && result.preference_checks.length > 0 && (
        <div>
          <h4 className="mb-2 text-sm font-medium text-text-2">{t("match.components.preferences")}</h4>
          <ul className="flex flex-col gap-1.5 text-sm">
            {result.preference_checks.map((check) => {
              const Icon = prefIcon[check.status];
              return (
                <li key={check.key} className="flex items-start gap-2">
                  <Icon className={cn("mt-0.5 size-4 shrink-0", prefTone[check.status])} aria-label={t(`match.prefStatus.${check.status}`)} />
                  <span><span className="font-medium text-text-2">{t(`match.preference.${check.key}`)}:</span> <span className="text-muted">{preferenceText(check)}</span></span>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {!compact && (
        <details className="rounded-lg bg-surface-2 px-4 py-3 text-sm text-text-2">
          <summary className="flex cursor-pointer items-center gap-2 font-medium"><Info className="size-4" />{t("match.howCalculated")}</summary>
          <p className="mt-2">{t("match.howCalculatedText")}</p>
          <p className="mt-2">{t("match.challenge")}</p>
          {calculatedAt && <p className="mt-2 text-xs text-muted">{t("match.calculatedAt", { date: new Date(calculatedAt).toLocaleString("nl-BE"), version: result.algorithm_version })}</p>}
        </details>
      )}
    </div>
  );
}
