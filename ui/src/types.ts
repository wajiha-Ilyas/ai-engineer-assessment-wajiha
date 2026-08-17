// ── API types ──────────────────────────────────────────────────────────────

export type RouteLabel = "superhero" | "dataset" | "both" | "none";

export interface Source {
  kind: "superhero_api" | "dataset";
  // superhero
  name?: string;
  url?: string;
  // dataset
  doc_id?: string;
  chunk_id?: number;
  title?: string;
}

export interface AskRequest {
  question: string;
  session_id?: string;
}

export interface AskResponse {
  answer: string;
  route: RouteLabel;
  sources: Source[];
  session_id: string;
}

// ── UI types ───────────────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  route?: RouteLabel;
  sources?: Source[];
  error?: boolean;
}
