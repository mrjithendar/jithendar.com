# Shell scripting vs Python article

Status: **draft for author review, not published.** Written 2026-11-03 against `jithendar.com` f12f8cc, `moks` 74a097d, `roboshop-ai` c81e85a and `tools` 387bd30. All four commits are on `origin/master`, and every cited file was clean in its working tree.

| Asset | Location |
| --- | --- |
| Article | `content/blog/shell-scripting-vs-python.mdx` (`status: review`, no `publishedAt`) |
| Example checker | `verify_examples.py` (this folder) |
| Script improvement notes (not part of the article) | `RECOMMENDED_SCRIPT_IMPROVEMENTS.md` (this folder) |

Live posts are stored in PostgreSQL, so after review the owner pastes the approved draft into the editor, as with earlier drafts.

## SEO and publishing metadata

The content schema has no excerpt or keyword field, so those live here, as for earlier drafts.

| Field | Value |
| --- | --- |
| H1 (`title`, 90 chars) | Shell Scripting vs Python: What They Have in Common, How They Differ, and When to Use Each |
| SEO title (`seoTitle`, 63) | Bash vs Python: Shell Scripting vs Python for DevOps Automation |
| Meta description (`description` and `seoDescription`, 160, the schema maximum) | Shell scripting vs Python, side by side: runnable Bash and Python examples for files, JSON, APIs, errors and DevOps automation, with real scripts from my repos. |
| Slug | `shell-scripting-vs-python` |
| Excerpt | Bash and Python share more than you might think, but they fail in very different ways. This guide puts runnable shell scripting vs Python examples side by side, from quoting and exit codes to JSON, APIs and cleanup, and uses real automation scripts from my repositories to show when each one fits. |
| Primary keyword | shell scripting vs Python |
| Secondary keywords | Bash vs Python; DevOps automation |
| Category | `devops-sre` |
| Content type | `tutorial` |
| Internal links | `/blog/python-tutorial-beginners-real-projects`, `/blog/python-vs-typescript`, `/blog/github-actions-authenticate-minikube` (all returned HTTP 200 on 2026-11-03) |
| `related` | the same three |
| Length | About 11,500 words of prose and tables, 17,800 including code; 114 code blocks |

## How the examples are checked

`verify_examples.py` parses the article, so the code that is checked is the code that is published.

```bash
cd www
python3 docs/knowledge-sharing/shell-vs-python/verify_examples.py                  # Bash 5.x, Python on PATH
python3 docs/knowledge-sharing/shell-vs-python/verify_examples.py --bash /bin/bash --skip-shellcheck   # macOS Bash 3.2 compatibility
```

Needs bash, dash, jq, curl, shellcheck and git, plus sibling checkouts of moks, roboshop-ai and tools next to jithendar.com. It uses port 8765 on 127.0.0.1 for the mock API and touches no other network.

### Results (2026-11-03, on this Mac)

| Check | Result |
| --- | --- |
| Checker, Bash 5.2.26, dash, Python 3.11.9, jq 1.7.1, curl 8.7.1, ShellCheck 0.11.0 | 124 run cases, 52 ShellCheck files, 44 Python files, 15 repository excerpts, **0 failures**; run twice |
| Checker with `/bin/bash` 3.2.57 | 3 failures, exactly the examples the article labels as needing Bash 4+: `vars.sh` (`${var^^}`), `arrays.sh` (`declare -A`, negative subscript), `summarize.sh` |
| `bash -n` on `deploy.sh`, `scripts/smoke.sh` (jithendar.com), `scripts/backup.sh`, `scripts/create-runtime-key.sh` (moks), `scripts/lib/check-argocd-ownership.sh`, `scripts/lib/require-centos.sh` (tools) | pass |
| `dash -n` on `services/web/nginx/start.sh` (roboshop-ai) | pass |
| ShellCheck on those seven repository scripts | 2 notes, both expected: SC1091 (`require-centos.sh` line 14), SC2016 (`start.sh` line 37) |
| `start.sh --test` under dash, scratch copy of the templates, placeholder `index.html`, local nginx 1.31.7 and envsubst | valid settings pass `nginx -t`; `FRONTEND_BASE_PATH='/a b'`, `GATEWAY_HOST='x;evil'` rejected with messages; `NGINX_HTTP_PORT=70000` exits 1 with **no** message |
| `python3 -m unittest tests.scripts.test_initialize` in tools (Python 3.11.9) | 16 tests, OK |
| `npm test` in www (Vitest, includes content schema and link checks) | 42 files, 434 tests, all passed |
| Article body rendered through `src/lib/mdx/compile.ts` with a throwaway Vitest file (deleted afterwards) | compiled; 114 `<pre>` blocks, 6 tables, no stray Markdown or directive output |

### Not run, and why

