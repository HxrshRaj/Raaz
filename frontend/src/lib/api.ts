import { z } from "zod";
import * as S from "./schemas";

const BASE = `${(import.meta.env.VITE_API_BASE as string | undefined) ?? ""}/api/v1`;
const TOKEN_KEY = "raaz.token";

export class ApiError extends Error {
  constructor(public status: number, public code: string, message: string, public details?: unknown) {
    super(message);
    this.name = "ApiError";
  }
}

export const tokenStore = {
  get(): string | null {
    try { return localStorage.getItem(TOKEN_KEY); } catch { return null; }
  },
  set(t: string | null) {
    try { if (t) localStorage.setItem(TOKEN_KEY, t); else localStorage.removeItem(TOKEN_KEY); } catch { /* storage unavailable */ }
  },
};

type Init = { method?: string; body?: unknown; headers?: Record<string, string>; signal?: AbortSignal };

async function request<T>(path: string, schema: z.ZodType<T>, init: Init = {}): Promise<T> {
  const headers: Record<string, string> = { Accept: "application/json", ...(init.headers ?? {}) };
  const t = tokenStore.get();
  if (t) headers.Authorization = `Bearer ${t}`;
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  let res: Response;
  try {
    res = await fetch(`${BASE}${path}`, {
      method: init.method ?? "GET", headers, signal: init.signal,
      body: init.body !== undefined ? JSON.stringify(init.body) : undefined,
    });
  } catch (e) {
    throw new ApiError(0, "network_error", "Can't reach the server. Is the backend running?", e);
  }
  if (res.status === 204) return schema.parse(undefined);
  let data: unknown = null;
  try { data = await res.json(); } catch { /* non-JSON error body */ }
  if (!res.ok) {
    const err = (data as { error?: { code?: string; message?: string; details?: unknown } } | null)?.error;
    if (res.status === 401) window.dispatchEvent(new CustomEvent("raaz:unauthorized"));
    throw new ApiError(res.status, err?.code ?? "http_error", err?.message ?? `Request failed (${res.status})`, err?.details);
  }
  const parsed = schema.safeParse(data);
  if (!parsed.success) {
    throw new ApiError(502, "bad_response", "The server sent something unexpected.", parsed.error.flatten());
  }
  return parsed.data;
}

const sp = (id: string) => `/sessions/${id}`;
const post = <T>(path: string, schema: z.ZodType<T>, body?: unknown, headers?: Record<string, string>) =>
  request(path, schema, { method: "POST", body: body ?? {}, headers });

