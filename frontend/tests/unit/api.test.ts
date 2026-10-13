import { afterEach, describe, expect, it, vi } from "vitest";

import { api, ApiError, query } from "@/lib/api";

describe("api client", () => {
  afterEach(() => { vi.restoreAllMocks(); document.cookie = "tf_csrf=; expires=Thu, 01 Jan 1970 00:00:00 GMT"; });

  it("sends the CSRF cookie value as header on state-changing requests", async () => {
    document.cookie = "tf_csrf=abc123";
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200, headers: { "content-type": "application/json" } }));
    await api.post("/auth/logout");
    const [, init] = fetchMock.mock.calls[0];
    expect((init?.headers as Record<string, string>)["X-CSRF-Token"]).toBe("abc123");
    expect(init?.credentials).toBe("same-origin");
  });

  it("turns error responses into ApiError with the server's message", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify({ error: { code: "email_taken", message: "Bestaat al." } }), { status: 409, headers: { "content-type": "application/json" } }),
    );
    await expect(api.get("/x")).rejects.toMatchObject({ status: 409, code: "email_taken", message: "Bestaat al." });
  });

  it("reports network failures clearly", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("fetch failed"));
    const error = (await api.get("/x").catch((e: unknown) => e)) as ApiError;
    expect(error).toBeInstanceOf(ApiError);
    expect(error.code).toBe("network_error");
  });

  it("builds query strings with repeated keys and skips empty values", () => {
    expect(query({ q: "python", remote: ["hybrid", "remote"], city: "", page: 2 })).toBe("?q=python&remote=hybrid&remote=remote&page=2");
  });
});
