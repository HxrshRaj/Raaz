import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bot, Eye, Loader2, Radar, Send, Sparkles, XCircle } from "lucide-react";
import { useEffect, useState } from "react";
import { api, errorMessage } from "@/lib/api";
import type { TNazar } from "@/lib/schemas";
import { cn } from "@/lib/utils";
import { keys, useRefreshGame } from "@/hooks/game";
import { Badge, Button, Empty, ErrorState, Input, Progress, Skeleton } from "./ui";
import { useToast } from "./Toasts";

const levels = [
  { n: 1, name: "Nudge", hint: "A question to think about" },
  { n: 2, name: "Evidence hint", hint: "Points at things you hold (−1 pt)" },
  { n: 3, name: "Analysis", hint: "Detailed breakdown (−2 pts)" },
] as const;

export function NazarPanel({ sid }: { sid: string }) {
  const [level, setLevel] = useState<1 | 2 | 3>(1);
  const [q, setQ] = useState("");
  const [last, setLast] = useState<TNazar | null>(null);
  const qc = useQueryClient();
  const refresh = useRefreshGame(sid);
  const toast = useToast();
  const hist = useQuery({ queryKey: keys.nazar(sid), queryFn: () => api.nazarHistory(sid) });
  const ask = useMutation({
    mutationFn: () => api.nazar(sid, q, level),
    onSuccess: (r) => { setLast(r); setQ(""); void qc.invalidateQueries({ queryKey: keys.nazar(sid) }); refresh(); },
    onError: (e) => toast({ title: "Nazar couldn't answer", body: errorMessage(e), tone: "warn" }),
  });
  return (
    <section aria-label="Nazar, detective's assistant" className="space-y-4">
      <div className="flex items-center gap-2">
        <Eye className="h-5 w-5 text-brass-light" aria-hidden />
        <h3 className="panel-title">Nazar <span className="font-deva text-base text-paper-mute">नज़र</span></h3>
      </div>
      <p className="text-sm text-paper-mute">Nazar works only from what you've collected. It won't name a culprit and it labels what is observed, what is interpretation, and what is speculation.</p>
      <div role="radiogroup" aria-label="Hint level" className="grid grid-cols-3 gap-2">
        {levels.map((l) => (
          <button key={l.n} role="radio" aria-checked={level === l.n} onClick={() => setLevel(l.n)}
            className={cn("rounded-md border p-2 text-left text-xs transition-colors", level === l.n ? "border-brass bg-brass/10 text-paper" : "border-ink-500 text-paper-mute hover:border-brass-dark")}>
            <span className="block font-medium">{l.name}</span><span className="opacity-80">{l.hint}</span>
          </button>
        ))}
      </div>
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); ask.mutate(); }}>
        <Input value={q} onChange={(e) => setQ(e.target.value)} maxLength={500} placeholder="Ask about contradictions, the timeline, a suspect… (or leave empty)" aria-label="Question for Nazar" />
        <Button type="submit" variant="brass" loading={ask.isPending} aria-label="Ask Nazar"><Send className="h-4 w-4" /></Button>
      </form>
      {last && (
        <article className="space-y-3 rounded-lg border border-brass-dark/50 bg-ink-800/70 p-4 animate-rise" aria-live="polite">
          <p className="text-sm leading-relaxed">{last.reply}</p>
          {last.structured.observed.length > 0 && <Section title="Observed" tone="green" items={last.structured.observed.map((o) => o.text)} />}
          {last.structured.interpretations.length > 0 && <Section title="Interpretation" tone="amber" items={last.structured.interpretations} />}
          {last.structured.speculation.length > 0 && <Section title="Speculation" tone="red" items={last.structured.speculation} />}
          {last.structured.suggested_questions.length > 0 && <Section title="Questions to pursue" tone="blue" items={last.structured.suggested_questions} />}
          {last.sources.length > 0 && (
            <div className="flex flex-wrap items-center gap-1 text-xs text-paper-mute">Sources: {last.sources.map((s) => <Badge key={s.ref} title={s.excerpt}>{s.title}</Badge>)}</div>
          )}
          <p className="text-[11px] text-paper-mute">{last.label}{last.hint_cost ? ` · −${last.hint_cost} pt on final score` : ""}</p>
        </article>
      )}
      {hist.data && hist.data.length > 0 && !last && <p className="text-xs text-paper-mute">{hist.data.length / 2} earlier exchange(s) saved.</p>}
    </section>
  );
}

