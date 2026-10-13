import { z } from "zod";

const person = z.object({ key: z.string(), name: z.string() });

export const User = z.object({ id: z.string(), display_name: z.string(), is_guest: z.boolean(), email: z.string().nullable().optional() });
export const AuthResp = z.object({ access_token: z.string(), token_type: z.string(), user: User });

export const Progress = z.object({
  percent: z.number(), evidence: z.number(), examined: z.number(), contradictions: z.number(), interviewed: z.number(),
  suspects: z.number(), places_searched: z.number(), places_visible: z.number(),
});
export const LocationSummary = z.object({
  key: z.string(), name: z.string(), scene: z.string(), off_site: z.boolean(), locked: z.boolean(), unlock_hint: z.string(),
  description: z.string(), visible_hotspots: z.number(), searched_hotspots: z.number(),
});
export const Overview = z.object({
  id: z.string(), case_id: z.string(), case_title: z.string(), tagline: z.string(), mode: z.string(), status: z.string(),
  attempts: z.number(), max_attempts: z.number(), reputation: z.number(), hints_used: z.number(), actions: z.number(),
  version: z.number(), score: z.number().nullable(), created_at: z.string(), updated_at: z.string(), briefing: z.string(),
  progress: Progress,
  unreviewed_evidence: z.array(z.object({ key: z.string(), name: z.string() })),
  recent_discoveries: z.array(z.object({ key: z.string(), name: z.string() })),
  suspect_updates: z.array(z.object({ key: z.string(), name: z.string(), mood: z.string(), turns: z.number() })),
  locations: z.array(LocationSummary), clock_known: z.boolean(),
});
export const SessionRow = z.object({
  id: z.string(), case_id: z.string(), case_title: z.string(), mode: z.string(), status: z.string(), attempts: z.number(),
  progress: Progress, updated_at: z.string(), created_at: z.string(), score: z.number().nullable(),
});

export const Hotspot = z.object({
  key: z.string(), label: z.string(), x: z.number(), y: z.number(), w: z.number(), h: z.number(), icon: z.string(), searched: z.boolean(),
});
export const LocationDetail = z.object({
  key: z.string(), name: z.string(), description: z.string(), scene: z.string(), off_site: z.boolean(), hotspots: z.array(Hotspot),
});

export const Bearing = z.object({ character: z.string(), name: z.string(), stance: z.string(), aspect: z.string(), note: z.string() });
export const Timestamp = z.object({
  label: z.string(), clock: z.string(), clock_label: z.string(), time: z.string(), real_time: z.string().optional(),
});
export const Evidence = z.object({
  key: z.string(), name: z.string(), category: z.string(), description: z.string(), examined_detail: z.string().nullable(),
  source: z.string(), location_key: z.string().nullable(), location_name: z.string().nullable(),
  discovered_at: z.string().nullable(), discovered_via: z.string(), action_no: z.number(), examined: z.boolean(),
  reliability: z.string(), related_people: z.array(person), related_events: z.array(z.object({ key: z.string(), title: z.string() })),
  timestamps: z.array(Timestamp), bearing: z.array(Bearing), is_testimony: z.boolean(), icon: z.string(),
  contradiction_rules: z.array(z.string()),
});
export const Contradiction = z.object({
  key: z.string(), title: z.string(), explanation: z.string(), about: z.string(), about_name: z.string(), importance: z.number(),
  evidence: z.array(z.string()), found_via: z.string().nullable(), found_at: z.string().nullable(),
});
export const InspectResult = z.object({
  narration: z.string(), new_evidence: z.array(Evidence), already_found: z.array(z.string()),
  unlocked_locations: z.array(z.object({ key: z.string(), name: z.string(), via: z.string() })),
});
export const ExamineResult = z.object({ first_examination: z.boolean(), evidence: Evidence });
export const CheckResult = z.object({
  established: z.boolean(), newly_found: z.boolean(), contradiction: Contradiction.nullable(), message: z.string(),
});
export const EventCard = z.object({ key: z.string(), title: z.string(), description: z.string(), basis: z.array(z.string()) });
export const TimestampsResp = z.object({
  clock_known: z.boolean(),
  items: z.array(z.object({
    evidence_key: z.string(), evidence_name: z.string(), label: z.string(), clock: z.string(), clock_label: z.string(),
    time: z.string(), real_time: z.string().nullable(),
  })),
});

