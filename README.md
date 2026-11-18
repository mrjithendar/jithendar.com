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
| `grafana/` | The site's Grafana dashboards (one ConfigMap; Argo CD's `grafana` Application reads this folder) |
| [`kubernetes/`](kubernetes/README.md) | Every manifest the site runs on mk4: the site (CMS image tag, ConfigMap `jithendar-com-site` from `site.json` and `config/`, practice catalog) and the SEO agent. The practice executor deploys from practice-programming |
| `scripts/` | Deploy (`keep-live-images.py`, `manifests.sh`), content check (`check-content.sh`), content push (`push-content.py`), first-time Secrets (`create-*.sh`), site settings (`set-*-config.sh`), CI access (`setup-ci-*.sh`) |
| `.github/workflows/` | `content.yml` (articles and images, through the site's API), `deploy-kubernetes.yml` (the whole app from `kubernetes/`), `check.yml` (pull requests) |

## Two workflows

| Workflow | When | What it does |
|---|---|---|
| `content.yml` | A push to `master` that changes `content/` or `public/images/`, or a manual run | Checks the files with the CMS image the site runs (`scripts/check-content.sh`), then pushes new and changed images to R2 and new or changed articles as drafts, through the site's API (`scripts/push-content.py`). No image is built and nothing is restarted |
| `deploy-kubernetes.yml` | A merged pull request that changes `kubernetes/`, `site.json` or `config/`, a manual run, or a `moks-cms-released` dispatch | Applies the whole app from the manifests (server dry run, diff, apply, wait, smoke test), including ConfigMap `jithendar-com-site` with `site.json` and `config/` (a change to them rolls the site). The manifests name the image tags of the CMS, the SEO agent and the practice executor. When moks-cms pushes a release, it sends `{component, tag}`; this workflow puts the tag in the manifests, commits it to `master` and applies it |

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

## Setting up this repository (once)

The workflows need these, which moved here from moks-cms:

- **Harbor** (pull the CMS image for the content check): secrets `HARBOR_USERNAME` and `HARBOR_PASSWORD`.
- **Content push** (content.yml): secret `JITHENDAR_API_KEY`, an API key created by an admin in Admin → API keys with
  the scopes `images:write` and `posts:draft`. It needs a moks-cms release that has `PUT /api/v1/images/…` and
  `PUT /api/v1/posts/by-path/…`, and storage configured (Admin → Storage). Without the secret the run fails.
- **Manifests** (deploy-kubernetes.yml): `scripts/setup-ci-applier.sh` (secret `MK4_CI_APPLY_TOKEN`, variable `MINIKUBE_DEPLOY=true`).
- **moks-cms → this repository**: in moks-cms, variable `RELEASE_NOTIFY_REPOS=moks-tech/jithendar.com` and secret
  `RELEASE_NOTIFY_TOKEN` (a fine-grained token with Contents: read and write on this repository).

Both setup scripts default to `GITHUB_REPO=moks-tech/jithendar.com` and need `KUBE_CONTEXT=<name>` or a
confirmation (`scripts/lib/kube-context.sh`).

## License

Copyright (c) 2026 Jithendar Dharmapuri. All rights reserved.
