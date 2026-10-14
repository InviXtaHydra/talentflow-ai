"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Eraser, Send, User as UserIcon, X } from "lucide-react";
import { useSearchParams } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { PageHeader, QueryError } from "@/components/page-header";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Alert, Badge, Skeleton, Spinner } from "@/components/ui/feedback";
import { Select, Textarea } from "@/components/ui/input";
import { usePublicConfig } from "@/hooks/use-auth";
import { api, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { AssistantMessage, JobDetail, JobSummary } from "@/types/api";

const STARTERS = [
  "Waarom past deze vacature bij mij?",
  "Welke vaardigheden mis ik nog en hoe leer ik ze?",
  "Schrijf een eerste versie van een motivatiebrief.",
  "Welke vragen kan ik op het sollicitatiegesprek verwachten?",
];

export function AssistantPage() {
  const params = useSearchParams();
  const qc = useQueryClient();
  const config = usePublicConfig();
  const [jobIds, setJobIds] = React.useState<string[]>(params.get("job") ? [params.get("job")!] : []);
  const [text, setText] = React.useState("");
  const bottom = React.useRef<HTMLDivElement>(null);
  const history = useQuery({ queryKey: ["assistant"], queryFn: () => api.get<AssistantMessage[]>("/assistant/messages") });
  const saved = useQuery({ queryKey: ["saved"], queryFn: () => api.get<JobSummary[]>("/jobs/saved") });
  const selectedJobs = useQuery({
    queryKey: ["assistant-jobs", jobIds],
    queryFn: () => Promise.all(jobIds.map((id) => api.get<JobDetail>(`/jobs/${id}`))),
    enabled: jobIds.length > 0,
  });
  const [pending, setPending] = React.useState<string | null>(null);
  const ask = useMutation({
    mutationFn: (message: string) => api.post<AssistantMessage>("/assistant/messages", { message, job_ids: jobIds }),
    onMutate: (message) => setPending(message),
    onSettled: () => setPending(null),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["assistant"] }),
  });
  const clear = useMutation({ mutationFn: () => api.delete("/assistant/messages"), onSuccess: () => qc.invalidateQueries({ queryKey: ["assistant"] }), onError: (e) => toast.error(errorMessage(e)) });
  // Block body on purpose: newer browsers return a Promise from scrollIntoView, which React would treat as a cleanup function.
  React.useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth" });
  }, [history.data, pending]);

  const send = (message: string) => { if (message.trim() && !ask.isPending) { ask.mutate(message.trim()); setText(""); } };
  const messages = history.data ?? [];

  return (
    <>
      <PageHeader title="Carrière-assistent" description="Vragen over vacatures, je profiel, sollicitatiegesprekken of motivatiebrieven. De assistent kent alleen jouw profiel en de vacatures die je kiest."
        actions={messages.length > 0 && <Button variant="ghost" loading={clear.isPending} onClick={() => clear.mutate()}><Eraser />Gesprek wissen</Button>} />
      {config.data && !config.data.ai_configured && <Alert tone="warning" title="Geen AI-model ingesteld" className="mb-4">De assistent is niet beschikbaar zolang er geen AI-model is ingesteld. Alle andere functies werken gewoon.</Alert>}

      <Card className="flex h-[calc(100dvh-16rem)] min-h-[28rem] flex-col">
        <div className="flex flex-wrap items-center gap-2 border-b border-border px-4 py-3 text-sm">
          <span className="text-muted">Context:</span>
          {(selectedJobs.data ?? []).map((j) => (
            <Badge key={j.id} tone="accent">{j.title}<button aria-label={`${j.title} verwijderen uit context`} onClick={() => setJobIds(jobIds.filter((id) => id !== j.id))}><X className="size-3" /></button></Badge>
          ))}
          {jobIds.length < 3 && (saved.data?.length ?? 0) > 0 && (
            <Select className="h-8 w-auto text-xs" value="" aria-label="Vacature toevoegen" onChange={(e) => e.target.value && setJobIds([...jobIds, e.target.value])}>
              <option value="">+ Bewaarde vacature toevoegen</option>
              {saved.data!.filter((j) => !jobIds.includes(j.id)).map((j) => <option key={j.id} value={j.id}>{j.title} · {j.company.name}</option>)}
            </Select>
          )}
          {jobIds.length === 0 && <span className="text-muted">alleen je profiel</span>}
        </div>

        <div className="flex-1 overflow-y-auto px-4 py-5" aria-live="polite">
          {history.error ? <QueryError error={history.error} /> : !history.data ? <Skeleton className="h-32" /> : messages.length === 0 && !pending ? (
            <div className="mx-auto flex max-w-lg flex-col items-center gap-4 py-8 text-center">
              <div className="rounded-full bg-accent-soft p-3"><Bot className="size-6 text-accent" /></div>
              <p className="text-sm text-muted">Probeer bijvoorbeeld:</p>
              <div className="flex flex-wrap justify-center gap-2">
                {STARTERS.map((s) => <button key={s} onClick={() => send(s)} className="rounded-full border border-border px-3 py-1.5 text-sm text-text-2 hover:bg-surface-2">{s}</button>)}
              </div>
            </div>
          ) : (
            <ul className="mx-auto flex max-w-3xl flex-col gap-4">
              {messages.map((m) => <Message key={m.id} role={m.role} content={m.content} />)}
              {pending && <Message role="user" content={pending} />}
              {pending && <li className="flex gap-3"><Avatar role="assistant" /><Spinner label="Aan het nadenken…" /></li>}
            </ul>
          )}
          {ask.error && <Alert tone="danger" className="mx-auto mt-4 max-w-3xl">{errorMessage(ask.error)}</Alert>}
          <div ref={bottom} />
        </div>

        <form className="flex items-end gap-2 border-t border-border p-3" onSubmit={(e) => { e.preventDefault(); send(text); }}>
          <Textarea value={text} onChange={(e) => setText(e.target.value)} rows={2} maxLength={4000} placeholder="Stel je vraag…" aria-label="Je vraag" className="min-h-0 resize-none"
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text); } }} />
          <Button type="submit" size="icon" className="size-10" loading={ask.isPending} disabled={!text.trim()} aria-label="Versturen"><Send /></Button>
        </form>
      </Card>
      <p className="mt-2 text-xs text-muted">De assistent kan fouten maken en dient niets namens jou in. Matchscores komen van de matching-engine.</p>
    </>
  );
}

function Avatar({ role }: { role: string }) {
  return <div className={cn("flex size-8 shrink-0 items-center justify-center rounded-full", role === "user" ? "bg-surface-2" : "bg-accent-soft")}>
    {role === "user" ? <UserIcon className="size-4 text-text-2" /> : <Bot className="size-4 text-accent" />}
  </div>;
}

function Message({ role, content }: { role: string; content: string }) {
  return (
    <li className={cn("flex gap-3", role === "user" && "flex-row-reverse")}>
      <Avatar role={role} />
      <div className={cn("max-w-[85%] whitespace-pre-wrap rounded-xl px-4 py-2.5 text-sm leading-relaxed", role === "user" ? "bg-accent text-accent-fg" : "bg-surface-2 text-text")}>{content}</div>
    </li>
  );
}
