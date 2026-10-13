import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, CheckCircle2, Gavel, MinusCircle, XCircle } from "lucide-react";
import { useMemo, useRef, useState } from "react";
import { EvidenceCard } from "@/components/EvidenceCard";
import { Portrait } from "@/components/Portrait";
import { useToast } from "@/components/Toasts";
import { Badge, Button, Empty, ErrorState, Progress, Skeleton } from "@/components/ui";
import { keys, useDossiers, useOverview, useRefreshGame, useSid } from "@/hooks/game";
import { api, errorMessage } from "@/lib/api";
import { sound } from "@/lib/audio";
import type { TAccusationResult } from "@/lib/schemas";
import { cn, titleCase } from "@/lib/utils";

const steps = ["Suspect", "Motive", "Sequence", "Evidence", "Contradictions", "Review"] as const;
const statusIcon = (s: string) => s === "supported" ? <CheckCircle2 className="h-4 w-4 text-emerald-400" /> : s === "partial" ? <MinusCircle className="h-4 w-4 text-amber-glow" /> : <XCircle className="h-4 w-4 text-blood-light" />;

export default function AccusePage() {
  const sid = useSid();
  const qc = useQueryClient();
  const toast = useToast();
  const refresh = useRefreshGame(sid);
  const opts = useQuery({ queryKey: keys.options(sid), queryFn: () => api.accusationOptions(sid) });
  const doss = useDossiers(sid);
  const ov = useOverview(sid);
  const [step, setStep] = useState(0);
  const [culprit, setCulprit] = useState("");
  const [motive, setMotive] = useState("");
  const [order, setOrder] = useState<string[] | null>(null);
  const [evidence, setEvidence] = useState<string[]>([]);
  const [cons, setCons] = useState<string[]>([]);
  const [result, setResult] = useState<TAccusationResult | null>(null);
  const idem = useRef(crypto.randomUUID());

  const events = useMemo(() => order ?? opts.data?.events.map((e) => e.key) ?? [], [order, opts.data]);
  const reopen = useMutation({ mutationFn: () => api.reopen(sid), onSuccess: () => { refresh(); setResult(null); } });
  const accuse = useMutation({
    mutationFn: () => api.accuse(sid, { culprit, motive, event_sequence: events, evidence, contradictions: cons }, idem.current),
    onSuccess: (r) => {
      setResult(r); refresh(); void qc.invalidateQueries({ queryKey: keys.options(sid) }); idem.current = crypto.randomUUID();
      if (r.closed) sound.discover(); else sound.alert();
    },
    onError: (e) => toast({ title: "Accusation not accepted", body: errorMessage(e), tone: "warn" }),
  });

  if (opts.isLoading) return <Skeleton className="h-96" />;
  if (opts.error) return <ErrorState error={opts.error} onRetry={() => opts.refetch()} />;
  const o = opts.data!;
  const move = (i: number, d: number) => { const a = [...events]; const j = i + d; if (j < 0 || j >= a.length) return; [a[i], a[j]] = [a[j], a[i]]; setOrder(a); };
  const toggle = (arr: string[], set: (v: string[]) => void, k: string) => set(arr.includes(k) ? arr.filter((x) => x !== k) : [...arr, k]);
  const suspect = o.suspects.find((s) => s.key === culprit);

  if (o.status === "solved" && !result) return <ClosedBanner score={ov.data?.score ?? null} />;
  if (o.status === "closed_unsolved" && !result) {
    return (
      <div className="panel mx-auto max-w-xl space-y-4 p-6 text-center">
        <Gavel className="mx-auto h-8 w-8 text-blood-light" /><h1 className="font-display text-3xl">The case has gone cold</h1>
        <p className="text-paper-dim">You've used all {o.max_attempts} accusations. Your reputation took the hit, but the file can be reopened and your evidence is intact.</p>
        <Button variant="brass" loading={reopen.isPending} onClick={() => reopen.mutate()}>Reopen the case</Button>
      </div>
    );
  }
  if (result) return <Report r={result} onAgain={() => { setResult(null); setStep(0); }} reopen={() => reopen.mutate()} />;

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end justify-between gap-2"><div><h1 className="font-display text-3xl">Final accusation</h1>
        <p className="text-sm text-paper-mute">Attempt {o.attempts + 1} of {o.max_attempts}. A wrong accusation costs reputation and the accused will stop trusting you. Scoring is a transparent rubric over evidence you hold; no AI judges the case.</p></div>
        <details className="text-sm"><summary className="cursor-pointer text-brass-light">Scoring rubric</summary><ul className="mt-2 space-y-1 text-paper-dim">{o.rubric.map((r) => <li key={r.key}>{r.label} — {r.weight} pts</li>)}</ul></details></div>

      <ol className="flex flex-wrap gap-2" aria-label="Steps">{steps.map((s, i) => (
        <li key={s}><button onClick={() => setStep(i)} aria-current={i === step ? "step" : undefined} className={cn("rounded-full border px-3 py-1 text-sm", i === step ? "border-brass bg-brass/15 text-brass-light" : i < step ? "border-ink-500 text-paper-dim" : "border-ink-500 text-paper-mute")}>{i + 1}. {s}</button></li>
      ))}</ol>

      <div className="panel p-5">
        {step === 0 && (
          <fieldset><legend className="panel-title mb-3">Who are you accusing?</legend>
            <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{o.suspects.map((s) => {
              const d = doss.data?.find((x) => x.key === s.key);
              return (<li key={s.key}><label className={cn("flex cursor-pointer gap-3 rounded-lg border p-3", culprit === s.key ? "border-brass bg-brass/10" : "border-ink-500 hover:border-brass-dark")}>
                <input type="radio" name="suspect" className="sr-only" checked={culprit === s.key} onChange={() => setCulprit(s.key)} />
                {d && <Portrait portrait={d.portrait} className="h-16 w-14 shrink-0 rounded" label="" />}
                <span><span className="block font-medium">{s.name}</span><span className="text-xs text-paper-mute">{s.role}</span></span></label></li>);
            })}</ul></fieldset>
        )}
        {step === 1 && (
          <fieldset><legend className="panel-title mb-3">Why did it happen?</legend>
            <ul className="space-y-2">{o.motives.map((m) => (
              <li key={m.key}><label className={cn("flex cursor-pointer gap-3 rounded-md border p-3", motive === m.key ? "border-brass bg-brass/10" : "border-ink-500 hover:border-brass-dark")}>
                <input type="radio" name="motive" className="mt-1 accent-amber-500" checked={motive === m.key} onChange={() => setMotive(m.key)} /><span><span className="block">{m.label}</span><span className="text-xs text-paper-mute">{m.description}</span></span></label></li>
            ))}</ul></fieldset>
        )}
        {step === 2 && (
          <div><h2 className="panel-title mb-1">Put the night in order</h2><p className="mb-3 text-sm text-paper-mute">Only events your evidence has revealed appear here. Order them from earliest to latest (real time).</p>
            {events.length === 0 ? <Empty title="No events established yet">Collect timestamped evidence and statements.</Empty> : (
              <ol className="space-y-2">{events.map((k, i) => { const e = o.events.find((x) => x.key === k)!; return (
                <li key={k} className="flex items-center gap-2 rounded-md border border-ink-500 p-3"><span className="w-6 text-center font-display text-xl text-brass-light">{i + 1}</span>
                  <div className="flex-1"><p className="font-medium">{e.title}</p><p className="text-xs text-paper-mute">{e.description}</p></div>
                  <Button size="icon" variant="ghost" aria-label={`Move ${e.title} earlier`} disabled={i === 0} onClick={() => move(i, -1)}><ArrowUp className="h-4 w-4" /></Button>
                  <Button size="icon" variant="ghost" aria-label={`Move ${e.title} later`} disabled={i === events.length - 1} onClick={() => move(i, 1)}><ArrowDown className="h-4 w-4" /></Button></li>); })}</ol>)}</div>
        )}
        {step === 3 && (
          <div><h2 className="panel-title mb-1">What proves it?</h2><p className="mb-3 text-sm text-paper-mute">Select the evidence you rely on. {evidence.length} selected.</p>
            {o.evidence.length === 0 ? <Empty title="No evidence collected" /> : <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">{o.evidence.map((e) => <li key={e.key}><EvidenceCard ev={e} compact selected={evidence.includes(e.key)} onClick={() => toggle(evidence, setEvidence, e.key)} /></li>)}</ul>}</div>
        )}
        {step === 4 && (
          <div><h2 className="panel-title mb-1">Which contradictions matter?</h2><p className="mb-3 text-sm text-paper-mute">Only contradictions you've established can be cited.</p>
            {o.contradictions.length === 0 ? <Empty title="None established yet">Test conflicting items in the inventory or present them in interviews.</Empty> : (
              <ul className="space-y-2">{o.contradictions.map((c) => (<li key={c.key}><label className={cn("flex cursor-pointer gap-3 rounded-md border p-3", cons.includes(c.key) ? "border-blood bg-blood/10" : "border-ink-500")}>
                <input type="checkbox" className="mt-1 accent-red-500" checked={cons.includes(c.key)} onChange={() => toggle(cons, setCons, c.key)} /><span><span className="block font-medium">{c.title}</span><span className="text-xs text-paper-mute">{c.explanation}</span></span></label></li>))}</ul>)}</div>
        )}
        {step === 5 && (
          <div className="space-y-3"><h2 className="panel-title">Review your case</h2>
            <dl className="grid gap-3 sm:grid-cols-2"><Item k="Accused" v={suspect?.name} /><Item k="Motive" v={o.motives.find((m) => m.key === motive)?.label} /><Item k="Events ordered" v={`${events.length}`} /><Item k="Evidence cited" v={`${evidence.length}`} /><Item k="Contradictions cited" v={`${cons.length}`} /></dl>
            <Button variant="danger" size="lg" disabled={!culprit || !motive} loading={accuse.isPending} onClick={() => accuse.mutate()}><Gavel className="h-5 w-5" /> Make the accusation</Button>
            {(!culprit || !motive) && <p className="text-xs text-paper-mute">Choose a suspect and a motive first.</p>}</div>
        )}
        <div className="mt-6 flex justify-between"><Button variant="ghost" disabled={step === 0} onClick={() => setStep(step - 1)}>Back</Button><Button disabled={step === steps.length - 1} onClick={() => setStep(step + 1)}>Next</Button></div>
      </div>
    </div>
  );
}
const Item = ({ k, v }: { k: string; v?: string }) => <div className="rounded-md border border-ink-500 p-3"><dt className="label">{k}</dt><dd className="font-display text-xl">{v ?? "—"}</dd></div>;

