import type { AskRequest, AskResponse } from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "";

export async function askNova(req: AskRequest): Promise<AskResponse> {
  const res = await fetch(`${BASE}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(
      (body as { detail?: string }).detail ?? `HTTP ${res.status}`
    );
  }

  return res.json() as Promise<AskResponse>;
}
