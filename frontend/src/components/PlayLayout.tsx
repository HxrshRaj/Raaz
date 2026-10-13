import { Briefcase, Clock, Eye, Gavel, Home, Map, Network, Users, Volume2, VolumeX } from "lucide-react";
import { NavLink, Outlet, Link } from "react-router-dom";
import { useEffect } from "react";
import { lastSession, useSettings } from "@/lib/app-context";
import { cn } from "@/lib/utils";
import { useOverview, useSid } from "@/hooks/game";
import { NazarPanel } from "./AssistantPanels";
import { Rain } from "./Rain";
import { Badge, Button, Dialog, DialogContent, DialogTrigger, ErrorState, Skeleton } from "./ui";

const nav = [
  { to: ".", end: true, label: "Office", icon: Home },
  { to: "explore", label: "Explore", icon: Map },
  { to: "evidence", label: "Evidence", icon: Briefcase },
  { to: "suspects", label: "Suspects", icon: Users },
  { to: "board", label: "Board", icon: Network },
  { to: "timeline", label: "Timeline", icon: Clock },
  { to: "accuse", label: "Accuse", icon: Gavel },
] as const;

export function PlayLayout() {
  const sid = useSid();
  const ov = useOverview(sid);
  const { settings, update } = useSettings();
  useEffect(() => { lastSession.set(sid); }, [sid]);

  return (
    <div className="relative flex min-h-screen flex-col">
      <header className="sticky top-0 z-30 border-b border-ink-500/70 bg-ink-900/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center gap-3 px-4 py-2">
          <Link to="/" className="flex items-baseline gap-2" aria-label="RAAZ home">
            <span className="font-deva text-2xl text-brass-light">राज़</span>
            <span className="hidden font-display text-lg tracking-[0.3em] text-paper sm:inline">RAAZ</span>
          </Link>
          <nav aria-label="Investigation" className="-mx-1 flex flex-1 gap-1 overflow-x-auto px-1">
            {nav.map(({ to, label, icon: I, ...rest }) => (
              <NavLink key={label} to={to} end={"end" in rest} className={({ isActive }) =>
                cn("flex shrink-0 items-center gap-1.5 rounded-md px-3 py-2 text-sm transition-colors", isActive ? "bg-ink-500 text-brass-light" : "text-paper-mute hover:bg-ink-600 hover:text-paper")}>
                <I className="h-4 w-4" aria-hidden /> <span>{label}</span>
              </NavLink>
            ))}
          </nav>
          <div className="flex items-center gap-2">
            {ov.data && (
              <span className="hidden items-center gap-2 md:flex">
                <Badge tone={ov.data.status === "solved" ? "green" : "neutral"}>{ov.data.status === "solved" ? "Case closed" : `${ov.data.progress.percent}% explored`}</Badge>
                <Badge tone={ov.data.reputation < 80 ? "red" : "neutral"} title="Reputation drops after wrong accusations">Rep {ov.data.reputation}</Badge>
              </span>
            )}
            <Dialog>
              <DialogTrigger asChild><Button size="sm" variant="outline"><Eye className="h-4 w-4" aria-hidden /> Nazar</Button></DialogTrigger>
              <DialogContent title="Nazar · नज़र" description="Your analytical assistant" className="w-[min(94vw,720px)]"><NazarPanel sid={sid} /></DialogContent>
            </Dialog>
            <Button size="icon" variant="ghost" aria-label={settings.muted ? "Unmute sound" : "Mute sound"} onClick={() => update({ muted: !settings.muted })}>
              {settings.muted ? <VolumeX className="h-4 w-4" /> : <Volume2 className="h-4 w-4" />}
            </Button>
          </div>
        </div>
      </header>
      <main className="relative mx-auto w-full max-w-7xl flex-1 px-4 py-6">
        {ov.isLoading && <div className="space-y-3"><Skeleton className="h-10 w-1/2" /><Skeleton className="h-64" /></div>}
        {ov.error && (
          <div className="mx-auto max-w-lg space-y-3">
            <ErrorState error={ov.error} onRetry={() => ov.refetch()} />
            <Button asChild variant="outline"><Link to="/archive">Open the case archive</Link></Button>
          </div>
        )}
        {ov.data && <Outlet />}
      </main>
      <div className="pointer-events-none fixed inset-0 -z-10 opacity-60" aria-hidden><Rain count={40} opacity={0.5} /></div>
    </div>
  );
}
