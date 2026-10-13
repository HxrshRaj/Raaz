import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { ApiError, api } from "@/lib/api";
import { SID, baseRoutes, conversation, evidence, evidence2, jsonError, mockApi, overview, portrait, renderApp } from "./helpers";

describe("navigation", () => {
  it("shows the office and moves between screens", async () => {
    mockApi({ ...baseRoutes(), [`GET /sessions/${SID}/dossiers`]: () => [], [`GET /sessions/${SID}/ml/leads`]: () => ({ model: "m", disclaimer: "d", ranking: [] }),
      [`GET /sessions/${SID}/ml/anomalies`]: () => ({ available: false, disclaimer: "d", findings: [], message: "nothing" }),
      [`GET /sessions/${SID}/contradictions`]: () => [] });
    renderApp(`/play/${SID}`);
    expect(await screen.findByRole("heading", { name: /Aakhri Gaadi/ })).toBeInTheDocument();
    expect(screen.getByText(/Police briefing/i)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: /Evidence/ }));
    expect(await screen.findByRole("heading", { name: "Evidence inventory" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: /Suspects/ }));
    expect(await screen.findByRole("heading", { name: /Suspects & witnesses/ })).toBeInTheDocument();
  });

  it("shows a loading skeleton and then recovers from a server error", async () => {
    let n = 0;
    mockApi({ ...baseRoutes(), [`GET /sessions/${SID}`]: () => (++n === 1 ? jsonError(500, "internal_error", "Something went wrong on our side.") : overview()),
      [`GET /sessions/${SID}/dossiers`]: () => [], [`GET /sessions/${SID}/ml/leads`]: () => ({ model: "m", disclaimer: "d", ranking: [] }),
      [`GET /sessions/${SID}/ml/anomalies`]: () => ({ available: false, disclaimer: "d", findings: [] }) });
    renderApp(`/play/${SID}`);
    expect(await screen.findByRole("alert")).toHaveTextContent("Something went wrong on our side.");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByRole("heading", { name: /Aakhri Gaadi/ })).toBeInTheDocument();
  });

  it("sends signed-out visitors back to the title screen", async () => {
    mockApi({});
    renderApp(`/play/${SID}`, { signedIn: false });
    expect(await screen.findByText("Continue Investigation")).toBeInTheDocument();
  });
});

describe("evidence inventory", () => {
  it("lists collected items, filters them, and examines one", async () => {
    let examined = false;
    const m = mockApi({
      ...baseRoutes(),
      [`GET /sessions/${SID}/evidence`]: () => [evidence({ examined, examined_detail: examined ? "Printed with the machine clock: station time." : null }), evidence2],
      [`GET /sessions/${SID}/contradictions`]: () => [],
      [`POST /sessions/${SID}/evidence/ev_ticket_stub/examine`]: () => { examined = true; return { first_examination: true, evidence: evidence({ examined: true, examined_detail: "Printed with the machine clock: station time." }) }; },
    });
    renderApp(`/play/${SID}/evidence`);
    expect(await screen.findByText("Torn platform-ticket stub PT-0412")).toBeInTheDocument();
    expect(screen.getByText("Platform-ticket machine journal")).toBeInTheDocument();
    await userEvent.type(screen.getByPlaceholderText("Search evidence…"), "journal");
    expect(screen.queryByText("Torn platform-ticket stub PT-0412")).not.toBeInTheDocument();
    await userEvent.clear(screen.getByPlaceholderText("Search evidence…"));
    await userEvent.click(screen.getByText("Torn platform-ticket stub PT-0412"));
    const dlg = await screen.findByRole("dialog");
    expect(within(dlg).getByText(/Examine this item to read the fine detail/)).toBeInTheDocument();
    await userEvent.click(within(dlg).getByRole("button", { name: /Examine closely/ }));
    expect(await within(dlg).findByText(/Printed with the machine clock/)).toBeInTheDocument();
    expect(m.calls.some((c) => c.method === "POST" && c.path.endsWith("/examine"))).toBe(true);
  });

  it("tests a contradiction between two marked items", async () => {
    const m = mockApi({
      ...baseRoutes(), [`GET /sessions/${SID}/contradictions`]: () => [],
      [`POST /sessions/${SID}/contradictions/check`]: () => ({ established: false, newly_found: false, contradiction: null, message: "Those two items don't conflict." }),
    });
    renderApp(`/play/${SID}/evidence`);
    await screen.findByText("Torn platform-ticket stub PT-0412");
    const test = screen.getByRole("button", { name: "Test contradiction" });
    expect(test).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: /Mark Torn platform-ticket stub PT-0412/ }));
    await userEvent.click(screen.getByRole("button", { name: /Mark Platform-ticket machine journal/ }));
    expect(test).toBeEnabled();
    await userEvent.click(test);
    await waitFor(() => expect(m.calls.find((c) => c.path.endsWith("/contradictions/check"))?.body).toEqual({ a: "ev_ticket_stub", b: "ev_ticket_log" }));
    expect(await screen.findByText("Those two items don't conflict.")).toBeInTheDocument();
  });
});