- `scripts/smoke.sh`: targets the live site. Checked with `bash -n` and ShellCheck only.
- `deploy.sh`, `scripts/backup.sh`, `scripts/create-runtime-key.sh`, `check-argocd-ownership.sh`: they apply manifests, read a production database or create and delete IAM keys, or need a cluster. Quoted only.
- MOKS Boto3 code: needs AWS credentials. Quoted only.
- RoboShop's `npm run test:nginx`: not run; the article says so.
- `npm run lint`, `typecheck`, `build`: not run; only content and docs changed, and `npm test` covers content validation.
- Docker was not running, so the `/bin/sh` of Alpine, Debian and Ubuntu images was not observed; the article cites Debian policy and the Alpine project page instead.
- Python 3.12–3.14 (used by the repositories' CI) are not installed here; examples were run on 3.11.9 only. They avoid newer syntax, but `pathlib` globbing of hidden files is stated as observed on 3.11.9.

## Verified project files used

| Repository | File | Used for |
| --- | --- | --- |
| jithendar.com | `www/AGENTS.md`, `www/docs/CONTENT_MODEL.md`, `src/config/taxonomy.ts`, `src/lib/mdx/compile.ts`, `tests/links.test.ts` | Draft mechanism, schema, category, Markdown-only rendering, link rules |
| jithendar.com | `deploy.sh` (lines 8–11, 17) | Re-exec under Bash, `BASH_SOURCE` directory |
| jithendar.com | `scripts/smoke.sh` (lines 6–8, 11–22, 24–25, 48) | Defaults, functions, `sed` JSON scraping, `grep -c ... \|\| true` |
| moks | `scripts/backup.sh` (lines 5–10) | `pipefail` in a backup pipeline, partial-file limitation |
| moks | `scripts/create-runtime-key.sh` (lines 19, 25–30) | AWS CLI `--query`, `umask` + `mktemp` + `trap`, shell-to-Python JSON hand-off |
| moks | `backend/moks/backup.py` (lines 152–156), `backend/moks/connectors/cloudwatch.py` (lines 62–67), `backend/moks/connectors/finops.py` (line 48) | Boto3 paginator, `Config` timeouts and retries |
| moks | `scripts/decrypt-backup.py`, `backend/requirements.txt`, `.github/workflows/ci.yml` | `cryptography` dependency, exact pins, Python 3.12 and pytest in CI |
| roboshop-ai | `services/web/nginx/start.sh` (lines 23–34, 42–47), `services/web/Dockerfile`, `services/web/nginx/README.md` | POSIX entrypoint, `envsubst`, `exec`, Alpine base image |
| roboshop-ai | `.github/workflows/*.yml` | Python 3.14 and `unittest` in CI |
| tools | `scripts/lib/repos.py` (lines 15–18), `scripts/lib/check-argocd-ownership.sh` (lines 4–9), `scripts/lib/require-centos.sh`, `tests/scripts/test_initialize.py` (lines 102–108), `scripts/argocd/validate.py` | `__file__` paths, `-o name`, `shift` + `"$@"`, PATH-mocked `uname`, PyYAML dependency |

## Sources for version-sensitive claims

| Claim | Source (checked 2026-11-03) |
| --- | --- |
| `set -e` exceptions, ignored inside functions called from those contexts; `-u`; `pipefail` | https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html |
| Bash invoked as `sh` enters POSIX mode | https://www.gnu.org/software/bash/manual/html_node/Bash-POSIX-Mode.html |
| Traps wait for a foreground command; `wait` returns immediately on a trapped signal | https://www.gnu.org/software/bash/manual/html_node/Signals.html |
| Associative arrays, `mapfile`, case modification (4.0); negative subscripts (4.2, extended 4.3); `wait -n` (4.3); `inherit_errexit` (4.4) | https://tiswww.case.edu/php/chet/bash/NEWS |
| POSIX has no `[[ ]]` (reserved, unspecified) or arrays; `set -o pipefail` is in POSIX.1-2024; `local` is not a special built-in | https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html |
| echo portability, "New applications are encouraged to use printf" | https://pubs.opengroup.org/onlinepubs/9799919799/utilities/echo.html |
| Debian `/bin/sh` is POSIX plus listed extras; name `#!/bin/bash` otherwise | https://www.debian.org/doc/debian-policy/ch-files.html |
| zsh default on macOS 10.15+ | https://support.apple.com/en-us/102360 |
| Alpine is built around musl and BusyBox | https://www.alpinelinux.org/about/ |
| `subprocess.run` timeout, `check`, `text`, `capture_output`; no implicit shell; `shell=True` uses `/bin/sh` | https://docs.python.org/3/library/subprocess.html |
| Default SIGINT and SIGPIPE handling; SIGKILL cannot be caught; main-thread handlers | https://docs.python.org/3/library/signal.html |
| `TemporaryDirectory`, `mkstemp` security, `mktemp()` unsafe | https://docs.python.org/3/library/tempfile.html |
| `newline=""` for csv, `DictReader` | https://docs.python.org/3/library/csv.html |
| curl `--fail` (exit 22, not fail-safe), `--fail-with-body` (7.76.0), `--retry` transient codes and `Retry-After`, `--retry-all-errors` (7.71.0) | https://curl.se/docs/manpage.html |
| SC2086 wording | https://www.shellcheck.net/wiki/SC2086 |
| AWS CLI retrieves all pages by default | https://docs.aws.amazon.com/cli/latest/userguide/cli-usage-pagination.html |
| Boto3 retry modes; `max_attempts` in `Config` excludes the first request; legacy default | https://docs.aws.amazon.com/boto3/latest/guide/retries.html |

Not from documentation but observed on this Mac, and stated as such in the article: `read -p` printing no prompt for piped input (also in the Bash manual), `input()` writing its prompt to stdout, `pathlib` matching hidden files while `glob` does not (3.11.9), `${VAR:?}` exit codes (1 in a Bash script, 127 in `bash -c`, 2 in dash), BSD `sed -i` failing without a suffix, curl 8.7.1 printing an error per failed retry, and dash reporting `[[: not found` and continuing with status 0.

## Limitations for the reviewer

- The repositories do not record why each script uses Bash, POSIX `sh` or Python. Every "why the language fits" paragraph is labelled as my assessment.
- No performance numbers: the per-process cost is described as a pattern, not measured.
- Outputs assume `LC_ALL=C`; glob and sort order can differ in other locales.
- The curl `-H @file` form for keeping tokens off the command line is mentioned by pointing to the manual's `-H` entry; its exact syntax and version were not checked.
- The `timeout` utility example is described, not run, because GNU `timeout` is not installed on macOS.