export const Portrait = z.object({
  skin: z.string(), hair: z.string(), outfit: z.string(), accent: z.string(), glasses: z.boolean(), beard: z.boolean(),
  hair_style: z.string(), age: z.string(),
});
export const DossierRow = z.object({
  key: z.string(), name: z.string(), role: z.string(), is_suspect: z.boolean(), portrait: Portrait, turns: z.number(),
  mood: z.string(), alibi_status: z.string(),
});
export const Dossier = z.object({
  key: z.string(), name: z.string(), role: z.string(), age: z.number(), is_suspect: z.boolean(),
  relationship_to_victim: z.string(), public_facts: z.array(z.string()), relationships: z.record(z.string()),
  portrait: Portrait, interview: z.object({ turns: z.number(), mood: z.string() }),
  statements: z.array(Evidence),
  evidence_connections: z.array(z.object({ key: z.string(), name: z.string(), stance: z.string(), note: z.string() })),
  alibi: z.object({ status: z.string(), statement: z.string(), window: z.string() }),
  unresolved_questions: z.array(z.string()),
});

export const LlmStatus = z.object({ enabled: z.boolean(), provider: z.string().nullable(), model: z.string().optional(), label: z.string() });
export const ChatMessage = z.object({
  id: z.string(), seq: z.number(), role: z.string(), content: z.string(), evidence_key: z.string().nullable(),
  created_at: z.string().nullable(), mode: z.string().nullable(),
});
export const ConvState = z.object({ mood: z.string(), trust: z.string(), turns: z.number() });
export const Conversation = z.object({
  character: z.object({ key: z.string(), name: z.string(), role: z.string(), portrait: Portrait }),
  messages: z.array(ChatMessage), state: ConvState, llm: LlmStatus, token_budget_used: z.number(), token_budget: z.number(),
});
export const MessageResult = z.object({
  player_message: ChatMessage, npc_message: ChatMessage, state: ConvState,
  generation: z.object({ mode: z.string(), provider: z.string().nullable(), model: z.string().nullable(), reason: z.string().nullable(), label: z.string() }),
  new_evidence: z.array(Evidence), contradictions: z.array(Contradiction), newly_found_contradictions: z.array(z.string()),
  unlocked_locations: z.array(z.object({ key: z.string(), name: z.string() })),
});

export const BoardItem = z.object({
  id: z.string(), kind: z.string(), ref_key: z.string(), label: z.string(), note: z.string(), x: z.number(), y: z.number(),
  predicted_category: z.string().nullable(),
});
export const BoardLink = z.object({
  id: z.string(), from: z.string(), to: z.string(), relation: z.string(), note: z.string(), validated: z.boolean(),
  rule_key: z.string().nullable(),
});
export const Board = z.object({ items: z.array(BoardItem), links: z.array(BoardLink), relations: z.array(z.string()) });
export const LinkResult = z.object({
  link: BoardLink, message: z.string(), newly_found_contradiction: z.boolean(), contradiction: Contradiction.nullable(),
});

export const TimelineEntry = z.object({
  id: z.string(), label: z.string(), time: z.string(), clock: z.string(), actor_key: z.string().nullable(),
  location_key: z.string().nullable(), evidence_keys: z.array(z.string()), real_time: z.string().nullable(),
});
export const TimelineIssue = z.object({ type: z.string(), severity: z.string(), entries: z.array(z.string()), message: z.string() });
export const Validation = z.object({ clock_known: z.boolean(), issues: z.array(TimelineIssue), ok: z.boolean() });
export const TimelineResp = z.object({ entries: z.array(TimelineEntry), validation: Validation });

const EvRef = z.object({ key: z.string(), name: z.string(), note: z.string(), aspect: z.string() });
export const HypothesisEval = z.object({
  strength: z.number(), supporting: z.array(EvRef), opposing: z.array(EvRef), undermined_claims: z.array(EvRef),
  contradictions: z.array(Contradiction),
  alibi: z.object({ status: z.string(), statement: z.string(), window: z.string() }).nullable(),
  open_questions: z.array(z.string()),
  motive_fit: z.object({
    label: z.string(), applies_to_suspect: z.boolean(), supporting_evidence: z.array(z.object({ key: z.string(), name: z.string() })),
  }).nullable(),
});
export const Hypothesis = z.object({
  id: z.string(), title: z.string(), culprit_key: z.string().nullable(), motive_key: z.string().nullable(),
  evidence_for: z.array(z.string()), evidence_against: z.array(z.string()), evaluation: z.any(), created_at: z.string(),
});

