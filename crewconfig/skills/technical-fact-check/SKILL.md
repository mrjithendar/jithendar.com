---
name: technical-fact-check
description: Checklist for reviewing commands, versions, config and code in technical writing against the sources.
agents:
  - editorial.reviewer
  - optimization.reviewer
tags: []
enabled: true
builtin: true
---

Check every item, not only the ones that look wrong.
- Commands: the subcommand and every flag exist in the version the article targets; spelling and short or long forms match the docs.
- Defaults and limits: ports, timeouts, sizes and quotas match the source for that version.
- APIs and config: apiVersion, kind and field names are current and not deprecated; YAML nesting is valid; required fields are present.
- Consistency: names, namespaces, file paths and versions are the same in every code block and in the prose.
- Time-sensitive words (latest, new, recently, now supports) need a version or a date from a source, or they go.
- Output shown as expected must be plausible for the command shown.
- Anything you cannot verify is flagged with what is missing, never rewritten from memory.
