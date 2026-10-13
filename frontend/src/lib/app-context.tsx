import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api, tokenStore } from "./api";
import { sound } from "./audio";

export type User = { id: string; display_name: string; is_guest: boolean; email?: string | null };

type AuthCtx = {
  user: User | null;
  ready: boolean;
  signIn: (token: string, user: User) => void;
  signOut: () => void;
};
const Auth = createContext<AuthCtx | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let alive = true;
    if (!tokenStore.get()) { setReady(true); return; }
    api.me().then((u) => alive && setUser(u)).catch(() => tokenStore.set(null)).finally(() => alive && setReady(true));
    return () => { alive = false; };
  }, []);

  useEffect(() => {
    const h = () => { tokenStore.set(null); setUser(null); };
    window.addEventListener("raaz:unauthorized", h);
    return () => window.removeEventListener("raaz:unauthorized", h);
  }, []);

  const signIn = useCallback((token: string, u: User) => { tokenStore.set(token); setUser(u); }, []);
  const signOut = useCallback(() => { tokenStore.set(null); setUser(null); }, []);
  const value = useMemo(() => ({ user, ready, signIn, signOut }), [user, ready, signIn, signOut]);
  return <Auth.Provider value={value}>{children}</Auth.Provider>;
}
export function useAuth() {
  const c = useContext(Auth);
  if (!c) throw new Error("AuthProvider missing");
  return c;
}

// ---------------------------------------------------------------- settings (per-browser convenience only)
export type Settings = { muted: boolean; volume: number; ambient: boolean; sfx: boolean; reduceMotion: boolean; typewriter: boolean };
const DEFAULTS: Settings = { muted: true, volume: 0.5, ambient: true, sfx: true, reduceMotion: false, typewriter: true };
const KEY = "raaz.settings";

function load(): Settings {
  try { return { ...DEFAULTS, ...(JSON.parse(localStorage.getItem(KEY) ?? "{}") as Partial<Settings>) }; } catch { return DEFAULTS; }
}

type SettingsCtx = { settings: Settings; update: (p: Partial<Settings>) => void };
const SettingsC = createContext<SettingsCtx | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(load);
  const update = useCallback((p: Partial<Settings>) => {
    setSettings((s) => {
      const n = { ...s, ...p };
      try { localStorage.setItem(KEY, JSON.stringify(n)); } catch { /* storage unavailable */ }
      return n;
    });
  }, []);

  useEffect(() => {
    sound.muted = settings.muted; sound.volume = settings.volume; sound.sfx = settings.sfx; sound.apply();
    if (!settings.muted && settings.ambient) sound.start();
    if (settings.muted || !settings.ambient) sound.stop();
    document.documentElement.dataset.reduceMotion = String(settings.reduceMotion);
  }, [settings]);

  const value = useMemo(() => ({ settings, update }), [settings, update]);
  return <SettingsC.Provider value={value}>{children}</SettingsC.Provider>;
}
export function useSettings() {
  const c = useContext(SettingsC);
  if (!c) throw new Error("SettingsProvider missing");
  return c;
}

// ---------------------------------------------------------------- last-opened investigation (resume)
const SID = "raaz.session";
export const lastSession = {
  get(): string | null { try { return localStorage.getItem(SID); } catch { return null; } },
  set(id: string | null) { try { if (id) localStorage.setItem(SID, id); else localStorage.removeItem(SID); } catch { /* ignore */ } },
};
