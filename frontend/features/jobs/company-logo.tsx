import { cn } from "@/lib/utils";
import type { CompanyBrief } from "@/types/api";

export function CompanyLogo({ company, size = 40, className }: { company: Pick<CompanyBrief, "name" | "logo_url">; size?: number; className?: string }) {
  if (company.logo_url) {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={company.logo_url} alt="" width={size} height={size} className={cn("shrink-0 rounded-lg border border-border bg-surface object-contain", className)} style={{ width: size, height: size }} />;
  }
  const initials = company.name.split(/\s+/).slice(0, 2).map((w) => w[0]).join("").toUpperCase();
  return (
    <div aria-hidden className={cn("flex shrink-0 items-center justify-center rounded-lg border border-border bg-surface-2 text-xs font-semibold text-text-2", className)} style={{ width: size, height: size }}>
      {initials}
    </div>
  );
}
