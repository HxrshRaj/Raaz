import { QueryClient } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { vi } from "vitest";
import { AppRoutes, Providers } from "@/App";

export const SID = "sess1";
export const portrait = { skin: "#c79a78", hair: "#222", outfit: "#445533", accent: "#99aa66", glasses: true, beard: false, hair_style: "short", age: "mid" };

export const evidence = (over: Record<string, unknown> = {}) => ({
  key: "ev_ticket_stub", name: "Torn platform-ticket stub PT-0412", category: "physical", description: "A torn stub under the desk.",
  examined_detail: null, source: "Under the writing desk", location_key: "carriage", location_name: "Private Saloon SC-4471",
  discovered_at: "2026-10-12T10:00:00Z", discovered_via: "hotspot:carriage/h_under_desk", action_no: 1, examined: false,
  reliability: "verified", related_people: [], related_events: [], timestamps: [{ label: "Issued", clock: "ST", clock_label: "Station clock", time: "22:25" }],
  bearing: [], is_testimony: false, icon: "ticket", contradiction_rules: [], ...over,
});
export const evidence2 = evidence({ key: "ev_ticket_log", name: "Platform-ticket machine journal", category: "access", description: "Journal of ticket sales." });

export const overview = (over: Record<string, unknown> = {}) => ({
  id: SID, case_id: "aakhri_gaadi", case_title: "Aakhri Gaadi — The Last Train", tagline: "Har raaz ke peeche ek kahaani hai.", mode: "standard",
  status: "active", attempts: 0, max_attempts: 3, reputation: 100, hints_used: 0, actions: 2, version: 3, score: null,
  created_at: "2026-10-12T09:00:00Z", updated_at: "2026-10-12T10:00:00Z", briefing: "Devgarh Junction, 11:47 PM.\n\nFive people had reasons.",
  progress: { percent: 12, evidence: 1, examined: 0, contradictions: 0, interviewed: 0, suspects: 6, places_searched: 1, places_visible: 8 },
  unreviewed_evidence: [{ key: "ev_ticket_stub", name: "Torn platform-ticket stub PT-0412" }],
  recent_discoveries: [{ key: "ev_ticket_stub", name: "Torn platform-ticket stub PT-0412" }], suspect_updates: [],
  locations: [
    { key: "carriage", name: "Private Saloon SC-4471", scene: "carriage", off_site: false, locked: false, unlock_hint: "", description: "d", visible_hotspots: 3, searched_hotspots: 1 },
    { key: "siding4", name: "Siding 4 & Storm Drain", scene: "siding", off_site: false, locked: true, unlock_hint: "hint", description: "", visible_hotspots: 0, searched_hotspots: 0 },
  ],
  clock_known: false, ...over,
});

export const conversation = (messages: unknown[] = []) => ({
  character: { key: "rohan", name: "Rohan Deshmukh", role: "Former CTO", portrait },
  messages: [{ id: "m0", seq: 0, role: "npc", content: "Inspector. I assume you want to hear that I was on a train.", evidence_key: null, created_at: null, mode: "scripted_greeting" }, ...messages],
  state: { mood: "guarded", trust: "medium", turns: 0 },
  llm: { enabled: false, provider: null, label: "Scripted fallback — no LLM provider is configured. Replies are authored lines." },
  token_budget_used: 0, token_budget: 40000,
});

type Handler = (body: unknown, url: URL) => unknown | Response | Promise<unknown | Response>;

/** Stub `fetch` with a tiny in-memory router: keys look like "GET /sessions/sess1". Unknown routes fail the test loudly. */
export function mockApi(routes: Record<string, Handler>) {
  const calls: { method: string; path: string; body: unknown }[] = [];
  const fn = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = new URL(String(input), "http://localhost");
    const path = url.pathname.replace(/^\/api\/v1/, "");
    const method = init?.method ?? "GET";
    const body = init?.body ? JSON.parse(String(init.body)) : undefined;
    calls.push({ method, path, body });
    const h = routes[`${method} ${path}`];
    if (!h) return new Response(JSON.stringify({ error: { code: "not_found", message: `unmocked ${method} ${path}` } }), { status: 404 });
    const out = await h(body, url);
    if (out instanceof Response) return out;
    return new Response(out === undefined ? null : JSON.stringify(out), { status: out === undefined ? 204 : 200, headers: { "Content-Type": "application/json" } });
  });
  vi.stubGlobal("fetch", fn);
  return { calls, fn };
}

export const jsonError = (status: number, code: string, message: string) =>
  new Response(JSON.stringify({ error: { code, message, details: {}, request_id: "t" } }), { status, headers: { "Content-Type": "application/json" } });

export const baseRoutes = (): Record<string, Handler> => ({
  "GET /auth/me": () => ({ id: "u1", display_name: "Tester", is_guest: true, email: null }),
  [`GET /sessions/${SID}`]: () => overview(),
  [`GET /sessions/${SID}/evidence`]: () => [evidence(), evidence2],
});

export function renderApp(path: string, { client, signedIn = true }: { client?: QueryClient; signedIn?: boolean } = {}) {
  if (signedIn) localStorage.setItem("raaz.token", "test-token");
  const qc = client ?? new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0 } } });
  return render(
    <Providers client={qc}>
      <MemoryRouter initialEntries={[path]}><AppRoutes /></MemoryRouter>
    </Providers>,
  );
}
