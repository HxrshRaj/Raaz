import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { api, errorMessage } from "@/lib/api";
import { useAuth } from "@/lib/app-context";
import { Button, DialogContent, Dialog, Input, Tabs, TabsContent, TabsList, TabsTrigger } from "./ui";

export function AuthDialog({ open, onOpenChange, onDone }: { open: boolean; onOpenChange: (o: boolean) => void; onDone?: () => void }) {
  const { signIn } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const done = (r: Awaited<ReturnType<typeof api.guest>>) => { signIn(r.access_token, r.user); onOpenChange(false); onDone?.(); };
  const fail = (e: unknown) => setErr(errorMessage(e));
  const guest = useMutation({ mutationFn: () => api.guest(name || "Inspector"), onSuccess: done, onError: fail });
  const login = useMutation({ mutationFn: () => api.login(email, password), onSuccess: done, onError: fail });
  const reg = useMutation({ mutationFn: () => api.register(email, password, name || "Inspector"), onSuccess: done, onError: fail });
  const go = (m: { mutate: () => void }) => (e: React.FormEvent) => { e.preventDefault(); setErr(null); m.mutate(); };
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent title="Take the case" description="Your investigation is saved on the server so you can resume it anywhere.">
        <Tabs defaultValue="guest">
          <TabsList aria-label="How to sign in">
            <TabsTrigger value="guest">Play as guest</TabsTrigger>
            <TabsTrigger value="login">Sign in</TabsTrigger>
            <TabsTrigger value="register">Create account</TabsTrigger>
          </TabsList>
          <TabsContent value="guest" className="mt-4">
            <form onSubmit={go(guest)} className="space-y-3">
              <label className="block text-sm">Detective name<Input className="mt-1" value={name} onChange={(e) => setName(e.target.value)} placeholder="Inspector" maxLength={60} /></label>
              <p className="text-xs text-paper-mute">Guest progress lives on this server under a temporary identity tied to this browser. Create an account to keep it.</p>
              <Button type="submit" variant="brass" loading={guest.isPending}>Start as guest</Button>
            </form>
          </TabsContent>
          <TabsContent value="login" className="mt-4">
            <form onSubmit={go(login)} className="space-y-3">
              <label className="block text-sm">Email<Input className="mt-1" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></label>
              <label className="block text-sm">Password<Input className="mt-1" type="password" required value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="current-password" /></label>
              <Button type="submit" variant="brass" loading={login.isPending}>Sign in</Button>
            </form>
          </TabsContent>
          <TabsContent value="register" className="mt-4">
            <form onSubmit={go(reg)} className="space-y-3">
              <label className="block text-sm">Name<Input className="mt-1" required value={name} onChange={(e) => setName(e.target.value)} maxLength={60} /></label>
              <label className="block text-sm">Email<Input className="mt-1" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} autoComplete="email" /></label>
              <label className="block text-sm">Password (8+ characters)<Input className="mt-1" type="password" required minLength={8} maxLength={72} value={password} onChange={(e) => setPassword(e.target.value)} autoComplete="new-password" /></label>
              <Button type="submit" variant="brass" loading={reg.isPending}>Create account</Button>
            </form>
          </TabsContent>
        </Tabs>
        {err && <p role="alert" className="mt-3 text-sm text-blood-light">{err}</p>}
      </DialogContent>
    </Dialog>
  );
}
