import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useParams } from "react-router-dom";
import { api } from "@/lib/api";

export function useSid(): string {
  const { sid } = useParams();
  if (!sid) throw new Error("No investigation selected");
  return sid;
}

export const keys = {
  overview: (s: string) => ["overview", s] as const,
  locations: (s: string) => ["locations", s] as const,
  location: (s: string, l: string) => ["location", s, l] as const,
  evidence: (s: string) => ["evidence", s] as const,
  contradictions: (s: string) => ["contradictions", s] as const,
  events: (s: string) => ["events", s] as const,
  dossiers: (s: string) => ["dossiers", s] as const,
  dossier: (s: string, k: string) => ["dossier", s, k] as const,
  conversation: (s: string, k: string) => ["conversation", s, k] as const,
  board: (s: string) => ["board", s] as const,
  timeline: (s: string) => ["timeline", s] as const,
  timestamps: (s: string) => ["timestamps", s] as const,
  options: (s: string) => ["accusation-options", s] as const,
  nazar: (s: string) => ["nazar", s] as const,
  runs: (s: string) => ["runs", s] as const,
  leads: (s: string) => ["leads", s] as const,
  anomalies: (s: string) => ["anomalies", s] as const,
  hypotheses: (s: string) => ["hypotheses", s] as const,
};

/** Invalidate everything derived from game state after any action that can change it. */
export function useRefreshGame(sid: string) {
  const qc = useQueryClient();
  return useCallback(() => {
    for (const k of ["overview", "locations", "location", "evidence", "contradictions", "events", "dossiers", "dossier", "board",
      "timeline", "timestamps", "accusation-options", "leads", "anomalies", "hypotheses"]) {
      void qc.invalidateQueries({ queryKey: [k, sid] });
    }
  }, [qc, sid]);
}

export const useOverview = (sid: string) => useQuery({ queryKey: keys.overview(sid), queryFn: () => api.overview(sid) });
export const useEvidence = (sid: string) => useQuery({ queryKey: keys.evidence(sid), queryFn: () => api.evidence(sid) });
export const useContradictions = (sid: string) => useQuery({ queryKey: keys.contradictions(sid), queryFn: () => api.contradictions(sid) });
export const useDossiers = (sid: string) => useQuery({ queryKey: keys.dossiers(sid), queryFn: () => api.dossiers(sid) });
export const useBoard = (sid: string) => useQuery({ queryKey: keys.board(sid), queryFn: () => api.board(sid) });
