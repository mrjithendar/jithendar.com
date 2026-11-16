# jithendar.com

The website [jithendar.com](https://jithendar.com): its identity, articles and images, and everything that deploys it
to the mk4 cluster. The software it runs is [moks-cms](https://github.com/mrjithendar/moks-cms), which only tests its
code and pushes images. This repository builds the site on those images and deploys it. Until 2026-11-16 the site
lived in moks-cms as `sites/jithendar.com/`. Its history up to then came along with it.

| Path | Contents |
|---|---|
| `site.json` | Identity: host, name, tagline, author, social links, AdSense ID, AI crawler policy |
| `config/` | `redirects.ts`, `gone.ts` (URLs answered with 410), `hire-me-profile.ts` (`/hire-me`) |
| `content/` | `blog/`, `news/`, `projects/`, `pages/`, `authors/` (MDX), `python-practice/` |
| `public/images/` | Images the articles use, served as `/images/…` |
| `docs/` | Sources of the articles' figures, and scripts that check the articles (never shipped) |
| `grafana/` | The site's Grafana dashboards (one ConfigMap; Argo CD's `grafana` Application reads this folder) |
| `moks-cms.json` | The moks-cms images this site runs: `builder` (the app is built on it), `seoAgent`, `practiceExecutor` |
| `Dockerfile`, `Dockerfile.content` | The app image (moks-cms built for this site) and the content image (MDX and images only) |
| [`kubernetes/`](kubernetes/README.md) | Every manifest the site runs on mk4: the site, the Python practice executor, the SEO agent |
| `scripts/` | Release and rollout (`ci-rollout.py`, `keep-live-images.py`), first-time Secrets (`create-*.sh`), site settings (`set-*-config.sh`), CI access (`setup-ci-*.sh`), checks |
| `.github/workflows/` | `check.yml` (pull requests), `release.yml` (deploys), `deploy-kubernetes.yml` (applies `kubernetes/`) |

## How a change ships

| Change | What happens when it reaches `master` |
|---|---|
| An article or image (`content/`, `public/images/`) | `release.yml` checks the MDX with moks-cms's own tests, pushes `jithendar-com-content:latest` and rolls the site. If the push only adds or edits drafts plus new images, it sends new drafts to Admin → Posts instead (secret `JITHENDAR_API_KEY`) and leaves the pods alone |
| `site.json`, `config/` | `release.yml` builds the app image on the pinned builder, smoke-tests it, pushes `jithendar-com:<builder pin>-<commit>` and rolls the site onto it |
| A new moks-cms release | moks-cms sends a `moks-cms-released` dispatch. `release.yml` moves the pin in `moks-cms.json`, commits it, and rebuilds the app (builder) or rolls the service onto the new tag (seo-agent, practice-executor; only when `SEO_AGENT_DEPLOY` / `PRACTICE_EXECUTOR_DEPLOY` is `true`) |
| A manifest (`kubernetes/`) | `deploy-kubernetes.yml` applies it when its pull request is merged (server dry run, diff, apply, wait, smoke test) |

To take a moks-cms release by hand, or to go back to an earlier one, edit the tag in `moks-cms.json` and push. To re-run
a release: Actions → release → Run workflow.

## Working on the site locally

The app comes from a moks-cms checkout next to this one:

```bash
cd ../moks-cms/services/www
SITE_DIR=../../../jithendar.com npm run dev          # content/ and public/images/ are links to this repository
```

Or check the content the way CI does, in the pinned builder (needs `docker login registry.jithendar.com`):

```bash
scripts/check-content.sh registry.jithendar.com/jithendar/moks-cms-builder:"$(jq -r .builder moks-cms.json)"
```

## Setting up this repository (once)

The workflows need these, which moved here from moks-cms:

- **Harbor** (pull moks-cms images, push `jithendar-com` and `jithendar-com-content`): secrets `HARBOR_USERNAME` and `HARBOR_PASSWORD`.
- **Rollouts**: `scripts/setup-ci-deployer.sh` (variables `MK4_API_SERVER` and `MK4_CA_DATA`, secret `MK4_CI_TOKEN`).
- **Manifests**: `scripts/setup-ci-applier.sh` (secret `MK4_CI_APPLY_TOKEN`, variable `MINIKUBE_DEPLOY=true`).
- **Drafts**: secret `JITHENDAR_API_KEY` (Admin → API keys, scopes posts:read + posts:write).
- **Services**: variables `SEO_AGENT_DEPLOY` and `PRACTICE_EXECUTOR_DEPLOY` set to `true`, to let pin moves roll them out.
- **moks-cms → this repository**: in moks-cms, variable `RELEASE_NOTIFY_REPOS=mrjithendar/jithendar.com` and secret
  `RELEASE_NOTIFY_TOKEN` (a fine-grained token with Contents: read and write on this repository).

Both setup scripts default to `GITHUB_REPO=mrjithendar/jithendar.com` and need `KUBE_CONTEXT=<name>` or a
confirmation (`scripts/lib/kube-context.sh`).

## License

Copyright (c) 2026 Jithendar Dharmapuri. All rights reserved.