describe("exploration", () => {
  it("searching a hotspot adds evidence and reports it", async () => {
    const m = mockApi({
      ...baseRoutes(),
      [`GET /sessions/${SID}/locations/carriage`]: () => ({ key: "carriage", name: "Private Saloon SC-4471", description: "A saloon.", scene: "carriage", off_site: false,
        hotspots: [{ key: "h_under_desk", label: "Under the desk", x: 52, y: 82, w: 9, h: 8, icon: "ticket", searched: false }] }),
      [`POST /sessions/${SID}/locations/carriage/hotspots/h_under_desk/inspect`]: () => ({ narration: "Something pale is wedged against the desk's iron foot.",
        new_evidence: [evidence()], already_found: [], unlocked_locations: [] }),
    });
    renderApp(`/play/${SID}/explore/carriage`);
    await userEvent.click(await screen.findByTestId("hotspot-h_under_desk"));
    expect(await screen.findByText(/wedged against the desk/)).toBeInTheDocument();
    expect(screen.getAllByText("Torn platform-ticket stub PT-0412").length).toBeGreaterThan(0);
    expect(m.calls.filter((c) => c.method === "POST")).toHaveLength(1);
  });

  it("explains a locked place without leaking where it leads", async () => {
    mockApi({ ...baseRoutes(), [`GET /sessions/${SID}/locations/siding4`]: () => jsonError(403, "location_locked", "You have no reason to go there yet.") });
    renderApp(`/play/${SID}/explore/siding4`);
    expect(await screen.findByRole("alert")).toHaveTextContent("You have no reason to go there yet.");
  });
});

