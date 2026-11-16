# Ansible explained (RoboShop repository) article

Status: **draft for author review, not published.** Written 2026-11-12 from `github.com/moks-tech/ansible` at `29ea7b1`,
for readers with no technical background.

| Asset | Location |
| --- | --- |
| Article | `content/blog/ansible-explained-roboshop-repository.mdx` (`status: review`, no `publishedAt`) |
| Figures | 11 SVGs + 2× PNGs in `public/images/ansible-roboshop/`; editable `.drawio` sources here in `diagrams/` |
| Featured image | `/images/ansible-roboshop/01-big-picture.png` (1440 × 840) |
| Reading time | ≈ 24 min (5,300 words at 220 words/min) once the `<Todo>` is removed |

Figures: `python3 sites/jithendar.com/docs/knowledge-sharing/ansible-roboshop/diagrams/build_diagrams.py` writes the `.drawio` files and the
SVGs (it reuses the RoboShop series' writer and checks that every label fits its box).
`CHROMIUM_PATH="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" python3 sites/jithendar.com/docs/knowledge-sharing/ansible-roboshop/diagrams/render_png.py`
writes the PNGs (Playwright's own browser is not installed on the owner's Mac). The SVGs are rendered by the builder, not
exported by draw.io: after editing a `.drawio` file in draw.io, export it over the SVG.

## SEO and publishing metadata

| Field | Value |
| --- | --- |
| H1 (`title`) | Ansible Explained Without the Jargon: How One Repository Sets Up a Whole Online Shop |
| SEO title | Ansible Explained Simply: Playbooks, Roles and Inventory |
| Slug | `ansible-explained-roboshop-repository` |
| Primary keyword | Ansible explained |
| Secondary keywords | what is an Ansible playbook; Ansible roles; Ansible dynamic inventory AWS; Ansible vault |
| Category | `devops-sre` (`infrastructure-as-code` also fits) |

## Facts the article relies on (check before publishing)

- Eight EC2 hosts (`terraform/terraform.tfvars` `COMPONENT`): frontend, catalogue, user, cart, shipping, payment, mongodb,
  rabbitmq. MySQL and Redis are Aurora and ElastiCache (Terraform); the `mysql`/`redis` roles are self-hosted alternatives.
- Play order, inventory, `ansible.cfg`, Jenkins actions and lint checks are quoted from `roboshop.yml`,
  `inventory/aws_ec2.yml`, `ansible.cfg`, `Jenkinsfile`, `.github/workflows/lint.yml` and `.pre-commit-config.yaml`.
- `group_vars/all/vault.yml` does not exist in the repository yet (only `examples/vault.yml.example`).
- Secrets: the owner plans to move to HashiCorp Vault at jithendar.com/vault. When that is live, rewrite "Keeping
  secrets" and figure `09-secrets`.
- Not checked against a live AWS run.
