# Python practice (`/python-practice`)

Role-based Python coding practice and interview preparation, built into the site (same Next.js app, same
Better Auth accounts, same Postgres, same admin). Code execution runs in a separate sandboxed service:
[PYTHON_PRACTICE_EXECUTOR.md](PYTHON_PRACTICE_EXECUTOR.md).

## Decisions

| Decision | Why |
|---|---|
| **Postgres, not MongoDB** (owner decision 2026-11-02) | The site already runs Postgres with Drizzle migrations, backups and transactions. The prompt's collections map to `practice_*` tables below; document-shaped fields are JSONB |
| Admin audit in the existing `audit_log` (`practice.*` actions) | One audit trail with severities, search and export already exists |
| **CodeMirror 6, not Monaco** | Monaco does not support mobile browsers; the spec requires phones and tablets. CodeMirror gives highlighting, line numbers, autocomplete, bracket matching, search and keyboard accessibility |
| Grading in the web app, execution in the sandbox | Expected outputs and hidden tests never enter untrusted code's environment |
| Function-call problems with JSON inputs | Deterministic, reproducible grading; cloud/API problems use fakes in a prelude instead of real credentials |
| Session deadlines stored server-side | Refreshing or reconnecting cannot extend a timed assessment |
| New dependencies: `codemirror`, `@codemirror/*`, `@aws-sdk/client-bedrock-runtime` | Editor; Bedrock Converse with SigV4 (the AWS SDK is already used for S3/SES) |

## Routes

Public (guests can read everything here): `/python-practice`, `/roles`, `/problems`, `/problems/[slug]`,
`/leaderboard`, `/achievements`. Signed-in only: `/dashboard`, `/history`, `/session/[id]`.
Protected actions — editing, running, submitting, hints, solutions, AI, bookmarks, notes, sessions — open a
sign-in dialog for guests (sign in / create account / return to browsing; `/login?next=` returns to the same
page). The server enforces it: every `/api/practice/*` call answers guests `401 {code: "auth_required"}`;
state-changing calls also require a same-site `Origin` (CSRF).

API: `POST /api/practice/run` (run or submit; idempotency key), `GET|DELETE /api/practice/submissions/[id]`,
`POST /api/practice/problems/[slug]/assist` (hint level n / solution with confirm), `GET|PUT
/api/practice/problems/[slug]/state` (draft, note, bookmark), `POST /api/practice/sessions`, `GET|POST
/api/practice/sessions/[id]`, `POST /api/practice/ai`, `GET|PUT|DELETE /api/practice/me` (preferences,
export, deletion).

## Data model (migration `0010_python_practice.sql`)

| Prompt collection | Table | Notes |
|---|---|---|
| practice_roles / topics | `practice_role`, `practice_topic` | admin-editable; topics roll up into 12 dashboard skill areas |
| practice_problems / versions | `practice_problem`, `practice_problem_version` | versions are immutable; `current_version` is what users get |
| practice_test_cases | `practice_test_case` | per version; read only by evaluator, seeder, admin and (examples only) catalog — enforced by `tests/practice.test.ts` |
| practice_sessions | `practice_session`, `practice_session_item` | items pin the problem version |
| practice_submissions / execution_jobs | `practice_submission`, `practice_execution_job` | unique `(user_id, idempotency_key)`; finalised once (conditional update) |
| practice_user_progress / skills | `practice_progress`, `practice_skill` | written only by the grader's transaction |
| bookmarks / notes / achievements / daily | `practice_bookmark`, `practice_note`, `practice_achievement`, `practice_daily_challenge` | |
| activity_events / ai_usage | `practice_activity_event`, `practice_ai_usage` | AI usage stores tokens and cost, never prompts or answers |
| (profile, XP, streaks) | `practice_profile` | opt-in leaderboard, public name |
| admin_audit_logs | existing `audit_log` | `practice.*` actions |

