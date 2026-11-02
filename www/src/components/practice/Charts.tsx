/**
 * Small, dependency-free charts for the practice dashboard (server-rendered SVG/HTML).
 * One series each, in the site accent (no legend needed; the heading names the series). Every mark has a
 * hover tooltip (title) and every chart has a text equivalent, so nothing depends on colour or hover alone.
 */

/** GitHub-style activity calendar: 53 weeks × 7 days, one hue light → dark (sequential). */
export function ActivityHeatmap({ days, today }: { days: { day: string; n: number }[]; today: string }) {
  const counts = new Map(days.map((d) => [d.day, d.n]));
  const end = new Date(`${today}T12:00:00Z`);
  const start = new Date(end);
  start.setUTCDate(start.getUTCDate() - 364 - end.getUTCDay());
  const cells: { day: string; n: number; x: number; y: number }[] = [];
  for (let d = new Date(start), i = 0; d <= end; d.setUTCDate(d.getUTCDate() + 1), i++) {
    const day = d.toISOString().slice(0, 10);
    cells.push({ day, n: counts.get(day) ?? 0, x: Math.floor(i / 7), y: i % 7 });
  }
  const max = Math.max(1, ...cells.map((c) => c.n));
  const level = (n: number) => (n === 0 ? 0 : Math.min(4, Math.ceil((n / max) * 4)));
  const fills = ["var(--color-surface-sunken)", "color-mix(in oklab, var(--color-accent) 30%, var(--color-surface))", "color-mix(in oklab, var(--color-accent) 55%, var(--color-surface))", "color-mix(in oklab, var(--color-accent) 78%, var(--color-surface))", "var(--color-accent)"];
  const activeDays = cells.filter((c) => c.n > 0).length;
  const total = cells.reduce((s, c) => s + c.n, 0);
  const size = 11;
  const gap = 2;
  return (
    <figure>
      <div className="overflow-x-auto">
        <svg width={(cells.at(-1)!.x + 1) * (size + gap)} height={7 * (size + gap)} role="img" aria-label={`${total} graded runs and submissions on ${activeDays} days in the last year`}>
          {cells.map((c) => (
            <rect key={c.day} x={c.x * (size + gap)} y={c.y * (size + gap)} width={size} height={size} rx={2} fill={fills[level(c.n)]}>
              <title>{`${c.day}: ${c.n} ${c.n === 1 ? "activity" : "activities"}`}</title>
            </rect>
          ))}
        </svg>
      </div>
      <figcaption className="mt-2 flex flex-wrap items-center gap-2 text-xs text-fg-subtle">
        <span>
          {activeDays} active days · {total} graded runs and submissions in the last year
        </span>
        <span className="ml-auto flex items-center gap-1" aria-hidden="true">
          Less
          {fills.map((f) => (
            <span key={f} className="inline-block h-2.5 w-2.5 rounded-sm" style={{ background: f }} />
          ))}
          More
        </span>
      </figcaption>
    </figure>
  );
}

/** Vertical bars over time (one series). Values are labelled on hover and listed in a details table. */
export function TimeBars({ data, unit, label }: { data: { key: string; value: number | null; caption?: string }[]; unit: string; label: string }) {
  if (!data.length) return <p className="text-sm text-fg-subtle">No data yet.</p>;
  const max = Math.max(1, ...data.map((d) => d.value ?? 0));
  const h = 96;
  return (
    <figure>
      <div className="flex h-28 items-end gap-0.5" role="img" aria-label={label}>
        {data.map((d) => {
          const v = d.value ?? 0;
          return (
            <div key={d.key} className="group relative flex h-full flex-1 flex-col justify-end" title={`${d.caption ?? d.key}: ${d.value === null ? "—" : `${v} ${unit}`}`}>
              <div className="rounded-t bg-accent transition-opacity group-hover:opacity-80" style={{ height: `${Math.max(v ? 2 : 0, (v / max) * h)}px` }} />
            </div>
          );
        })}
      </div>
      <div className="mt-1 flex justify-between text-[0.6875rem] text-fg-subtle">
        <span>{data[0]!.caption ?? data[0]!.key}</span>
        <span>{data.at(-1)!.caption ?? data.at(-1)!.key}</span>
      </div>
      <details className="mt-2 text-xs text-fg-muted">
        <summary className="cursor-pointer">Show as table</summary>
        <table className="mt-1 w-full">
          <tbody>
            {data.map((d) => (
              <tr key={d.key}>
                <td className="py-0.5">{d.caption ?? d.key}</td>
                <td className="py-0.5 text-right tabular-nums">{d.value === null ? "—" : `${d.value} ${unit}`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}

/** Horizontal meter rows (label, bar, value) — for skill areas and role progress. */
export function MeterRows({ rows }: { rows: { label: string; value: number | null; detail: string }[] }) {
  return (
    <ul className="space-y-2.5">
      {rows.map((r) => (
        <li key={r.label} className="grid grid-cols-[minmax(8rem,12rem)_1fr_auto] items-center gap-3 text-sm" title={`${r.label}: ${r.detail}`}>
          <span className="truncate text-fg">{r.label}</span>
          <span className="h-2 overflow-hidden rounded-full bg-surface-sunken">
            <span className="block h-full rounded-full bg-accent" style={{ width: `${r.value ?? 0}%` }} />
          </span>
          <span className="w-28 text-right tabular-nums text-fg-muted">{r.detail}</span>
        </li>
      ))}
    </ul>
  );
}
