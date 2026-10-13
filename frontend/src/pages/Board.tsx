import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link2, MapPin, Pin, StickyNote, Trash2, User } from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { CategoryIcon } from "@/components/EvidenceCard";
import { useToast } from "@/components/Toasts";
import { Badge, Button, Dialog, DialogContent, Empty, ErrorState, Input, Progress, Select, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui";
import { keys, useBoard, useDossiers, useEvidence, useOverview, useRefreshGame, useSid } from "@/hooks/game";
import { api, errorMessage } from "@/lib/api";
import { sound } from "@/lib/audio";
import type { TBoard } from "@/lib/schemas";
import { cn, titleCase } from "@/lib/utils";

type Item = TBoard["items"][number];
const W = 168, H = 76;
const REL_LABEL: Record<string, string> = { related: "Related to", supports: "Supports", contradicts: "Contradicts", implicates: "Implicates", clears: "Clears", located_at: "Located at", happened_at: "Happened at" };

export default function BoardPage() {
  return (
    <div className="space-y-4">
      <h1 className="font-display text-3xl">Investigation board</h1>
      <Tabs defaultValue="board">
        <TabsList><TabsTrigger value="board">Clue board</TabsTrigger><TabsTrigger value="theories">Theories</TabsTrigger></TabsList>
        <TabsContent value="board" className="mt-4"><Corkboard /></TabsContent>
        <TabsContent value="theories" className="mt-4"><Theories /></TabsContent>
      </Tabs>
    </div>
  );
}

function Corkboard() {
  const sid = useSid();
  const board = useBoard(sid);
  const ev = useEvidence(sid);
  const doss = useDossiers(sid);
  const ov = useOverview(sid);
  const qc = useQueryClient();
  const toast = useToast();
  const refresh = useRefreshGame(sid);
  const [sel, setSel] = useState<string | null>(null);
  const [connect, setConnect] = useState(false);
  const [pair, setPair] = useState<[string, string] | null>(null);
  const [relation, setRelation] = useState("related");
  const [note, setNote] = useState("");
  const [noteText, setNoteText] = useState("");
  const drag = useRef<{ id: string; dx: number; dy: number } | null>(null);
  const [local, setLocal] = useState<Record<string, { x: number; y: number }>>({});

  const add = useMutation({
    mutationFn: (b: { kind: string; ref_key?: string; text?: string }) => {
      const n = (board.data?.items.length ?? 0);
      return api.boardAdd(sid, { ...b, x: 30 + (n % 5) * 190, y: 30 + Math.floor(n / 5) * 110 });
    },
    onSuccess: () => { void qc.invalidateQueries({ queryKey: keys.board(sid) }); sound.paper(); setNoteText(""); },
    onError: (e) => toast({ title: "Couldn't pin that", body: errorMessage(e), tone: "warn" }),
  });
  const move = useMutation({ mutationFn: (v: { id: string; x: number; y: number }) => api.boardMove(sid, v.id, v.x, v.y) });
  const del = useMutation({ mutationFn: (id: string) => api.boardDelete(sid, id), onSuccess: () => { setSel(null); void qc.invalidateQueries({ queryKey: keys.board(sid) }); } });
  const link = useMutation({
    mutationFn: () => api.boardLink(sid, pair![0], pair![1], relation, note),
    onSuccess: (r) => {
      void qc.invalidateQueries({ queryKey: keys.board(sid) }); refresh(); setPair(null); setNote(""); setConnect(false); setSel(null);
      if (r.newly_found_contradiction && r.contradiction) { sound.alert(); toast({ title: "Contradiction established", body: r.contradiction.title, tone: "clue" }); }
      else toast({ title: r.link.validated ? "Connection backed by the record" : "Saved as your theory", body: r.message, tone: r.link.validated ? "success" : "info" });
    },
    onError: (e) => toast({ title: "Couldn't connect", body: errorMessage(e), tone: "warn" }),
  });
  const unlink = useMutation({ mutationFn: (id: string) => api.boardUnlink(sid, id), onSuccess: () => qc.invalidateQueries({ queryKey: keys.board(sid) }) });

  const pos = useCallback((it: Item) => local[it.id] ?? { x: it.x, y: it.y }, [local]);
  const items = board.data?.items ?? [];
  const byId = useMemo(() => new Map(items.map((i) => [i.id, i])), [items]);

  const onDown = (e: React.PointerEvent, it: Item) => {
    if (connect) return;
    (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);
    const p = pos(it);
    drag.current = { id: it.id, dx: e.clientX - p.x, dy: e.clientY - p.y };
  };
  const onMove = (e: React.PointerEvent) => {
    const d = drag.current; if (!d) return;
    setLocal((l) => ({ ...l, [d.id]: { x: Math.max(0, e.clientX - d.dx), y: Math.max(0, e.clientY - d.dy) } }));
  };
  const onUp = () => {
    const d = drag.current; drag.current = null; if (!d) return;
    const p = local[d.id]; if (p) move.mutate({ id: d.id, x: Math.round(p.x), y: Math.round(p.y) });
  };
  const onKey = (e: React.KeyboardEvent, it: Item) => {
    const step = e.shiftKey ? 40 : 10; const p = pos(it);
    const m: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
    if (m[e.key]) { e.preventDefault(); const n = { x: Math.max(0, p.x + m[e.key][0]), y: Math.max(0, p.y + m[e.key][1]) }; setLocal((l) => ({ ...l, [it.id]: n })); move.mutate({ id: it.id, ...n }); }
    if (e.key === "Enter" || e.key === " ") { e.preventDefault(); click(it); }
    if (e.key === "Delete") del.mutate(it.id);
  };
  const click = (it: Item) => {
    if (!connect) { setSel(it.id === sel ? null : it.id); return; }
    if (!sel) { setSel(it.id); return; }
    if (sel === it.id) { setSel(null); return; }
    setPair([sel, it.id]);
  };

  if (board.isLoading) return <Skeleton className="h-[70vh]" />;
  if (board.error) return <ErrorState error={board.error} onRetry={() => board.refetch()} />;
  const pinned = new Set(items.map((i) => `${i.kind}:${i.ref_key}`));
  const unlocked = ov.data?.locations.filter((l) => !l.locked) ?? [];

  return (
    <div className="grid gap-4 xl:grid-cols-[280px_1fr]">
      <aside className="panel space-y-3 p-4">
        <h2 className="panel-title flex items-center gap-2"><Pin className="h-4 w-4" /> Pin to the board</h2>
        <Tabs defaultValue="evidence">
          <TabsList className="w-full"><TabsTrigger value="evidence" className="flex-1">Clues</TabsTrigger><TabsTrigger value="person" className="flex-1">People</TabsTrigger><TabsTrigger value="place" className="flex-1">Places</TabsTrigger></TabsList>
          <TabsContent value="evidence" className="mt-3 max-h-72 space-y-1 overflow-y-auto">
            {ev.data?.length ? ev.data.map((e) => <PinRow key={e.key} icon={<CategoryIcon category={e.category} className="h-4 w-4" />} label={e.name} disabled={pinned.has(`evidence:${e.key}`)} onClick={() => add.mutate({ kind: "evidence", ref_key: e.key })} />) : <Empty title="No clues yet" />}
          </TabsContent>
          <TabsContent value="person" className="mt-3 space-y-1">
            <PinRow icon={<User className="h-4 w-4" />} label="Adrian Vale (victim)" disabled={pinned.has("person:adrian")} onClick={() => add.mutate({ kind: "person", ref_key: "adrian" })} />
            {doss.data?.map((d) => <PinRow key={d.key} icon={<User className="h-4 w-4" />} label={d.name} disabled={pinned.has(`person:${d.key}`)} onClick={() => add.mutate({ kind: "person", ref_key: d.key })} />)}
          </TabsContent>
          <TabsContent value="place" className="mt-3 space-y-1">
            {unlocked.map((l) => <PinRow key={l.key} icon={<MapPin className="h-4 w-4" />} label={l.name} disabled={pinned.has(`location:${l.key}`)} onClick={() => add.mutate({ kind: "location", ref_key: l.key })} />)}
          </TabsContent>
        </Tabs>
        <form className="space-y-2 border-t border-ink-500 pt-3" onSubmit={(e) => { e.preventDefault(); if (noteText.trim()) add.mutate({ kind: "note", text: noteText }); }}>
          <label className="label flex items-center gap-1" htmlFor="note"><StickyNote className="h-3 w-3" /> Your own note</label>
          <Input id="note" value={noteText} onChange={(e) => setNoteText(e.target.value)} maxLength={300} placeholder="e.g. Who paid for the siding?" />
          <Button type="submit" size="sm" className="w-full" disabled={!noteText.trim()}>Pin note</Button>
        </form>
        <div className="space-y-2 border-t border-ink-500 pt-3">
          <Button variant={connect ? "brass" : "outline"} className="w-full" aria-pressed={connect} onClick={() => { setConnect((c) => !c); setSel(null); }}><Link2 className="h-4 w-4" /> {connect ? "Connecting… pick two items" : "Connect two items"}</Button>
          <Button variant="ghost" className="w-full" disabled={!sel || connect} onClick={() => sel && del.mutate(sel)}><Trash2 className="h-4 w-4" /> Remove selected</Button>
        </div>
      </aside>

      <div className="space-y-3">
        {items.length === 0 && <Empty title="An empty board">Pin clues, people and places from the panel, then connect what belongs together.</Empty>}
        <div className="relative h-[70vh] min-h-[460px] overflow-auto rounded-xl border border-ink-500 shadow-card"
          style={{ backgroundColor: "#131a26", backgroundImage: "radial-gradient(#27324599 1px, transparent 1px)", backgroundSize: "22px 22px" }}
          onPointerMove={onMove} onPointerUp={onUp} data-testid="board-canvas">
          <div className="relative" style={{ width: 1400, height: 900 }}>
            <svg className="pointer-events-none absolute inset-0 h-full w-full" aria-hidden>
              {board.data!.links.map((l) => {
                const a = byId.get(l.from), b = byId.get(l.to); if (!a || !b) return null;
                const pa = pos(a), pb = pos(b);
                const x1 = pa.x + W / 2, y1 = pa.y + H / 2, x2 = pb.x + W / 2, y2 = pb.y + H / 2;
                const col = l.relation === "contradicts" && l.validated ? "#e0634e" : l.validated ? "#d9b572" : "#6f87a6";
                return (
                  <g key={l.id}>
                    <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={col} strokeWidth={l.validated ? 2.6 : 1.6} strokeDasharray={l.validated ? undefined : "6 5"} />
                    <circle cx={x1} cy={y1} r="4" fill={col} /><circle cx={x2} cy={y2} r="4" fill={col} />
                    <text x={(x1 + x2) / 2} y={(y1 + y2) / 2 - 6} textAnchor="middle" fontSize="11" fill={col} style={{ paintOrder: "stroke" }} stroke="#131a26" strokeWidth="3">{REL_LABEL[l.relation] ?? l.relation}{l.validated ? " ✓" : ""}</text>
                  </g>
                );
              })}
            </svg>
            {items.map((it) => {
              const p = pos(it);
              return (
                <div key={it.id} role="button" tabIndex={0} aria-label={`${titleCase(it.kind)}: ${it.label}${sel === it.id ? " (selected)" : ""}`} aria-pressed={sel === it.id}
                  data-testid={`board-item-${it.ref_key}`}
                  onPointerDown={(e) => onDown(e, it)} onClick={() => click(it)} onKeyDown={(e) => onKey(e, it)}
                  className={cn("absolute cursor-grab touch-none select-none rounded-md border p-2 text-left shadow-card active:cursor-grabbing",
                    it.kind === "evidence" ? "paper-card" : it.kind === "note" ? "border-amber-deep/60 bg-amber-glow/90 text-ink-900" : "border-brass-dark bg-ink-600 text-paper",
                    sel === it.id && "ring-2 ring-sky-300")}
                  style={{ left: p.x, top: p.y, width: W, minHeight: H }}>
                  <span className="mb-0.5 flex items-center gap-1 text-[10px] uppercase tracking-wider opacity-70">
                    {it.kind === "person" ? <User className="h-3 w-3" /> : it.kind === "location" ? <MapPin className="h-3 w-3" /> : it.kind === "note" ? <StickyNote className="h-3 w-3" /> : <Pin className="h-3 w-3" />}{it.kind}
                  </span>
                  <span className="block font-display text-[15px] font-bold leading-tight">{it.label}</span>
                  {it.predicted_category && <span className="mt-1 block text-[10px] opacity-75" title="Predicted by the clue-classification model">ML guess: {titleCase(it.predicted_category)}</span>}
                </div>
              );
            })}
          </div>
        </div>
        {board.data!.links.length > 0 && (
          <ul className="flex flex-wrap gap-2 text-xs">{board.data!.links.map((l) => (
            <li key={l.id} className="chip">{byId.get(l.from)?.label.slice(0, 22)} <b className={l.validated ? "text-brass-light" : "text-sky-300"}>{REL_LABEL[l.relation]}</b> {byId.get(l.to)?.label.slice(0, 22)}
              <button aria-label="Remove connection" className="ml-1 text-paper-mute hover:text-blood-light" onClick={() => unlink.mutate(l.id)}>×</button></li>
          ))}</ul>
        )}
        <p className="text-xs text-paper-mute">Solid brass lines are backed by the record. Dashed blue lines are your theory. Drag cards, or focus one and use the arrow keys.</p>
      </div>

      <Dialog open={!!pair} onOpenChange={(o) => !o && setPair(null)}>
        {pair && (
          <DialogContent title="How are these connected?" description={`${byId.get(pair[0])?.label}  →  ${byId.get(pair[1])?.label}`}>
            <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); link.mutate(); }}>
              <Select value={relation} onChange={(e) => setRelation(e.target.value)} aria-label="Connection type">{(board.data?.relations ?? []).map((r) => <option key={r} value={r}>{REL_LABEL[r] ?? r}</option>)}</Select>
              <Input value={note} onChange={(e) => setNote(e.target.value)} maxLength={300} placeholder="Why? (optional)" aria-label="Why" />
              <Button type="submit" variant="brass" loading={link.isPending}>Connect</Button>
            </form>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}

function PinRow({ icon, label, disabled, onClick }: { icon: React.ReactNode; label: string; disabled: boolean; onClick: () => void }) {
  return <button disabled={disabled} onClick={onClick} className="flex w-full items-center gap-2 rounded px-2 py-1.5 text-left text-sm text-paper-dim hover:bg-ink-600 disabled:opacity-40">{icon}<span className="truncate">{label}</span>{disabled && <Badge className="ml-auto">pinned</Badge>}</button>;
}

function Theories() {
  const sid = useSid();
  const qc = useQueryClient();
  const toast = useToast();
  const opts = useQuery({ queryKey: keys.options(sid), queryFn: () => api.accusationOptions(sid) });
  const saved = useQuery({ queryKey: keys.hypotheses(sid), queryFn: () => api.hypotheses(sid) });
  const [culprit, setCulprit] = useState("");
  const [motive, setMotive] = useState("");
  const [title, setTitle] = useState("");
  const evalQ = useQuery({ queryKey: ["hyp-eval", sid, culprit, motive], enabled: !!culprit, queryFn: () => api.evaluate(sid, culprit || null, motive || null) });
  const save = useMutation({
    mutationFn: () => api.saveHypothesis(sid, { title: title || `${opts.data?.suspects.find((s) => s.key === culprit)?.name}'s theory`, culprit_key: culprit, motive_key: motive || null, evidence_for: evalQ.data?.supporting.map((s) => s.key) ?? [], evidence_against: evalQ.data?.opposing.map((s) => s.key) ?? [] }),
    onSuccess: () => { void qc.invalidateQueries({ queryKey: keys.hypotheses(sid) }); setTitle(""); toast({ title: "Theory saved", tone: "success" }); },
    onError: (e) => toast({ title: "Couldn't save", body: errorMessage(e), tone: "warn" }),
  });
  const del = useMutation({ mutationFn: (id: string) => api.deleteHypothesis(sid, id), onSuccess: () => qc.invalidateQueries({ queryKey: keys.hypotheses(sid) }) });
  if (opts.isLoading) return <Skeleton className="h-64" />;
  if (opts.error) return <ErrorState error={opts.error} onRetry={() => opts.refetch()} />;
  const ev = evalQ.data;
  return (
    <div className="grid gap-5 lg:grid-cols-2">
      <section className="panel space-y-3 p-5">
        <h2 className="panel-title">Weigh a theory</h2>
        <label className="block text-sm">Suspect<Select className="mt-1" value={culprit} onChange={(e) => setCulprit(e.target.value)}><option value="">Choose…</option>{opts.data!.suspects.map((s) => <option key={s.key} value={s.key}>{s.name} — {s.role}</option>)}</Select></label>
        <label className="block text-sm">Motive<Select className="mt-1" value={motive} onChange={(e) => setMotive(e.target.value)}><option value="">(not decided)</option>{opts.data!.motives.map((m) => <option key={m.key} value={m.key}>{m.label}</option>)}</Select></label>
        {evalQ.isFetching && <p className="text-sm text-paper-mute">Weighing the evidence…</p>}
        {ev && (
          <div className="space-y-3" aria-live="polite">
            <div><div className="flex justify-between text-xs"><span className="label">Weight of evidence you hold</span><span>{ev.strength}/100</span></div><Progress value={ev.strength} tone={ev.strength > 55 ? "green" : "brass"} className="mt-1" /><p className="mt-1 text-[11px] text-paper-mute">This measures your evidence, not whether the theory is true.</p></div>
            <EvList title="Points toward" tone="red" rows={ev.supporting} /><EvList title="Counts against" tone="green" rows={ev.opposing} /><EvList title="Undermined claims" tone="amber" rows={ev.undermined_claims} />
            {ev.motive_fit && <p className="text-sm"><Badge tone={ev.motive_fit.applies_to_suspect ? "green" : "neutral"}>{ev.motive_fit.applies_to_suspect ? "Motive fits this person" : "Motive doesn't obviously fit"}</Badge> {ev.motive_fit.supporting_evidence.length ? `Backed by ${ev.motive_fit.supporting_evidence.map((x) => x.name).join(", ")}` : "No evidence yet backs this motive."}</p>}
            {ev.open_questions.length > 0 && <div><p className="label mb-1">Open questions</p><ul className="list-disc space-y-1 pl-5 text-sm text-paper-dim">{ev.open_questions.map((q, i) => <li key={i}>{q}</li>)}</ul></div>}
            <div className="flex gap-2"><Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Name this theory" maxLength={200} aria-label="Theory name" /><Button variant="brass" loading={save.isPending} onClick={() => save.mutate()}>Save</Button></div>
          </div>
        )}
      </section>
      <section className="space-y-3">
        <h2 className="panel-title">Saved theories</h2>
        {saved.data?.length ? saved.data.map((h) => (
          <article key={h.id} className="panel p-4"><div className="flex items-start justify-between gap-2"><div><h3 className="font-display text-lg">{h.title}</h3><p className="text-xs text-paper-mute">{opts.data!.suspects.find((s) => s.key === h.culprit_key)?.name ?? "—"} · {opts.data!.motives.find((m) => m.key === h.motive_key)?.label ?? "motive open"}</p></div>
            <Button size="icon" variant="ghost" aria-label={`Delete ${h.title}`} onClick={() => del.mutate(h.id)}><Trash2 className="h-4 w-4" /></Button></div>
            <Progress value={(h.evaluation as { strength?: number })?.strength ?? 0} className="mt-3" /></article>
        )) : <Empty title="No saved theories">Weigh a suspect and save it to compare against others.</Empty>}
      </section>
    </div>
  );
}
function EvList({ title, rows, tone }: { title: string; rows: { key: string; name: string; note: string }[]; tone: "red" | "green" | "amber" }) {
  if (!rows.length) return null;
  return <div><Badge tone={tone}>{title}</Badge><ul className="mt-1 space-y-1 text-sm">{rows.map((r) => <li key={r.key}>{r.name}<span className="text-paper-mute"> — {r.note}</span></li>)}</ul></div>;
}
