"use client";

import { useQuery } from "@tanstack/react-query";
import { Download, FileText, RefreshCw } from "lucide-react";
import * as React from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Alert, Spinner } from "@/components/ui/feedback";
import { Select } from "@/components/ui/input";
import { api, downloadFile, errorMessage } from "@/lib/api";
import { t } from "@/lib/i18n";
import type { CvTemplate } from "@/types/api";

function useObjectUrl(blob: Blob | undefined) {
  const url = React.useMemo(() => (blob ? URL.createObjectURL(blob) : null), [blob]);
  React.useEffect(() => () => { if (url) URL.revokeObjectURL(url); }, [url]);
  return url;
}

/** Live PDF preview rendered by the backend (the same renderer as the download), plus PDF/DOCX download. */
export function CvPreview({ basePath, template, onTemplateChange, version }: {
  basePath: string; template: CvTemplate; onTemplateChange?: (t: CvTemplate) => void; version: string;
}) {
  const preview = useQuery({
    queryKey: ["cv-preview", basePath, template, version],
    queryFn: () => api.blob(`${basePath}/export`, { format: "pdf", template, preview: true }),
    staleTime: Infinity,
  });
  const url = useObjectUrl(preview.data);
  const [downloading, setDownloading] = React.useState<string | null>(null);

  async function download(format: "pdf" | "docx") {
    setDownloading(format);
    try {
      await downloadFile(`${basePath}/export`, { format, template }, `cv.${format}`);
      toast.success(format === "pdf" ? "PDF gedownload" : "Word-bestand gedownload");
    } catch (e) {
      toast.error(errorMessage(e));
    } finally {
      setDownloading(null);
    }
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        {onTemplateChange && (
          <Select value={template} onChange={(e) => onTemplateChange(e.target.value as CvTemplate)} aria-label="Sjabloon" className="h-9 w-auto flex-1">
            {(["modern", "minimal", "technical"] as CvTemplate[]).map((x) => <option key={x} value={x}>{t(`enums.template.${x}`)}</option>)}
          </Select>
        )}
        <Button size="sm" variant="ghost" onClick={() => preview.refetch()} aria-label="Voorbeeld vernieuwen"><RefreshCw /></Button>
      </div>
      <div className="relative aspect-[1/1.414] w-full overflow-hidden rounded-lg border border-border bg-white">
        {url && <iframe src={`${url}#toolbar=0&navpanes=0&view=FitH`} title="Voorbeeld van het cv" className="size-full" />}
        {preview.isFetching && <div className="absolute inset-0 flex items-center justify-center bg-surface/70"><Spinner label="Voorbeeld maken…" /></div>}
        {!url && !preview.isFetching && !preview.error && <div className="flex size-full items-center justify-center"><FileText className="size-8 text-muted" /></div>}
      </div>
      {preview.error && <Alert tone="danger">{errorMessage(preview.error)}</Alert>}
      <div className="grid grid-cols-2 gap-2">
        <Button loading={downloading === "pdf"} onClick={() => download("pdf")}><Download />PDF</Button>
        <Button variant="secondary" loading={downloading === "docx"} onClick={() => download("docx")}><Download />Word</Button>
      </div>
    </div>
  );
}