describe("interrogation", () => {
  const routes = (reply: (body: { text: string; evidence_key: string | null }) => unknown) => ({
    ...baseRoutes(),
    [`GET /sessions/${SID}/conversations/rohan`]: () => conversation(),
    [`POST /sessions/${SID}/conversations/rohan/messages`]: (b: unknown) => reply(b as { text: string; evidence_key: string | null }),
  });
  const result = (text: string, extra: Record<string, unknown> = {}) => ({
    player_message: { id: "p1", seq: 1, role: "player", content: text, evidence_key: null, created_at: null, mode: null },
    npc_message: { id: "n1", seq: 2, role: "npc", content: "I took the 10:15 Kosi Passenger.", evidence_key: null, created_at: null, mode: "fallback" },
    state: { mood: "guarded", trust: "medium", turns: 1 },
    generation: { mode: "fallback", provider: null, model: null, reason: "no_llm_configured", label: "Scripted fallback" },
    new_evidence: [], contradictions: [], newly_found_contradictions: [], unlocked_locations: [], ...extra,
  });

  it("asks a question in free text and shows the reply, mood and the honest fallback label", async () => {
    const m = mockApi(routes((b) => result(b.text)));
    renderApp(`/play/${SID}/interview/rohan`);
    expect(await screen.findByText(/Inspector. I assume/)).toBeInTheDocument();
    expect(screen.getByTestId("llm-label")).toHaveTextContent(/Scripted fallback/);
    expect(screen.getByTestId("mood")).toHaveTextContent("Guarded");
    await userEvent.type(screen.getByLabelText("Your question"), "Which train did you take?{Enter}");
    expect(await screen.findByText("I took the 10:15 Kosi Passenger.")).toBeInTheDocument();
    expect(screen.getByText("Which train did you take?")).toBeInTheDocument();
    expect(m.calls.find((c) => c.method === "POST")?.body).toEqual({ text: "Which train did you take?", evidence_key: null });
  });

  it("presents evidence and surfaces a contradiction", async () => {
    const m = mockApi(routes((b) => result(b.text, {
      contradictions: [{ key: "c_rohan_stub", title: "Rohan's claim vs the ticket", explanation: "x", about: "rohan", about_name: "Rohan Deshmukh", importance: 3, evidence: ["a", "b"], found_via: "presentation:rohan", found_at: null }],
      newly_found_contradictions: ["c_rohan_stub"],
    })));
    renderApp(`/play/${SID}/interview/rohan`);
    await screen.findByText(/Inspector. I assume/);
    await userEvent.click(screen.getByRole("button", { name: "Choose evidence to present" }));
    const dlg = await screen.findByRole("dialog");
    await userEvent.click(within(dlg).getByRole("button", { name: /Torn platform-ticket stub/ }));
    expect(await screen.findByText(/Presenting/)).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Your question"), "Explain this.{Enter}");
    expect(await screen.findByText("Contradiction exposed!")).toBeInTheDocument();
    expect(m.calls.find((c) => c.method === "POST")?.body).toEqual({ text: "Explain this.", evidence_key: "ev_ticket_stub" });
  });

  it("handles a rate-limit or conflict error without losing the typed question flow", async () => {
    mockApi(routes(() => jsonError(409, "still_answering", "They are still answering your last question. Try again in a moment.")));
    renderApp(`/play/${SID}/interview/rohan`);
    await screen.findByText(/Inspector. I assume/);
    await userEvent.type(screen.getByLabelText("Your question"), "Hello?{Enter}");
    expect(await screen.findByText("They're still answering")).toBeInTheDocument();
    expect(screen.queryByText("I took the 10:15 Kosi Passenger.")).not.toBeInTheDocument();
    expect(screen.getByLabelText("Your question")).toHaveValue("Hello?");
  });

  it("shows a loading state while the conversation loads", async () => {
    mockApi({ ...baseRoutes(), [`GET /sessions/${SID}/conversations/rohan`]: () => new Promise(() => {}) });
    const { container } = renderApp(`/play/${SID}/interview/rohan`);
    await screen.findByRole("heading", { name: /Aakhri Gaadi|Rohan/ }).catch(() => undefined);
    await waitFor(() => expect(container.querySelector(".animate-pulse")).not.toBeNull());
  });
});

