"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { FileUp, Loader2 } from "lucide-react";
import * as React from "react";

import { Alert, Progress } from "@/components/ui/feedback";
import { usePublicConfig } from "@/hooks/use-auth";
import { useTask } from "@/hooks/use-task";
import { api, errorMessage } from "@/lib/api";
import { cn } from "@/lib/utils";
import type { CvDocumentDetail } from "@/types/api";

/** Upload + wait for extraction. Calls onDone with the processed document (completed, needs_ocr or failed). */
export function CvUpload({ onDone }: { onDone: (doc: CvDocumentDetail) => void }) {
  const qc = useQueryClient();
  const config = usePublicConfig();
  const maxMb = config.data?.max_upload_mb ?? 5;
  const [error, setError] = React.useState<string | null>(null);
  const [uploading, setUploading] = React.useState(false);
  const [dragging, setDragging] = React.useState(false);
  const [job, setJob] = React.useState<{ cvId: string; taskId: string | null } | null>(null);
  const input = React.useRef<HTMLInputElement>(null);

  const task = useTask(job?.taskId);
  const finished = !!job && (!job.taskId || ["succeeded", "failed", "cancelled"].includes(task.data?.status ?? ""));
  const doc = useQuery({
    queryKey: ["cv", job?.cvId],
    queryFn: () => api.get<CvDocumentDetail>(`/cvs/${job!.cvId}`),
    enabled: finished,
  });
  const reported = React.useRef<string | null>(null);
  React.useEffect(() => {
    if (doc.data && reported.current !== doc.data.id && !["pending", "processing"].includes(doc.data.extraction_status)) {
      reported.current = doc.data.id;
      qc.invalidateQueries({ queryKey: ["cvs"] });
      onDone(doc.data);
    }
  }, [doc.data, onDone, qc]);

  async function upload(file: File) {
    setError(null);
    const ext = file.name.toLowerCase().split(".").pop();
    if (ext !== "pdf" && ext !== "docx") return setError("Kies een PDF- of Word-bestand (.docx).");
    if (file.size > maxMb * 1024 * 1024) return setError(`Het bestand is groter dan ${maxMb} MB.`);
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const result = await api.post<{ document: { id: string }; task_id: string | null }>("/cvs/upload", form);
      setJob({ cvId: result.document.id, taskId: result.task_id });
    } catch (e) {
      setError(errorMessage(e));
    } finally {
      setUploading(false);
    }
  }

  const busy = uploading || (!!job && !doc.data);
  const progress = uploading ? 5 : task.data?.progress ?? 10;

  return (
    <div className="flex flex-col gap-3">
      {error && <Alert tone="danger">{error}</Alert>}
      {task.data?.status === "failed" && <Alert tone="danger">{task.data.error_message}</Alert>}
      <div
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); const f = e.dataTransfer.files[0]; if (f && !busy) upload(f); }}
        className={cn("flex flex-col items-center justify-center rounded-xl border-2 border-dashed px-6 py-10 text-center transition-colors",
          dragging ? "border-accent bg-accent-soft" : "border-border-strong bg-surface")}>
        {busy ? (
          <div className="flex w-full max-w-sm flex-col items-center gap-3" aria-live="polite">
            <Loader2 className="size-6 animate-spin text-accent" />
            <p className="text-sm font-medium text-text">{uploading ? "Bestand uploaden…" : task.data?.progress_message ?? "In de wachtrij…"}</p>
            <Progress value={progress} label="Voortgang" />
            <p className="text-xs text-muted">Met een lokaal AI-model kan dit tot een minuut duren.</p>
          </div>
        ) : (
          <>
            <div className="mb-3 rounded-full bg-accent-soft p-3"><FileUp className="size-6 text-accent" /></div>
            <p className="font-medium text-text">Sleep je cv hierheen</p>
            <p className="mt-1 text-sm text-muted">PDF of Word (.docx), max. {maxMb} MB</p>
            <button type="button" onClick={() => input.current?.click()} className="mt-4 h-10 rounded-lg bg-accent px-4 text-sm font-medium text-accent-fg hover:bg-accent-hover">
              Bestand kiezen
            </button>
            <input ref={input} type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" className="sr-only"
              aria-label="Cv-bestand kiezen" onChange={(e) => { const f = e.target.files?.[0]; if (f) upload(f); e.target.value = ""; }} />
          </>
        )}
      </div>
      <p className="text-xs text-muted">Je bestand wordt privé bewaard. We gebruiken het alleen om je profiel in te vullen; jij controleert alles voordat het opgeslagen wordt.</p>
    </div>
  );
}