export const AccusationOptions = z.object({
  suspects: z.array(z.object({ key: z.string(), name: z.string(), role: z.string() })),
  motives: z.array(z.object({ key: z.string(), label: z.string(), description: z.string() })),
  events: z.array(EventCard), evidence: z.array(Evidence), contradictions: z.array(Contradiction),
  attempts: z.number(), max_attempts: z.number(), status: z.string(),
  rubric: z.array(z.object({ key: z.string(), label: z.string(), weight: z.number() })),
});
const Criterion = z.object({
  key: z.string(), label: z.string(), status: z.string(), points: z.number(), max: z.number(), message: z.string(),
  rows: z.array(z.object({
    key: z.string(), label: z.string(), status: z.string(), points: z.number(), max: z.number(),
    evidence: z.array(z.object({ key: z.string(), name: z.string() })),
  })).optional(),
}).passthrough();
export const AccusationResult = z.object({
  verdict: z.string(), score: z.number(), criteria: z.array(Criterion),
  evidence_annotations: z.array(z.object({ key: z.string(), name: z.string(), role: z.string(), note: z.string() })),
  next_steps: z.array(z.string()), closed: z.boolean(), accused: z.string(), attempt: z.number(), attempts_left: z.number(),
  status: z.string(), reputation_delta: z.number(), solution: z.string().optional(), consequence: z.string().optional(),
});

export const NazarResult = z.object({
  reply: z.string(), mode: z.string(), reason: z.string().nullable(), intent: z.string(), level: z.number(),
  structured: z.object({
    summary: z.string(), observed: z.array(z.object({ text: z.string(), refs: z.array(z.string()) })),
    interpretations: z.array(z.string()), speculation: z.array(z.string()), suggested_questions: z.array(z.string()),
  }),
  evidence_refs: z.array(z.object({ key: z.string(), name: z.string() })),
  sources: z.array(z.object({ ref: z.string(), title: z.string(), scope: z.string(), excerpt: z.string() })),
  hint_cost: z.number(), label: z.string(),
});
export const NazarMsg = z.object({ id: z.string(), role: z.string(), content: z.string(), level: z.number().nullable(), created_at: z.string() });

export const RunStep = z.object({
  idx: z.number(), node: z.string(), tool: z.string().nullable(), summary: z.string(), refs: z.array(z.string()),
  status: z.string(), duration_ms: z.number(),
});
export const Run = z.object({
  id: z.string(), question: z.string(), status: z.string(), plan: z.array(z.string()), iterations: z.number(),
  error: z.string().nullable(), result: z.any().nullable(), created_at: z.string(), finished_at: z.string().nullable(),
  steps: z.array(RunStep).optional(),
});
export const RunStart = z.object({ id: z.string(), status: z.string(), job_id: z.string() });

export const Leads = z.object({
  model: z.string(), disclaimer: z.string(),
  ranking: z.array(z.object({
    character: z.string(), name: z.string(), priority: z.number(), baseline: z.number(), reasons: z.array(z.string()), rank: z.number(),
  })),
});
export const Anomalies = z.object({
  available: z.boolean(), disclaimer: z.string(), message: z.string().optional(), model: z.string().optional(),
  findings: z.array(z.object({
    kind: z.string(), subject: z.string(), score: z.number(), reasons: z.array(z.string()), person: z.string().nullable().optional(),
    detail: z.string().optional(),
  })),
});
export const SystemInfo = z.object({ llm: LlmStatus, env: z.string(), version: z.string(), ml_workbench: z.boolean(), notes: z.string() });
export const Progress2 = z.object({ sessions: z.number(), solved: z.number(), best_score: z.number().nullable(), total_actions: z.number() });

export type TOverview = z.infer<typeof Overview>;
export type TEvidence = z.infer<typeof Evidence>;
export type TContradiction = z.infer<typeof Contradiction>;
export type TDossier = z.infer<typeof Dossier>;
export type TDossierRow = z.infer<typeof DossierRow>;
export type TPortrait = z.infer<typeof Portrait>;
export type TMessageResult = z.infer<typeof MessageResult>;
export type TBoard = z.infer<typeof Board>;
export type TAccusationResult = z.infer<typeof AccusationResult>;
export type TRun = z.infer<typeof Run>;
export type TLocationDetail = z.infer<typeof LocationDetail>;
export type TTimeline = z.infer<typeof TimelineResp>;
export type TNazar = z.infer<typeof NazarResult>;
