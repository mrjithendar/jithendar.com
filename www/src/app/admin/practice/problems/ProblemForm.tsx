import { Button, Field, Input, Select, Textarea } from "@/components/ui/form";
import type { getAdminProblem } from "@/lib/practice/admin";
import type { RoleRow, TopicRow } from "@/lib/practice/catalog";
import { COMPARATORS, DIFFICULTIES, DIFFICULTY_INFO } from "@/lib/practice/types";
import { saveProblemAction } from "./actions";

type Data = Awaited<ReturnType<typeof getAdminProblem>> | null;

const mono = "font-mono !text-sm";

/** The problem editor (create and edit). Test cases are JSON so they can be pasted or uploaded in bulk. */
export function ProblemForm({ data, roles, topics }: { data: Data; roles: RoleRow[]; topics: TopicRow[] }) {
  const p = data?.problem;
  const v = data?.version;
  const tests = (data?.tests ?? []).map((t) => ({ visibility: t.visibility, example: t.isExample, args: t.args, kwargs: t.kwargs, ...(t.expected !== null ? { expected: t.expected } : {}), explanation: t.explanation, label: t.label }));
  const example = [
    { visibility: "public", example: true, args: [[1, 2, 3]], expected: 6, explanation: "Shown in the statement." },
    { visibility: "public", args: [[]], expected: 0 },
    { visibility: "hidden", args: [[-1, 1]] },
    { visibility: "hidden", args: [[10 ** 6]] },
  ];
  return (
    <form action={saveProblemAction} className="space-y-8">
      <input type="hidden" name="id" value={p?.id ?? ""} />
      <section className="grid gap-4 sm:grid-cols-2">
        <Field label="Title" htmlFor="title"><Input id="title" name="title" defaultValue={v?.title ?? ""} required /></Field>
        <Field label="Slug (URL)" htmlFor="slug"><Input id="slug" name="slug" defaultValue={p?.slug ?? ""} required className={mono} /></Field>
        <Field label="Difficulty" htmlFor="difficulty">
          <Select id="difficulty" name="difficulty" defaultValue={p?.difficulty ?? "easy"}>
            {DIFFICULTIES.map((d) => <option key={d} value={d}>{DIFFICULTY_INFO[d].label} — {DIFFICULTY_INFO[d].criteria}</option>)}
          </Select>
        </Field>
        <Field label="Estimated minutes" htmlFor="minutes"><Input id="minutes" name="minutes" type="number" defaultValue={p?.estimatedMinutes ?? 15} /></Field>
        <Field label="Roles" htmlFor="roles" hint="Ctrl/⌘-click to pick several.">
          <select id="roles" name="roles" multiple size={8} defaultValue={p?.roles ?? []} className="w-full rounded-lg border border-line-strong bg-surface p-2 text-sm">
            {roles.map((r) => <option key={r.slug} value={r.slug}>{r.name}</option>)}
          </select>
        </Field>
        <Field label="Topics" htmlFor="topics">
          <select id="topics" name="topics" multiple size={8} defaultValue={p?.topics ?? []} className="w-full rounded-lg border border-line-strong bg-surface p-2 text-sm">
            {topics.map((t) => <option key={t.slug} value={t.slug}>{t.name}</option>)}
          </select>
        </Field>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="dailyEligible" defaultChecked={p?.dailyEligible ?? true} /> Can be picked as the daily challenge</label>
      </section>
      <section className="space-y-4">
        <Field label="Statement (Markdown)" htmlFor="description"><Textarea id="description" name="description" rows={10} defaultValue={v?.description ?? ""} required /></Field>
        <Field label="Constraints (one per line)" htmlFor="constraints" optional><Textarea id="constraints" name="constraints" rows={3} defaultValue={v?.constraints.join("\n") ?? ""} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Input format" htmlFor="ioInput" optional><Input id="ioInput" name="ioInput" defaultValue={v?.io.input ?? ""} /></Field>
          <Field label="Output format" htmlFor="ioOutput" optional><Input id="ioOutput" name="ioOutput" defaultValue={v?.io.output ?? ""} /></Field>
        </div>
      </section>
      <section className="space-y-4">
        <div className="grid gap-4 sm:grid-cols-3">
          <Field label="Entry point (function or class name)" htmlFor="entrypoint"><Input id="entrypoint" name="entrypoint" defaultValue={v?.entrypoint ?? "solve"} className={mono} /></Field>
          <Field label="Comparison" htmlFor="comparator">
            <Select id="comparator" name="comparator" defaultValue={v?.comparator ?? "exact"}>
              {COMPARATORS.map((c) => <option key={c} value={c}>{c === "exact" ? "Exact" : c === "unordered" ? "Unordered list" : "Floats with tolerance"}</option>)}
            </Select>
          </Field>
          <Field label="Tolerance (floats)" htmlFor="tolerance"><Input id="tolerance" name="tolerance" defaultValue={String(v?.tolerance ?? 0.000001)} /></Field>
          <Field label="Seconds per test" htmlFor="perTestSeconds"><Input id="perTestSeconds" name="perTestSeconds" type="number" step="0.5" defaultValue={v?.limits.perTestSeconds ?? 2} /></Field>
          <Field label="Seconds per run" htmlFor="totalSeconds"><Input id="totalSeconds" name="totalSeconds" type="number" defaultValue={v?.limits.totalSeconds ?? 10} /></Field>
          <Field label="Memory (MB)" htmlFor="memoryMb"><Input id="memoryMb" name="memoryMb" type="number" defaultValue={v?.limits.memoryMb ?? 256} /></Field>
        </div>
        <Field label="Starter code" htmlFor="starterCode"><Textarea id="starterCode" name="starterCode" rows={8} defaultValue={v?.starterCode ?? "def solve():\n    pass\n"} className={mono} /></Field>
        <Field label="Prelude (helpers and optional __harness__(fn, *args), shown to users)" htmlFor="prelude" optional hint="Fakes for cloud SDKs, clocks or APIs. Never real credentials."><Textarea id="prelude" name="prelude" rows={6} defaultValue={v?.prelude ?? ""} className={mono} /></Field>
      </section>
      <section className="space-y-4">
        <h2 className="font-semibold text-fg">Hints and solution</h2>
        <Field label="Hint 1 — concept" htmlFor="hint1"><Textarea id="hint1" name="hint1" rows={2} defaultValue={v?.hints[0] ?? ""} /></Field>
        <Field label="Hint 2 — approach" htmlFor="hint2"><Textarea id="hint2" name="hint2" rows={2} defaultValue={v?.hints[1] ?? ""} /></Field>
        <Field label="Hint 3 — pseudocode or partial implementation" htmlFor="hint3"><Textarea id="hint3" name="hint3" rows={4} defaultValue={v?.hints[2] ?? ""} className={mono} /></Field>
        <Field label="Reference solution" htmlFor="solutionCode"><Textarea id="solutionCode" name="solutionCode" rows={10} defaultValue={v?.solution.code ?? ""} className={mono} /></Field>
        <Field label="Step-by-step explanation" htmlFor="explanation"><Textarea id="explanation" name="explanation" rows={4} defaultValue={v?.solution.explanation ?? ""} /></Field>
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Time complexity" htmlFor="time"><Input id="time" name="time" defaultValue={v?.solution.time ?? ""} /></Field>
          <Field label="Space complexity" htmlFor="space"><Input id="space" name="space" defaultValue={v?.solution.space ?? ""} /></Field>
        </div>
        <Field label="Alternative approaches (one per line)" htmlFor="alternatives"><Textarea id="alternatives" name="alternatives" rows={3} defaultValue={v?.solution.alternatives.join("\n") ?? ""} /></Field>
        <Field label="Edge cases (one per line)" htmlFor="edgeCases"><Textarea id="edgeCases" name="edgeCases" rows={3} defaultValue={v?.solution.edgeCases.join("\n") ?? ""} /></Field>
        <Field label="Production considerations (one per line)" htmlFor="production"><Textarea id="production" name="production" rows={3} defaultValue={v?.solution.production.join("\n") ?? ""} /></Field>
      </section>
      <section className="space-y-2">
        <h2 className="font-semibold text-fg">Test cases</h2>
        <p className="text-sm text-fg-muted">
          JSON array. Each case: <code>visibility</code> (public | hidden), <code>example</code> (shown in the statement), <code>args</code>, optional <code>kwargs</code>, <code>expected</code>, <code>explanation</code>.
          Omit <code>expected</code> and use “Validate and fill expected outputs” to compute it from the reference solution. Hidden cases are only ever read by the grader.
        </p>
        <Textarea id="tests" name="tests" rows={14} defaultValue={JSON.stringify(tests.length ? tests : example, null, 2)} className={mono} aria-label="Test cases (JSON)" />
      </section>
      <section className="flex flex-wrap items-center gap-4">
        <Field label="Change note" htmlFor="note" optional><Input id="note" name="note" placeholder="What changed in this version" /></Field>
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" name="allowDuplicate" /> Allow a similar problem (skip duplicate detection)</label>
        <Button type="submit">{p ? "Save new version" : "Create draft"}</Button>
      </section>
    </form>
  );
}
