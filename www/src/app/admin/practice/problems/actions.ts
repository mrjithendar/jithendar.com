"use server";

import { redirect } from "next/navigation";
import { staffActor } from "@/lib/admin";
import { flash } from "@/lib/flash";
import { saveProblem, setProblemStatus, validateProblem } from "@/lib/practice/admin";
import { PracticeError } from "@/lib/practice/errors";

const s = (f: FormData, k: string) => String(f.get(k) ?? "");

function parseProblemForm(form: FormData) {
  let tests: unknown;
  try {
    tests = JSON.parse(s(form, "tests") || "[]");
  } catch (e) {
    throw new PracticeError(`Test cases are not valid JSON: ${(e as Error).message}`);
  }
  return {
    slug: s(form, "slug"),
    title: s(form, "title"),
    difficulty: s(form, "difficulty"),
    roles: form.getAll("roles").map(String),
    topics: form.getAll("topics").map(String),
    minutes: s(form, "minutes"),
    dailyEligible: form.get("dailyEligible") === "on",
    description: s(form, "description"),
    constraints: s(form, "constraints"),
    ioInput: s(form, "ioInput"),
    ioOutput: s(form, "ioOutput"),
    entrypoint: s(form, "entrypoint"),
    starterCode: s(form, "starterCode"),
    prelude: s(form, "prelude"),
    comparator: s(form, "comparator"),
    tolerance: s(form, "tolerance") || "0.000001",
    hints: [s(form, "hint1"), s(form, "hint2"), s(form, "hint3")],
    solution: {
      code: s(form, "solutionCode"),
      explanation: s(form, "explanation"),
      time: s(form, "time"),
      space: s(form, "space"),
      alternatives: s(form, "alternatives"),
      edgeCases: s(form, "edgeCases"),
      production: s(form, "production"),
    },
    limits: { perTestSeconds: s(form, "perTestSeconds"), totalSeconds: s(form, "totalSeconds"), memoryMb: s(form, "memoryMb") },
    tests,
    note: s(form, "note"),
    allowDuplicate: form.get("allowDuplicate") === "on",
  };
}

export async function saveProblemAction(form: FormData) {
  const actor = await staffActor();
  const id = s(form, "id") || null;
  let savedId: string | null = null;
  await flash(id ? `/admin/practice/problems/${id}` : "/admin/practice/problems/new", async () => {
    savedId = await saveProblem(actor, id, parseProblemForm(form));
    if (!id) redirect(`/admin/practice/problems/${savedId}?ok=${encodeURIComponent("Problem created as a draft.")}`);
    return "Saved as a new version.";
  });
}

export async function statusAction(form: FormData) {
  const actor = await staffActor();
  const id = s(form, "id");
  const status = s(form, "status") as "draft" | "published" | "archived";
  await flash(`/admin/practice/problems/${id}`, async () => {
    await setProblemStatus(actor, id, status);
    return status === "published" ? "Published." : status === "archived" ? "Archived." : "Moved back to draft.";
  });
}

export async function validateAction(form: FormData) {
  const actor = await staffActor();
  const id = s(form, "id");
  await flash(`/admin/practice/problems/${id}`, async () => {
    const r = await validateProblem(actor, id, { fillExpected: form.get("fill") === "1" });
    if (!r.ok) throw new PracticeError(`Validation found problems: ${r.problems.slice(0, 5).join(" ")}`);
    return r.filled ? "Reference solution passes; missing expected outputs were filled in a new version." : "The reference solution passes every test.";
  });
}
