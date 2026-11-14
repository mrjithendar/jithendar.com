/**
 * The facts on /hire-me that come from the owner's résumé (shared 2026-11-11). Prices, booking links, availability
 * and the offers' wording are NOT here: they are edited in Admin → Appearance → Hire me.
 *
 * Deliberately left out: phone number, personal email and a downloadable CV (they would be public to every scraper;
 * enquiries go through the form), and the HashiCorp Terraform Associate certification, which the résumé dates June
 * 2026 (re-add it here if it is still current).
 */

export const PROFILE = {
  name: "Jithendar Dharmapuri",
  role: "Lead Platform Engineer, AI",
  location: "Singapore",
  yearsExperience: "9+",
  linkedin: "https://linkedin.com/in/jithendardharmapuri",
  github: "https://github.com/mrjithendar",
};

export const CERTIFICATIONS = [{ name: "AWS Certified Solutions Architect – Professional", detail: "valid to April 2027" }];

/** Things built in production, from the current role. */
export const HIGHLIGHTS = [
  "An AI gateway that centralises LLM access, request routing and Amazon Bedrock-backed workflows.",
  "Custom Model Context Protocol (MCP) integrations that give AI agents operational tools and infrastructure context.",
  "AI agents and an SRE agent for incident investigation, diagnostics, knowledge retrieval and troubleshooting.",
  "An AI-assisted incident knowledge application (FastAPI, Ollama, Pinecone, RAG) for natural-language search of past incidents.",
  "Production EKS platforms for regulated workloads, with Istio mTLS, NetworkPolicies and OPA Gatekeeper.",
  "SLO/SLI-driven observability with Prometheus, Grafana, Alertmanager, Langfuse and CloudWatch, including error budgets.",
  "A custom Terraform importer and standardised AWS provisioning through Terraform and GitHub Actions across environments.",
];

export const SKILLS: { group: string; items: string[] }[] = [
  { group: "AI platform engineering", items: ["Amazon Bedrock", "AI gateways", "Model Context Protocol (MCP)", "AI agents", "SRE agents", "RAG", "Langfuse", "LLM observability"] },
  { group: "Cloud, Kubernetes and CI/CD", items: ["AWS", "Azure", "GCP", "EKS", "Kubernetes", "Docker", "Helm", "Argo CD", "Istio", "GitHub Actions", "GitLab CI", "Jenkins"] },
  { group: "Infrastructure as code and languages", items: ["Terraform", "CloudFormation", "Packer", "Python", "Go", "Shell", "Node.js", "TypeScript"] },
  { group: "Observability and security", items: ["Prometheus", "Grafana", "Loki", "Tempo", "CloudWatch", "OPA Gatekeeper", "Istio mTLS", "Wiz", "RBAC"] },
];

export const EXPERIENCE = [
  { role: "Lead Platform Engineer, AI", org: "S&P Global", place: "Singapore", from: "12/2024", to: "present" },
  { role: "Application Engineer", org: "Adecco", place: "Singapore", from: "03/2024", to: "11/2024" },
  { role: "Senior System Engineer", org: "EPAM", place: "Hyderabad", from: "01/2023", to: "03/2024" },
  { role: "Technical Lead", org: "HCL Tech", place: "Hyderabad", from: "10/2021", to: "01/2023" },
  { role: "Senior System Engineer", org: "Wipro", place: "Hyderabad", from: "10/2020", to: "10/2021" },
  { role: "System Administrator", org: "CGS Inc", place: "Hyderabad", from: "04/2019", to: "06/2020" },
  { role: "IT Support Engineer", org: "Coreintegra", place: "Mumbai", from: "04/2017", to: "12/2018" },
];

/** Public work on this site that shows the kind of thing a client gets (all answered 200 on 2026-11-11). */
export const SELECTED_WORK = [
  { title: "RoboShop AI", href: "/projects/roboshop-ai", what: "A polyglot microservices store with an AI shopping assistant, MCP tools and full observability, deployed with Argo CD." },
  { title: "MOKS", href: "/projects/moks", what: "An AI-assisted SRE investigation portal that works from live Kubernetes, Prometheus and Loki evidence." },
  { title: "How jithendar.com runs", href: "/projects/nextjs-site-on-kubernetes", what: "A self-hosted Next.js platform on Kubernetes with PostgreSQL, R2, an admin, audit log, backups and full observability." },
  { title: "Observability for a Next.js platform", href: "/blog/logging-tracing-observability-jithendar-com", what: "Structured logs, traces and metrics wired together, and the gaps a review found." },
];

export const PROCESS = [
  { step: "Intro call", text: "A short call about your goal, your current setup and constraints. No preparation needed." },
  { step: "Proposal", text: "A written scope with deliverables, timeline and price, so you know exactly what you get." },
  { step: "Delivery", text: "Working code and infrastructure in your repositories, documented, with a hand-over your team can run." },
];