User rows cascade: deleting an account deletes its practice data. `GET /api/practice/me?export=1` exports it;
`DELETE /api/practice/me` deletes it but keeps the account. Retention (Admin → Settings): activity events
(default 730 days) and submitted code (365 days) are trimmed daily by the scheduler.

## Scoring rules

- **Solved** = accepted without having revealed the solution (hints allowed and recorded). **Solved with
  solution** is separate and never counts as solved, earns no XP, and does not advance badges.
- XP on the first independent solve: beginner 10, easy 20, medium 40, hard 70, expert 120; −10% per hint
  level (max −30%); +20 for the day's daily challenge.
- Streak: consecutive days (IST) with at least one graded submission.
- Assessment item score: 100 − 10 per hint when accepted (min 50), up to 60 for partial passes, 0 if the
  solution was revealed. Solutions are locked during timed assessments and mock interviews; hints are off in
  mock interviews. Mock feedback is a labelled heuristic rubric (correctness, quality, Python proficiency,
  efficiency, error handling, readability, testing); correctness always comes from the tests.
- Badges are computed from graded results and server-side streaks (`lib/practice/achievements.ts`).
- Metric definitions shown on the dashboard live in `lib/practice/dashboard.ts`.

## Content

`www/content/python-practice/` holds `roles.yaml`, `topics.yaml` and `problems/*.yaml` (100 original problems:
20 beginner, 25 easy, 30 medium, 17 hard, 8 expert; every role has ≥ 5). Build the catalog after editing:

```sh
python executor/tools/build_problems.py          # needs PyYAML; writes catalog.generated.json
```

It runs every reference solution through the real sandbox runner to compute expected outputs, checks
hand-written expectations, requires three hints, ≥ 2 hidden tests and an example, checks that the starter
code loads but does not pass, and flags near-duplicates. The site seeds the catalog at start-up: new problems
are inserted, changed seed problems get a new version, and problems edited in the admin are left alone.
CI (`ci-practice-executor.yml`) fails if the committed catalog is stale.

### Problem format

```yaml
- slug: kebab-case
  title: …
  difficulty: beginner | easy | medium | hard | expert
  roles: [role slugs]
  topics: [topic slugs]
  minutes: 10
  entrypoint: function_or_class_name
  comparator: exact | unordered | float      # optional, default exact
  description: | Markdown
  constraints: [...]
  io: { input: "...", output: "..." }
  prelude: | optional helper code and __harness__(fn, *args)
  starter: | code
  hints: [concept, approach, pseudocode]
  solution: { code, explanation, time, space, alternatives, edge_cases, production, alternative_code? }
  examples: [{ args, kwargs?, expected?, explanation? }]   # public, shown in the statement
  tests:    [{ args, expected? }]                          # public, run by Run
  hidden:   [{ args }]                                     # graded on Submit only
```

## AI tutor

Optional; off until configured in Admin → Python practice → Settings (provider OpenAI-compatible, Gemini or
Bedrock; model id; key sealed with `SETTINGS_ENCRYPTION_KEY`, or `OPENAI_API_KEY` / `GEMINI_API_KEY`; Bedrock
uses the pod's AWS credentials). Features: explain error, explain a failed test, review, complexity, suggest
tests, concept questions, recommendations. Structured JSON output, prompt version
`practice-tutor-v1-2026-11-02`, per-user daily quota, global daily budget, per-request id, token and cost
records, one retry on 429/5xx/timeouts. Only public information is sent (statement, the user's own code,
public test results). Answers claiming correctness that contradicts the grader are flagged; code that would
implement the whole solution is withheld unless the user already revealed it. The tutor is disabled during
assessments. Provider failures never block practice. **Requires manual configuration.**

## Admin

Admin → Content → Python practice: overview (executor status, queue, verdicts, abuse signals, AI cost),
settings (admins), problems (create/edit → new version, quality checks, duplicate detection, JSON test
upload, validate in the sandbox and fill expected outputs, publish / unpublish / archive), roles, topics and
the daily challenge (authors and admins).
