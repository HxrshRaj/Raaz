import { useMutation, useQuery } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { Archive, FlaskConical, FolderOpen, LogOut, Settings as Cog, Volume2, VolumeX, Play } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AuthDialog } from "@/components/AuthDialog";
import { Rain } from "@/components/Rain";
import { SceneArt } from "@/components/SceneArt";
import { Badge, Button, Dialog, DialogContent } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { lastSession, useAuth, useSettings } from "@/lib/app-context";
import { sound } from "@/lib/audio";
import { cn } from "@/lib/utils";

export default function Title() {
  const nav = useNavigate();
  const { user, signOut } = useAuth();
  const { settings, update } = useSettings();
  const [authOpen, setAuthOpen] = useState(false);
  const [newOpen, setNewOpen] = useState(false);
  const [pending, setPending] = useState<"continue" | "new" | "archive" | null>(null);
  const [mode, setMode] = useState<"standard" | "demo">("standard");
  const [err, setErr] = useState<string | null>(null);

  const info = useQuery({ queryKey: ["system"], queryFn: api.systemInfo, enabled: !!user });
  const resumeId = user ? lastSession.get() : null;
  const create = useMutation({
    mutationFn: () => api.createSession("aakhri_gaadi", mode),
    onSuccess: (o) => { lastSession.set(o.id); nav(`/play/${o.id}`); },
    onError: (e) => setErr(errorMessage(e)),
  });

  const gate = (what: "continue" | "new" | "archive", fn: () => void) => () => {
    sound.click();
    if (!settings.muted && settings.ambient) sound.start();
    if (!user) { setPending(what); setAuthOpen(true); return; }
    fn();
  };
  const actions = {
    continue: () => (resumeId ? nav(`/play/${resumeId}`) : nav("/archive")),
    new: () => setNewOpen(true),
    archive: () => nav("/archive"),
  };

  const items = [
    { key: "continue", label: "Continue Investigation", icon: Play, onClick: gate("continue", actions.continue), primary: true, hint: resumeId ? "Resume where you left off" : "Pick up a saved investigation" },
    { key: "new", label: "New Case", icon: FolderOpen, onClick: gate("new", actions.new), hint: "Aakhri Gaadi — The Last Train" },
    { key: "archive", label: "Case Archive", icon: Archive, onClick: gate("archive", actions.archive), hint: "Your investigations and results" },
  ] as const;

  return (
    <div className="relative min-h-screen overflow-hidden">
      <SceneArt scene="platform" className="absolute inset-0 h-full w-full opacity-60" />
      <Rain count={110} />
      <div className="vignette" />
      <div className="relative z-10 mx-auto flex min-h-screen max-w-5xl flex-col items-center justify-center px-6 py-12 text-center">
        <motion.div initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 1 }}>
          <h1 className="font-deva text-7xl leading-none text-brass-light drop-shadow-[0_0_24px_rgba(242,169,78,0.35)] sm:text-8xl" lang="hi">राज़</h1>
          <p className="mt-2 font-display text-5xl tracking-[0.5em] text-paper sm:text-6xl">RAAZ</p>
          <p className="mt-1 font-display text-xl italic text-paper-dim">The AI Detective</p>
          <p className="mt-6 font-display text-lg text-amber-glow" lang="hi-Latn">Har raaz ke peeche ek kahaani hai.</p>
          <p className="text-sm text-paper-mute">Every secret has a story behind it.</p>
        </motion.div>

        <nav aria-label="Main menu" className="mt-12 flex w-full max-w-sm flex-col gap-3">
          {items.map((it, i) => (
            <motion.div key={it.key} initial={{ opacity: 0, x: -14 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.35 + i * 0.12 }}>
              <button onClick={it.onClick}
                className={cn("group flex w-full items-center gap-3 rounded-lg border px-5 py-3.5 text-left backdrop-blur transition-all",
                  "primary" in it && it.primary ? "border-brass bg-brass/15 hover:bg-brass/25" : "border-ink-500 bg-ink-800/70 hover:border-brass-dark hover:bg-ink-700")}>
                <it.icon className="h-5 w-5 text-brass-light" aria-hidden />
                <span><span className="block font-display text-xl text-paper">{it.label}</span><span className="block text-xs text-paper-mute">{it.hint}</span></span>
              </button>
            </motion.div>
          ))}
          <div className="mt-1 flex items-center justify-center gap-2">
            <Button variant="ghost" onClick={() => nav("/settings")}><Cog className="h-4 w-4" /> Settings</Button>
            <Button variant="ghost" aria-pressed={!settings.muted} onClick={() => update({ muted: !settings.muted })}>
              {settings.muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />} {settings.muted ? "Sound off" : "Sound on"}
            </Button>
            {user && <Button variant="ghost" asChild><Link to="/workbench"><FlaskConical className="h-4 w-4" /> ML</Link></Button>}
          </div>
        </nav>

        <footer className="mt-10 space-y-1 text-xs text-paper-mute">
          {user ? (
            <p>Signed in as <strong className="text-paper-dim">{user.display_name}</strong>{user.is_guest && " (guest)"} ·{" "}
              <button className="underline hover:text-paper" onClick={() => { signOut(); lastSession.set(null); }}><LogOut className="mr-1 inline h-3 w-3" />Sign out</button></p>
          ) : <p>Sign in or play as a guest to begin.</p>}
          {info.data && <p><Badge tone={info.data.llm.enabled ? "green" : "amber"}>{info.data.llm.enabled ? `AI dialogue: ${info.data.llm.provider}` : "AI dialogue off — scripted fallback"}</Badge></p>}
          <p>Fictional story. Original artwork. Devgarh is not a real city.</p>
        </footer>
      </div>

      <AuthDialog open={authOpen} onOpenChange={setAuthOpen} onDone={() => { const p = pending; setPending(null); if (p) setTimeout(actions[p], 0); }} />
      <Dialog open={newOpen} onOpenChange={setNewOpen}>
        <DialogContent title="Aakhri Gaadi — The Last Train" description="Devgarh Junction, a monsoon night. A founder is dead in a locked carriage.">
          <div className="space-y-4">
            <fieldset className="space-y-2">
              <legend className="label mb-1">Mode</legend>
              {([["standard", "Standard", "Full game. NPCs speak through the configured AI provider when available."], ["demo", "Demo", "Same case and engine. Clearly labelled; if no AI provider is configured, suspects use authored fallback lines."]] as const).map(([v, t, d]) => (
                <label key={v} className={cn("flex cursor-pointer gap-3 rounded-md border p-3", mode === v ? "border-brass bg-brass/10" : "border-ink-500")}>
                  <input type="radio" name="mode" className="mt-1 accent-amber-500" checked={mode === v} onChange={() => setMode(v)} />
                  <span><span className="block font-medium">{t}</span><span className="text-sm text-paper-mute">{d}</span></span>
                </label>
              ))}
            </fieldset>
            {info.data && !info.data.llm.enabled && <p className="rounded-md border border-amber-deep/50 bg-amber-glow/5 p-3 text-sm text-amber-glow">{info.data.llm.label}</p>}
            {err && <p role="alert" className="text-sm text-blood-light">{err}</p>}
            <Button variant="brass" size="lg" loading={create.isPending} onClick={() => { setErr(null); create.mutate(); }}>Open the case file</Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
