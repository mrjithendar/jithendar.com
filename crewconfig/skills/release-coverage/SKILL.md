---
name: release-coverage
description: "Covering a software release: the changes operators will notice, breaking changes, and the upgrade path."
agents:
  - news.analyst
  - news.writer
tags:
  - release
enabled: true
builtin: true
---

- Lead with the version and the two or three changes operators will notice.
- Breaking changes, removals and deprecations get their own section, each with what to change before upgrading.
- Keep generally available features apart from beta or alpha ones, as the release notes label them.
- Upgrade notes: supported upgrade paths, required intermediate versions and known issues, from the release notes.
- Skip the long tail of minor fixes unless one closes a well-known problem.
