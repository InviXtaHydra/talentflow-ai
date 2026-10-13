"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Check, FileUp, PenLine } from "lucide-react";
import { useRouter } from "next/navigation";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { Alert, Skeleton } from "@/components/ui/feedback";
import { Field, Input, Textarea } from "@/components/ui/input";
import { ExtractionReview } from "@/features/cv/extraction-review";
import { CvUpload } from "@/features/cv/upload";
import { api, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CandidateProfile, CvDocumentDetail, ProfileContent } from "@/types/api";

import { PreferencesForm } from "./preferences-form";
import { cleanProfile, ProfileContentEditor, profileProblems } from "./profile-editor";
import { useDraft } from "@/hooks/use-draft";

type Step = "start" | "upload" | "review" | "manual" | "preferences" | "done";
const STEPS: { key: Step[]; label: string }[] = [
  { key: ["start", "upload"], label: "Cv" },
  { key: ["review", "manual"], label: "Profiel" },
  { key: ["preferences"], label: "Voorkeuren" },
  { key: ["done"], label: "Klaar" },
];

function Stepper({ step }: { step: Step }) {
  const current = STEPS.findIndex((s) => s.key.includes(step));
  return (
    <ol className="mb-8 flex items-center gap-2" aria-label="Stappen">
      {STEPS.map((s, i) => (
        <li key={s.label} className="flex flex-1 items-center gap-2">
          <span className={cn("flex size-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
            i < current ? "bg-accent text-accent-fg" : i === current ? "border-2 border-accent text-accent" : "border border-border text-muted")}
            aria-current={i === current ? "step" : undefined}>
            {i < current ? <Check className="size-3.5" /> : i + 1}
          </span>
          <span className={cn("hidden text-sm sm:inline", i === current ? "font-medium text-text" : "text-muted")}>{s.label}</span>
          {i < STEPS.length - 1 && <span className="h-px flex-1 bg-border" />}
        </li>
      ))}
    </ol>
  );
}

function ManualProfile({ onSaved }: { onSaved: () => void }) {
  const qc = useQueryClient();
  const profile = useQuery({ queryKey: ["profile"], queryFn: () => api.get<CandidateProfile>("/candidates/me") });
  const [state, setState] = useDraft<CandidateProfile, { headline: string; summary: string; city: string; content: ProfileContent }>(
    profile.data, profile.data?.id, (p) => ({ headline: p.headline ?? "", summary: p.summary ?? "", city: p.city ?? "", content: p.content }));
  const [problems, setProblems] = React.useState<string[]>([]);
  const save = useMutation({
    mutationFn: () => api.patch("/candidates/me", { headline: state!.headline || null, summary: state!.summary || null, city: state!.city || null, content: cleanProfile(state!.content) }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["profile"] }); onSaved(); },
    onError: (e) => toast.error(errorMessage(e)),
  });
  if (!state) return <Skeleton className="h-96" />;
  return (
    <div className="flex flex-col gap-5">
      <Card><CardBody className="grid gap-4 sm:grid-cols-2">
        <Field label="Titel / headline"><Input value={state.headline} placeholder="bv. Boekhouder met 5 jaar ervaring" onChange={(e) => setState({ ...state, headline: e.target.value })} /></Field>
        <Field label="Woonplaats"><Input value={state.city} onChange={(e) => setState({ ...state, city: e.target.value })} /></Field>
        <Field label="Korte samenvatting" className="sm:col-span-2"><Textarea rows={3} value={state.summary} onChange={(e) => setState({ ...state, summary: e.target.value })} /></Field>
      </CardBody></Card>
      <ProfileContentEditor value={state.content} onChange={(content) => setState({ ...state, content })} />
      {problems.length > 0 && <Alert tone="danger"><ul className="list-disc pl-4">{problems.map((p) => <li key={p}>{p}</li>)}</ul></Alert>}
      <div className="flex justify-end">
        <Button size="lg" loading={save.isPending} onClick={() => { const p = profileProblems(state.content); setProblems(p); if (!p.length) save.mutate(); }}>Profiel opslaan</Button>
      </div>
    </div>
  );
}

