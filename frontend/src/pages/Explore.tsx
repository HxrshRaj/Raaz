import { useMutation, useQuery } from "@tanstack/react-query";
import { Camera, ChevronLeft, FileText, Key, Lock, Monitor, Phone, Search, Ticket, Eye, Train, Armchair, Cog, Trash2, Book, Briefcase, ShieldQuestion, Droplets, DoorClosed, Coffee, Printer, Archive, User } from "lucide-react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useState } from "react";
import { EvidenceCard } from "@/components/EvidenceCard";
import { Rain } from "@/components/Rain";
import { SceneArt } from "@/components/SceneArt";
import { useToast } from "@/components/Toasts";
import { Badge, Button, ErrorState, Skeleton } from "@/components/ui";
import { keys, useOverview, useRefreshGame, useSid } from "@/hooks/game";
import { api, errorMessage } from "@/lib/api";
import { sound } from "@/lib/audio";
import type { z } from "zod";
import type { InspectResult } from "@/lib/schemas";
import { cn } from "@/lib/utils";

const icons: Record<string, typeof Search> = {
  clock: Eye, board: FileText, body: User, watch: Eye, phone: Phone, desk: Briefcase, ticket: Ticket, chair: Armchair, cup: Coffee,
  case: Briefcase, lock: Lock, book: Book, key: Key, drawer: Archive, printer: Printer, tray: FileText, window: Eye, bin: Trash2,
  news: FileText, monitor: Monitor, pc: Monitor, camera: Camera, gate: DoorClosed, drain: Droplets, doc: FileText, folder: Archive,
  train: Train, cog: Cog, search: Search,
};

