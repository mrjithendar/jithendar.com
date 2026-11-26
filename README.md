# jithendar.com

The website [jithendar.com](https://jithendar.com): its identity, articles and images, and everything that deploys it
to the mk4 cluster. The software it runs is [moks-cms](https://github.com/moks-tech/moks-cms), which only tests its
code and pushes the CMS image `registry.jithendar.com/jithendar/moks-cms:pr-<number>`. That image serves any site and
reads the site's files at run time. Until 2026-11-16 the site lived in moks-cms as `sites/jithendar.com/`. Its history
up to then came along with it.

| Path | Contents |
|---|---|
| `site.json` | Identity: host, name, tagline, author, social links, AdSense ID, AI crawler policy |
| `config/` | `redirects.json` (308s: `[{"source", "destination"}]`), `gone.json` (paths answered with 410), `hire-me-profile.json` (`/hire-me`) |
| `content/` | `blog/`, `news/`, `projects/`, `pages/`, `authors/` (MDX). The Python practice problems are in [`moks-tech/practice-programming`](https://github.com/moks-tech/practice-programming) |
| `public/images/` | Images the articles use, served as `/images/…` |
| `docs/` | Sources of the articles' figures, and scripts that check the articles (never shipped) |
| [`crewconfig/`](crewconfig/README.md) | The CrewAI configuration: every crew with its agents and tasks, flow, skill, schedule, content source and category, and (read-only) the tools, prompt guardrails and model providers. Written and edited from the admin (AI & SEO → Configuration) or here; restored on the site after every deployment |
| [`kubernetes/`](kubernetes/README.md) | Every manifest the site runs on mk4: the site (CMS image tag, ConfigMap `jithendar-com-site` from `site.json` and `config/`, practice catalog) and the SEO agent. The practice executor deploys from practice-programming |
| `scripts/` | Deploy (`manifests.sh`, `ci-app-manifests.py`), content check (`check-content.sh`), content push (`push-content.py`), first-time Secrets (`create-*.sh`), site settings (`set-*-config.sh`), CI access (`setup-ci-*.sh`) |
| `.github/workflows/` | `content.yml` (articles and images, through the site's API), `deploy-kubernetes.yml` (the whole app from `kubernetes/`, then the CrewAI configuration), `crewconfig.yml` (the CrewAI configuration, through the site's API), `check.yml` (pull requests) |

## Workflows

| Workflow | When | What it does |
|---|---|---|
| `content.yml` | A push to `master` that changes `content/` or `public/images/`, or a manual run | Checks the files with the CMS image the site runs (`scripts/check-content.sh`), then pushes new and changed images to R2 and new or changed articles as drafts, through the site's API (`scripts/push-content.py`). No image is built and nothing is restarted |
| `deploy-kubernetes.yml` | A merged pull request that changes `kubernetes/`, `site.json` or `config/`, a manual run, or a `moks-cms-released` dispatch | Applies the whole app from the manifests (server dry run, diff, apply, restart, wait, smoke test), including ConfigMap `jithendar-com-site` with `site.json` and `config/`. Every manifest names `:latest`, so a restart pulls the newest image: a merged pull request or a manual run restarts every Deployment it applies in namespace `jithendar` (`jithendar-com`, `seo-agent`), a dispatch only the released component. Each Deployment is restarted only if it exists; a missing one is skipped with a warning |

| `crewconfig.yml` | Called by `deploy-kubernetes.yml` after each successful deploy, a push to `master` that changes `crewconfig/`, or a manual run | Checks `crewconfig/` (`scripts/crewconfig.py check`), waits until the site's database, migrations and SEO agent are ready, then imports it through the site's API in one transaction, verified and recorded with the commit. An item an admin changed on the site since the last sync is kept and reported (policy `skip`); a manual run can overwrite, refuse on conflicts, remove what is gone, or only plan. A refused or failed import changes nothing and fails the job |

To move to a moks-cms release by hand, or back to an earlier one, change its tag in `kubernetes/30-jithendar-com.yaml`
(or the seo-agent manifests) in a pull request. Merging it applies the change.

## Working on the site locally

The app comes from a moks-cms checkout next to this one:

```bash
cd ../moks-cms/services/www
SITE_DIR=../../../jithendar.com npm run dev          # links content/ and public/images/, copies site.json and config/
```

Or check the content the way CI does (needs Docker and `docker login registry.jithendar.com`):

```bash
scripts/check-content.sh                             # the CMS image named in kubernetes/30-jithendar-com.yaml
```

## Pushing images and articles (`scripts/push-content.py`)

`content.yml` sends images and articles to the site through its API, so a new article or diagram needs no image build
and no restart. The same script works from a laptop:

```bash
export JITHENDAR_API_KEY=jk_…                         # Admin → API keys: images:write + posts:draft
scripts/push-content.py --dry-run                     # which images would be sent
scripts/push-content.py content/blog/my-post.mdx      # images first, then this article
scripts/push-content.py --all-posts --create-only     # every article that is not a post yet; changes none
```

- **Images** under `public/images/` go to the site's storage (Cloudflare R2). The site remembers the SHA-256 of every
  file it was sent, so only new and changed files are uploaded. A PNG is stored as lossless WebP (the same pixels,
  about half the size); keep writing the `.png` path in articles. An image that is removed here stays on the site.
- **Articles** in `content/{blog,news,projects}/`: a new one becomes a **draft**, whatever its `status` says; a post
  that is still a draft or in review is updated from the file; a published post is left alone (edit it in
  Admin → Posts). Nothing is published from here. Pages and author profiles are edited in the admin.

## The CrewAI configuration (`crewconfig/`)

`crewconfig/` is the site's whole CrewAI setup as reviewable files (moks-cms `docs/seo/CREWCONFIG.md`): one file per
crew, agent, task, flow and skill (agents, tasks and skills are Markdown with front matter), the schedules, content
sources and categories, the read-only tools, guardrails and providers, JSON Schemas of every file kind, and a manifest
with checksums. No secrets: providers say where their key is, never the key.

- **Edit** it in the admin (AI & SEO → Configuration → Repository: a pull request or a commit per save, with history,
  compare and revert) or here in a pull request. `check.yml` checks it and, with the key, shows what the site would
  change. Merging restores it (`crewconfig.yml`).
- **From the site to Git**: AI & SEO → Configuration → Write to Git, or locally
  `JITHENDAR_CREWAI_KEY=jk_… scripts/crewconfig.py pull` (then commit). Do this whenever the admin's pages were used
  to change crews, flows or schedules, so Git holds what runs (the Overview shows such drift).
- **From Git to the site**: every deployment and every merge; locally `scripts/crewconfig.py push` (a plan) or
  `push --apply`.
- **Bootstrapped 2026-11-24** with the CMS's exporter from the SEO agent's code (crews, agents, tasks, flows, tools,
  guardrails), the CMS's shipped skills and categories and production's export of that day (its 15 schedules, no crew
  versions or edited skills). Production may also have content flows, sources, crews or flows made in the admin and
  catalogue edits that are not here yet: after the release, run Write to Git once. Until then a deployment only adds
  what is missing and keeps every difference (they are conflicts without an earlier sync).

## Setting up this repository (once)

The workflows need these, which moved here from moks-cms:

- **Harbor** (pull the CMS image for the content check): secrets `HARBOR_USERNAME` and `HARBOR_PASSWORD`.
- **Content push** (content.yml): secret `JITHENDAR_API_KEY`, an API key created by an admin in Admin → API keys with
  the scopes `images:write` and `posts:draft`. It needs a moks-cms release that has `PUT /api/v1/images/…` and
  `PUT /api/v1/posts/by-path/…`, and storage configured (Admin → Storage). Without the secret the run fails.
- **CrewAI configuration** (crewconfig.yml, deploy-kubernetes.yml, check.yml): secret `JITHENDAR_CREWAI_KEY`, an admin's
  API key (Admin → API keys) with the scopes `crewai:read` and `crewai:import`. Without it the configuration is checked,
  not restored. For editing from the admin: a fine-grained GitHub token with Contents and Pull requests (read and write)
  on this repository only, saved in AI & SEO → Configuration → Settings, or as the Secret the site Deployment reads:
  `kubectl -n jithendar create secret generic jithendar-com-crewconfig --from-literal=token=github_pat_…`.
- **Hybrid RAG** (moks-rag, optional; moks-cms `docs/RAG.md`): the site syncs published posts to rag-api's
  `cms_content` with a token in Secret `jithendar-com-rag` (key `token`). With rag-api 0.2.0 the site gets its own
  token, which may read and write `cms_content` only: from a moks-rag checkout, `scripts/issue-service-token.sh moks-cms`
  (it writes the Secret and restarts rag-api). Until then a copy of rag-api's shared token works:
  `kubectl -n jithendar create secret generic jithendar-com-rag --from-literal=token="$(kubectl -n rag get secret rag-secrets -o jsonpath='{.data.RAG_BEARER_TOKEN}' | base64 -d)"`.
  Either way, then `kubectl -n jithendar rollout restart deploy/jithendar-com`. Without the Secret the sync stays off.
  Then, once, Admin → Integrations → Hybrid RAG → Reindex all posts (the backfill; rag-api skips posts it already has
  unchanged). The SEO agent's token: `scripts/create-seo-agent-rag-secret.sh`.
- **Manifests** (deploy-kubernetes.yml): `scripts/setup-ci-applier.sh` (secret `MK4_CI_APPLY_TOKEN`, variable `MINIKUBE_DEPLOY=true`).
- **moks-cms → this repository**: in moks-cms, variable `RELEASE_NOTIFY_REPOS=moks-tech/jithendar.com` and secret
  `RELEASE_NOTIFY_TOKEN` (a fine-grained token with Contents: read and write on this repository).

Both setup scripts default to `GITHUB_REPO=moks-tech/jithendar.com` and need `KUBE_CONTEXT=<name>` or a
confirmation (`scripts/lib/kube-context.sh`).

## License

Copyright (c) 2026 Jithendar Dharmapuri. All rights reserved.