export function Onboarding() {
  const router = useRouter();
  const qc = useQueryClient();
  const [step, setStep] = React.useState<Step>("start");
  const [doc, setDoc] = React.useState<CvDocumentDetail | null>(null);

  const finish = useMutation({
    mutationFn: async (target: string) => {
      void target;
      await api.patch("/candidates/me", { complete_onboarding: true });
      // Initial analysis of the confirmed profile; it runs in the background.
      await api.post("/cv-analyses").catch(() => undefined);
    },
    onSuccess: (_data, target) => {
      qc.invalidateQueries();
      router.push(target);
    },
    onError: (e) => toast.error(errorMessage(e)),
  });

  const handleDoc = React.useCallback((d: CvDocumentDetail) => { setDoc(d); setStep("review"); }, []);

  return (
    <div className="mx-auto max-w-3xl">
      <h1 className="text-2xl font-semibold tracking-tight text-text">Welkom! Laten we je profiel opbouwen</h1>
      <p className="mb-6 mt-1 text-muted">Hoe vollediger je profiel, hoe beter de matches. Je kunt elke stap overslaan en later aanvullen.</p>
      <Stepper step={step} />

      {step === "start" && (
        <div className="grid gap-4 sm:grid-cols-2">
          <button onClick={() => setStep("upload")} className="rounded-xl border border-border bg-surface p-6 text-left shadow-card transition hover:border-accent">
            <FileUp className="mb-3 size-6 text-accent" />
            <p className="font-semibold text-text">Ik heb een cv</p>
            <p className="mt-1 text-sm text-muted">Upload je cv (PDF of Word). We vullen je profiel in en jij controleert alles.</p>
          </button>
          <button onClick={() => setStep("manual")} className="rounded-xl border border-border bg-surface p-6 text-left shadow-card transition hover:border-accent">
            <PenLine className="mb-3 size-6 text-accent" />
            <p className="font-semibold text-text">Zelf invullen</p>
            <p className="mt-1 text-sm text-muted">Nog geen cv? Vul je ervaring en vaardigheden zelf in. Daarna kun je er een cv van maken.</p>
          </button>
          <div className="sm:col-span-2">
            <Button variant="ghost" onClick={() => setStep("preferences")}>Overslaan, ik vul mijn profiel later in</Button>
          </div>
        </div>
      )}

      {step === "upload" && (
        <div className="flex flex-col gap-4">
          <CvUpload onDone={handleDoc} />
          <Button variant="ghost" className="self-start" onClick={() => setStep("start")}>Terug</Button>
        </div>
      )}

      {step === "review" && doc && (
        doc.extraction_status === "completed" ? (
          <ExtractionReview doc={doc} onConfirmed={() => setStep("preferences")} />
        ) : (
          <div className="flex flex-col gap-4">
            <Alert tone={doc.extraction_status === "needs_ocr" ? "warning" : "danger"} title="We konden dit cv niet automatisch lezen">{doc.extraction_error}</Alert>
            <div className="flex gap-2">
              <Button onClick={() => setStep("upload")}>Ander bestand proberen</Button>
              <Button variant="secondary" onClick={() => setStep("manual")}>Profiel zelf invullen</Button>
            </div>
          </div>
        )
      )}

      {step === "manual" && <ManualProfile onSaved={() => setStep("preferences")} />}

      {step === "preferences" && (
        <Card><CardBody>
          <PreferencesForm submitLabel="Opslaan en verder" onSaved={() => setStep("done")} />
          <Button variant="ghost" className="mt-2" onClick={() => setStep("done")}>Overslaan</Button>
        </CardBody></Card>
      )}

      {step === "done" && (
        <Card><CardBody className="flex flex-col items-start gap-4 py-8">
          <div className="rounded-full bg-success-soft p-3"><Check className="size-6 text-success" /></div>
          <div>
            <p className="text-lg font-semibold text-text">Je bent klaar</p>
            <p className="mt-1 text-muted">We berekenen nu je matches en analyseren je profiel. Je vindt alles op je dashboard.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button size="lg" loading={finish.isPending && finish.variables === "/dashboard"} onClick={() => finish.mutate("/dashboard")}>Naar mijn dashboard</Button>
            <Button size="lg" variant="secondary" loading={finish.isPending && finish.variables === "/profile"} onClick={() => finish.mutate("/profile")}>Profiel verder aanvullen</Button>
          </div>
        </CardBody></Card>
      )}
    </div>
  );
}
