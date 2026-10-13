import { locale, t } from "@/lib/i18n";
import type { SalaryPeriod } from "@/types/api";

export function formatDate(value: string | null | undefined, opts: Intl.DateTimeFormatOptions = { day: "numeric", month: "short", year: "numeric" }) {
  if (!value) return "";
  return new Intl.DateTimeFormat(locale, opts).format(new Date(value));
}

export function formatDateTime(value: string | null | undefined) {
  return formatDate(value, { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

export function relativeTime(value: string | null | undefined): string {
  if (!value) return "";
  const diff = (new Date(value).getTime() - Date.now()) / 1000;
  const rtf = new Intl.RelativeTimeFormat(locale, { numeric: "auto" });
  const units: [Intl.RelativeTimeFormatUnit, number][] = [["year", 31536000], ["month", 2592000], ["week", 604800], ["day", 86400], ["hour", 3600], ["minute", 60]];
  for (const [unit, seconds] of units) {
    if (Math.abs(diff) >= seconds) return rtf.format(Math.round(diff / seconds), unit);
  }
  return rtf.format(Math.round(diff), "second");
}

export function formatMoney(amount: number, currency = "EUR") {
  return new Intl.NumberFormat(locale, { style: "currency", currency, maximumFractionDigits: 0 }).format(amount);
}

/** "€ 3.600 – € 4.800 per maand"; null when no salary is stated (shown as "not specified", never as 0). */
export function formatSalary(min: number | null, max: number | null, currency: string, period: SalaryPeriod | null): string | null {
  if (min == null && max == null) return null;
  const range = min != null && max != null && min !== max ? `${formatMoney(min, currency)} – ${formatMoney(max, currency)}` : formatMoney((min ?? max)!, currency);
  return period ? `${range} ${t(`enums.salaryPeriod.${period}`)}` : range;
}

export function yearMonth(value: string | null | undefined): string {
  if (!value) return "";
  const [year, month] = value.split("-");
  if (!month) return year;
  return new Intl.DateTimeFormat(locale, { month: "short", year: "numeric" }).format(new Date(Number(year), Number(month) - 1, 1));
}

export function period(start?: string | null, end?: string | null, current?: boolean): string {
  const from = yearMonth(start);
  const to = current ? "heden" : yearMonth(end);
  return [from, to].filter(Boolean).join(" – ");
}

export function fileSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} kB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}

export function languageName(code: string): string {
  const label = t(`enums.languages.${code}`);
  return label.startsWith("enums.") ? code.toUpperCase() : label;
}
