import { describe, expect, it } from "vitest";

import { cleanProfile, emptyProfile, profileProblems } from "@/features/profile/profile-editor";

describe("profile validation", () => {
  it("reports missing required fields and bad dates", () => {
    const problems = profileProblems({ ...emptyProfile, experiences: [{ title: "", employer: "Acme", start: "03/2021", end: null, is_current: true, bullets: [] }] });
    expect(problems).toHaveLength(2);
  });

  it("removes empty bullets and clears the end date of current jobs", () => {
    const cleaned = cleanProfile({ ...emptyProfile, experiences: [{ title: "Dev", employer: "Acme", start: "2021-03", end: "2022-01", is_current: true, bullets: ["Bouwde API's", "  "] }] });
    expect(cleaned.experiences[0].bullets).toEqual(["Bouwde API's"]);
    expect(cleaned.experiences[0].end).toBeNull();
  });
});
