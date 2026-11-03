# TypeScript tutorial: article package

Draft for author review. **Not published.** The article file has `status: review`. Live posts are stored in
Postgres, so publishing means pasting the approved draft into the editor (see `docs/CONTENT_AUDIT.md`).

| File | Purpose |
|---|---|
| `content/blog/learning-typescript-real-project-jithendar-com.mdx` | The article |
| `docs/knowledge-sharing/typescript-tutorial/verify_article.py` | Checks every code block against the pinned commit and the compiler |

Reviewed source: jithendar.com commit `dc249e807f83ef5a0e2aaa34638c42399e91e905` (`origin/master`, 2026-11-03;
`www/` had no uncommitted changes). Every GitHub link in the article is pinned to it. Installed versions:
TypeScript 6.0.3, Next.js 16.4.3, React 19.3.1, `@types/react` 19.3.0, Zod 4.6.7, Node.js 26.13.0.

## SEO metadata

| Field | Value |
|---|---|
| H1 (`title`, 73 chars) | Learning TypeScript Through a Real Project: How I Use It on jithendar.com |
| SEO title (65 chars) | TypeScript Tutorial: Real TypeScript Examples from a Next.js Site |
| Meta description (`seoDescription`, 143 chars) | Learn TypeScript with React through real examples from a Next.js codebase: types, narrowing, props, async code, unknown, generics and tsconfig. |
| Listing description (`description`, 146 chars) | A beginner-friendly TypeScript tutorial built on real code from jithendar.com: types, unions, React props, API calls, Zod validation and tsconfig. |
| Slug | `learning-typescript-real-project-jithendar-com` |
| Category / type | `devops-sre` / `tutorial` (**owner decision needed**, see below) |

**Excerpt** (for the listing card or social post):

> A beginner's TypeScript tutorial that uses the real code behind jithendar.com: typed React props and state, a
> comment form traced from the browser to PostgreSQL, Zod validation at the API boundary, and what TypeScript
> cannot check for you.

**Category.** None of the eight built-in categories in `src/config/taxonomy.ts` covers web development or
programming languages. `devops-sre` is a placeholder so the file validates. Categories are editable in
Admin → Categories, so a new category (for example "Web development") may fit better before publishing.

**Keywords in the body:** "TypeScript tutorial" 1, "TypeScript examples" 1, "TypeScript with React" 1. The SEO
title and meta description carry them too. No stuffing.

**Headings:** one H1 from the title, 17 H2s and 39 H3s.

**Internal links.** Both returned HTTP 200 on 2026-11-03:

- `/projects/nextjs-site-on-kubernetes` (also in `related`)
- `/contact`

Not linked: `/blog/deploy-nextjs-kubernetes-github-actions` returned 404. `/python-practice` returns 200 but is
not in the link checker's route list (`src/lib/content/links.ts`), so a link would fail `npm test` once this
article is published. The article names the Python practice section in plain text instead.

**No diagram image.** The renderer has no Mermaid support (no `mermaid` anywhere in `src/`), so the end-to-end
flow is a `text` code block.

## Project files used as examples

| File | Used for |
|---|---|
| `www/tsconfig.json` | Whole file; compiler options section |
| `www/package.json` | `typecheck` script and versions (described, not quoted) |
| `www/src/lib/comment-types.ts` | `.ts` file, literal unions, `as const` with `typeof`, `Record` |
| `www/src/components/Comments.tsx` | `.tsx` server component |
| `www/src/components/discussion/Composer.tsx` | Props, state, refs, events, `ComposerSubmit` discriminated union |
| `www/src/components/discussion/Discussion.tsx` | `fetchPage` with `Promise<CommentPage>` and `as`, catch narrowing, `post()` |
| `www/src/app/_actions/comments.ts` | `threadOf` with `?? null`, `CommentResult<T>`, `signedIn` catch, `postCommentAction`, `@/` import |
| `www/src/app/api/comments/[postId]/route.ts` | GET route (simplified) |
| `www/src/lib/comments.ts` | `cleanBody(body: unknown)`, `reportComment` assertion, `submitComment` (simplified) |
| `www/src/db/schema.ts` | `FeaturedImage`, `comment` table (simplified) |
| `www/src/lib/post-form.ts` | `PostFormValue` (simplified), `str` helper |
| `www/src/lib/posts.ts` | `PostError` and `readonly` |
| `www/src/lib/safe-next.ts` | `safeNext` signature, `loginHref` |
| `www/src/config/taxonomy.ts` | `tagSlug`, `collectionLabels` |
| `www/src/components/Turnstile.tsx` | `declare global` and `interface Window` |
| `www/src/components/practice/api.ts` | `api<T>` generic |
| `www/src/app/api/practice/problems/[slug]/state/route.ts` | Zod `safeParse` at an API boundary |
| `www/src/lib/contact.ts` | `contactInput` Zod schema |
| `www/src/lib/content/schema.ts` | `z.output<typeof articleFrontmatter>` |

