import { useMutation } from "@tanstack/react-query";
import { Link2, Search, Swords } from "lucide-react";
import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { EvidenceCard, EvidenceDetail } from "@/components/EvidenceCard";
import { useToast } from "@/components/Toasts";
import { Badge, Button, Dialog, DialogContent, Empty, ErrorState, Input, Select, Skeleton, Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui";
import { useContradictions, useEvidence, useRefreshGame, useSid } from "@/hooks/game";
import { api, errorMessage } from "@/lib/api";
import { sound } from "@/lib/audio";
import { titleCase } from "@/lib/utils";

const CATS = ["timeline", "financial", "access", "testimony", "physical", "digital"];

export default function EvidencePage() {
  const sid = useSid();
  const ev = useEvidence(sid);
  const cons = useContradictions(sid);
  const refresh = useRefreshGame(sid);
  const toast = useToast();
  const [params, setParams] = useSearchParams();
  const [text, setText] = useState("");
  const [cat, setCat] = useState("all");
  const [onlyNew, setOnlyNew] = useState(false);
  const [pair, setPair] = useState<string[]>([]);
  const open = params.get("open");

  const examine = useMutation({
    mutationFn: (k: string) => api.examine(sid, k),
    onSuccess: (r) => { refresh(); sound.paper(); toast({ title: r.first_examination ? "Examined closely" : "Already examined", body: r.evidence.name, tone: "info" }); },
    onError: (e) => toast({ title: "Couldn't examine", body: errorMessage(e), tone: "warn" }),
  });
  const check = useMutation({
    mutationFn: () => api.checkContradiction(sid, pair[0], pair[1]),
    onSuccess: (r) => {
      refresh();
      if (r.established) { sound.alert(); toast({ title: r.newly_found ? "Contradiction established" : "Already established", body: r.contradiction?.title, tone: "clue" }); setPair([]); }
      else toast({ title: "No contradiction", body: r.message, tone: "info" });
    },
    onError: (e) => toast({ title: "Check failed", body: errorMessage(e), tone: "warn" }),
  });

  const list = useMemo(() => (ev.data ?? []).filter((e) =>
    (cat === "all" || e.category === cat) && (!onlyNew || !e.examined) &&
    (!text || `${e.name} ${e.description}`.toLowerCase().includes(text.toLowerCase()))), [ev.data, cat, onlyNew, text]);
  const selected = ev.data?.find((e) => e.key === open) ?? null;
  const togglePair = (k: string) => setPair((p) => (p.includes(k) ? p.filter((x) => x !== k) : [...p.slice(-1), k]));

  if (ev.isLoading) return <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-32" />)}</div>;
  if (ev.error) return <ErrorState error={ev.error} onRetry={() => ev.refetch()} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div><h1 className="font-display text-3xl">Evidence inventory</h1><p className="text-sm text-paper-mute">{ev.data!.length} item(s) · {ev.data!.filter((e) => !e.examined && !e.is_testimony).length} unexamined</p></div>
      </div>
      <Tabs defaultValue="items">
        <TabsList><TabsTrigger value="items">Items</TabsTrigger><TabsTrigger value="contradictions">Contradictions ({cons.data?.length ?? 0})</TabsTrigger></TabsList>
        <TabsContent value="items" className="mt-4 space-y-4">
          <div className="grid gap-2 sm:grid-cols-[1fr_180px_auto]">
            <label className="relative"><Search className="absolute left-3 top-3 h-4 w-4 text-paper-mute" aria-hidden /><span className="sr-only">Search evidence</span>
              <Input className="pl-9" placeholder="Search evidence…" value={text} onChange={(e) => setText(e.target.value)} /></label>
            <label><span className="sr-only">Category</span><Select value={cat} onChange={(e) => setCat(e.target.value)}><option value="all">All categories</option>{CATS.map((c) => <option key={c} value={c}>{titleCase(c)}</option>)}</Select></label>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="accent-amber-500" checked={onlyNew} onChange={(e) => setOnlyNew(e.target.checked)} /> Unexamined only</label>
          </div>
          <div className="flex flex-wrap items-center gap-2 rounded-lg border border-ink-500 bg-ink-800/60 p-3 text-sm" aria-live="polite">
            <Swords className="h-4 w-4 text-blood-light" aria-hidden />
            <span className="text-paper-dim">Think two items conflict? Mark both, then test it.</span>
            {pair.map((k) => <Badge key={k} tone="amber">{ev.data!.find((e) => e.key === k)?.name}</Badge>)}
            <Button size="sm" variant="danger" disabled={pair.length !== 2} loading={check.isPending} onClick={() => check.mutate()}>Test contradiction</Button>
            {pair.length > 0 && <Button size="sm" variant="ghost" onClick={() => setPair([])}>Clear</Button>}
          </div>
          {list.length === 0 ? <Empty title="No evidence matches">Explore the locations and interview suspects to fill your inventory.</Empty> : (
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {list.map((e) => (
                <li key={e.key} className="relative">
                  <EvidenceCard ev={e} selected={pair.includes(e.key)} onClick={() => setParams({ open: e.key })} />
                  <button aria-pressed={pair.includes(e.key)} aria-label={`Mark ${e.name} for contradiction test`} onClick={() => togglePair(e.key)}
                    className={`absolute right-2 top-2 rounded-full border p-1 ${pair.includes(e.key) ? "border-blood bg-blood text-white" : "border-brass-dark/60 bg-paper/80 text-brass-dark hover:bg-paper"}`}><Link2 className="h-3.5 w-3.5" /></button>
                </li>
              ))}
            </ul>
          )}
        </TabsContent>
        <TabsContent value="contradictions" className="mt-4">
          {!cons.data?.length ? <Empty title="No contradictions established">Compare statements with records, or present evidence to a suspect.</Empty> : (
            <ul className="space-y-3">{cons.data.map((c) => (
              <li key={c.key} className="panel border-blood/40 p-4"><div className="flex flex-wrap items-center gap-2"><Badge tone="red">Contradiction</Badge><Badge>{c.about_name}</Badge><span className="text-xs text-paper-mute">via {c.found_via?.split(":")[0]}</span></div>
                <h3 className="mt-2 font-display text-xl">{c.title}</h3><p className="mt-1 text-sm text-paper-dim">{c.explanation}</p>
                <p className="mt-2 text-xs text-paper-mute">{c.evidence.map((k) => ev.data!.find((e) => e.key === k)?.name ?? k).join("  ×  ")}</p></li>
            ))}</ul>
          )}
        </TabsContent>
      </Tabs>

      <Dialog open={!!selected} onOpenChange={(o) => !o && setParams({})}>
        {selected && (
          <DialogContent title={selected.name} className="w-[min(94vw,720px)]">
            <EvidenceDetail ev={selected} />
            <div className="mt-5 flex gap-2">
              {!selected.examined && <Button variant="brass" loading={examine.isPending} onClick={() => examine.mutate(selected.key)}><Search className="h-4 w-4" /> Examine closely</Button>}
              <Button variant={pair.includes(selected.key) ? "danger" : "outline"} onClick={() => togglePair(selected.key)}><Link2 className="h-4 w-4" /> {pair.includes(selected.key) ? "Unmark" : "Mark for contradiction test"}</Button>
            </div>
          </DialogContent>
        )}
      </Dialog>
    </div>
  );
}
