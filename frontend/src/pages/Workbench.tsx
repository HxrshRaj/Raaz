import { useMutation, useQuery } from "@tanstack/react-query";
import { ChevronLeft, FlaskConical, Play } from "lucide-react";
import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { Link } from "react-router-dom";
import { Badge, Button, ErrorState, Input, Skeleton } from "@/components/ui";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/app-context";

type Cmp = Record<string, { val: { macro_f1: number }; test: { macro_f1: number }; real_ood: { macro_f1: number } }>;
const COLORS = { val: "#6f87a6", test: "#b8924f", real: "#e0634e" };

export default function Workbench() {
  const { user } = useAuth();
  const q = useQuery({ queryKey: ["workbench"], queryFn: api.workbench, enabled: !!user, retry: false });
  const [job, setJob] = useState<string | null>(null);
  const [text, setText] = useState("The badge reader logged a swipe at the siding gate at 22:41.");
  const train = useMutation({ mutationFn: () => api.workbenchTrain(7, true), onSuccess: (r) => setJob(r.job_id) });
  const jobQ = useQuery({ queryKey: ["wbjob", job], enabled: !!job, queryFn: () => api.workbenchJob(job!), refetchInterval: (s) => (s.state.data && ["queued", "running"].includes(s.state.data.status) ? 1000 : false) });
  const pred = useMutation({ mutationFn: () => api.workbenchPredict(text) });
  useEffect(() => { if (jobQ.data?.status === "succeeded") void q.refetch(); }, [jobQ.data?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!user) return <div className="p-8">Sign in first. <Link className="underline" to="/">Back</Link></div>;
  const d = q.data as Record<string, any> | undefined; // eslint-disable-line @typescript-eslint/no-explicit-any
  const sum = d?.latest_summary;
  const cmp: Cmp | undefined = sum?.models?.clue_classifier_sklearn?.comparison;
  const torch = sum?.models?.clue_classifier_torch;
  const bars = cmp ? [...Object.entries(cmp).map(([k, v]) => ({ model: k, val: v.val.macro_f1, test: v.test.macro_f1, real: v.real_ood.macro_f1 })),
    ...(torch ? [{ model: "torch_textcnn", val: torch.val.macro_f1, test: torch.test.macro_f1, real: torch.real_ood.macro_f1 }] : [])] : [];

  return (
    <div className="mx-auto max-w-6xl space-y-6 px-4 py-8">
      <div className="flex items-center gap-3"><Button asChild variant="ghost" size="sm"><Link to="/"><ChevronLeft className="h-4 w-4" /> Title</Link></Button>
        <h1 className="font-display text-3xl">ML workbench</h1><Badge tone="amber"><FlaskConical className="h-3 w-3" /> developer tool — not part of gameplay</Badge></div>
      {q.isLoading && <Skeleton className="h-64" />}
      {q.error && <ErrorState error={q.error} onRetry={() => q.refetch()} />}
      {d && (
        <>
          <section className="panel p-5 text-sm"><h2 className="panel-title mb-2">Dataset</h2>
            <p>{d.dataset.version} · hash <code className="text-brass-light">{d.dataset.hash.slice(0, 12)}</code> · {d.dataset.total} synthetic samples (train {d.dataset.train} / val {d.dataset.val} / test {d.dataset.test}) · {d.dataset.real_ood} real OOD items</p>
            <p className="mt-1 text-amber-glow">{d.dataset.warning}</p>
            <div className="mt-3 h-40"><ResponsiveContainer><BarChart data={Object.entries(d.dataset.class_counts).map(([k, v]) => ({ k, v }))}><CartesianGrid stroke="#2a3547" /><XAxis dataKey="k" stroke="#8e98a8" /><YAxis stroke="#8e98a8" /><Tooltip contentStyle={{ background: "#10151f", border: "1px solid #2a3547" }} /><Bar dataKey="v" fill="#b8924f" name="samples" /></BarChart></ResponsiveContainer></div></section>
          <section className="panel space-y-3 p-5"><div className="flex items-center justify-between"><h2 className="panel-title">Models</h2>
            <Button variant="brass" onClick={() => train.mutate()} loading={train.isPending || jobQ.data?.status === "running"}><Play className="h-4 w-4" /> Train all</Button></div>
            {jobQ.data && <p className="text-sm" role="status">Job {jobQ.data.status}{jobQ.data.error ? `: ${jobQ.data.error}` : ""}</p>}
            {train.error && <p className="text-sm text-blood-light">{errorMessage(train.error)}</p>}
            <div className="flex flex-wrap gap-2">{Object.entries(d.available as Record<string, boolean>).map(([k, v]) => <Badge key={k} tone={v ? "green" : "red"}>{k}: {v ? "trained" : "missing"}</Badge>)}</div>
            {bars.length > 0 ? (
              <div className="h-72"><ResponsiveContainer><BarChart data={bars}><CartesianGrid stroke="#2a3547" /><XAxis dataKey="model" stroke="#8e98a8" fontSize={11} /><YAxis domain={[0, 1]} stroke="#8e98a8" /><Tooltip contentStyle={{ background: "#10151f", border: "1px solid #2a3547" }} /><Legend />
                <Bar dataKey="val" name="validation F1" fill={COLORS.val} /><Bar dataKey="test" name="test F1 (synthetic)" fill={COLORS.test} /><Bar dataKey="real" name="real OOD F1" fill={COLORS.real} /></BarChart></ResponsiveContainer></div>
            ) : <p className="text-sm text-paper-mute">No training summary yet — run “Train all” or <code>python -m app.ml.train_all</code>.</p>}
            {torch && <div className="h-56"><p className="label mb-1">PyTorch TextCNN — loss (best epoch {torch.best_epoch}, {torch.params} params)</p><ResponsiveContainer><LineChart data={torch.history}><CartesianGrid stroke="#2a3547" /><XAxis dataKey="epoch" stroke="#8e98a8" /><YAxis stroke="#8e98a8" /><Tooltip contentStyle={{ background: "#10151f", border: "1px solid #2a3547" }} /><Legend /><Line dataKey="train_loss" stroke="#b8924f" dot={false} /><Line dataKey="val_loss" stroke="#6f87a6" dot={false} /></LineChart></ResponsiveContainer></div>}
            {sum && <p className="text-xs text-paper-mute">Measured on held-out splits by this code. Selected sklearn model (chosen on validation only): <b>{sum.models.clue_classifier_sklearn.selected_on_validation}</b>. Lead ranker AUC (proxy label): {sum.models.lead_ranker.test_auc_model} vs heuristic {sum.models.lead_ranker.test_auc_heuristic_baseline}.</p>}
          </section>
          <section className="panel p-5"><h2 className="panel-title mb-2">Try a prediction</h2>
            <form className="flex gap-2" onSubmit={(e) => { e.preventDefault(); pred.mutate(); }}><Input value={text} onChange={(e) => setText(e.target.value)} aria-label="Clue text" maxLength={600} /><Button type="submit" loading={pred.isPending}>Classify</Button></form>
            {pred.error && <p className="mt-2 text-sm text-blood-light">{errorMessage(pred.error)}</p>}
            {pred.data && <ul className="mt-2 text-sm">{(pred.data as { predictions: { model: string; category: string; confidence: number | null }[] }).predictions.map((p) => <li key={p.model}><Badge>{p.model}</Badge> {p.category} {p.confidence != null && `(${p.confidence})`}</li>)}</ul>}
            <h3 className="label mb-1 mt-4">Held-out examples</h3>
            <ul className="space-y-1 text-xs">{(d.prediction_examples as { text: string; truth: string; predictions: { model: string; category: string }[] }[]).map((e, i) => <li key={i}><span className="text-paper-mute">{e.text}</span> → truth <Badge>{e.truth}</Badge> {e.predictions.map((p) => <Badge key={p.model} tone={p.category === e.truth ? "green" : "red"}>{p.model}: {p.category}</Badge>)}</li>)}</ul></section>
          <section className="panel p-5"><h2 className="panel-title mb-2">Experiment history</h2>
            <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="label"><tr><th className="p-1">#</th><th>name</th><th>task</th><th>dataset</th><th>metrics</th><th>when</th></tr></thead>
              <tbody>{(d.experiments as { id: number; name: string; task: string; dataset_version: string; metrics: Record<string, number>; created_at: string }[]).map((e) => <tr key={e.id} className="border-t border-ink-500"><td className="p-1">{e.id}</td><td>{e.name}</td><td>{e.task}</td><td>{e.dataset_version}</td><td className="text-xs">{Object.entries(e.metrics).map(([k, v]) => `${k}=${v}`).join(" · ")}</td><td className="text-xs">{new Date(e.created_at).toLocaleString()}</td></tr>)}</tbody></table></div>
            <p className="mt-2 text-xs text-paper-mute">{d.measured_vs_estimated}</p></section>
        </>
      )}
    </div>
  );
}