## Validation (run 2026-11-03)

| Check | Result |
|---|---|
| `python3 -I docs/knowledge-sharing/typescript-tutorial/verify_article.py` (from `www/`) | pass: 77 code blocks (31 actual, 6 simplified, 40 teaching); 36 TS/TSX teaching blocks compiled with TypeScript 6.0.3 under the project's `strict` and `noUncheckedIndexedAccess` settings; 13 deliberate-error examples fail with exactly the codes quoted |
| Verifier negative test (a copy with one changed project line, one wrong error code, one stray brace) | all three caught |
| Compile the body with the installed `@mdx-js/mdx` and `remark-gfm` | pass |
| `tests/editor-workflow.test.ts` visual-editor round trip | first run failed; fixed, then pass (see below) |
| `npm test` | pass: 42 files, 425 tests |
| `npm run typecheck` | pass |
| `npm run lint` | pass (clean) |
| `npm run build` | **Not run.** No application code changed, and the MDX compile was checked directly |

Runtime claims checked with Node.js 26.13.0: the JavaScript typo example prints `NaN min read`, and the
`JSON.parse(...) as Post` example prints `undefined` and then throws
`TypeError: Cannot read properties of undefined (reading 'toUpperCase')`.

Compiler defaults in the tsconfig table come from `tsc --help --all` of the installed 6.0.3 (`strict` true,
`target` es2025, `esModuleInterop` true, `noUncheckedIndexedAccess` false, `resolveJsonModule` false, and so on).

Corrections made while verifying (claims in my first draft that turned out wrong):

- The JavaScript typo example returns `"NaN min read"`, not `"1 min read"`.
- `let x = null; x = "Hello";` compiles: TypeScript follows later assignments to a `let` variable. The
  "annotate empty values" advice and its exercise now use an object field, which does fail (`TS2322`).
- `www/src` does contain two `interface` declarations (`declare global { interface Window ... }` in
  `Turnstile.tsx` and `AdSlot.tsx`). The article now uses one as the declaration-merging example.
- `resolveJsonModule` and `incremental` default to `false`, not "not set".
- The type-only import note no longer ties `type` imports to `isolatedModules`, which does not require them.
- A paragraph starting with inline code containing `<p>` broke the visual-editor round trip (the editor escaped
  it and split the line). The paragraph now starts with plain text.

## Limitations

- The teaching examples were checked with a tsconfig that copies the project's compiler options, not inside the
  Next.js project itself (they would be swept into `npm run typecheck` there).
- `CommentPage`/`CommentView` field lists and other quoted types are true at `dc249e8`. If the comment code
  changes, rerun the verifier: it reads the pinned commit, so it will not notice. Bump `COMMIT` in the script
  and in the article's links together.
- The article describes server actions as HTTP endpoints that can be called directly. That is how Next.js
  works. I did not send a hand-made request to this site to demonstrate it.

## Implementation gaps found (not part of the article)

None of these are fixed. They are observations for the owner.

1. **Deprecated `FormEvent`.** `@types/react` 19.3.0 marks `React.FormEvent` deprecated ("FormEvent doesn't
   actually exist"; use `SubmitEvent` or `ChangeEvent`). It is used 8 times in 7 files: `Composer.tsx`,
   `ContactForm.tsx`, `LoginForm.tsx`, `ProfileForm.tsx`, `EmailSettings.tsx`, `PrivacyForm.tsx`,
   `StartPracticeForm.tsx`. Neither lint nor typecheck reports deprecations, so it is silent today.
2. **JSON responses are asserted, not validated, in the browser.** `fetchPage` in `Discussion.tsx` and `api<T>`
   in `components/practice/api.ts` end with `as CommentPage` / `as T`. Both talk to same-origin routes whose
   server code is type-checked, so the risk is low, but a changed response shape would not be noticed at
   runtime. Server-side input validation (Zod, `cleanBody`, regex checks) is in place where I looked.
3. **`likeCommentAction(id, liked: boolean)` trusts `liked` at runtime.** Server actions accept any
   serialisable arguments from a crafted request. `setLike` branches on `if (liked)` and echoes `liked` back
   in its result, so a non-boolean truthy value adds a like and is returned unchanged. The effect is limited
   to the caller's own like and response; `liked === true` would close it.
4. **The link checker does not know app routes like `/python-practice`.** `STATIC_ROUTES` in
   `src/lib/content/links.ts` lists only feeds, search and collection roots, so published content cannot link
   to `/python-practice` without failing `npm test`.
5. **`AGENTS.md` says TypeScript 5.9.** `www/package.json` pins `typescript` 6.0.3, whose defaults differ
   (`strict` now defaults to true).
6. **Untracked root `package.json` and `package-lock.json`** (repository root, not `www/`, created
   2026-11-03 09:53) install `typescript` 7.0.2 and a package named `g` 2.0.1. I did not create or change
   them. They do not affect `www/`, which resolves its own TypeScript 6.0.3.
