import { describe, expect, it } from "vitest";

import { formatSalary, period, yearMonth } from "@/lib/format";
import { t } from "@/lib/i18n";

describe("formatting", () => {
  it("shows a missing salary as null, never as zero", () => {
    expect(formatSalary(null, null, "EUR", "month")).toBeNull();
    expect(formatSalary(3600, 4800, "EUR", "month")).toMatch(/3\.600.*4\.800.*per maand/);
    expect(formatSalary(55000, null, "EUR", "year")).toMatch(/55\.000.*per jaar/);
  });

  it("formats CV periods", () => {
    expect(yearMonth("2021")).toBe("2021");
    expect(period("2021-03", null, true)).toMatch(/2021 – heden$/);
  });

  it("translates keys with parameters and falls back to the key", () => {
    expect(t("enums.remote.hybrid")).toBe("Hybride");
    expect(t("match.weight", { weight: 35 })).toBe("weegt 35%");
    expect(t("does.not.exist")).toBe("does.not.exist");
  });
});

describe("months", () => {
  it("formats experience in years and months", async () => {
    const { formatMonths } = await import("@/lib/format");
    expect(formatMonths(14)).toBe("1 jaar en 2 maanden");
    expect(formatMonths(6)).toBe("6 maanden");
    expect(formatMonths(1)).toBe("1 maand");
    expect(formatMonths(24)).toBe("2 jaar");
  });
});
