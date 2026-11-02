/**
 * Mock-interview feedback: a deterministic rubric from the grader's results and simple static checks of the
 * code. These are automated heuristics, labelled as such in the UI; correctness always comes from the tests.
 * Each dimension scores 0–5.
 */
export type Dimension = "correctness" | "codeQuality" | "pythonProficiency" | "efficiency" | "errorHandling" | "readability" | "testing";
export type Feedback = { scores: Record<Dimension, number>; notes: Record<Dimension, string[]>; overall: number };

export const DIMENSION_LABELS: Record<Dimension, string> = {
  correctness: "Correctness",
  codeQuality: "Code quality",
  pythonProficiency: "Python proficiency",
  efficiency: "Efficiency",
  errorHandling: "Error handling",
  readability: "Readability",
  testing: "Testing",
};

const clamp = (n: number) => Math.max(0, Math.min(5, Math.round(n)));

export function reviewCode(input: {
  code: string;
  verdict: string | null;
  passed: number;
  total: number;
  maxMs: number | null;
  perTestSeconds: number;
  runsBeforeSubmit: number;
  customInputsTried: number;
}): Feedback {
  const code = input.code;
  const lines = code.split("\n");
  const nonEmpty = lines.filter((l) => l.trim() && !l.trim().startsWith("#"));
  const notes: Record<Dimension, string[]> = { correctness: [], codeQuality: [], pythonProficiency: [], efficiency: [], errorHandling: [], readability: [], testing: [] };

  // Correctness: share of tests passed.
  const correctness = input.total ? (input.passed / input.total) * 5 : 0;
  notes.correctness.push(input.verdict === "accepted" ? "All tests passed, including hidden edge cases." : `${input.passed} of ${input.total} tests passed (${input.verdict ?? "not graded"}).`);

  // Code quality: function size, globals, bare excepts, leftover debugging.
  let quality = 5;
  const longest = longestFunction(lines);
  if (longest > 40) {
    quality -= 1.5;
    notes.codeQuality.push(`The longest function is ${longest} lines; split it into helpers.`);
  }
  if (/^\s*global\s/m.test(code)) {
    quality -= 1;
    notes.codeQuality.push("Avoid `global`; pass state explicitly.");
  }
  if (/^\s*print\(/m.test(code)) {
    quality -= 0.5;
    notes.codeQuality.push("Remove debugging print() calls before submitting.");
  }
  if (!notes.codeQuality.length) notes.codeQuality.push("Functions are small and side effects are contained.");

  // Python proficiency: idioms.
  const idioms = [
    [/\bfor\s+\w+\s*,\s*\w+\s+in\s+enumerate\(/, "enumerate()"],
    [/\[[^\]]+\bfor\b[^\]]+\bin\b[^\]]+\]/, "comprehensions"],
    [/\bwith\s+/, "context managers"],
    [/f["']/, "f-strings"],
    [/\bfrom collections import|\bcollections\./, "collections"],
    [/\bzip\(/, "zip()"],
    [/->\s*[\w\[\], |.]+:/, "type hints"],
  ] as const;
  const used = idioms.filter(([re]) => re.test(code)).map(([, name]) => name);
  const proficiency = 2 + Math.min(3, used.length);
  if (/for\s+\w+\s+in\s+range\(len\(/.test(code)) notes.pythonProficiency.push("`for i in range(len(x))` usually reads better as `for i, item in enumerate(x)`.");
  notes.pythonProficiency.push(used.length ? `Uses ${used.join(", ")}.` : "Consider idiomatic constructs: comprehensions, enumerate(), collections.");

  // Efficiency: time used relative to the limit; timeouts score lowest.
  let efficiency = 5;
  if (input.verdict === "timeout") {
    efficiency = 1;
    notes.efficiency.push("At least one test exceeded the time limit — look for repeated work inside loops.");
  } else if (input.maxMs !== null) {
    const share = input.maxMs / (input.perTestSeconds * 1000);
    efficiency = share > 0.5 ? 3 : share > 0.2 ? 4 : 5;
    notes.efficiency.push(`Slowest test took ${input.maxMs.toFixed(1)} ms.`);
  }
  if (/\.index\(|\bin\s+\w+_list\b/.test(code) && /for\s/.test(code)) notes.efficiency.push("Membership checks on lists inside loops are O(n); a set or dict is O(1).");

  // Error handling.
  let errorHandling = 4;
  if (/except\s*:/.test(code)) {
    errorHandling -= 2;
    notes.errorHandling.push("A bare `except:` also catches KeyboardInterrupt and SystemExit; catch specific exceptions.");
  } else if (/except\s+Exception\b/.test(code)) {
    notes.errorHandling.push("`except Exception` is broad; narrow it where you know what can fail.");
  } else if (/except\s+\w+/.test(code)) {
    errorHandling += 1;
    notes.errorHandling.push("Catches specific exceptions.");
  } else {
    notes.errorHandling.push("No exception handling — fine if inputs are guaranteed valid; otherwise guard the edges.");
  }

  // Readability: naming, line length, comments/docstrings.
  let readability = 5;
  const shortNames = (code.match(/\b(?:def|for)\s+([a-z])\b/g) ?? []).length;
  if (shortNames > 3) {
    readability -= 1;
    notes.readability.push("Several one-letter names; descriptive names make intent clearer.");
  }
  const longLines = nonEmpty.filter((l) => l.length > 110).length;
  if (longLines) {
    readability -= 1;
    notes.readability.push(`${longLines} line(s) longer than 110 characters.`);
  }
  if (/[A-Z][a-z]+[A-Z]\w*\s*=/.test(code)) {
    readability -= 0.5;
    notes.readability.push("Python uses snake_case for variables (PEP 8).");
  }
  if (!notes.readability.length) notes.readability.push("Clear names and tidy formatting.");

  // Testing: did the candidate run the code and try their own inputs before submitting?
  const testing = clamp((input.runsBeforeSubmit > 0 ? 2 : 0) + Math.min(3, input.customInputsTried));
  notes.testing.push(
    input.customInputsTried
      ? `Tried ${input.customInputsTried} custom input(s) before submitting.`
      : input.runsBeforeSubmit
        ? "Ran the public tests but didn't try your own edge cases."
        : "Submitted without running the code first — in an interview, test before you submit.",
  );

  const scores: Record<Dimension, number> = {
    correctness: clamp(correctness),
    codeQuality: clamp(quality),
    pythonProficiency: clamp(proficiency),
    efficiency: clamp(efficiency),
    errorHandling: clamp(errorHandling),
    readability: clamp(readability),
    testing,
  };
  // Correctness counts double: working code matters most.
  const overall = Math.round(((scores.correctness * 2 + scores.codeQuality + scores.pythonProficiency + scores.efficiency + scores.errorHandling + scores.readability + scores.testing) / 40) * 100);
  return { scores, notes, overall };
}

function longestFunction(lines: string[]): number {
  let longest = 0;
  let start = -1;
  let indent = 0;
  lines.forEach((line, i) => {
    const m = /^(\s*)(?:async\s+)?def\s/.exec(line);
    if (m) {
      if (start >= 0) longest = Math.max(longest, i - start);
      start = i;
      indent = m[1]!.length;
    } else if (start >= 0 && line.trim() && line.length - line.trimStart().length <= indent && !line.trim().startsWith("#")) {
      longest = Math.max(longest, i - start);
      start = -1;
    }
  });
  if (start >= 0) longest = Math.max(longest, lines.length - start);
  return longest;
}
