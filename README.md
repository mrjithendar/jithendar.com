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
| `Dockerfile.content` | The content image: `content/`, `public/images/`, `site.json` and `config/` |
| [`kubernetes/`](kubernetes/README.md) | Every manifest the site runs on mk4: the site (CMS image tag, content image, practice catalog) and the SEO agent. The practice executor deploys from practice-programming |
| `scripts/` | Rollout (`ci-rollout.py`, `keep-live-images.py`), content check (`check-content.sh`), first-time Secrets (`create-*.sh`), site settings (`set-*-config.sh`), CI access (`setup-ci-*.sh`) |
| `.github/workflows/` | `content.yml` (content image), `deploy-kubernetes.yml` (the whole app from `kubernetes/`), `check.yml` (pull requests) |

## Two workflows

| Workflow | When | What it does |
|---|---|---|
| `content.yml` | A push to `master` that changes `content/`, `public/images/`, `site.json` or `config/`, or a manual run | Checks the files with the CMS image the site runs (`scripts/check-content.sh`), builds and pushes `jithendar-com-content:latest`, and restarts `deploy/jithendar-com` so its init container copies them in. It skips the restart only when existing unpublished articles were edited and images added: readers would see nothing new. New articles, even drafts, need the restart, since the CMS imports new files into Admin → Posts when it starts |
| `deploy-kubernetes.yml` | A merged pull request that changes `kubernetes/`, a manual run, or a `moks-cms-released` dispatch | Applies the whole app from the manifests (server dry run, diff, apply, wait, smoke test). The manifests name the image tags of the CMS, the SEO agent and the practice executor. When moks-cms pushes a release, it sends `{component, tag}`; this workflow puts the tag in the manifests, commits it to `master` and applies it |

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

## Setting up this repository (once)

The workflows need these, which moved here from moks-cms:

- **Harbor** (pull the CMS image for the content check, push `jithendar-com-content`): secrets `HARBOR_USERNAME` and `HARBOR_PASSWORD`.
- **Restarts** (content.yml): `scripts/setup-ci-deployer.sh` (variables `MK4_API_SERVER` and `MK4_CA_DATA`, secret `MK4_CI_TOKEN`).
- **Manifests** (deploy-kubernetes.yml): `scripts/setup-ci-applier.sh` (secret `MK4_CI_APPLY_TOKEN`, variable `MINIKUBE_DEPLOY=true`).
- **moks-cms → this repository**: in moks-cms, variable `RELEASE_NOTIFY_REPOS=moks-tech/jithendar.com` and secret
  `RELEASE_NOTIFY_TOKEN` (a fine-grained token with Contents: read and write on this repository).

Both setup scripts default to `GITHUB_REPO=moks-tech/jithendar.com` and need `KUBE_CONTEXT=<name>` or a
confirmation (`scripts/lib/kube-context.sh`).

## First deploy from this repository

1. Run `content.yml` by hand: it pushes `jithendar-com-content:latest` (now with `site.json` and `config/`) and moves
   the init container onto it.
2. Then run `deploy-kubernetes.yml` by hand: it applies the `site` volume that brings `site.json` and `config/` into
   the pod. The manifests pin today's CMS image (`moks-cms:pr-111`), so nothing else changes. practice-programming must
   have pushed `practice-catalog:latest` first: the new init container needs it.
3. After the moks-cms change that reads site files at run time is merged and released, its dispatch (or a pull
   request) moves `moks-cms:pr-111` to that release.

## License

Copyright (c) 2026 Jithendar Dharmapuri. All rights reserved.
