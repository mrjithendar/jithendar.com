---
crew: report
key: analyse
agent: site_analyst
label: Analyse a console report
expected_output: JSON with executive_summary, achievements, risks, root_causes, fixes, recommendations and action_plan.
variables:
  - period
  - categories
contract: Then the facts block (every figure the analysis may use, with ids M…), the findings block (problems the web app found in the data, ids F…, each confirmed or not), the categories block (each category's figures and source status) and the untrusted block (error messages and log lines, ids E…). Afterwards every number must equal a fact and every evidence id must exist; an item that fails is left out, and a cause marked confirmed whose evidence is not a confirmed finding or an error is shown as probable.
output_editable: false
---

Analyse the {period} report of this site ({categories}). Write: an executive summary (overall performance, the main achievements, the major problems and risks, what changed); achievements and risks; root causes for the significant problems; fixes; improvement recommendations (SEO, content, keywords and topics, internal linking, editorial planning, crews and agents, prompts and tasks, workflow reliability, cost, performance); and a prioritised action plan (critical = act now, high, medium, low) with the component or person that owns each action when the evidence names one. Be specific to these dates and this data: name the flows, crews, models, pages, queries and sources involved. No generic advice: every item cites the evidence ids (F…, M…, E…) it rests on. A root cause is "confirmed" only when the evidence shows it directly (an error message, a failed check), "probable" when it is the most likely explanation, "investigate" when more data is needed, and then say which check would settle it. Copy figures exactly as written in the facts; never compute a new number, percentage or difference. Say where data is missing (sources not available).
