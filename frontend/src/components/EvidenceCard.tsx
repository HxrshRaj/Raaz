import { BookOpen, Camera, CircleHelp, Clock, FileText, Footprints, Key, MessageSquareQuote, Phone, ReceiptText, Search } from "lucide-react";
import type { TEvidence } from "@/lib/schemas";
import { cn, fmtDateTime, titleCase } from "@/lib/utils";
import { Badge } from "./ui";

const catIcon: Record<string, typeof FileText> = {
  timeline: Clock, financial: ReceiptText, access: Key, testimony: MessageSquareQuote, physical: Footprints, digital: Phone,
};
const relTone = (r: string) => (r === "verified" ? "green" : r === "altered" || r === "disputed" ? "red" : r === "testimony" ? "blue" : "neutral") as "green" | "red" | "blue" | "neutral";
export const stanceLabel: Record<string, string> = { points_to: "Points toward", clears: "Clears", undermines_claim: "Undermines a claim" };

export function CategoryIcon({ category, className }: { category: string; className?: string }) {
  const I = catIcon[category] ?? (category === "camera" ? Camera : BookOpen);
  return <I className={className} aria-hidden />;
}

export function EvidenceCard({ ev, selected, onClick, compact, children }: {
  ev: TEvidence; selected?: boolean; onClick?: () => void; compact?: boolean; children?: React.ReactNode;
}) {
  const Wrapper = onClick ? "button" : "div";
  return (
    <Wrapper
      type={onClick ? "button" : undefined}
      onClick={onClick}
      aria-pressed={onClick ? !!selected : undefined}
      className={cn(
        "paper-card block w-full p-3 text-left transition-transform",
        onClick && "hover:-translate-y-0.5 focus-visible:-translate-y-0.5",
        selected && "ring-2 ring-amber-glow",
      )}
    >
      <div className="flex items-start gap-2">
        <CategoryIcon category={ev.category} className="mt-0.5 h-4 w-4 shrink-0 text-brass-dark" />
        <div className="min-w-0 flex-1">
          <p className="font-display text-base font-bold leading-tight text-ink-900">{ev.name}</p>
          {!compact && <p className="mt-1 font-type text-[12.5px] leading-snug text-ink-700">{ev.description}</p>}
        </div>
        {!ev.examined && !ev.is_testimony && <span title="Not yet examined" className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-blood" />}
      </div>
      {!compact && (
        <div className="mt-2 flex flex-wrap gap-1">
          <Badge tone={relTone(ev.reliability)}>{titleCase(ev.reliability)}</Badge>
          <Badge>{titleCase(ev.category)}</Badge>
          {ev.contradiction_rules.length > 0 && <Badge tone="red">Contradiction</Badge>}
        </div>
      )}
      {children}
    </Wrapper>
  );
}

export function EvidenceDetail({ ev }: { ev: TEvidence }) {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge tone={relTone(ev.reliability)}>{titleCase(ev.reliability)}</Badge>
        <Badge>{titleCase(ev.category)}</Badge>
        {ev.examined ? <Badge tone="green">Examined</Badge> : <Badge tone="red">Not examined</Badge>}
      </div>
      <p className="typewriter">{ev.description}</p>
      {ev.examined_detail ? (
        <div className="rounded-md border border-amber-deep/50 bg-amber-glow/5 p-3">
          <p className="label mb-1 flex items-center gap-1 text-amber-glow"><Search className="h-3 w-3" /> Examination notes</p>
          <p className="typewriter">{ev.examined_detail}</p>
        </div>
      ) : (
        <p className="flex items-center gap-2 text-sm text-paper-mute"><CircleHelp className="h-4 w-4" /> Examine this item to read the fine detail.</p>
      )}
      <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
        <div><dt className="label">Found</dt><dd>{ev.location_name ?? "In conversation"} · {fmtDateTime(ev.discovered_at)}</dd></div>
        <div><dt className="label">Source</dt><dd>{ev.source}</dd></div>
        {ev.related_people.length > 0 && <div><dt className="label">Related people</dt><dd>{ev.related_people.map((p) => p.name).join(", ")}</dd></div>}
        {ev.related_events.length > 0 && <div><dt className="label">Related events</dt><dd>{ev.related_events.map((e) => e.title).join(" · ")}</dd></div>}
      </dl>
      {ev.timestamps.length > 0 && (
        <div>
          <p className="label mb-1">Timestamps</p>
          <ul className="space-y-1 text-sm">
            {ev.timestamps.map((t, i) => (
              <li key={i} className="flex flex-wrap items-center gap-2">
                <span className="font-type text-paper">{t.time}</span><Badge tone={t.clock === "ST" ? "amber" : "blue"}>{t.clock_label}</Badge>
                <span className="text-paper-mute">{t.label}</span>
                {t.real_time && t.clock === "ST" && <span className="text-emerald-300">= {t.real_time} real time</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
      {ev.bearing.length > 0 && (
        <div>
          <p className="label mb-1">Bearing on suspects</p>
          <ul className="space-y-1 text-sm">
            {ev.bearing.map((b, i) => (
              <li key={i}><Badge tone={b.stance === "clears" ? "green" : "red"}>{stanceLabel[b.stance] ?? b.stance}</Badge> <strong>{b.name}</strong> <span className="text-paper-mute">— {b.note}</span></li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
