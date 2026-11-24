# CrewAI configuration

The CrewAI setup of jithendar.com as files: every crew with its agents and tasks, every flow, skill, schedule and
content source, and, read-only, the tools, prompt guardrails and model providers they run with. This folder is the
source the site's configuration is restored from after a deployment, and every change to it is a reviewed commit.

Written by the CMS (AI & SEO → Configuration → Export, or Write to repository). Edit the files here or in the admin's
repository editor; `manifest.json` is rewritten by both (an import only warns when a checksum in it is stale).

| Folder | What | Items | On import |
|---|---|---|---|
| `categories/categories.yaml` | Categories | 7 | imported |
| `sources/sources.yaml` | Content sources | 0 | imported |
| `crews/` | Crews | 5 | imported |
| `agents/` | Agents | 16 | imported |
| `tasks/` | Tasks | 17 | imported |
| `skills/` | Skills | 22 | imported |
| `flows/` | Flows | 21 | imported |
| `schedules/schedules.yaml` | Schedules | 15 | imported |
| `tools/tools.yaml` | Tools | 12 | read-only |
| `prompts/guardrails.yaml` | Prompt guardrails | 3 | read-only |
| `providers/providers.yaml` | Model providers | 0 | read-only |

## Editing

- **Agents, tasks and skills** are Markdown: the front matter holds the fields, the body the long text (an agent's
  backstory, a task's instructions with its `{placeholders}`, a skill's instructions).
- **Crews defined in code** (`editorial`, `news`, `optimization`, `promotion`, `report`) keep their structure in the SEO agent's code: change their
  agents' role, goal, backstory, model, limits and tools (from the crew's `code.allowed_tools`) and their tasks'
  instructions and editable expected outputs. An import saves the difference from the code as a new crew version. Adding
  or removing one of their agents or tasks is refused: duplicate the crew in the admin to change its structure.
- **Crews and flows made in the admin** (`definition: spec`) are complete here and can be added, changed and removed.
- **Removing a file** removes nothing on the site, unless the import is run with removal switched on
  (it never removes what is defined in code or shipped with the CMS).
- **No secrets**: keys and tokens never belong here. Providers list where a key is (`key_ref`), never the key; an export
  redacts anything that looks like a credential and says so.

## Checks

`schemas/` has the JSON Schema of every file kind. Every import checks the files' schemas, that every reference
resolves (a crew's agents and tasks, a flow's crews, a schedule's flow, a skill's agents, categories and sources), that
no id is used twice, and then asks the SEO agent to check every crew and flow it would save. An import is a plan first
(added, changed, unchanged, in conflict, removed), applied in one transaction, and verified afterwards.

Format 2 (`moks-crewai-bundle`); the CMS also imports the one-file export of earlier versions (`moks-crewai-config`).
