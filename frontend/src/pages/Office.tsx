import { Lock, MapPin, NotebookPen, Users } from "lucide-react";
import { Link } from "react-router-dom";
import { InvestigationPanel, LeadsPanel } from "@/components/AssistantPanels";
import { SceneArt } from "@/components/SceneArt";
import { Badge, Button } from "@/components/ui";
import { useOverview, useSid } from "@/hooks/game";
import { cn, titleCase } from "@/lib/utils";

function Ring({ value }: { value: number }) {
  const r = 38, c = 2 * Math.PI * r;
  return (
    <svg viewBox="0 0 100 100" className="h-24 w-24" role="img" aria-label={`${value}% of the case explored`}>
      <circle cx="50" cy="50" r={r} fill="none" stroke="#1d2636" strokeWidth="9" />
      <circle cx="50" cy="50" r={r} fill="none" stroke="#b8924f" strokeWidth="9" strokeLinecap="round" strokeDasharray={c} strokeDashoffset={c * (1 - value / 100)} transform="rotate(-90 50 50)" />
      <text x="50" y="56" textAnchor="middle" className="fill-paper font-display" fontSize="24">{value}%</text>
    </svg>
  );
}

export default function Office() {
  const sid = useSid();
  const { data: ov } = useOverview(sid);
  if (!ov) return null;
  const p = ov.progress;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_380px]">
      <div className="space-y-6">
        <section className="panel overflow-hidden">
          <div className="relative h-40 sm:h-52">
            <SceneArt scene="office" className="absolute inset-0 h-full w-full" />
            <div className="absolute inset-0 bg-gradient-to-t from-ink-700 via-ink-700/30 to-transparent" />
            <div className="absolute bottom-3 left-5 right-5 flex items-end justify-between gap-4">
              <div>
                <p className="label">Detective's office · Devgarh</p>
                <h1 className="font-display text-3xl text-paper sm:text-4xl">{ov.case_title}</h1>
                <p className="text-sm italic text-amber-glow">{ov.tagline}</p>
              </div>
              <Ring value={p.percent} />
            </div>
          </div>
          <div className="grid gap-6 p-5 md:grid-cols-[1.4fr_1fr]">
            <div className="paper-card p-4">
              <p className="mb-1 flex items-center gap-2 font-type text-xs uppercase tracking-widest text-brass-dark"><NotebookPen className="h-3.5 w-3.5" /> Police briefing</p>
              {ov.briefing.split("\n\n").map((para, i) => <p key={i} className="mb-2 font-type text-[13px] leading-relaxed text-ink-800">{para}</p>)}
            </div>
            <dl className="grid grid-cols-2 content-start gap-3 text-sm">
              {[["Evidence", `${p.evidence}`], ["Examined", `${p.examined}`], ["Contradictions", `${p.contradictions}`],
                ["Interviews", `${p.interviewed}/${p.suspects}`], ["Places searched", `${p.places_searched}/${p.places_visible}`],
                ["Accusations", `${ov.attempts}/${ov.max_attempts}`], ["Reputation", `${ov.reputation}`], ["Hint cost", `${ov.hints_used}`]].map(([k, v]) => (
                <div key={k} className="rounded-md border border-ink-500 bg-ink-800/60 p-2.5"><dt className="label">{k}</dt><dd className="font-display text-2xl text-paper">{v}</dd></div>
              ))}
            </dl>
          </div>
          {ov.status === "solved" && (
            <div className="border-t border-emerald-700/40 bg-emerald-700/10 p-4 text-sm text-emerald-200">Case closed · final score {ov.score}. You can still review your notes.</div>
          )}
        </section>

        <section aria-labelledby="places" className="space-y-3">
          <h2 id="places" className="panel-title">Places</h2>
          <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {ov.locations.map((l) => (
              <li key={l.key}>
                {l.locked ? (
                  <div className="relative overflow-hidden rounded-lg border border-ink-500 bg-ink-800/70">
                    <div className="h-24 opacity-30 grayscale"><SceneArt scene={l.scene} className="h-full w-full" /></div>
                    <div className="p-3"><p className="flex items-center gap-2 text-sm font-medium text-paper-mute"><Lock className="h-3.5 w-3.5" /> {l.name}</p><p className="mt-1 text-xs text-paper-mute">{l.unlock_hint ? "Locked — something you find may lead here." : "Locked"}</p></div>
                  </div>
                ) : (
                  <Link to={`explore/${l.key}`} className="group block overflow-hidden rounded-lg border border-ink-500 bg-ink-800/70 transition hover:border-brass focus-visible:border-brass">
                    <div className="h-24"><SceneArt scene={l.scene} className="h-full w-full transition group-hover:scale-105" /></div>
                    <div className="p-3">
                      <p className="flex items-center gap-2 text-sm font-medium text-paper"><MapPin className="h-3.5 w-3.5 text-brass-light" /> {l.name}</p>
                      <p className="mt-1 text-xs text-paper-mute">{l.searched_hotspots}/{l.visible_hotspots} details searched{l.off_site && " · off-site"}</p>
                    </div>
                  </Link>
                )}
              </li>
            ))}
          </ul>
        </section>

        <div className="grid gap-6 md:grid-cols-2">
          <section className="panel p-5" aria-labelledby="unrev">
            <h2 id="unrev" className="panel-title mb-3">Unreviewed evidence</h2>
            {ov.unreviewed_evidence.length === 0 ? <p className="text-sm text-paper-mute">Nothing waiting. Examine new finds under the lens.</p> : (
              <ul className="space-y-1.5">{ov.unreviewed_evidence.map((e) => <li key={e.key}><Link className="flex items-center gap-2 text-sm hover:text-brass-light" to={`evidence?open=${e.key}`}><span className="h-2 w-2 rounded-full bg-blood" /> {e.name}</Link></li>)}</ul>
            )}
          </section>
          <section className="panel p-5" aria-labelledby="recent">
            <h2 id="recent" className="panel-title mb-3">Recent discoveries</h2>
            {ov.recent_discoveries.length === 0 ? <p className="text-sm text-paper-mute">Nothing yet — start at the platform.</p> : (
              <ul className="space-y-1.5 text-sm">{ov.recent_discoveries.map((e) => <li key={e.key}>• {e.name}</li>)}</ul>
            )}
          </section>
        </div>
      </div>

      <aside className="space-y-6">
        <section className="panel p-5" aria-labelledby="sus">
          <h2 id="sus" className="panel-title mb-3 flex items-center gap-2"><Users className="h-5 w-5" /> Suspect updates</h2>
          {ov.suspect_updates.length === 0 ? <p className="text-sm text-paper-mute">You haven't interviewed anyone yet.</p> : (
            <ul className="space-y-2">{ov.suspect_updates.map((s) => (
              <li key={s.key} className="flex items-center justify-between text-sm"><Link to={`interview/${s.key}`} className="hover:text-brass-light">{s.name}</Link>
                <span className="flex items-center gap-2"><Badge tone={["hostile", "cornered", "defensive"].includes(s.mood) ? "red" : "neutral"}>{titleCase(s.mood)}</Badge><span className="text-xs text-paper-mute">{s.turns} turns</span></span></li>
            ))}</ul>
          )}
          <Button asChild variant="outline" className="mt-4 w-full"><Link to="suspects">Open dossiers</Link></Button>
        </section>
        <section className={cn("panel p-5")}><LeadsPanel sid={sid} /></section>
        <section className="panel p-5"><InvestigationPanel sid={sid} /></section>
      </aside>
    </div>
  );
}
