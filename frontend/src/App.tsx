import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { lazy, Suspense } from "react";
import { BrowserRouter, MemoryRouter, Navigate, Route, Routes, useParams } from "react-router-dom";
import { PlayLayout } from "@/components/PlayLayout";
import { ToastProvider } from "@/components/Toasts";
import { Spinner, TooltipProvider } from "@/components/ui";
import { ApiError } from "@/lib/api";
import { AuthProvider, SettingsProvider, useAuth } from "@/lib/app-context";
import EvidencePage from "@/pages/Evidence";
import { ExploreIndex, ExploreLocation } from "@/pages/Explore";
import Interview from "@/pages/Interview";
import { Archive, NotFound, SettingsPage } from "@/pages/Misc";
import Office from "@/pages/Office";
import { SuspectDossier, SuspectList } from "@/pages/Suspects";
import Title from "@/pages/Title";

// Heavier screens are split out of the first bundle.
const BoardPage = lazy(() => import("@/pages/Board"));
const TimelinePage = lazy(() => import("@/pages/Timeline"));
const AccusePage = lazy(() => import("@/pages/Accuse"));
const Workbench = lazy(() => import("@/pages/Workbench"));

export function makeClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5_000, refetchOnWindowFocus: false,
        retry: (n, e) => !(e instanceof ApiError && e.status >= 400 && e.status < 500) && n < 2,
      },
    },
  });
}

function RequireAuth({ children }: { children: React.ReactNode }) {
  const { user, ready } = useAuth();
  if (!ready) return <div className="p-8"><Spinner label="Opening the case file" /></div>;
  if (!user) return <Navigate to="/" replace />;
  return <>{children}</>;
}

function Interview404() { const { sid } = useParams(); return <Navigate to={`/play/${sid}/suspects`} replace />; }

export function AppRoutes() {
  return (
    <Suspense fallback={<div className="p-8"><Spinner /></div>}>
      <Routes>
        <Route path="/" element={<Title />} />
        <Route path="/archive" element={<Archive />} />
        <Route path="/settings" element={<SettingsPage />} />
        <Route path="/workbench" element={<Workbench />} />
        <Route path="/play/:sid" element={<RequireAuth><PlayLayout /></RequireAuth>}>
          <Route index element={<Office />} />
          <Route path="explore" element={<ExploreIndex />} />
          <Route path="explore/:loc" element={<ExploreLocation />} />
          <Route path="evidence" element={<EvidencePage />} />
          <Route path="suspects" element={<SuspectList />} />
          <Route path="suspects/:key" element={<SuspectDossier />} />
          <Route path="interview" element={<Interview404 />} />
          <Route path="interview/:key" element={<Interview />} />
          <Route path="board" element={<BoardPage />} />
          <Route path="timeline" element={<TimelinePage />} />
          <Route path="accuse" element={<AccusePage />} />
        </Route>
        <Route path="*" element={<NotFound />} />
      </Routes>
    </Suspense>
  );
}

export function Providers({ children, client }: { children: React.ReactNode; client?: QueryClient }) {
  return (
    <QueryClientProvider client={client ?? makeClient()}>
      <SettingsProvider><AuthProvider><TooltipProvider><ToastProvider>{children}</ToastProvider></TooltipProvider></AuthProvider></SettingsProvider>
    </QueryClientProvider>
  );
}

export default function App() {
  return <Providers><BrowserRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}><AppRoutes /></BrowserRouter></Providers>;
}

export { MemoryRouter };