function Section({ title, items, tone }: { title: string; items: string[]; tone: "green" | "amber" | "red" | "blue" }) {
  return (
    <div>
      <Badge tone={tone}>{title}</Badge>
      <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-paper-dim">{items.map((t, i) => <li key={i}>{t}</li>)}</ul>
    </div>
  );
}

export function InvestigationPanel({ sid }: { sid: string }) {
  const [question, setQuestion] = useState("Does anyone's account of the evening fall apart against the clocks and the records?");
  const [runId, setRunId] = useState<string | null>(null);
  const qc = useQueryClient();
  const toast = useToast();
  const start = useMutation({
    mutationFn: () => api.startRun(sid, question),
    onSuccess: (r) => setRunId(r.id),
    onError: (e) => toast({ title: "Couldn't start the investigation", body: errorMessage(e), tone: "warn" }),
  });
  const run = useQuery({
    queryKey: ["run", sid, runId], enabled: !!runId, queryFn: () => api.run(sid, runId!),
    refetchInterval: (q) => (q.state.data && ["queued", "running"].includes(q.state.data.status) ? 700 : false),
  });
  useEffect(() => { if (run.data && !["queued", "running"].includes(run.data.status)) void qc.invalidateQueries({ queryKey: keys.runs(sid) }); }, [run.data, qc, sid]);
  const cancel = useMutation({ mutationFn: () => api.cancelRun(sid, runId!) });
  const r = run.data;
  const busy = !!r && ["queued", "running"].includes(r.status);
  return (
    <section aria-label="Agent investigation" className="space-y-3">
      <div className="flex items-center gap-2"><Bot className="h-5 w-5 text-brass-light" aria-hidden /><h3 className="panel-title">Investigation desk</h3></div>
      <p className="text-sm text-paper-mute">A bounded team of analysts (evidence, timeline, witnesses, research, verification) examines what you hold using permissioned tools. They propose; you decide.</p>
      <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); start.mutate(); }}>
        <Input value={question} onChange={(e) => setQuestion(e.target.value)} minLength={3} maxLength={400} aria-label="Investigation question" />
        <Button type="submit" variant="brass" loading={start.isPending || busy}>Run</Button>
        {busy && <Button type="button" onClick={() => cancel.mutate()} aria-label="Cancel investigation"><XCircle className="h-4 w-4" /></Button>}
      </form>
      {r && (
        <div className="space-y-3 rounded-lg border border-ink-500 bg-ink-800/70 p-4" aria-live="polite">
          <div className="flex items-center gap-2 text-sm">
            <Badge tone={r.status === "succeeded" ? "green" : r.status === "failed" ? "red" : r.status === "cancelled" ? "neutral" : "amber"}>{r.status}</Badge>
            {busy && <Loader2 className="h-4 w-4 animate-spin text-amber-glow" />}
            <span className="text-paper-mute">{r.plan.length ? `Plan: ${r.plan.join(" → ")}` : "Planning…"}</span>
          </div>
          {r.error && <ErrorState error={new Error(r.error)} />}
          <ol className="space-y-1 text-xs">
            {(r.steps ?? []).map((s) => (
              <li key={s.idx} className="flex gap-2">
                <span className={cn("mt-0.5 h-1.5 w-1.5 shrink-0 rounded-full", s.status === "ok" ? "bg-emerald-400" : "bg-blood")} />
                <span><strong className="text-paper-dim">{s.node.replace(/_/g, " ")}</strong>{s.tool ? <code className="mx-1 text-brass-light">{s.tool}</code> : " "}— {s.summary}</span>
              </li>
            ))}
          </ol>
          {r.status === "succeeded" && r.result && <RunReport result={r.result} sid={sid} />}
        </div>
      )}
    </section>
  );
}

