import { type Download, expect, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";

const SAMPLE_CV = path.join(__dirname, "fixtures", "sample-cv-noor-vermeulen.pdf");

test("candidate: register → upload CV → confirm → matches → optimize → edit → export → persisted", async ({ page }) => {
  const email = `e2e-${Date.now()}@example.com`;

  // 1. Register
  await page.goto("/register");
  await page.getByLabel("Volledige naam").fill("Noor Vermeulen");
  await page.getByLabel("E-mailadres").fill(email);
  await page.getByLabel("Wachtwoord").fill("e2e-password-123");
  await page.getByText("Ik aanvaard de").click();
  await page.getByRole("button", { name: "Account aanmaken" }).click();
  await expect(page).toHaveURL(/\/onboarding/);

  // 2. Upload the CV and review the extraction
  await page.getByRole("button", { name: /Ik heb een cv/ }).click();
  await page.getByLabel("Cv-bestand kiezen").setInputFiles(SAMPLE_CV);
  await expect(page.getByRole("heading", { name: "Werkervaring" })).toBeVisible({ timeout: 4 * 60_000 });
  await expect(page.getByRole("textbox", { name: "Naam", exact: true })).toHaveValue(/Noor/);
  await page.getByRole("button", { name: "Bevestigen en profiel opslaan" }).click();

  // 3. Skip preferences, finish onboarding
  await page.getByRole("button", { name: "Overslaan" }).click();
  await page.getByRole("button", { name: "Naar mijn dashboard" }).click();
  await expect(page).toHaveURL(/\/dashboard/);

  // 4. Personalized matches from real records
  await expect(page.getByRole("heading", { name: "Aanbevolen voor jou" })).toBeVisible();
  const firstJob = page.locator("article").first();
  await expect(firstJob).toBeVisible({ timeout: 30_000 });
  await firstJob.getByRole("link", { name: "Bekijken" }).click();

  // 5. Vacancy with explained match
  await expect(page).toHaveURL(/\/jobs\/[0-9a-f-]+/);
  await expect(page.getByText(/% match|Onvoldoende gegevens/)).toBeVisible();
  await expect(page.getByText("Score per onderdeel").or(page.getByRole("list", { name: "Score per onderdeel" }))).toBeVisible();

  // 6. Optimize the CV for this vacancy
  await page.getByRole("button", { name: "Optimaliseer mijn cv voor deze vacature" }).click();
  await page.getByRole("button", { name: "Start optimalisatie" }).click();
  await expect(page).toHaveURL(/\/cv\/optimizations\//);
  await expect(page.getByText("Controleer je cv voordat je het verstuurt")).toBeVisible({ timeout: 5 * 60_000 });
  await expect(page.getByText("Matchscore, met dezelfde berekening vóór en na")).toBeVisible();

  // 7. Edit and save
  const summary = page.getByRole("textbox", { name: "Samenvatting" });
  await summary.fill("Backend developer met drie jaar ervaring in Python en PostgreSQL. (e2e)");
  await page.getByRole("button", { name: "Wijzigingen opslaan" }).click();
  await expect(page.getByRole("button", { name: "Opgeslagen" })).toBeVisible();

  // 8. Export: a real PDF and a real DOCX. (Headless Chromium has no PDF viewer, so the preview iframe also
  //    shows up as a download; wait for the CV download specifically.)
  const isCv = (d: Download) => d.suggestedFilename().startsWith("CV_");
  const [pdf] = await Promise.all([page.waitForEvent("download", { predicate: isCv }), page.getByRole("button", { name: "PDF", exact: true }).click()]);
  const pdfPath = await pdf.path();
  expect(fs.readFileSync(pdfPath!).subarray(0, 5).toString()).toBe("%PDF-");
  expect(pdf.suggestedFilename()).toMatch(/^CV_Noor_Vermeulen.*\.pdf$/);
  const [docx] = await Promise.all([page.waitForEvent("download", { predicate: isCv }), page.getByRole("button", { name: "Word", exact: true }).click()]);
  expect(fs.readFileSync((await docx.path())!).subarray(0, 2).toString()).toBe("PK");

  // 9. Persisted across reloads, listed in the CV library
  await page.reload();
  await expect(page.getByRole("textbox", { name: "Samenvatting" })).toHaveValue(/\(e2e\)/);
  await page.goto("/cv");
  await expect(page.getByRole("heading", { name: "Per vacature afgestemd" })).toBeVisible();
  await expect(page.getByRole("link", { name: "Openen" }).first()).toBeVisible();

  // 10. Clean up through the privacy flow: delete the account and all its data
  await page.goto("/privacy/data");
  await page.getByRole("button", { name: "Account verwijderen" }).click();
  await page.getByRole("dialog").getByLabel("Wachtwoord").fill("e2e-password-123");
  await page.getByText("Ik begrijp dat al mijn gegevens definitief verwijderd worden.").click();
  await page.getByRole("button", { name: "Definitief verwijderen" }).click();
  await expect(page).toHaveURL("/");
  await page.goto("/login");
  await page.getByLabel("E-mailadres").fill(email);
  await page.getByLabel("Wachtwoord").fill("e2e-password-123");
  await page.getByRole("button", { name: "Inloggen" }).click();
  await expect(page.getByText("E-mailadres of wachtwoord is onjuist.")).toBeVisible();
});

test("failure states: wrong password and protected pages", async ({ page }) => {
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/\/login\?next=%2Fdashboard/);
  await page.getByLabel("E-mailadres").fill("nobody@example.com");
  await page.getByLabel("Wachtwoord").fill("wrong-password-1");
  await page.getByRole("button", { name: "Inloggen" }).click();
  await expect(page.getByText("E-mailadres of wachtwoord is onjuist.")).toBeVisible();
});