export const api = {
  guest: (display_name: string) => post("/auth/guest", S.AuthResp, { display_name }),
  register: (email: string, password: string, display_name: string) => post("/auth/register", S.AuthResp, { email, password, display_name }),
  login: (email: string, password: string) => post("/auth/login", S.AuthResp, { email, password }),
  me: () => request("/auth/me", S.User),
  systemInfo: () => request("/system/info", S.SystemInfo),
  cases: () => request("/cases", z.array(z.object({ id: z.string(), title: z.string(), tagline: z.string(), summary: z.string(), version: z.string() }))),
  progress: () => request("/progress", S.Progress2),

  sessions: () => request("/sessions", z.array(S.SessionRow)),
  createSession: (case_id: string, mode: "standard" | "demo") => post("/sessions", S.Overview, { case_id, mode }),
  overview: (id: string) => request(sp(id), S.Overview),
  reopen: (id: string) => post(`${sp(id)}/reopen`, S.Overview),

  locations: (id: string) => request(`${sp(id)}/locations`, z.array(S.LocationSummary)),
  location: (id: string, loc: string) => request(`${sp(id)}/locations/${loc}`, S.LocationDetail),
  inspect: (id: string, loc: string, h: string) => post(`${sp(id)}/locations/${loc}/hotspots/${h}/inspect`, S.InspectResult),

  evidence: (id: string) => request(`${sp(id)}/evidence`, z.array(S.Evidence)),
  examine: (id: string, key: string) => post(`${sp(id)}/evidence/${key}/examine`, S.ExamineResult),
  timestamps: (id: string) => request(`${sp(id)}/evidence/timestamps`, S.TimestampsResp),
  contradictions: (id: string) => request(`${sp(id)}/contradictions`, z.array(S.Contradiction)),
  checkContradiction: (id: string, a: string, b: string) => post(`${sp(id)}/contradictions/check`, S.CheckResult, { a, b }),
  events: (id: string) => request(`${sp(id)}/events`, z.array(S.EventCard)),

  dossiers: (id: string) => request(`${sp(id)}/dossiers`, z.array(S.DossierRow)),
  dossier: (id: string, key: string) => request(`${sp(id)}/dossiers/${key}`, S.Dossier),
  conversation: (id: string, key: string) => request(`${sp(id)}/conversations/${key}`, S.Conversation),
  say: (id: string, key: string, text: string, evidence_key?: string | null) =>
    post(`${sp(id)}/conversations/${key}/messages`, S.MessageResult, { text, evidence_key: evidence_key ?? null }),

  board: (id: string) => request(`${sp(id)}/board`, S.Board),
  boardAdd: (id: string, body: { kind: string; ref_key?: string; text?: string; x: number; y: number }) =>
    post(`${sp(id)}/board/items`, S.BoardItem, body),
  boardMove: (id: string, item: string, x: number, y: number) =>
    request(`${sp(id)}/board/items/${item}`, z.object({ id: z.string(), x: z.number(), y: z.number() }), { method: "PATCH", body: { x, y } }),
  boardDelete: (id: string, item: string) => request(`${sp(id)}/board/items/${item}`, z.undefined(), { method: "DELETE" }),
  boardLink: (id: string, from_item: string, to_item: string, relation: string, note = "") =>
    post(`${sp(id)}/board/links`, S.LinkResult, { from_item, to_item, relation, note }),
  boardUnlink: (id: string, link: string) => request(`${sp(id)}/board/links/${link}`, z.undefined(), { method: "DELETE" }),

  timeline: (id: string) => request(`${sp(id)}/timeline`, S.TimelineResp),
  timelineAdd: (id: string, body: { label: string; time: string; clock: "RT" | "ST"; actor_key?: string | null; location_key?: string | null; evidence_keys: string[] }) =>
    post(`${sp(id)}/timeline`, z.object({ entry: S.TimelineEntry, validation: S.Validation }), body),
  timelineDelete: (id: string, e: string) => request(`${sp(id)}/timeline/${e}`, z.undefined(), { method: "DELETE" }),

  hypotheses: (id: string) => request(`${sp(id)}/hypotheses`, z.array(S.Hypothesis)),
  evaluate: (id: string, culprit_key: string | null, motive_key: string | null) =>
    post(`${sp(id)}/hypotheses/evaluate`, S.HypothesisEval, { culprit_key, motive_key }),
  saveHypothesis: (id: string, body: { title: string; culprit_key: string | null; motive_key: string | null; evidence_for: string[]; evidence_against: string[] }) =>
    post(`${sp(id)}/hypotheses`, S.Hypothesis, body),
  deleteHypothesis: (id: string, h: string) => request(`${sp(id)}/hypotheses/${h}`, z.undefined(), { method: "DELETE" }),

  accusationOptions: (id: string) => request(`${sp(id)}/accusation/options`, S.AccusationOptions),
  accuse: (id: string, body: { culprit: string; motive: string; event_sequence: string[]; evidence: string[]; contradictions: string[] }, key: string) =>
    post(`${sp(id)}/accusation`, S.AccusationResult, body, { "Idempotency-Key": key }),
  accusationHistory: (id: string) => request(`${sp(id)}/accusation/history`, z.array(z.object({ attempt: z.number(), verdict: z.string(), score: z.number(), accused: z.string().nullable(), report: z.any(), created_at: z.string() }))),

  nazar: (id: string, question: string, hint_level: 1 | 2 | 3) => post(`${sp(id)}/nazar`, S.NazarResult, { question, hint_level }),
  nazarHistory: (id: string) => request(`${sp(id)}/nazar`, z.array(S.NazarMsg)),
  startRun: (id: string, question: string) => post(`${sp(id)}/investigations`, S.RunStart, { question }),
  run: (id: string, run: string) => request(`${sp(id)}/investigations/${run}`, S.Run),
  runs: (id: string) => request(`${sp(id)}/investigations`, z.array(S.Run)),
  cancelRun: (id: string, run: string) => post(`${sp(id)}/investigations/${run}/cancel`, z.object({ id: z.string(), status: z.string(), cancel_requested: z.boolean() })),

  leads: (id: string) => request(`${sp(id)}/ml/leads`, S.Leads),
  anomalies: (id: string) => request(`${sp(id)}/ml/anomalies`, S.Anomalies),

  workbench: () => request("/ml/workbench", z.any()),
  workbenchTrain: (seed: number, include_torch: boolean) => post("/ml/workbench/train", z.object({ job_id: z.string() }), { seed, include_torch }),
  workbenchJob: (job: string) => request(`/ml/workbench/jobs/${job}`, z.object({ id: z.string(), status: z.string(), attempts: z.number(), result: z.any().nullable(), error: z.string().nullable() })),
  workbenchPredict: (text: string) => post("/ml/workbench/predict", z.any(), { text }),
};

export function errorMessage(e: unknown): string {
  if (e instanceof ApiError) return e.message;
  if (e instanceof Error) return e.message;
  return "Something went wrong.";
}
