import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, LogOut } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Rain } from "@/components/Rain";
import { Badge, Button, Empty, ErrorState, Progress, Skeleton } from "@/components/ui";
import { api } from "@/lib/api";
import { lastSession, useAuth, useSettings } from "@/lib/app-context";
import { sound } from "@/lib/audio";
import { fmtDateTime, titleCase } from "@/lib/utils";

function Page({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="relative min-h-screen">
      <div className="pointer-events-none absolute inset-0 opacity-50" aria-hidden><Rain count={50} opacity={0.5} /></div>
      <div className="relative mx-auto max-w-4xl px-4 py-8">
        <Button asChild variant="ghost" size="sm"><Link to="/"><ChevronLeft className="h-4 w-4" /> Title</Link></Button>
        <h1 className="mt-2 font-display text-4xl">{title}</h1>
        <div className="mt-6">{children}</div>
      </div>
    </div>
  );
}

export function Archive() {
  const nav = useNavigate();
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["sessions"], queryFn: api.sessions, enabled: !!user });
  const prog = useQuery({ queryKey: ["progress"], queryFn: api.progress, enabled: !!user });
  if (!user) return <Page title="Case archive"><Empty title="Sign in to see your investigations"><Link className="underline" to="/">Back to the title screen</Link></Empty></Page>;
  return (
    <Page title="Case archive">
      {prog.data && <p className="mb-4 text-sm text-paper-mute">{prog.data.sessions} investigation(s) · {prog.data.solved} solved{prog.data.best_score != null && ` · best score ${prog.data.best_score}`}</p>}
      {q.isLoading && <Skeleton className="h-32" />}
      {q.error && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {q.data?.length === 0 && <Empty title="No investigations yet">Start a new case from the title screen.</Empty>}
      <ul className="space-y-3">
        {q.data?.map((s) => (
          <li key={s.id} className="panel flex flex-wrap items-center gap-4 p-4">
            <div className="min-w-0 flex-1"><h2 className="font-display text-xl">{s.case_title}</h2>
              <p className="text-xs text-paper-mute">Started {fmtDateTime(s.created_at)} · last played {fmtDateTime(s.updated_at)}</p>
              <div className="mt-2 flex flex-wrap items-center gap-2"><Badge tone={s.status === "solved" ? "green" : s.status === "closed_unsolved" ? "red" : "neutral"}>{titleCase(s.status.replace("closed_unsolved", "gone cold"))}</Badge>
                {s.mode === "demo" && <Badge tone="amber">Demo</Badge>}<Badge>{s.progress.evidence} evidence</Badge><Badge>{s.attempts} accusation(s)</Badge>{s.score != null && <Badge tone="brass">Score {s.score}</Badge>}</div>
              <Progress value={s.progress.percent} className="mt-3 max-w-xs" /></div>
            <Button variant="brass" onClick={() => { lastSession.set(s.id); nav(`/play/${s.id}`); }}>{s.status === "solved" ? "Review" : "Resume"}</Button>
          </li>
        ))}
      </ul>
    </Page>
  );
}

export function SettingsPage() {
  const { settings, update } = useSettings();
  const { user, signOut } = useAuth();
  const info = useQuery({ queryKey: ["system"], queryFn: api.systemInfo, enabled: !!user });
  const row = "flex items-center justify-between gap-4 rounded-lg border border-ink-500 bg-ink-800/60 p-4";
  return (
    <Page title="Settings">
      <div className="space-y-3">
        <label className={row}><span><span className="block font-medium">Sound</span><span className="text-sm text-paper-mute">Procedural rain and ambience. Off by default.</span></span>
          <input type="checkbox" className="h-5 w-5 accent-amber-500" checked={!settings.muted} onChange={(e) => update({ muted: !e.target.checked })} /></label>
        <label className={row}><span><span className="block font-medium">Ambient rain &amp; drone</span></span><input type="checkbox" className="h-5 w-5 accent-amber-500" checked={settings.ambient} onChange={(e) => update({ ambient: e.target.checked })} /></label>
        <label className={row}><span><span className="block font-medium">Interface sounds</span></span><input type="checkbox" className="h-5 w-5 accent-amber-500" checked={settings.sfx} onChange={(e) => update({ sfx: e.target.checked })} /></label>
        <label className={row}><span className="block font-medium">Volume</span><input aria-label="Volume" type="range" min={0} max={1} step={0.05} value={settings.volume} onChange={(e) => update({ volume: Number(e.target.value) })} className="w-48 accent-amber-500" /></label>
        <label className={row}><span><span className="block font-medium">Reduce motion</span><span className="text-sm text-paper-mute">Stops rain, flicker and pulsing. Your OS preference is also respected.</span></span><input type="checkbox" className="h-5 w-5 accent-amber-500" checked={settings.reduceMotion} onChange={(e) => update({ reduceMotion: e.target.checked })} /></label>
        <label className={row}><span className="block font-medium">Typewriter dialogue</span><input type="checkbox" className="h-5 w-5 accent-amber-500" checked={settings.typewriter} onChange={(e) => update({ typewriter: e.target.checked })} /></label>
        <div className={row}><span><span className="block font-medium">AI dialogue</span><span className="text-sm text-paper-mute">{info.data ? info.data.llm.label : user ? "Checking…" : "Sign in to see this server's configuration."}</span></span>{info.data && <Badge tone={info.data.llm.enabled ? "green" : "amber"}>{info.data.llm.enabled ? "On" : "Fallback"}</Badge>}</div>
        <div className="flex gap-2"><Button onClick={() => sound.discover()}>Test sound</Button>{user && <Button variant="outline" onClick={() => { signOut(); lastSession.set(null); }}><LogOut className="h-4 w-4" /> Sign out</Button>}</div>
        <p className="text-xs text-paper-mute">Settings are stored only in this browser. Your investigation itself is saved on the server.</p>
      </div>
    </Page>
  );
}

export function NotFound() {
  return <Page title="Nothing here"><Empty title="That page doesn't exist"><Link className="underline" to="/">Return to the title screen</Link></Empty></Page>;
}
