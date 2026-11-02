import { Flash, type FlashParams } from "@/components/admin/Flash";
import { AdminHeader, Card } from "@/components/admin/ui";
import { Button, Field, Input, Select, Textarea } from "@/components/ui/form";
import { iconNames } from "@/components/icons";
import { staffActor } from "@/lib/admin";
import { flash } from "@/lib/flash";
import { saveRole, saveTopic, setDailyChallenge } from "@/lib/practice/admin";
import { listRoles, listTopics, publishedProblems, type RoleRow } from "@/lib/practice/catalog";
import { recentDailies } from "@/lib/practice/daily";
import { practiceDay } from "@/lib/practice/progress";
import { DIFFICULTIES, DIFFICULTY_INFO, SKILL_AREAS } from "@/lib/practice/types";
import { requireRole } from "@/lib/session";

export const metadata = { title: "Practice roles, topics and daily challenge" };
const PATH = "/admin/practice/catalog";
const s = (f: FormData, k: string) => String(f.get(k) ?? "");

async function roleAction(form: FormData) {
  "use server";
  const actor = await staffActor();
  await flash(PATH, async () => {
    await saveRole(actor, s(form, "original") || null, {
      slug: s(form, "slug"),
      name: s(form, "name"),
      description: s(form, "description"),
      icon: s(form, "icon"),
      competencies: s(form, "competencies"),
      learningPath: s(form, "learningPath"),
      topics: s(form, "topics"),
      scenarios: s(form, "scenarios"),
      libraries: s(form, "libraries"),
      mix: Object.fromEntries(DIFFICULTIES.map((d) => [d, s(form, `mix_${d}`) || "0"])),
      sort: s(form, "sort"),
      status: s(form, "status"),
    });
    return "Role saved.";
  });
}

async function topicAction(form: FormData) {
  "use server";
  const actor = await staffActor();
  await flash(PATH, async () => {
    await saveTopic(actor, { slug: s(form, "slug"), name: s(form, "name"), area: s(form, "area"), description: s(form, "description"), sort: s(form, "sort") || "100" });
    return "Topic saved.";
  });
}

async function dailyAction(form: FormData) {
  "use server";
  const actor = await staffActor();
  await flash(PATH, async () => {
    await setDailyChallenge(actor, s(form, "day"), s(form, "slug"));
    return "Daily challenge scheduled.";
  });
}

function RoleFields({ r }: { r?: RoleRow }) {
  const id = r?.slug ?? "new";
  return (
    <form action={roleAction} className="mt-4 grid gap-4 sm:grid-cols-2">
      <input type="hidden" name="original" value={r?.slug ?? ""} />
      <Field label="Name" htmlFor={`name-${id}`}><Input id={`name-${id}`} name="name" defaultValue={r?.name} required /></Field>
      <Field label="Slug" htmlFor={`slug-${id}`} hint="Renaming updates problems and learner preferences."><Input id={`slug-${id}`} name="slug" defaultValue={r?.slug} required /></Field>
      <div className="sm:col-span-2"><Field label="Description" htmlFor={`d-${id}`}><Textarea id={`d-${id}`} name="description" rows={2} defaultValue={r?.description} required /></Field></div>
      <Field label="Icon" htmlFor={`i-${id}`}><Select id={`i-${id}`} name="icon" defaultValue={r?.icon ?? "code"}>{iconNames.map((n) => <option key={n}>{n}</option>)}</Select></Field>
      <Field label="Visibility" htmlFor={`st-${id}`}><Select id={`st-${id}`} name="status" defaultValue={r?.status ?? "active"}><option value="active">Active</option><option value="hidden">Hidden</option></Select></Field>
      <Field label="Competencies (one per line)" htmlFor={`c-${id}`}><Textarea id={`c-${id}`} name="competencies" rows={4} defaultValue={r?.competencies.join("\n")} /></Field>
      <Field label="Learning path (one step per line)" htmlFor={`p-${id}`}><Textarea id={`p-${id}`} name="learningPath" rows={4} defaultValue={r?.learningPath.join("\n")} /></Field>
      <Field label="Interview scenarios (one per line)" htmlFor={`sc-${id}`}><Textarea id={`sc-${id}`} name="scenarios" rows={3} defaultValue={r?.scenarios.join("\n")} /></Field>
      <Field label="Topic slugs (space or comma separated)" htmlFor={`t-${id}`}><Textarea id={`t-${id}`} name="topics" rows={3} defaultValue={r?.topics.join(", ")} /></Field>
      <Field label="Libraries (comma separated)" htmlFor={`l-${id}`}><Input id={`l-${id}`} name="libraries" defaultValue={r?.libraries.join(", ")} /></Field>
      <Field label="Order" htmlFor={`o-${id}`}><Input id={`o-${id}`} name="sort" type="number" defaultValue={r?.sort ?? 100} /></Field>
      <fieldset className="sm:col-span-2">
        <legend className="text-sm font-medium text-fg">Difficulty mix (%)</legend>
        <div className="mt-2 grid grid-cols-5 gap-2">
          {DIFFICULTIES.map((d) => (
            <label key={d} className="text-xs text-fg-muted">{DIFFICULTY_INFO[d].label}<Input name={`mix_${d}`} type="number" min={0} max={100} defaultValue={r?.difficultyMix[d] ?? 0} /></label>
          ))}
        </div>
      </fieldset>
      <div><Button type="submit">{r ? "Save role" : "Add role"}</Button></div>
    </form>
  );
}

