/** Shared constants and types of the Python practice platform (safe to import from client components). */

export const DIFFICULTIES = ["beginner", "easy", "medium", "hard", "expert"] as const;
export type Difficulty = (typeof DIFFICULTIES)[number];

/** What each level means; shown on /python-practice and used by admins when classifying problems. */
export const DIFFICULTY_INFO: Record<Difficulty, { label: string; criteria: string; minutes: string }> = {
  beginner: { label: "Beginner", criteria: "Basic syntax, loops, strings, lists and dictionaries. One idea per problem.", minutes: "5–10 min" },
  easy: { label: "Easy", criteria: "Functions, collections, parsing and straightforward scripting with a few edge cases.", minutes: "10–15 min" },
  medium: {
    label: "Medium",
    criteria: "API integration against fakes, data processing, error handling, decorators and asyncio. Several cooperating parts.",
    minutes: "15–25 min",
  },
  hard: { label: "Hard", criteria: "Concurrency, resilience patterns, performance constraints and production-style automation.", minutes: "25–40 min" },
  expert: {
    label: "Expert",
    criteria: "Distributed-systems behaviour, resilient AI gateways, agent orchestration and scheduling — complete, working implementations.",
    minutes: "45–60 min",
  },
};

export const MODES = ["guided", "timed", "mock", "adaptive", "daily"] as const;
export type Mode = (typeof MODES)[number];

export const MODE_INFO: Record<Mode, { label: string; description: string }> = {
  guided: { label: "Guided practice", description: "No timer. Hints, solutions, notes and as many runs as you like." },
  timed: { label: "Timed assessment", description: "A fixed set of questions against a server-side countdown. Unsubmitted work is finalised when time runs out." },
  mock: { label: "Mock interview", description: "Questions one at a time with structured feedback on correctness, quality, efficiency and testing." },
  adaptive: { label: "Adaptive practice", description: "Questions chosen from your recorded weak topics, with the reason for each choice." },
  daily: { label: "Daily challenge", description: "One curated question per day. Solve it to extend your streak." },
};

export const TIMED_DURATIONS = [15, 30, 45, 60] as const;

/** The dashboard's skill areas; every topic belongs to one (practice_topic.area). */
export const SKILL_AREAS = {
  fundamentals: "Python fundamentals",
  "data-structures": "Data structures",
  algorithms: "Algorithms",
  async: "Async Python",
  api: "API development",
  automation: "Automation",
  cloud: "Cloud SDKs",
  ai: "AI engineering",
  "data-processing": "Data processing",
  "error-handling": "Error handling",
  testing: "Testing",
  performance: "Performance optimisation",
} as const;
export type SkillArea = keyof typeof SKILL_AREAS;

export const VERDICTS = {
  accepted: "Accepted",
  wrong_answer: "Wrong answer",
  runtime_error: "Runtime error",
  timeout: "Time limit exceeded",
  memory: "Memory limit exceeded",
  syntax_error: "Syntax error",
  missing_entrypoint: "Missing function",
  infrastructure_error: "Could not run",
  cancelled: "Cancelled",
} as const;
export type Verdict = keyof typeof VERDICTS;

export const COMPARATORS = ["exact", "unordered", "float"] as const;
export type Comparator = (typeof COMPARATORS)[number];

/** Public view of a problem: never hints, solutions, hidden tests or expected outputs of non-example tests. */
export type PublicProblem = {
  id: string;
  slug: string;
  title: string;
  difficulty: Difficulty;
  roles: string[];
  topics: string[];
  minutes: number;
  version: number;
  description: string;
  constraints: string[];
  io: { input?: string; output?: string };
  entrypoint: string;
  starterCode: string;
  prelude: string;
  comparator: Comparator;
  examples: { args: unknown[]; kwargs: Record<string, unknown>; expected: unknown; explanation: string; label: string }[];
  hintCount: number;
  publicTestCount: number;
  hiddenTestCount: number;
};

export type ProblemSummary = {
  slug: string;
  title: string;
  difficulty: Difficulty;
  roles: string[];
  topics: string[];
  minutes: number;
};

export type UserProblemState = "solved" | "solved_assisted" | "attempted" | null;
