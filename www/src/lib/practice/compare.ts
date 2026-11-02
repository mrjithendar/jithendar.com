import type { Comparator } from "./types";

/**
 * Deterministic output comparison (mirrored by executor/tools/build_problems.py). Values are the sandbox's
 * normalised JSON (sets as {"__set__": [...]}, big ints as {"__int__": "..."}), so plain JSON equality is
 * lossless. JSON has a single number type: 3 and 3.0 are equal.
 */
export function canonical(value: unknown): string {
  return JSON.stringify(sortKeys(value));
}

function sortKeys(value: unknown): unknown {
  if (Array.isArray(value)) return value.map(sortKeys);
  if (value && typeof value === "object") {
    return Object.fromEntries(
      Object.keys(value as Record<string, unknown>)
        .sort()
        .map((k) => [k, sortKeys((value as Record<string, unknown>)[k])]),
    );
  }
  return value;
}

function close(a: unknown, b: unknown, tol: number): boolean {
  if (typeof a === "boolean" || typeof b === "boolean") return a === b;
  if (typeof a === "number" && typeof b === "number") return Math.abs(a - b) <= Math.max(tol, tol * Math.max(Math.abs(a), Math.abs(b)));
  if (Array.isArray(a) && Array.isArray(b)) return a.length === b.length && a.every((x, i) => close(x, b[i], tol));
  if (a && b && typeof a === "object" && typeof b === "object" && !Array.isArray(a) && !Array.isArray(b)) {
    const ka = Object.keys(a).sort();
    const kb = Object.keys(b).sort();
    return canonical(ka) === canonical(kb) && ka.every((k) => close((a as Record<string, unknown>)[k], (b as Record<string, unknown>)[k], tol));
  }
  return canonical(a) === canonical(b);
}

export function outputsEqual(actual: unknown, expected: unknown, comparator: Comparator = "exact", tolerance = 1e-6): boolean {
  if (comparator === "unordered" && Array.isArray(actual) && Array.isArray(expected)) {
    if (actual.length !== expected.length) return false;
    const a = actual.map(canonical).sort();
    const b = expected.map(canonical).sort();
    return a.every((x, i) => x === b[i]);
  }
  if (comparator === "float") return close(actual, expected, tolerance);
  return canonical(actual) === canonical(expected);
}

/** Human-readable Python-ish rendering of a normalised value (for test result tables). */
export function pyRepr(value: unknown, depth = 0): string {
  if (depth > 20) return "…";
  if (value === null || value === undefined) return "None";
  if (value === true) return "True";
  if (value === false) return "False";
  if (typeof value === "number") return Number.isInteger(value) ? String(value) : String(value);
  if (typeof value === "string") return JSON.stringify(value).replace(/^"|"$/g, "'").replace(/\\"/g, '"');
  if (Array.isArray(value)) return `[${value.map((v) => pyRepr(v, depth + 1)).join(", ")}]`;
  const obj = value as Record<string, unknown>;
  if (typeof obj.__int__ === "string" && Object.keys(obj).length === 1) return obj.__int__;
  if (Array.isArray(obj.__set__) && Object.keys(obj).length === 1) return obj.__set__.length ? `{${obj.__set__.map((v) => pyRepr(v, depth + 1)).join(", ")}}` : "set()";
  if (typeof obj.__float__ === "string") return `float('${obj.__float__}')`;
  if (Array.isArray(obj.__map__)) return `{${(obj.__map__ as [unknown, unknown][]).map(([k, v]) => `${pyRepr(k, depth + 1)}: ${pyRepr(v, depth + 1)}`).join(", ")}}`;
  return `{${Object.entries(obj).map(([k, v]) => `${pyRepr(k)}: ${pyRepr(v, depth + 1)}`).join(", ")}}`;
}

/** Python call text for a test case, e.g. solve([1, 2], limit=3). */
export function callRepr(entrypoint: string, args: unknown[] = [], kwargs: Record<string, unknown> = {}): string {
  const parts = [...args.map((a) => pyRepr(a)), ...Object.entries(kwargs).map(([k, v]) => `${k}=${pyRepr(v)}`)];
  return `${entrypoint}(${parts.join(", ")})`;
}
