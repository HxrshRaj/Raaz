import { AnimatePresence, motion } from "framer-motion";
import { createContext, useCallback, useContext, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, CheckCircle2, Info, Search } from "lucide-react";
import { cn } from "@/lib/utils";

type Tone = "info" | "success" | "warn" | "clue";
type Toast = { id: number; title: string; body?: string; tone: Tone };
const Ctx = createContext<{ push: (t: Omit<Toast, "id">) => void } | null>(null);

const icon: Record<Tone, ReactNode> = {
  info: <Info className="h-4 w-4 text-sky-300" />, success: <CheckCircle2 className="h-4 w-4 text-emerald-400" />,
  warn: <AlertTriangle className="h-4 w-4 text-blood-light" />, clue: <Search className="h-4 w-4 text-amber-glow" />,
};

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((t: Omit<Toast, "id">) => {
    const id = Date.now() + Math.random();
    setItems((s) => [...s.slice(-3), { ...t, id }]);
    window.setTimeout(() => setItems((s) => s.filter((x) => x.id !== id)), 6500);
  }, []);
  const value = useMemo(() => ({ push }), [push]);
  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="pointer-events-none fixed bottom-4 right-4 z-[60] flex w-[min(92vw,360px)] flex-col gap-2" aria-live="polite" role="status">
        <AnimatePresence>
          {items.map((t) => (
            <motion.div key={t.id} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, x: 30 }}
              className={cn("pointer-events-auto rounded-lg border bg-ink-700/95 p-3 shadow-card backdrop-blur",
                t.tone === "clue" ? "border-amber-deep/70" : t.tone === "warn" ? "border-blood/60" : "border-ink-500")}>
              <div className="flex items-start gap-2">
                <span className="mt-0.5">{icon[t.tone]}</span>
                <div className="min-w-0"><p className="text-sm font-medium text-paper">{t.title}</p>{t.body && <p className="mt-0.5 text-xs text-paper-mute">{t.body}</p>}</div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </Ctx.Provider>
  );
}
export function useToast() {
  const c = useContext(Ctx);
  if (!c) throw new Error("ToastProvider missing");
  return c.push;
}