describe("investigation board", () => {
  it("pins a clue, connects two items and reports whether the record backs the link", async () => {
    const items: unknown[] = [];
    const links: unknown[] = [];
    const m = mockApi({
      ...baseRoutes(),
      [`GET /sessions/${SID}/board`]: () => ({ items, links, relations: ["related", "supports", "contradicts", "implicates", "clears", "located_at", "happened_at"] }),
      [`GET /sessions/${SID}/dossiers`]: () => [{ key: "rohan", name: "Rohan Deshmukh", role: "x", is_suspect: true, portrait, turns: 0, mood: "unmet", alibi_status: "unverified" }],
      [`POST /sessions/${SID}/board/items`]: (b) => {
        const body = b as { ref_key: string };
        const it = { id: `i${items.length + 1}`, kind: "evidence", ref_key: body.ref_key, label: body.ref_key === "ev_ticket_stub" ? "Torn platform-ticket stub PT-0412" : "Platform-ticket machine journal", note: "", x: 30, y: 30, predicted_category: null };
        items.push(it);
        return it;
      },
      [`POST /sessions/${SID}/board/links`]: (b) => {
        const body = b as { from_item: string; to_item: string; relation: string };
        const link = { id: "l1", from: body.from_item, to: body.to_item, relation: body.relation, note: "", validated: true, rule_key: null };
        links.push(link);
        return { link, message: "Checked against shared people and events.", newly_found_contradiction: false, contradiction: null };
      },
    });
    renderApp(`/play/${SID}/board`);
    await userEvent.click(await screen.findByRole("button", { name: /Torn platform-ticket stub PT-0412/ }));
    await userEvent.click(await screen.findByRole("button", { name: /Platform-ticket machine journal/ }));
    expect(await screen.findByTestId("board-item-ev_ticket_stub")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Connect two items/ }));
    await userEvent.click(screen.getByTestId("board-item-ev_ticket_stub"));
    await userEvent.click(screen.getByTestId("board-item-ev_ticket_log"));
    const dlg = await screen.findByRole("dialog");
    await userEvent.click(within(dlg).getByRole("button", { name: "Connect" }));
    expect(await screen.findByText("Connection backed by the record")).toBeInTheDocument();
    expect(m.calls.find((c) => c.path.endsWith("/board/links"))?.body).toMatchObject({ from_item: "i1", to_item: "i2", relation: "related" });
  });
});

describe("save and resume", () => {
  it("offers to continue the saved investigation from the title screen", async () => {
    localStorage.setItem("raaz.session", SID);
    mockApi({ ...baseRoutes(), "GET /system/info": () => ({ llm: { enabled: false, provider: null, label: "Scripted fallback" }, env: "dev", version: "0.1.0", ml_workbench: true, notes: "" }) });
    renderApp("/");
    await userEvent.click(await screen.findByText("Continue Investigation"));
    expect(await screen.findByRole("heading", { name: /Aakhri Gaadi/ })).toBeInTheDocument();
  });

  it("lists past investigations in the archive and resumes one with its server-side progress", async () => {
    mockApi({ ...baseRoutes(), "GET /sessions": () => [{ id: SID, case_id: "aakhri_gaadi", case_title: "Aakhri Gaadi — The Last Train", mode: "standard", status: "active", attempts: 1,
      progress: overview().progress, updated_at: "2026-10-12T10:00:00Z", created_at: "2026-10-12T09:00:00Z", score: null }], "GET /progress": () => ({ sessions: 1, solved: 0, best_score: null, total_actions: 5 }) });
    renderApp("/archive");
    expect(await screen.findByText("1 accusation(s)")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Resume" }));
    expect(await screen.findByRole("heading", { name: /Aakhri Gaadi/ })).toBeInTheDocument();
    expect(localStorage.getItem("raaz.session")).toBe(SID);
  });
});

describe("api client", () => {
  it("turns error envelopes into ApiError, reports network failure, and rejects malformed payloads", async () => {
    mockApi({ "GET /auth/me": () => jsonError(401, "unauthenticated", "Sign in to continue.") });
    await expect(api.me()).rejects.toMatchObject({ status: 401, code: "unauthenticated", message: "Sign in to continue." });
    mockApi({ "GET /auth/me": () => ({ nope: true }) });
    await expect(api.me()).rejects.toMatchObject({ code: "bad_response" });
    const { vi } = await import("vitest");
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("fetch failed"); }));
    const err = await api.me().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("network_error");
  });

  it("dispatches an unauthorized event so the app can sign the player out", async () => {
    mockApi({ "GET /auth/me": () => jsonError(401, "unauthenticated", "Sign in to continue.") });
    let fired = false;
    window.addEventListener("raaz:unauthorized", () => { fired = true; }, { once: true });
    await api.me().catch(() => undefined);
    expect(fired).toBe(true);
  });
});
