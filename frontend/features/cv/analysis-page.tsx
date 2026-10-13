"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Lightbulb, ScanSearch, Star, XCircle } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { Alert, Badge, EmptyState, Progress, Skeleton } from "@/components/ui/feedback";
import { scoreTone } from "@/features/jobs/match-score";
import { useTask } from "@/hooks/use-task";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { CvAnalysis } from "@/types/api";

const CHECKS: Record<string, [string, string]> = {
  contact: ["Contactgegevens", "Telefoonnummer en woonplaats staan vermeld."],
  headline: ["Titel", "Een korte titel bovenaan je cv."],
  summary: ["Samenvatting", "Een samenvatting van 30 tot 150 woorden."],
  experience: ["Werkervaring", "Minstens één functie."],
  experience_dates: ["Data", "Elke functie heeft een begindatum."],
  bullets: ["Concrete taken", "Minstens twee punten per functie."],
  quantified: ["Resultaten", "Minstens twee punten met cijfers (alleen als je ze echt hebt)."],
  skills: ["Vaardigheden", "Minstens zes vaardigheden."],
  education: ["Opleiding", "Minstens één opleiding."],
  languages: ["Talen", "Je talenkennis staat vermeld."],
};

export function CvAnalysisPage() {
  const qc = useQueryClient();
  const analyses = useQuery({ queryKey: ["analyses"], queryFn: () => api.get<CvAnalysis[]>("/cv-analyses") });
  const [taskId, setTaskId] = React.useState<string | null>(null);
  const task = useTask(taskId);
  const finished = !!task.data && ["succeeded", "failed", "cancelled"].includes(task.data.status);
  React.useEffect(() => {
    if (!finished || !task.data) return;
    if (task.data.status === "failed") toast.error(task.data.error_message ?? "Analyse mislukt");
    qc.invalidateQueries({ queryKey: ["analyses"] });
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  }, [finished, task.data, qc]);
  const run = useMutation({
    mutationFn: () => api.post<{ task_id: string }>("/cv-analyses"),
    onSuccess: (data) => setTaskId(data.task_id),
    onError: (e) => toast.error(errorMessage(e)),
  });
  const latest = analyses.data?.[0];
  const busy = run.isPending || (!!taskId && !finished);

  return (
    <>
      <PageHeader title="Cv-analyse" description="Een controle van je profiel zoals het op je cv komt, met concrete verbeterpunten."
        actions={<Button loading={busy} onClick={() => run.mutate()}><ScanSearch />{latest ? "Opnieuw analyseren" : "Analyse starten"}</Button>} />
      {busy && <Card className="mb-6"><CardBody className="flex flex-col gap-2"><p className="text-sm text-text-2">{task.data?.progress_message ?? "Analyse in de wachtrij…"}</p><Progress value={task.data?.progress ?? 10} /></CardBody></Card>}
      {analyses.error ? <QueryError error={analyses.error} /> : !analyses.data ? <Skeleton className="h-64" /> : !latest ? (
        <EmptyState icon={ScanSearch} title="Nog geen analyse" description="Start een analyse om te zien hoe volledig en sterk je cv is. We tonen geen score voordat de analyse gedaan is." />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[320px_1fr]">
          <Card>
            <CardBody className="flex flex-col items-center gap-2 py-8 text-center">
              <p className={cn("text-5xl font-semibold tabular-nums", scoreTone(latest.quality_score))}>{latest.quality_score}<span className="text-xl text-muted">/100</span></p>
              <p className="text-sm font-medium text-text">Kwaliteitscontrole</p>
              <p className="text-xs text-muted">Regelgebaseerde checklist{latest.method.includes("ai") ? " + AI-feedback" : ""} · {formatDateTime(latest.created_at)}</p>
              {latest.status === "completed_without_ai" && <Badge tone="warning">AI-feedback was niet beschikbaar</Badge>}
            </CardBody>
          </Card>
          <div className="flex flex-col gap-6">
            <Card>
              <CardHeader title="Checklist" description="De score is het gewogen aandeel geslaagde controles." />
              <CardBody>
                <ul className="grid gap-3 sm:grid-cols-2">
                  {latest.checks.map((c) => (
                    <li key={c.key} className="flex gap-2.5 text-sm">
                      {c.passed ? <CheckCircle2 className="mt-0.5 size-4 shrink-0 text-success" /> : <XCircle className="mt-0.5 size-4 shrink-0 text-danger" />}
                      <div><p className="font-medium text-text">{CHECKS[c.key]?.[0] ?? c.key}</p><p className="text-muted">{CHECKS[c.key]?.[1]}</p></div>
                    </li>
                  ))}
                </ul>
              </CardBody>
            </Card>
            {(latest.strengths.length > 0 || latest.suggestions.length > 0) ? (
              <div className="grid gap-6 md:grid-cols-2">
                <Card><CardHeader title="Sterke punten" /><CardBody><ul className="flex flex-col gap-2 text-sm text-text-2">{latest.strengths.map((s) => <li key={s} className="flex gap-2"><Star className="mt-0.5 size-4 shrink-0 text-success" />{s}</li>)}</ul></CardBody></Card>
                <Card><CardHeader title="Suggesties" /><CardBody><ul className="flex flex-col gap-2 text-sm text-text-2">{latest.suggestions.map((s) => <li key={s} className="flex gap-2"><Lightbulb className="mt-0.5 size-4 shrink-0 text-warning" />{s}</li>)}</ul></CardBody></Card>
              </div>
            ) : <Alert tone="neutral">Schriftelijke feedback van het AI-model is niet beschikbaar voor deze analyse.</Alert>}
          </div>
        </div>
      )}
    </>
  );
}