function ClosedBanner({ score }: { score: number | null }) {
  return <div className="panel mx-auto max-w-xl space-y-3 p-8 text-center"><CheckCircle2 className="mx-auto h-10 w-10 text-emerald-400" /><h1 className="font-display text-3xl">Case closed</h1><p className="text-paper-dim">Final score {score ?? "—"}. Review your evidence and notes any time.</p></div>;
}

function Report({ r, onAgain, reopen }: { r: TAccusationResult; onAgain: () => void; reopen: () => void }) {
  const title = r.verdict === "case_closed" ? "Case closed" : r.verdict === "insufficient_evidence" ? "Not enough to hold them" : "Wrong person";
  return (
    <div className="mx-auto max-w-4xl space-y-5" data-testid="report">
      <header className={cn("panel p-6", r.closed ? "border-emerald-700/60" : "border-blood/50")}>
        <p className="label">Attempt {r.attempt}</p><h1 className="font-display text-4xl">{title}</h1>
        <div className="mt-3 flex items-center gap-4"><span className="font-display text-5xl text-brass-light">{r.score}</span><div className="flex-1"><Progress value={r.score} tone={r.closed ? "green" : "red"} /><p className="mt-1 text-xs text-paper-mute">out of 100 · reputation {r.reputation_delta >= 0 ? "+" : ""}{r.reputation_delta} · {r.attempts_left} attempt(s) left</p></div></div>
        {r.consequence && <p className="mt-3 rounded border border-blood/40 bg-blood/10 p-3 text-sm text-blood-light">{r.consequence}</p>}
        {r.solution && <div className="paper-card mt-4 p-4"><p className="font-type text-xs uppercase tracking-widest text-brass-dark">What happened</p><p className="mt-1 font-type text-[13px] leading-relaxed text-ink-800">{r.solution}</p></div>}
      </header>
      <section className="space-y-3" aria-label="Rubric">{r.criteria.map((c) => (
        <article key={c.key} className="panel p-4"><div className="flex items-center gap-2">{statusIcon(c.status)}<h2 className="font-display text-xl">{c.label}</h2><Badge className="ml-auto">{c.points}/{c.max}</Badge></div>
          <p className="mt-1 text-sm text-paper-dim">{c.message}</p>
          {c.rows && <ul className="mt-3 space-y-1.5 text-sm">{c.rows.map((row) => <li key={row.key} className="flex gap-2">{statusIcon(row.status)}<span><span>{row.label}</span>{row.evidence.length > 0 && <span className="text-paper-mute"> — {row.evidence.map((e) => e.name).join(", ")}</span>}</span></li>)}</ul>}</article>
      ))}</section>
      {r.evidence_annotations.length > 0 && <section className="panel p-4"><h2 className="panel-title mb-2">Your evidence, annotated</h2><ul className="space-y-1.5 text-sm">{r.evidence_annotations.map((a) => <li key={a.key}><Badge tone={a.role === "supports" ? "green" : a.role === "contradicts" ? "red" : "neutral"}>{titleCase(a.role)}</Badge> {a.name} <span className="text-paper-mute">— {a.note}</span></li>)}</ul></section>}
      {r.next_steps.length > 0 && <section className="panel p-4"><h2 className="panel-title mb-2">Next steps</h2><ul className="list-disc space-y-1 pl-5 text-sm">{r.next_steps.map((n, i) => <li key={i}>{n}</li>)}</ul></section>}
      <div className="flex gap-2">{r.status === "closed_unsolved" ? <Button variant="brass" onClick={reopen}>Reopen the case</Button> : !r.closed && <Button variant="brass" onClick={onAgain}>Keep investigating</Button>}</div>
    </div>
  );
}