export function ExploreIndex() {
  const sid = useSid();
  const { data } = useOverview(sid);
  const nav = useNavigate();
  if (!data) return null;
  return (
    <div className="space-y-4">
      <h1 className="font-display text-3xl">Where to?</h1>
      <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        {data.locations.map((l) => (
          <li key={l.key}>
            <button disabled={l.locked} onClick={() => nav(`/play/${sid}/explore/${l.key}`)} className={cn("group w-full overflow-hidden rounded-lg border bg-ink-800/70 text-left transition", l.locked ? "cursor-not-allowed border-ink-500 opacity-60" : "border-ink-500 hover:border-brass")}>
              <div className="h-28"><SceneArt scene={l.scene} className={cn("h-full w-full", l.locked && "grayscale")} /></div>
              <div className="p-3"><p className="flex items-center gap-2 font-medium">{l.locked && <Lock className="h-3.5 w-3.5" />}{l.name}</p>
                <p className="text-xs text-paper-mute">{l.locked ? l.unlock_hint ? "Locked" : "Locked" : `${l.searched_hotspots}/${l.visible_hotspots} details searched`}</p></div>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function ExploreLocation() {
  const sid = useSid();
  const { loc = "" } = useParams();
  const toast = useToast();
  const refresh = useRefreshGame(sid);
  const q = useQuery({ queryKey: keys.location(sid, loc), queryFn: () => api.location(sid, loc) });
  const [result, setResult] = useState<{ title: string; res: z.infer<typeof InspectResult> } | null>(null);
  const [focus, setFocus] = useState<string | null>(null);
  const inspect = useMutation({
    mutationFn: (h: { key: string; label: string }) => api.inspect(sid, loc, h.key).then((res) => ({ title: h.label, res })),
    onSuccess: ({ title, res }) => {
      setResult({ title, res });
      refresh();
      if (res.new_evidence.length) { sound.discover(); toast({ title: `Found: ${res.new_evidence.map((e) => e.name).join(", ")}`, body: "Added to your evidence inventory.", tone: "clue" }); }
      else sound.paper();
      res.unlocked_locations.forEach((u) => toast({ title: `New place unlocked: ${u.name}`, tone: "success" }));
    },
    onError: (e) => toast({ title: "Couldn't search there", body: errorMessage(e), tone: "warn" }),
  });
  if (q.isLoading) return <Skeleton className="aspect-[5/3] w-full" />;
  if (q.error) return <div className="space-y-3"><ErrorState error={q.error} onRetry={() => q.refetch()} /><Button asChild variant="outline"><Link to={`/play/${sid}/explore`}>Back to the map</Link></Button></div>;
  const d = q.data!;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_340px]">
      <section aria-label={d.name} className="space-y-3">
        <div className="flex items-center gap-3"><Button asChild size="sm" variant="ghost"><Link to={`/play/${sid}/explore`}><ChevronLeft className="h-4 w-4" /> Map</Link></Button>
          <h1 className="font-display text-2xl sm:text-3xl">{d.name}</h1>{d.off_site && <Badge tone="blue">Off-site</Badge>}</div>
        <div className="relative aspect-[5/3] w-full overflow-hidden rounded-xl border border-ink-500 shadow-card">
          <SceneArt scene={d.scene} className="absolute inset-0 h-full w-full" />
          <Rain count={50} opacity={0.7} />
          <div className="vignette" />
          {d.hotspots.map((h) => {
            const Ic = icons[h.icon] ?? ShieldQuestion;
            return (
              <button key={h.key} onClick={() => { sound.click(); setFocus(h.key); inspect.mutate({ key: h.key, label: h.label }); }}
                style={{ left: `${h.x}%`, top: `${h.y}%`, width: `${Math.max(h.w, 7)}%`, height: `${Math.max(h.h, 9)}%` }}
                aria-label={`${h.label}${h.searched ? " (searched)" : ""}`} data-testid={`hotspot-${h.key}`}
                className="group absolute -translate-x-1/2 -translate-y-1/2 rounded-lg focus-visible:outline-amber-glow">
                <span className="absolute inset-0 flex items-center justify-center">
                  {!h.searched && <span className="absolute h-8 w-8 animate-pulseRing rounded-full border border-amber-glow" aria-hidden />}
                  <span className={cn("relative flex h-8 w-8 items-center justify-center rounded-full border backdrop-blur transition group-hover:scale-110", h.searched ? "border-ink-500 bg-ink-800/80 text-paper-mute" : "border-amber-glow bg-ink-900/70 text-amber-glow shadow-lamp")}>
                    {inspect.isPending && focus === h.key ? <Cog className="h-4 w-4 animate-spin" /> : <Ic className="h-4 w-4" aria-hidden />}
                  </span>
                </span>
                <span className="pointer-events-none absolute left-1/2 top-full z-10 mt-1 -translate-x-1/2 whitespace-nowrap rounded bg-ink-900/95 px-2 py-0.5 text-xs text-paper opacity-0 shadow-card transition group-hover:opacity-100 group-focus-visible:opacity-100">{h.label}</span>
              </button>
            );
          })}
        </div>
        <p className="text-sm text-paper-mute">{d.description}</p>
        {d.hotspots.length === 0 && <p className="text-sm text-paper-mute">Nothing here to search.</p>}
      </section>
      <aside className="space-y-4" aria-live="polite">
        <div className="panel min-h-[200px] p-5">
          <h2 className="panel-title mb-2">{result ? result.title : "Look around"}</h2>
          {!result ? <p className="text-sm text-paper-mute">Click a glowing marker to search it. Brass rings mean something here hasn't been searched yet.</p> : (
            <div className="space-y-3">
              <p className="typewriter">{result.res.narration}</p>
              {result.res.new_evidence.length === 0 && <p className="text-sm text-paper-mute">Nothing new. You've already taken what's here.</p>}
              {result.res.new_evidence.map((e) => <div key={e.key} className="animate-rise"><Badge tone="amber" className="mb-1">New evidence</Badge><EvidenceCard ev={e} /></div>)}
              {result.res.new_evidence.length > 0 && <Button asChild size="sm" variant="outline"><Link to={`/play/${sid}/evidence`}>Open inventory</Link></Button>}
            </div>
          )}
        </div>
      </aside>
    </div>
  );
}