type Report = {
  observed: { text: string }[]; interpretations: { text: string }[];
  contradictions: { rule: string; title: string; established: boolean; evidence: { key: string; name: string }[]; provenance: string }[];
  suggested_player_actions: { a: string; b: string; why: string }[]; caveats: string[];
  hypotheses: { suspect: string; strength: number; supporting: string[]; opposing: string[] }[];
};
function RunReport({ result, sid }: { result: Report; sid: string }) {
  const refresh = useRefreshGame(sid);
  const toast = useToast();
  const confirm = useMutation({
    mutationFn: (v: { a: string; b: string }) => api.checkContradiction(sid, v.a, v.b),
    onSuccess: (r) => { refresh(); toast({ title: r.established ? "Contradiction recorded" : "Not established", body: r.contradiction?.title ?? r.message, tone: r.established ? "clue" : "info" }); },
  });
  return (
    <div className="space-y-3 border-t border-ink-500 pt-3 text-sm">
      {result.observed.length > 0 && <Section title="Observed" tone="green" items={result.observed.map((o) => o.text)} />}
      {result.interpretations.length > 0 && <Section title="Interpretation" tone="amber" items={result.interpretations.map((o) => (typeof o === "string" ? o : o.text))} />}
      {result.contradictions.length > 0 && (
        <div>
          <Badge tone="red">Conflicts found among your records</Badge>
          <ul className="mt-2 space-y-2">
            {result.contradictions.map((c) => (
              <li key={c.rule} className="rounded border border-ink-500 p-2">
                <p className="font-medium">{c.title} {c.established ? <Badge tone="green">Established</Badge> : <Badge tone="amber">Candidate</Badge>}</p>
                <p className="text-xs text-paper-mute">{c.evidence.map((e) => e.name).join("  ×  ")}</p>
                {!c.established && (
                  <Button size="sm" className="mt-2" onClick={() => confirm.mutate({ a: c.evidence[0].key, b: c.evidence[1].key })} loading={confirm.isPending}>
                    I confirm this contradiction
                  </Button>
                )}
              </li>
            ))}
          </ul>
        </div>
      )}
      {result.hypotheses.length > 0 && (
        <div><Badge>Evidence weight by suspect (not guilt)</Badge>
          <ul className="mt-2 space-y-1">{result.hypotheses.map((h) => <li key={h.suspect} className="flex items-center gap-2"><span className="w-36 truncate">{h.suspect}</span><Progress value={h.strength} className="flex-1" /><span className="w-8 text-right text-xs text-paper-mute">{h.strength}</span></li>)}</ul></div>
      )}
      <p className="text-xs text-paper-mute">{result.caveats.at(-1)}</p>
    </div>
  );
}

export function LeadsPanel({ sid }: { sid: string }) {
  const leads = useQuery({ queryKey: keys.leads(sid), queryFn: () => api.leads(sid) });
  const anomalies = useQuery({ queryKey: keys.anomalies(sid), queryFn: () => api.anomalies(sid) });
  return (
    <section aria-label="Lead priority" className="space-y-3">
      <div className="flex items-center gap-2"><Radar className="h-5 w-5 text-brass-light" aria-hidden /><h3 className="panel-title">Where to look next</h3></div>
      {leads.isLoading && <Skeleton className="h-28" />}
      {leads.error && <ErrorState error={leads.error} onRetry={() => leads.refetch()} />}
      {leads.data && (
        <>
          <ul className="space-y-2">
            {leads.data.ranking.map((r) => (
              <li key={r.character}>
                <div className="flex items-center justify-between text-sm"><span>{r.rank}. {r.name}</span><span className="text-xs text-paper-mute">{Math.round(r.priority * 100)}</span></div>
                <Progress value={r.priority * 100} className="mt-1" />
                {r.reasons.length > 0 && <p className="mt-0.5 text-[11px] text-paper-mute">{r.reasons.join(" · ")}</p>}
              </li>
            ))}
          </ul>
          <p className="text-[11px] italic text-paper-mute"><Sparkles className="mr-1 inline h-3 w-3" />{leads.data.model}. {leads.data.disclaimer}</p>
        </>
      )}
      {anomalies.data?.available && anomalies.data.findings.length > 0 && (
        <div className="rounded-md border border-amber-deep/50 p-3">
          <p className="label text-amber-glow">Record anomalies</p>
          <ul className="mt-1 space-y-1 text-sm">{anomalies.data.findings.slice(0, 4).map((f, i) => <li key={i}><strong>{f.subject}</strong> — {f.reasons[0]}</li>)}</ul>
          <p className="mt-1 text-[11px] italic text-paper-mute">{anomalies.data.disclaimer}</p>
        </div>
      )}
      {anomalies.data && !anomalies.data.available && <Empty title="Machine-log scan unavailable">{anomalies.data.message}</Empty>}
    </section>
  );
}
