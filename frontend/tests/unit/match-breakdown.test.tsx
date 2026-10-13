import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MatchBreakdown } from "@/features/jobs/match-breakdown";
import { MatchScore } from "@/features/jobs/match-score";
import type { MatchResult } from "@/types/api";

const base: MatchResult = {
  score: 58, status: "ok", capped: true, semantic_method: "lexical", algorithm_version: "1.3.0",
  components: [
    { key: "skills", weight: 0.35, effective_weight: 0.5, applicable: true, score: 50, details: { matched: 1, total: 2, required_matched: 1, required_total: 2 } },
    { key: "qualifications", weight: 0.1, effective_weight: 0, applicable: false, score: null, details: { reason: "no_candidate_education" } },
  ],
  eligibility: { status: "not_met", issues: [{ code: "language", value: "fr" }], unknown: [] },
  matching_skills: [{ name: "Python", evidence: "listed", required: "yes" }],
  missing_required_skills: [{ name: "Java" }], missing_preferred_skills: [], relevant_experience: [], preference_checks: [],
  strongest_factors: [], needs_review: ["qualifications"],
};

describe("match explanation", () => {
  it("shows hard requirements, the cap and non-applicable components", () => {
    render(<MatchBreakdown result={base} />);
    expect(screen.getByText("Vereiste taal: Frans")).toBeInTheDocument();
    expect(screen.getByText(/begrensd tot 60%/)).toBeInTheDocument();
    expect(screen.getByText("Niet beoordeeld")).toBeInTheDocument();
    expect(screen.getByText("Je profiel vermeldt geen opleidingsniveau.")).toBeInTheDocument();
    expect(screen.getByText("Java")).toBeInTheDocument();
  });

  it("never shows a missing score as 0%", () => {
    render(<MatchScore score={null} />);
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
    expect(screen.getByText("?")).toBeInTheDocument();
  });
});
