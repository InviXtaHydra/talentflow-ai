/**
 * Fetch wrapper for the TalentFlow API (same origin, proxied by Next.js to FastAPI).
 * Sends the session cookie automatically and echoes the CSRF cookie in the X-CSRF-Token header.
 */

export class ApiError extends Error {
  status: number;
  code: string;
  details: unknown;

  constructor(status: number, code: string, message: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

function readCookie(name: string): string | null {
  if (typeof document === "undefined") return null;
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=")[1]) : null;
}

let csrfPromise: Promise<void> | null = null;

async function ensureCsrf(): Promise<string> {
  let token = readCookie("tf_csrf");
  if (!token) {
    csrfPromise ??= fetch("/api/v1/auth/csrf", { credentials: "same-origin" }).then(() => undefined);
    await csrfPromise;
    csrfPromise = null;
    token = readCookie("tf_csrf");
  }
  return token ?? "";
}

type Method = "GET" | "POST" | "PUT" | "PATCH" | "DELETE";

async function request<T>(method: Method, path: string, body?: unknown, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json" };
  if (method !== "GET") headers["X-CSRF-Token"] = await ensureCsrf();
  let payload: BodyInit | undefined;
  if (body instanceof FormData) payload = body;
  else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }
  let response: Response;
  try {
    response = await fetch(`/api/v1${path}`, { method, headers, body: payload, credentials: "same-origin", ...init });
  } catch {
    throw new ApiError(0, "network_error", "Geen verbinding met de server. Controleer je internetverbinding.");
  }
  if (!response.ok) {
    let code = "http_error";
    let message = "Er ging iets mis. Probeer het opnieuw.";
    let details: unknown;
    try {
      const data = await response.json();
      code = data?.error?.code ?? code;
      message = data?.error?.message ?? message;
      details = data?.error?.details;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(response.status, code, message, details);
  }
  if (response.status === 204) return undefined as T;
  const type = response.headers.get("content-type") ?? "";
  return (type.includes("application/json") ? response.json() : response.blob()) as Promise<T>;
}

export const api = {
  get: <T>(path: string) => request<T>("GET", path),
  post: <T>(path: string, body?: unknown) => request<T>("POST", path, body),
  put: <T>(path: string, body?: unknown) => request<T>("PUT", path, body),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  delete: <T>(path: string) => request<T>("DELETE", path),
  blob: (path: string, body?: unknown) => request<Blob>("POST", path, body),
};

export function query(params: Record<string, string | number | boolean | string[] | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    if (Array.isArray(value)) value.forEach((v) => search.append(key, v));
    else search.set(key, String(value));
  }
  const s = search.toString();
  return s ? `?${s}` : "";
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  // Keep the link (and its download name) around until the browser has picked up the download.
  setTimeout(() => {
    link.remove();
    URL.revokeObjectURL(url);
  }, 1500);
}

/** POST that returns a file; the filename comes from Content-Disposition. */
export async function downloadFile(path: string, body: unknown, fallbackName: string): Promise<void> {
  const headers: Record<string, string> = { "Content-Type": "application/json", "X-CSRF-Token": await ensureCsrf() };
  const response = await fetch(`/api/v1${path}`, { method: "POST", headers, body: JSON.stringify(body), credentials: "same-origin" });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new ApiError(response.status, data?.error?.code ?? "http_error", data?.error?.message ?? "Downloaden mislukt.");
  }
  const disposition = response.headers.get("content-disposition") ?? "";
  const name = /filename="([^"]+)"/.exec(disposition)?.[1] ?? fallbackName;
  downloadBlob(await response.blob(), name);
}

export function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return error.message;
  if (error instanceof Error) return error.message;
  return "Er ging iets mis.";
}
