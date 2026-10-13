"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertTriangle, ArrowLeft, ArrowRight, Check, CircleHelp, Copy, Info, Loader2, RotateCcw, Save, Sparkles } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { PageSkeleton } from "@/components/page-suspense";
import { Button } from "@/components/ui/button";
import { Card, CardBody, CardHeader } from "@/components/ui/card";
import { ConfirmDialog } from "@/components/ui/dialog";
import { Alert, Badge, Progress } from "@/components/ui/feedback";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { MatchBreakdown } from "@/features/jobs/match-breakdown";
import { MatchScore } from "@/features/jobs/match-score";
import { api, errorMessage } from "@/lib/api";
import { formatDateTime, period } from "@/lib/format";
import { t } from "@/lib/i18n";
import { cn } from "@/lib/utils";
import type { CvContent, CvTemplate, CvVersionDetail, ReviewItem } from "@/types/api";

import { CvContentEditor } from "./cv-editor";
import { CvPreview } from "./cv-preview";
import { useDraft } from "@/hooks/use-draft";

function ScoreComparison({ v }: { v: CvVersionDetail }) {
  const before = v.score_before;
  const after = v.score_after;
  const same = before === after;
  return (
    <Card>
      <CardBody className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div className="flex items-center gap-3">
          <div className="text-center"><MatchScore score={before} size={56} /><p className="mt-1 text-xs text-muted">Vóór</p></div>
          <ArrowRight className="size-5 text-muted" />
          <div className="text-center"><MatchScore score={after} size={56} /><p className="mt-1 text-xs text-muted">Na</p></div>
        </div>
        <div className="text-sm text-text-2 sm:border-l sm:border-border sm:pl-4">
          <p className="font-medium text-text">Matchscore, met dezelfde berekening vóór en na</p>
          {same ? (
            <p className="mt-1">De score blijft gelijk. Dat is normaal: het nieuwe cv presenteert je bestaande ervaring beter, maar verandert niets aan je echte vaardigheden of ervaring.</p>
          ) : after != null && before != null && after > before ? (
            <p className="mt-1">De score steeg omdat relevante ervaring nu explicieter in je cv staat. Je kwalificaties zelf zijn niet veranderd.</p>
          ) : (
            <p className="mt-1">De score daalde licht, bijvoorbeeld omdat minder relevante punten weggelaten werden. Bekijk de wijzigingen hieronder.</p>
          )}
        </div>
      </CardBody>
    </Card>
  );
}

function Generating({ v }: { v: CvVersionDetail }) {
  return (
    <Card>
      <CardBody className="flex flex-col items-center gap-4 py-12 text-center" aria-live="polite">
        <Loader2 className="size-8 animate-spin text-accent" />
        <div>
          <p className="font-semibold text-text">Je cv wordt afgestemd op deze vacature</p>
          <p className="mt-1 text-sm text-muted">{v.task_message ?? (v.task_status === "queued" ? "In de wachtrij…" : "Bezig…")}</p>
        </div>
        <Progress value={v.task_progress ?? 5} className="max-w-sm" label="Voortgang" />
        <p className="max-w-md text-xs text-muted">Je mag deze pagina verlaten; je vindt het resultaat terug onder Mijn cv&apos;s en krijgt een melding wanneer het klaar is.</p>
      </CardBody>
    </Card>
  );
}

function SideBySide({ original, tailored }: { original: CvContent; tailored: CvContent }) {
  const originalBullets = new Set(original.experiences.flatMap((e) => e.bullets.map((b) => b.text)));
  const column = (title: string, cv: CvContent, highlight: boolean) => (
    <div className="min-w-0 rounded-lg border border-border bg-surface p-4">
      <p className="mb-3 text-xs font-semibold uppercase tracking-wide text-muted">{title}</p>
      {cv.headline && <p className="font-medium text-text">{cv.headline}</p>}
      <p className={cn("mt-1 text-sm text-text-2", highlight && cv.summary !== original.summary && "rounded bg-accent-soft/60 px-1")}>{cv.summary}</p>
      {cv.experiences.map((e, i) => (
        <div key={e.source_id ?? i} className="mt-4">
          <p className="text-sm font-medium text-text">{e.title} — {e.employer}</p>
          <p className="text-xs text-muted">{period(e.start, e.end, e.is_current)}</p>
          <ul className="mt-1.5 list-disc space-y-1 pl-4 text-sm text-text-2">
            {e.bullets.map((b, k) => <li key={k} className={cn(highlight && !originalBullets.has(b.text) && "rounded bg-accent-soft/60 px-1")}>{b.text}</li>)}
          </ul>
        </div>
      ))}
      <p className="mt-4 text-sm font-medium text-text">Vaardigheden</p>
      <p className="text-sm text-text-2">{cv.skills.join(" · ")}</p>
    </div>
  );
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {column("Origineel", original, false)}
      {column("Afgestemd (gemarkeerd = gewijzigd)", tailored, true)}
    </div>
  );
}