export default async function CatalogAdmin({ searchParams }: { searchParams: FlashParams }) {
  await requireRole("admin", "author");
  const [roles, topics, problems, dailies, sp] = await Promise.all([listRoles({ includeHidden: true }), listTopics(), publishedProblems(), recentDailies(14), searchParams]);
  return (
    <>
      <AdminHeader title="Roles, topics & daily challenge" description="Add engineering roles and topics without code changes. Roles drive the role pages, session filters and dashboards." />
      <Flash ok={sp.ok} error={sp.error} />
      <div className="space-y-6">
        <Card>
          <h2 className="font-semibold text-fg">Daily challenge</h2>
          <form action={dailyAction} className="mt-4 flex flex-wrap items-end gap-3">
            <Field label="Date (IST)" htmlFor="day"><Input id="day" name="day" type="date" defaultValue={practiceDay()} /></Field>
            <Field label="Problem" htmlFor="dslug">
              <Select id="dslug" name="slug">{problems.map((p) => <option key={p.slug} value={p.slug}>{p.title} ({p.difficulty})</option>)}</Select>
            </Field>
            <Button type="submit">Schedule</Button>
          </form>
          <ul className="mt-4 space-y-1 text-sm text-fg-muted">
            {dailies.map((d) => <li key={d.day}>{d.day}: {d.title} {d.chosenBy === "auto" ? "(automatic)" : "(scheduled)"}</li>)}
          </ul>
        </Card>
        <Card>
          <h2 className="font-semibold text-fg">Roles ({roles.length})</h2>
          <div className="mt-2 divide-y divide-line">
            {roles.map((r) => (
              <details key={r.slug} className="py-3">
                <summary className="cursor-pointer font-medium text-fg">{r.name} <span className="text-sm font-normal text-fg-subtle">/{r.slug}{r.status === "hidden" ? " · hidden" : ""}</span></summary>
                <RoleFields r={r} />
              </details>
            ))}
            <details className="py-3">
              <summary className="cursor-pointer font-medium text-accent-text">Add a role</summary>
              <RoleFields />
            </details>
          </div>
        </Card>
        <Card>
          <h2 className="font-semibold text-fg">Topics ({topics.length})</h2>
          <div className="mt-4 space-y-2">
            {[...topics, null].map((t) => (
              <form key={t?.slug ?? "new"} action={topicAction} className="grid items-end gap-2 sm:grid-cols-[1fr_1fr_1fr_6rem_auto]">
                <Input name="slug" defaultValue={t?.slug} placeholder="slug" aria-label="Slug" required readOnly={Boolean(t)} />
                <Input name="name" defaultValue={t?.name} placeholder="Name" aria-label="Name" required />
                <Select name="area" defaultValue={t?.area ?? "fundamentals"} aria-label="Skill area">{Object.entries(SKILL_AREAS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</Select>
                <Input name="sort" type="number" defaultValue={t?.sort ?? 100} aria-label="Order" />
                <Button type="submit" variant={t ? "secondary" : "primary"} size="sm">{t ? "Save" : "Add"}</Button>
              </form>
            ))}
          </div>
        </Card>
      </div>
    </>
  );
}
