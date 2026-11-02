import "server-only";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";
import { eq, inArray, sql } from "drizzle-orm";
import { getDb, schema, type Db } from "@/db";
import { log } from "../log";
import type { PracticeLimits, PracticeSolution } from "@/db/schema";
import type { Difficulty } from "./types";

/**
 * Loads content/python-practice/catalog.generated.json (built and verified by executor/tools/build_problems.py)
 * into the database. Idempotent and safe with several replicas (transaction-scoped advisory lock):
 * - roles and topics are inserted once; admins own them afterwards;
 * - a new problem is inserted as version 1, published;
 * - a seed problem whose content changed gets a new version (old versions stay for old submissions);
 * - problems edited in the admin (source "admin") are never touched again.
 */
const LOCK_ID = 7_250_032;

type SeedTest = { visibility: "public" | "hidden"; example: boolean; args: unknown[]; kwargs: Record<string, unknown>; expected: unknown; explanation: string; label: string };
type SeedProblem = {
  slug: string;
  title: string;
  difficulty: Difficulty;
  roles: string[];
  topics: string[];
  minutes: number;
  entrypoint: string;
  description: string;
  constraints?: string[];
  io?: { input?: string; output?: string };
  starter: string;
  prelude?: string;
  comparator: string;
  tolerance?: number;
  hints: string[];
  solution: { code: string; explanation: string; time: string; space: string; alternatives: string[]; edge_cases: string[]; production: string[]; alternative_code?: string[] };
  tests: SeedTest[];
  content_hash: string;
};
type SeedRole = { slug: string; name: string; icon: string; description: string; competencies: string[]; path: string[]; topics: string[]; mix: Record<string, number>; scenarios: string[]; libraries: string[] };
type SeedTopic = { slug: string; name: string; area: string };
export type Catalog = { schema: number; roles: SeedRole[]; topics: SeedTopic[]; problems: SeedProblem[] };

export const DEFAULT_LIMITS: Record<Difficulty, PracticeLimits> = {
  beginner: { perTestSeconds: 2, totalSeconds: 10, memoryMb: 256 },
  easy: { perTestSeconds: 2, totalSeconds: 10, memoryMb: 256 },
  medium: { perTestSeconds: 3, totalSeconds: 15, memoryMb: 256 },
  hard: { perTestSeconds: 4, totalSeconds: 20, memoryMb: 256 },
  expert: { perTestSeconds: 5, totalSeconds: 20, memoryMb: 256 },
};

export function catalogPath(): string {
  return process.env.PRACTICE_CATALOG_PATH ?? path.join(/*turbopackIgnore: true*/ process.cwd(), "content", "python-practice", "catalog.generated.json");
}

export function readCatalog(file = catalogPath()): Catalog {
  return JSON.parse(fs.readFileSync(file, "utf8")) as Catalog;
}

export function solutionOf(p: SeedProblem): PracticeSolution {
  const s = p.solution;
  return { code: s.code, explanation: s.explanation, time: s.time, space: s.space, alternatives: s.alternatives, edgeCases: s.edge_cases, production: s.production, ...(s.alternative_code?.length ? { alternativeCode: s.alternative_code } : {}) };
}

export const contentHash = (value: unknown) => createHash("sha256").update(JSON.stringify(value)).digest("hex");

type Tx = Parameters<Parameters<Db["transaction"]>[0]>[0];

async function insertVersion(tx: Tx, problemId: string, version: number, p: SeedProblem) {
  await tx.insert(schema.practiceProblemVersion).values({
    problemId,
    version,
    title: p.title,
    description: p.description,
    entrypoint: p.entrypoint,
    starterCode: p.starter,
    prelude: p.prelude ?? "",
    comparator: p.comparator,
    tolerance: p.tolerance ?? 1e-6,
    constraints: p.constraints ?? [],
    io: p.io ?? {},
    hints: p.hints,
    solution: solutionOf(p),
    limits: DEFAULT_LIMITS[p.difficulty],
    contentHash: p.content_hash,
    note: version === 1 ? "Seeded from the repository catalog." : "Updated from the repository catalog.",
  });
  await tx.insert(schema.practiceTestCase).values(
    p.tests.map((t, i) => ({
      problemId,
      version,
      ordinal: i,
      visibility: t.visibility,
      isExample: t.example,
      label: t.label ?? "",
      explanation: t.explanation ?? "",
      args: t.args ?? [],
      kwargs: t.kwargs ?? {},
      expected: t.expected ?? null,
    })),
  );
}

export async function seedPractice(catalog: Catalog = readCatalog()): Promise<{ created: number; updated: number }> {
  const db = await getDb();
  return db.transaction(async (tx) => {
    await tx.execute(sql`select pg_advisory_xact_lock(${LOCK_ID})`);
    if (catalog.roles.length) {
      await tx
        .insert(schema.practiceRole)
        .values(
          catalog.roles.map((r, i) => ({
            slug: r.slug,
            name: r.name,
            description: r.description,
            icon: r.icon,
            competencies: r.competencies,
            learningPath: r.path,
            topics: r.topics,
            difficultyMix: r.mix,
            scenarios: r.scenarios,
            libraries: r.libraries,
            sort: (i + 1) * 10,
          })),
        )
        .onConflictDoNothing();
    }
    if (catalog.topics.length) {
      await tx
        .insert(schema.practiceTopic)
        .values(catalog.topics.map((t, i) => ({ slug: t.slug, name: t.name, area: t.area, sort: (i + 1) * 10 })))
        .onConflictDoNothing();
    }
    const slugs = catalog.problems.map((p) => p.slug);
    const existing = slugs.length ? await tx.select().from(schema.practiceProblem).where(inArray(schema.practiceProblem.slug, slugs)) : [];
    const bySlug = new Map(existing.map((e) => [e.slug, e]));
    let created = 0;
    let updated = 0;
    for (const p of catalog.problems) {
      const row = bySlug.get(p.slug);
      if (!row) {
        const [inserted] = await tx
          .insert(schema.practiceProblem)
          .values({ slug: p.slug, title: p.title, difficulty: p.difficulty, roles: p.roles, topics: p.topics, estimatedMinutes: p.minutes, status: "published", source: "seed", seedHash: p.content_hash, publishedAt: new Date() })
          .returning({ id: schema.practiceProblem.id });
        await insertVersion(tx, inserted!.id, 1, p);
        created++;
      } else if (row.source === "seed" && row.seedHash !== p.content_hash) {
        const version = row.currentVersion + 1;
        await insertVersion(tx, row.id, version, p);
        await tx
          .update(schema.practiceProblem)
          .set({ title: p.title, difficulty: p.difficulty, roles: p.roles, topics: p.topics, estimatedMinutes: p.minutes, currentVersion: version, seedHash: p.content_hash, updatedAt: new Date() })
          .where(eq(schema.practiceProblem.id, row.id));
        updated++;
      }
    }
    return { created, updated };
  });
}

const g = globalThis as unknown as { __practiceSeed?: Promise<void> };

/** Seed once per process (instrumentation at start-up; lazily on first use in development and tests). */
export function ensurePracticeSeeded(): Promise<void> {
  g.__practiceSeed ??= (async () => {
    const started = Date.now();
    const result = await seedPractice();
    if (result.created || result.updated) log.info("practice catalog seeded", { ...result, ms: Date.now() - started });
  })().catch((err) => {
    g.__practiceSeed = undefined;
    throw err;
  });
  return g.__practiceSeed;
}

/** Tests: forget that this process already seeded. */
export function resetPracticeSeed() {
  g.__practiceSeed = undefined;
}
