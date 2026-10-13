import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import { ChevronLeft, FileSearch, Send, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { EvidenceCard } from "@/components/EvidenceCard";
import { Portrait } from "@/components/Portrait";
import { useToast } from "@/components/Toasts";
import { Badge, Button, Dialog, DialogContent, ErrorState, Skeleton, Textarea } from "@/components/ui";
import { keys, useEvidence, useRefreshGame, useSid } from "@/hooks/game";
import { ApiError, api, errorMessage } from "@/lib/api";
import { useSettings } from "@/lib/app-context";
import { sound } from "@/lib/audio";
import type { z } from "zod";
import type { Conversation } from "@/lib/schemas";
import { cn, titleCase } from "@/lib/utils";

type Conv = z.infer<typeof Conversation>;
const moodTone = (m: string) => (["hostile", "cornered", "defensive"].includes(m) ? "red" : ["open", "cooperative"].includes(m) ? "green" : m === "anxious" ? "amber" : "neutral") as "red" | "green" | "amber" | "neutral";
const SUGGESTIONS = ["Where were you when the train arrived?", "Why do the records show a different time?", "Who else knew about the private carriage?", "Did you have any contact with Adrian tonight?"];

function Typed({ text, animate }: { text: string; animate: boolean }) {
  const [n, setN] = useState(animate ? 0 : text.length);
  useEffect(() => {
    if (!animate) { setN(text.length); return; }
    setN(0);
    const id = window.setInterval(() => setN((v) => { if (v >= text.length) { window.clearInterval(id); return v; } return v + 2; }), 16);
    return () => window.clearInterval(id);
  }, [text, animate]);
  const done = n >= text.length;
  return <span className={done ? "" : "typing"} onClick={() => setN(text.length)}>{text.slice(0, n)}</span>;
}

export default function Interview() {
  const sid = useSid();
  const { key = "" } = useParams();
  const qc = useQueryClient();
  const toast = useToast();
  const refresh = useRefreshGame(sid);
  const { settings } = useSettings();
  const conv = useQuery({ queryKey: keys.conversation(sid, key), queryFn: () => api.conversation(sid, key) });
  const evidence = useEvidence(sid);
  const [text, setText] = useState("");
  const [present, setPresent] = useState<string | null>(null);
  const [pickerOpen, setPickerOpen] = useState(false);
  const [pending, setPending] = useState<string | null>(null);
  const [freshId, setFreshId] = useState<string | null>(null);
  const logRef = useRef<HTMLDivElement>(null);

  const send = useMutation({
    mutationFn: (v: { text: string; ev: string | null }) => api.say(sid, key, v.text, v.ev),
    onMutate: (v) => setPending(v.text),
    onSuccess: (r) => {
      setPending(null); setText(""); setPresent(null); setFreshId(r.npc_message.id);
      qc.setQueryData<Conv>(keys.conversation(sid, key), (old) => old && ({ ...old, messages: [...old.messages, r.player_message, r.npc_message], state: r.state }));
      refresh();
      void qc.invalidateQueries({ queryKey: keys.evidence(sid) });
      r.new_evidence.forEach((e) => toast({ title: e.is_testimony ? `Statement recorded: ${e.name}` : `New evidence: ${e.name}`, tone: "clue" }));
      if (r.new_evidence.length) sound.discover();
      r.contradictions.forEach((c) => { sound.alert(); toast({ title: r.newly_found_contradictions.includes(c.key) ? "Contradiction exposed!" : "Contradiction (already known)", body: c.title, tone: "warn" }); });
      r.unlocked_locations.forEach((u) => toast({ title: `New place unlocked: ${u.name}`, tone: "success" }));
    },
    onError: (e) => {
      setPending(null);
      toast({ title: e instanceof ApiError && e.status === 409 ? "They're still answering" : "Couldn't ask that", body: errorMessage(e), tone: "warn" });
    },
  });

  useEffect(() => { logRef.current?.scrollTo({ top: logRef.current.scrollHeight, behavior: "smooth" }); }, [conv.data?.messages.length, pending]);

  if (conv.isLoading) return <Skeleton className="h-[70vh]" />;
  if (conv.error) return <ErrorState error={conv.error} onRetry={() => conv.refetch()} />;
  const c = conv.data!;
  const ev = evidence.data?.find((e) => e.key === present);
  const submit = () => { const t = text.trim() || (present ? "What can you tell me about this?" : ""); if (t && !send.isPending) send.mutate({ text: t, ev: present }); };
  const lastNpc = [...c.messages].reverse().find((m) => m.role === "npc");

  return (
    <div className="grid gap-5 lg:grid-cols-[260px_1fr]">
      <aside className="space-y-3">
        <Button asChild variant="ghost" size="sm"><Link to={`/play/${sid}/suspects/${key}`}><ChevronLeft className="h-4 w-4" /> Dossier</Link></Button>
        <div className="flex items-start gap-3 lg:block lg:space-y-3">
          <motion.div key={c.state.mood} initial={{ opacity: 0.6, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} className="w-28 shrink-0 sm:w-40 lg:w-full">
            <Portrait portrait={c.character.portrait} mood={c.state.mood} className="w-full rounded-xl border border-ink-500 shadow-card" label={`${c.character.name}, ${c.state.mood}`} />
          </motion.div>
          <div className="panel min-w-0 flex-1 space-y-2 p-3 text-sm">
            <h1 className="font-display text-2xl">{c.character.name}</h1><p className="text-xs text-paper-mute">{c.character.role}</p>
            <div className="flex flex-wrap gap-1.5" aria-label="Conversational state">
              <Badge tone={moodTone(c.state.mood)} data-testid="mood">{titleCase(c.state.mood)}</Badge>
              <Badge title="How much they trust you">Trust: {c.state.trust}</Badge><Badge>{c.state.turns} turns</Badge>
            </div>
            <p className={cn("rounded border p-2 text-[11px] leading-snug", c.llm.enabled ? "border-emerald-700/50 text-emerald-200" : "border-amber-deep/50 text-amber-glow")} data-testid="llm-label">{c.llm.label}</p>
          </div>
        </div>
      </aside>

      <section className="flex min-h-[70vh] flex-col rounded-xl border border-ink-500 bg-ink-800/70" aria-label={`Interrogation of ${c.character.name}`}>
        <div ref={logRef} role="log" aria-live="polite" aria-relevant="additions" className="flex-1 space-y-3 overflow-y-auto p-4 sm:p-6" style={{ maxHeight: "60vh" }}>
          {c.messages.map((m) => (
            <div key={m.id} className={cn("flex", m.role === "player" ? "justify-end" : "justify-start")}>
              <div className={cn("max-w-[85%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed", m.role === "player" ? "rounded-br-sm bg-brass/20 text-paper" : "rounded-bl-sm border border-ink-500 bg-ink-700 text-paper")}>
                {m.role === "player" && m.evidence_key && <p className="mb-1 flex items-center gap-1 text-xs text-amber-glow"><FileSearch className="h-3 w-3" /> presented: {evidence.data?.find((e) => e.key === m.evidence_key)?.name ?? m.evidence_key}</p>}
                {m.role === "npc" ? <Typed text={m.content} animate={settings.typewriter && !settings.reduceMotion && m.id === freshId && m.id === lastNpc?.id} /> : m.content}
                {m.role === "npc" && m.mode === "fallback" && <span className="mt-1 block text-[10px] uppercase tracking-wider text-amber-glow/80">scripted</span>}
              </div>
            </div>
          ))}
          {pending && (<><div className="flex justify-end"><div className="max-w-[85%] rounded-2xl rounded-br-sm bg-brass/10 px-4 py-2.5 text-paper-dim">{pending}</div></div>
            <div className="flex" role="status" aria-label={`${c.character.name} is thinking`}><div className="rounded-2xl rounded-bl-sm border border-ink-500 bg-ink-700 px-4 py-2.5 text-paper-mute typing">…</div></div></>)}
        </div>

        <div className="space-y-2 border-t border-ink-500 p-3 sm:p-4">
          {c.messages.length <= 1 && <div className="flex flex-wrap gap-1.5">{SUGGESTIONS.map((s) => <button key={s} className="chip hover:border-brass hover:text-paper" onClick={() => setText(s)}>{s}</button>)}</div>}
          {ev && (
            <div className="flex items-center gap-2 rounded-md border border-amber-deep/60 bg-amber-glow/5 p-2 text-sm"><FileSearch className="h-4 w-4 text-amber-glow" aria-hidden /> Presenting <strong>{ev.name}</strong>
              <button className="ml-auto text-paper-mute hover:text-paper" onClick={() => setPresent(null)} aria-label="Stop presenting evidence"><X className="h-4 w-4" /></button></div>
          )}
          <form onSubmit={(e) => { e.preventDefault(); submit(); }} className="flex items-end gap-2">
            <Textarea value={text} onChange={(e) => setText(e.target.value)} maxLength={600} rows={2} aria-label="Your question" placeholder="Ask in your own words…"
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); } }} className="flex-1 resize-none" />
            <Button type="button" variant="outline" onClick={() => setPickerOpen(true)} aria-label="Choose evidence to present"><FileSearch className="h-4 w-4" /> <span className="hidden sm:inline">Present</span></Button>
            <Button type="submit" variant="brass" loading={send.isPending} aria-label="Send question" disabled={!text.trim() && !present}><Send className="h-4 w-4" /></Button>
          </form>
          <p className="text-[11px] text-paper-mute">Enter to ask · Shift+Enter for a new line. Present evidence to see how they react.</p>
        </div>
      </section>

      <Dialog open={pickerOpen} onOpenChange={setPickerOpen}>
        <DialogContent title="Present evidence" description="Choose something you've collected. They will react to what it shows." className="w-[min(94vw,820px)]">
          {evidence.data?.length ? (
            <ul className="grid gap-3 sm:grid-cols-2">{evidence.data.map((e) => <li key={e.key}><EvidenceCard ev={e} compact selected={present === e.key} onClick={() => { setPresent(e.key); setPickerOpen(false); }} /></li>)}</ul>
          ) : <p className="text-paper-mute">You haven't collected anything yet.</p>}
        </DialogContent>
      </Dialog>
    </div>
  );
}
