import { useQuery } from "@tanstack/react-query";
import { ChevronLeft, MessageSquareText, ShieldCheck, ShieldQuestion, ShieldAlert } from "lucide-react";
import { Link, useParams } from "react-router-dom";
import { Portrait } from "@/components/Portrait";
import { Badge, Button, Empty, ErrorState, Skeleton } from "@/components/ui";
import { keys, useDossiers, useSid } from "@/hooks/game";
import { api } from "@/lib/api";
import { stanceLabel } from "@/components/EvidenceCard";
import { titleCase } from "@/lib/utils";

const alibiBadge = (s: string) =>
  s === "cleared_for_window" ? <Badge tone="green"><ShieldCheck className="h-3 w-3" /> Alibi established</Badge>
  : s === "claims_contradicted" ? <Badge tone="red"><ShieldAlert className="h-3 w-3" /> Claim contradicted</Badge>
  : <Badge><ShieldQuestion className="h-3 w-3" /> Unverified</Badge>;

export function SuspectList() {
  const sid = useSid();
  const q = useDossiers(sid);
  if (q.isLoading) return <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">{Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-64" />)}</div>;
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  return (
    <div className="space-y-4">
      <h1 className="font-display text-3xl">Suspects &amp; witnesses</h1>
      <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {q.data!.map((c) => (
          <li key={c.key} className="panel overflow-hidden transition hover:border-brass">
            <Link to={c.key} className="block">
              <Portrait portrait={c.portrait} mood={c.mood === "unmet" ? "guarded" : c.mood} className="h-56 w-full bg-ink-900 object-cover" label={`Portrait of ${c.name}`} />
              <div className="space-y-2 p-4">
                <h2 className="font-display text-xl">{c.name}</h2><p className="text-xs text-paper-mute">{c.role}</p>
                <div className="flex flex-wrap gap-1">{!c.is_suspect && <Badge tone="blue">Witness</Badge>}{alibiBadge(c.alibi_status)}<Badge>{c.turns ? `${titleCase(c.mood)} · ${c.turns} turns` : "Not interviewed"}</Badge></div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

export function SuspectDossier() {
  const sid = useSid();
  const { key = "" } = useParams();
  const q = useQuery({ queryKey: keys.dossier(sid, key), queryFn: () => api.dossier(sid, key) });
  if (q.isLoading) return <Skeleton className="h-96" />;
  if (q.error) return <ErrorState error={q.error} onRetry={() => q.refetch()} />;
  const d = q.data!;
  return (
    <div className="space-y-5">
      <Button asChild variant="ghost" size="sm"><Link to={`/play/${sid}/suspects`}><ChevronLeft className="h-4 w-4" /> All dossiers</Link></Button>
      <div className="grid gap-6 md:grid-cols-[260px_1fr]">
        <div className="space-y-3">
          <Portrait portrait={d.portrait} mood={d.interview.mood === "unmet" ? "guarded" : d.interview.mood} className="w-full rounded-xl border border-ink-500" label={`Portrait of ${d.name}`} />
          <Button asChild variant="brass" className="w-full"><Link to={`/play/${sid}/interview/${d.key}`}><MessageSquareText className="h-4 w-4" /> Interrogate</Link></Button>
        </div>
        <div className="space-y-5">
          <header><h1 className="font-display text-4xl">{d.name}</h1><p className="text-paper-mute">{d.role} · age {d.age}</p>
            <div className="mt-2 flex flex-wrap gap-2">{alibiBadge(d.alibi.status)}<Badge>{d.interview.turns ? `Interviewed ${d.interview.turns}×` : "Not interviewed"}</Badge></div></header>
          <section className="panel p-4"><h2 className="label mb-1">Relationship to the victim</h2><p>{d.relationship_to_victim}</p></section>
          <section className="panel p-4"><h2 className="label mb-1">Publicly known</h2><ul className="list-disc space-y-1 pl-5 text-sm">{d.public_facts.map((f, i) => <li key={i}>{f}</li>)}</ul></section>
          <section className="panel p-4"><h2 className="label mb-1">Alibi at the time of death</h2><p className="text-sm">{d.alibi.statement}</p></section>
          <section className="panel p-4"><h2 className="label mb-2">Statements on record</h2>
            {d.statements.length === 0 ? <p className="text-sm text-paper-mute">Nothing on record yet. Interview them.</p> : (
              <ul className="space-y-2">{d.statements.map((s) => <li key={s.key} className="rounded border border-ink-500 p-2.5 text-sm"><strong>{s.name}</strong><p className="typewriter mt-1">{s.description}</p>{s.contradiction_rules.length > 0 && <Badge tone="red" className="mt-1">Contradicted</Badge>}</li>)}</ul>
            )}</section>
          <section className="panel p-4"><h2 className="label mb-2">Evidence connections</h2>
            {d.evidence_connections.length === 0 ? <p className="text-sm text-paper-mute">No collected evidence connects to them yet.</p> : (
              <ul className="space-y-1.5 text-sm">{d.evidence_connections.map((c) => <li key={c.key}><Badge tone={c.stance === "clears" ? "green" : c.stance === "related" ? "neutral" : "red"}>{stanceLabel[c.stance] ?? "Related"}</Badge> {c.name}{c.note && <span className="text-paper-mute"> — {c.note}</span>}</li>)}</ul>
            )}</section>
          <section className="panel p-4"><h2 className="label mb-2">Unresolved questions</h2>
            {d.unresolved_questions.length === 0 ? <Empty title="Nothing outstanding" /> : <ul className="list-disc space-y-1 pl-5 text-sm">{d.unresolved_questions.map((u, i) => <li key={i}>{u}</li>)}</ul>}</section>
        </div>
      </div>
    </div>
  );
}
