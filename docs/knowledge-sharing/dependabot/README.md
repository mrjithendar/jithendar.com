# Dependabot article: evidence and figure notes

Draft: `content/blog/dependabot-setup-five-repositories.mdx` (status `review`, 2026-11-09).

## Figures

`diagrams/build_diagrams.py` writes the editable `diagrams/dependabot-flow.drawio` and the SVG in
`public/images/dependabot/`. `diagrams/render_png.sh` renders a 2x PNG with headless Chrome. Run both from `www/`.
The SVG is rendered by the script (shared writer in `../roboshop-ai/diagrams`), not exported by draw.io: if the
`.drawio` file is edited in draw.io, export it over the SVG, or change the script and rebuild.

## Sources of the labels (read on 2026-11-09)

- `.github/dependabot.yml` in jithendar.com, moks, roboshop-ai, tools and miniKube (schedule, cooldown, groups, ignores).
- `gh api repos/mrjithendar/<repo>` → `security_and_analysis`, `/vulnerability-alerts`, `/automated-security-fixes`:
  alerts and security updates enabled in all five; `allow_auto_merge` false.
- `gh pr list --author app/dependabot --state all` and `/dependabot/alerts` for the counts in section 1.
- Deploy row: header comments of each `dependabot.yml`, `tools/.github/workflows/create-aws-infrastructure.yml`
  (master only), `moks-cms/.github/workflows/ci-jithendar-com.yml` (forks skipped).
