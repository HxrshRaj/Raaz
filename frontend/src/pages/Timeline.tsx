import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertOctagon, AlertTriangle, CheckCircle2, Clock, Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import { useToast } from "@/components/Toasts";
import { Badge, Button, Empty, ErrorState, Input, Select, Skeleton } from "@/components/ui";
import { keys, useDossiers, useEvidence, useOverview, useSid } from "@/hooks/game";
import { api, errorMessage } from "@/lib/api";

export default function TimelinePage() {
  const sid = useSid();
  const qc = useQueryClient();
  const toast = useToast();
  const ts = useQuery({ queryKey: keys.timestamps(sid), queryFn: () => api.timestamps(sid) });
  const tl = useQuery({ queryKey: keys.timeline(sid), queryFn: () => api.timeline(sid) });
  const ev = useEvidence(sid);
  const doss = useDossiers(sid);
  const ov = useOverview(sid);
  const [f, setF] = useState({ label: "", time: "", clock: "RT" as "RT" | "ST", actor: "", loc: "", ev: "" });

  const add = useMutation({
    mutationFn: () => api.timelineAdd(sid, { label: f.label, time: f.time, clock: f.clock, actor_key: f.actor || null, location_key: f.loc || null, evidence_keys: f.ev ? [f.ev] : [] }),
    onSuccess: (r) => {
      void qc.invalidateQueries({ queryKey: keys.timeline(sid) });
      setF({ ...f, label: "", time: "", ev: "" });
      if (!r.validation.ok) toast({ title: "The record disagrees with your timeline", body: r.validation.issues.find((i) => i.severity === "error")?.message, tone: "warn" });
    },
    onError: (e) => toast({ title: "Couldn't add that", body: errorMessage(e), tone: "warn" }),
  });
  const del = useMutation({ mutationFn: (id: string) => api.timelineDelete(sid, id), onSuccess: () => qc.invalidateQueries({ queryKey: keys.timeline(sid) }) });

  if (ts.isLoading || tl.isLoading) return <Skeleton className="h-96" />;
  if (ts.error || tl.error) return <ErrorState error={ts.error ?? tl.error} onRetry={() => { void ts.refetch(); void tl.refetch(); }} />;
  const known = ts.data!.clock_known;
  const entries = tl.data!.entries.slice().sort((a, b) => (a.real_time ?? a.time).localeCompare(b.real_time ?? b.time));
  const issuesFor = (id: string) => tl.data!.validation.issues.filter((i) => i.entries.includes(id));

  return (
    <div className="space-y-5">
      <div><h1 className="font-display text-3xl">Timeline reconstruction</h1>
        <p className="text-sm text-paper-mute">Station records keep the platform clock; phones, banks and wearables keep network time. {known ? "You've established how they relate." : "You haven't yet established how those clocks relate."}</p></div>
      <div className="grid gap-5 lg:grid-cols-2">
        <section className="panel p-5" aria-labelledby="src">
          <h2 id="src" className="panel-title mb-3 flex items-center gap-2"><Clock className="h-5 w-5" /> Timestamps in your evidence</h2>
          {known ? <Badge tone="green" className="mb-3"><CheckCircle2 className="h-3 w-3" /> Station time + 12 min = real time</Badge> : <Badge tone="amber" className="mb-3"><AlertTriangle className="h-3 w-3" /> Clock offset unknown</Badge>}
          {ts.data!.items.length === 0 ? <Empty title="No timestamps yet">Collect logs, registers and phone records.</Empty> : (
            <ol className="relative space-y-3 border-l border-ink-500 pl-5">
              {ts.data!.items.map((t, i) => (
                <li key={i} className="relative"><span className="absolute -left-[26px] top-1.5 h-2.5 w-2.5 rounded-full bg-brass" />
                  <div className="flex flex-wrap items-center gap-2"><span className="font-type text-lg text-paper">{t.time}</span><Badge tone={t.clock === "ST" ? "amber" : "blue"}>{t.clock === "ST" ? "Station clock" : "Real time"}</Badge>
                    {t.real_time && t.clock === "ST" && <span className="text-sm text-emerald-300">= {t.real_time} real</span>}</div>
                  <p className="text-sm text-paper-dim">{t.label} <span className="text-paper-mute">· {t.evidence_name}</span></p></li>
              ))}
            </ol>
          )}
        </section>

        <section className="panel p-5" aria-labelledby="mine">
          <h2 id="mine" className="panel-title mb-3">My reconstruction</h2>
          <form className="grid grid-cols-2 gap-2" onSubmit={(e) => { e.preventDefault(); add.mutate(); }}>
            <label className="col-span-2 text-sm">What happened<Input className="mt-1" required maxLength={300} value={f.label} onChange={(e) => setF({ ...f, label: e.target.value })} placeholder="e.g. Kabir leaves the siding gate" /></label>
            <label className="text-sm">Time<Input className="mt-1" required pattern="\d{1,2}:\d{2}(:\d{2})?" placeholder="22:45" value={f.time} onChange={(e) => setF({ ...f, time: e.target.value })} /></label>
            <label className="text-sm">Clock<Select className="mt-1" value={f.clock} onChange={(e) => setF({ ...f, clock: e.target.value as "RT" | "ST" })}><option value="RT">Real time (phones, banks)</option><option value="ST">Station clock</option></Select></label>
            <label className="text-sm">Who<Select className="mt-1" value={f.actor} onChange={(e) => setF({ ...f, actor: e.target.value })}><option value="">—</option><option value="adrian">Adrian Vale</option>{doss.data?.map((d) => <option key={d.key} value={d.key}>{d.name}</option>)}</Select></label>
            <label className="text-sm">Where<Select className="mt-1" value={f.loc} onChange={(e) => setF({ ...f, loc: e.target.value })}><option value="">—</option>{ov.data?.locations.filter((l) => !l.locked).map((l) => <option key={l.key} value={l.key}>{l.name}</option>)}</Select></label>
            <label className="col-span-2 text-sm">Source<Select className="mt-1" value={f.ev} onChange={(e) => setF({ ...f, ev: e.target.value })}><option value="">(no source)</option>{ev.data?.filter((e) => e.timestamps.length).map((e) => <option key={e.key} value={e.key}>{e.name}</option>)}</Select></label>
            <Button type="submit" variant="brass" className="col-span-2" loading={add.isPending}><Plus className="h-4 w-4" /> Add to timeline</Button>
          </form>

          <div className="mt-5" aria-live="polite">
            {entries.length === 0 ? <Empty title="Nothing placed yet" /> : (
              <ol className="space-y-2">{entries.map((e) => {
                const iss = issuesFor(e.id);
                return (
                  <li key={e.id} className={`rounded-md border p-3 ${iss.some((i) => i.severity === "error") ? "border-blood/70 bg-blood/10" : iss.length ? "border-amber-deep/60 bg-amber-glow/5" : "border-ink-500"}`}>
                    <div className="flex items-start justify-between gap-2"><div><span className="font-type text-paper">{e.time}</span> <Badge tone={e.clock === "ST" ? "amber" : "blue"}>{e.clock}</Badge>{e.real_time && e.clock === "ST" && <span className="ml-2 text-xs text-emerald-300">= {e.real_time} real</span>}
                      <p className="text-sm">{e.label}</p></div><Button size="icon" variant="ghost" aria-label={`Remove ${e.label}`} onClick={() => del.mutate(e.id)}><Trash2 className="h-4 w-4" /></Button></div>
                    {iss.map((i, k) => <p key={k} className="mt-2 flex gap-2 text-xs text-paper-dim">{i.severity === "error" ? <AlertOctagon className="h-4 w-4 shrink-0 text-blood-light" /> : <AlertTriangle className="h-4 w-4 shrink-0 text-amber-glow" />}{i.message}</p>)}
                  </li>
                );
              })}</ol>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