function ReviewList({ items, onAccept }: { items: ReviewItem[]; onAccept: (item: ReviewItem) => void }) {
  const unsupported = items.filter((i) => i.kind !== "gap");
  const gaps = items.filter((i) => i.kind === "gap");
  return (
    <div className="flex flex-col gap-5">
      <div>
        <h3 className="mb-2 flex items-center gap-2 font-semibold text-text"><AlertTriangle className="size-4 text-warning" />Niet overgenomen: niet terug te vinden in je profiel</h3>
        {unsupported.length === 0 ? <p className="text-sm text-muted">De feitencontrole vond geen voorstellen die afwijken van je profiel.</p> : (
          <ul className="flex flex-col gap-2">
            {unsupported.map((item, i) => (
              <li key={i} className="rounded-lg border border-warning/30 bg-warning-soft/50 p-3 text-sm">
                <p className="text-text">“{item.text}”</p>
                <p className="mt-1 text-xs text-warning">{item.reason}</p>
                {(item.kind === "bullet" || item.kind === "skill") && (
                  <Button size="sm" variant="ghost" className="mt-1 h-7 px-2" onClick={() => onAccept(item)}><Check />Klopt, toch toevoegen</Button>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>
      {gaps.length > 0 && (
        <div>
          <h3 className="mb-2 flex items-center gap-2 font-semibold text-text"><Info className="size-4 text-accent" />Gevraagd in de vacature, niet in je profiel</h3>
          <div className="flex flex-wrap gap-1.5">{gaps.map((g) => <Badge key={g.text} tone="warning">{g.text}</Badge>)}</div>
          <p className="mt-2 text-xs text-muted">Heb je deze ervaring wel? Voeg ze toe aan je <Link className="underline" href="/profile">profiel</Link> en genereer opnieuw. Voeg niets toe dat niet klopt.</p>
        </div>
      )}
    </div>
  );
}

export function OptimizationWorkspace() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const qc = useQueryClient();
  const key = ["optimization", id];
  const query = useQuery({
    queryKey: key,
    queryFn: () => api.get<CvVersionDetail>(`/cv-optimizations/${id}`),
    refetchInterval: (q) => (q.state.data?.status === "generating" ? 2000 : false),
  });
  const v = query.data;
  const [confirm, setConfirm] = React.useState<null | "generated" | "original" | "regenerate">(null);
  const savedKey = v?.updated_at ?? "";
  const ready = v?.status === "ready" && !!v.content;
  const [local, setLocal] = useDraft(ready ? v : undefined, ready ? savedKey : undefined, (x: CvVersionDetail) => ({ content: x.content as CvContent, template: x.template }));
  const draft = local?.content ?? null;
  const template: CvTemplate = local?.template ?? "modern";
  const setDraft = (content: CvContent) => setLocal((l) => ({ ...l, content }));
  const setTemplate = (tpl: CvTemplate) => setLocal((l) => ({ ...l, template: tpl }));

  const dirty = !!v?.content && !!draft && JSON.stringify(draft) !== JSON.stringify(v.content);

  const save = useMutation({
    mutationFn: (body: { content?: CvContent; template?: CvTemplate }) => api.patch<CvVersionDetail>(`/cv-optimizations/${id}`, body),
    onSuccess: (data) => { qc.setQueryData(key, data); qc.invalidateQueries({ queryKey: ["cv-versions"] }); toast.success("Versie opgeslagen"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const restore = useMutation({
    mutationFn: (target: "generated" | "original") => api.post<CvVersionDetail>(`/cv-optimizations/${id}/restore`, { target }),
    onSuccess: (data) => { qc.setQueryData(key, data); setConfirm(null); toast.success("Inhoud hersteld"); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const regenerate = useMutation({
    mutationFn: () => api.post<{ optimization_id: string }>(`/cv-optimizations/${id}/regenerate`),
    onSuccess: (data) => { setConfirm(null); router.push(`/cv/optimizations/${data.optimization_id}`); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  const duplicate = useMutation({
    mutationFn: () => api.post<{ id: string }>(`/cv-versions/${id}/duplicate`),
    onSuccess: (data) => { toast.success("Kopie gemaakt"); router.push(`/cv/versions/${data.id}`); },
    onError: (e) => toast.error(errorMessage(e)),
  });

  if (query.error) return <QueryError error={query.error} onRetry={() => query.refetch()} />;
  if (!v) return <PageSkeleton />;

  const acceptReview = (item: ReviewItem) => {
    if (!draft) return;
    if (item.kind === "skill") setDraft({ ...draft, skills: [...draft.skills, item.text] });
    if (item.kind === "bullet") {
      setDraft({ ...draft, experiences: draft.experiences.map((e) => (e.source_id === item.source_id ? { ...e, bullets: [...e.bullets, { text: item.text, source_refs: [] }] } : e)) });
    }
    toast.message("Toegevoegd aan je ontwerp. Vergeet niet op te slaan.");
  };

  const report = v.optimization;
  return (
    <div className="flex flex-col gap-6">
      <Link href="/cv" className="inline-flex items-center gap-1.5 text-sm text-muted hover:text-text"><ArrowLeft className="size-4" />Mijn cv&apos;s</Link>
      <PageHeader
        eyebrow={<span className="inline-flex items-center gap-1.5"><Sparkles className="size-4 text-accent" />Cv afgestemd op vacature</span>}
        title={v.target_job_title ?? v.title}
        description={v.target_company_name ? `${v.target_company_name} · ${t(`enums.languages.${v.language}`)}` : undefined}
        actions={v.status === "ready" && (
          <>
            <Button variant="secondary" onClick={() => setConfirm("regenerate")}><RotateCcw />Opnieuw genereren</Button>
            <Button variant="secondary" loading={duplicate.isPending} onClick={() => duplicate.mutate()}><Copy />Kopie bewerken</Button>
            <Button disabled={!dirty} loading={save.isPending} onClick={() => draft && save.mutate({ content: draft, template })}><Save />{dirty ? "Wijzigingen opslaan" : "Opgeslagen"}</Button>
          </>
        )}
      />

      {v.is_simulated && (
        <Alert tone="warning" title="Gesimuleerd resultaat (demo)">
          Er is geen AI-model ingesteld. Dit demo-resultaat is regelgebaseerd: werkervaring en vaardigheden zijn herschikt op relevantie, de tekst is niet herschreven.
        </Alert>
      )}
      {v.target_job_id && v.status !== "generating" && (
        <p className="-mt-3 text-sm"><Link className="text-accent hover:underline" href={`/jobs/${v.target_job_id}`}>Bekijk de vacature</Link>
          {v.provider && <span className="text-muted"> · gemaakt met {v.provider === "demo" ? "demo-modus" : `${v.model} (${v.provider})`} op {formatDateTime(v.created_at)}</span>}</p>
      )}

      {v.status === "generating" && <Generating v={v} />}
      {v.status === "failed" && (
        <Alert tone="danger" title="Het afstemmen is niet gelukt" action={<Button size="sm" onClick={() => regenerate.mutate()} loading={regenerate.isPending}>Opnieuw proberen</Button>}>
          {v.error_message ?? "Onbekende fout."}
        </Alert>
      )}

      {v.status === "ready" && draft && report && (
        <>
          <Alert tone="accent" title="Controleer je cv voordat je het verstuurt">
            We hebben feiten automatisch vergeleken met je profiel, maar die controle is nooit perfect. Lees alles na en pas aan waar nodig.
          </Alert>
          <ScoreComparison v={v} />

          <Tabs defaultValue="edit">
            <TabsList>
              <TabsTrigger value="edit">Bewerken en downloaden</TabsTrigger>
              <TabsTrigger value="compare">Origineel vs. afgestemd</TabsTrigger>
              <TabsTrigger value="changes">Wijzigingen en controle {report.review_items.filter((r) => r.kind !== "gap").length > 0 && <Badge tone="warning" className="ml-1.5">{report.review_items.filter((r) => r.kind !== "gap").length}</Badge>}</TabsTrigger>
              <TabsTrigger value="match">Match-details</TabsTrigger>
            </TabsList>

            <TabsContent value="edit" className="mt-5">
              <div className="grid gap-6 xl:grid-cols-[1fr_400px]">
                <CvContentEditor value={draft} onChange={setDraft} />
                <div className="xl:sticky xl:top-6 xl:self-start">
                  <Card>
                    <CardHeader title="Voorbeeld" description={dirty ? "Sla op om je wijzigingen in het voorbeeld en de download te zien." : "Zo ziet je download eruit."} />
                    <CardBody>
                      <CvPreview basePath={`/cv-optimizations/${id}`} template={template} version={savedKey}
                        onTemplateChange={(tpl) => { setTemplate(tpl); save.mutate({ template: tpl }); }} />
                    </CardBody>
                  </Card>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <Button size="sm" variant="ghost" onClick={() => setConfirm("generated")}><RotateCcw />Terug naar gegenereerde versie</Button>
                    <Button size="sm" variant="ghost" onClick={() => setConfirm("original")}><RotateCcw />Originele inhoud herstellen</Button>
                  </div>
                </div>
              </div>
            </TabsContent>

            <TabsContent value="compare" className="mt-5">
              {v.original_content ? <SideBySide original={v.original_content} tailored={draft} /> : <p className="text-sm text-muted">Geen origineel bewaard.</p>}
            </TabsContent>

            <TabsContent value="changes" className="mt-5">
              <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader title="Wat er veranderde" />
                  <CardBody className="flex flex-col gap-4">
                    {report.changes.length === 0 ? <p className="text-sm text-muted">Geen inhoudelijke wijzigingen.</p> : (
                      <ul className="flex flex-col gap-2 text-sm text-text-2">{report.changes.map((c, i) => <li key={i} className="flex gap-2"><Check className="mt-0.5 size-4 shrink-0 text-success" />{c.description}</li>)}</ul>
                    )}
                    {report.emphasized_keywords.length > 0 && (
                      <div>
                        <p className="mb-1.5 text-sm font-medium text-text-2">Benadrukte trefwoorden</p>
                        <div className="flex flex-wrap gap-1.5">{report.emphasized_keywords.map((k) => <Badge key={k} tone="accent">{k}</Badge>)}</div>
                      </div>
                    )}
                    {report.gap.matching_skills.length > 0 && (
                      <div>
                        <p className="mb-1.5 text-sm font-medium text-text-2">Sterktes voor deze vacature</p>
                        <div className="flex flex-wrap gap-1.5">{report.gap.matching_skills.map((k) => <Badge key={k} tone="success">{k}</Badge>)}</div>
                      </div>
                    )}
                  </CardBody>
                </Card>
                <Card>
                  <CardHeader title="Vragen voor jou" description="Antwoorden die je cv sterker kunnen maken. Vul ze alleen in als ze kloppen." />
                  <CardBody>
                    {report.questions.length === 0 ? <p className="text-sm text-muted">Geen openstaande vragen.</p> : (
                      <ul className="flex flex-col gap-3 text-sm">
                        {report.questions.map((q, i) => (
                          <li key={i} className="flex gap-2"><CircleHelp className="mt-0.5 size-4 shrink-0 text-accent" /><div><p className="text-text">{q.question}</p>{q.reason && <p className="text-xs text-muted">{q.reason}</p>}</div></li>
                        ))}
                      </ul>
                    )}
                  </CardBody>
                </Card>
                <Card className="lg:col-span-2"><CardHeader title="Feitencontrole" /><CardBody><ReviewList items={report.review_items} onAccept={acceptReview} /></CardBody></Card>
              </div>
            </TabsContent>

            <TabsContent value="match" className="mt-5">
              <div className="grid gap-6 lg:grid-cols-2">
                {v.match_before && <Card><CardHeader title="Origineel cv" /><CardBody><MatchBreakdown result={v.match_before} compact /></CardBody></Card>}
                {v.match_after && <Card><CardHeader title="Afgestemd cv" /><CardBody><MatchBreakdown result={v.match_after} compact /></CardBody></Card>}
              </div>
            </TabsContent>
          </Tabs>
        </>
      )}

      <ConfirmDialog open={confirm === "generated" || confirm === "original"} onOpenChange={(o) => !o && setConfirm(null)}
        title={confirm === "original" ? "Originele inhoud herstellen?" : "Terug naar de gegenereerde versie?"}
        description="Je huidige bewerkingen in deze versie worden overschreven. Je originele cv blijft altijd bewaard."
        confirmLabel="Herstellen" loading={restore.isPending} onConfirm={() => confirm && confirm !== "regenerate" && restore.mutate(confirm)} />
      <ConfirmDialog open={confirm === "regenerate"} onOpenChange={(o) => !o && setConfirm(null)} tone="primary"
        title="Opnieuw genereren?" description="Er wordt een nieuwe versie gemaakt op basis van je huidige profiel. Deze versie blijft bewaard."
        confirmLabel="Nieuwe versie maken" loading={regenerate.isPending} onConfirm={() => regenerate.mutate()} />
    </div>
  );
}
