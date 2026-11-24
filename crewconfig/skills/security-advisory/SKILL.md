---
name: security-advisory
description: "Covering vulnerabilities: CVE ids, severity, affected and fixed versions, exploitation status and mitigation."
agents:
  - news.analyst
  - news.writer
  - news.fact_checker
tags:
  - cve
  - topic:security
enabled: true
builtin: true
---

- Lead with the CVE id(s), the affected product and the fixed version.
- Severity: the CVSS score and who assigned it (NVD or the vendor); when they differ, give both.
- Affected and fixed versions exactly as the advisory lists them; never widen or narrow the range.
- Say exploited in the wild only when CISA KEV or the vendor says so; otherwise say the sources report no exploitation.
- What to do: the upgrade path first, then the vendor's mitigation if patching has to wait, then how to check whether you run an affected version.
- No exploit details or proof-of-concept code.
