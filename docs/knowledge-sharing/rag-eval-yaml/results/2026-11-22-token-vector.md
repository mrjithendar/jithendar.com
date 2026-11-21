# RAG eval: token-vector

- Date: 2026-11-22 · commit `e4669f7` · embeddings `onnx:bge-small-en-v1.5` · full text: none (vector only)
- Corpus: 45 articles, 2117 chunks (chunker `token`, token counter `onnx:bge-small-en-v1.5`, longest embedded input 471 tokens, 0 over 512)
- Questions: 95 (11 no-answer), k = 6, configured floor 0.15
- Retrieval config: `mode=vector candidates=20 rrf_k=60 identifier_boost=0.0164 max_per_article=0`

| Recall@1 | Recall@3 | Recall@6 | MRR | Anchor hit | No-answer FP @ floor | Calibrated floor | No-answer FP @ calibrated | p50 ms | p95 ms |
|---|---|---|---|---|---|---|---|---|---|
| 81.0 | 90.5 | 95.2 | 0.865 | 88.1 | 100.0 | 0.59 | 90.9 | 0.74 | 0.77 |

## By question type

| Type | n | Recall@3 | MRR |
|---|---|---|---|
| concept | 31 | 87.1 | 0.817 |
| how-to | 18 | 88.9 | 0.796 |
| exact-term | 22 | 95.5 | 0.966 |
| troubleshooting | 13 | 92.3 | 0.904 |

## Hard set by tag

| Tag | n | Recall@3 | MRR |
|---|---|---|---|
| paraphrase | 19 | 68.4 | 0.570 |
| multi-hop | 7 | 85.7 | 0.798 |
| exact | 11 | 90.9 | 0.932 |

## Floor table (cosine pre-filter)

| Floor | Expected answers lost | No-answer FP rate |
|---|---|---|
| 0.00 | 0 | 100.0 |
| 0.15 | 0 | 100.0 |
| 0.30 | 0 | 100.0 |
| 0.40 | 0 | 100.0 |
| 0.50 | 0 | 100.0 |
| 0.55 | 0 | 90.9 |
| 0.59 | 0 | 90.9 |
| 0.60 | 1 | 90.9 |
| 0.65 | 2 | 72.7 |
| 0.70 | 11 | 45.5 |

## Per question

| id | type | rank | anchor | best cos | top results |
|---|---|---|---|---|---|
| c01 | concept | 1 | ✓ | 0.800 | 15-essential-kubernetes-tools-devops-engineers-2026-part-1#helm-or-kustomize (0.80); 15-essential-kubernetes-tools-devops-engineers-2026-part-1#4-kustomize-configuration-without-templates (0.73); 15-essential-kubernetes-tools-devops-engineers-2026-part-1#1-helm-the-kubernetes-package-manager (0.71) |
| c02 | concept | 1 | ✓ | 0.834 | 15-essential-kubernetes-tools-devops-engineers-2026-part-2#9-keda-event-driven-autoscaling (0.83); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#9-keda-event-driven-autoscaling (0.78); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#keda-or-hpa (0.73) |
| c03 | concept | 1 | ✓ | 0.822 | cloudnativepg-postgres-cluster-minikube-terraform#what-we-wanted (0.82); cloudnativepg-postgres-cluster-minikube-terraform#44-one-database-and-one-role-per-application (0.81); cloudnativepg-postgres-cluster-minikube-terraform#conclusion (0.79) |
| c04 | concept | 1 | ✓ | 0.771 | valkey-redis-sentinel-minikube-terraform#can-i-use-valkeyredissvc-instead-of-valkey-master (0.77); valkey-redis-sentinel-minikube-terraform#why-valkey-instead-of-redis (0.76); valkey-redis-sentinel-minikube-terraform#6-moving-the-applications (0.75) |
| c05 | concept | 1 | ✓ | 0.866 | fastapi-and-fastmcp-ai-projects#an-http-api-and-an-agent-tool-are-different-contracts (0.87); devops-interview-preparation-guide#top-mcp-questions-and-model-answers (0.78); roboshop-ai-mcp-server#mcp-in-plain-language (0.74) |
| c06 | concept | 1 | ✓ | 0.840 | pytorch-rag-reranking-moks-sre-agent#live-fallback-and-what-is-not-measured (0.84); pytorch-rag-reranking-moks-sre-agent#evaluation-and-results (0.84); pytorch-rag-reranking-moks-sre-agent#where-pytorch-fits (0.83) |
| c07 | concept | 1 | ✓ | 0.804 | kubernetes-history-origins-evolution-milestones#the-founders-and-the-codename (0.80); kubernetes-history-origins-evolution-milestones#lessons-not-a-code-dump (0.80); kubernetes-history-origins-evolution-milestones#the-founders-and-the-codename (0.78) |
| c08 | concept | 1 | ✓ | 0.793 | moks-rag-and-skills-design# (0.79); moks-rag-and-skills-design#the-short-version (0.78); moks-rag-and-skills-design#how-rag-works (0.77) |
| c09 | concept | 1 | ✓ | 0.846 | shell-scripting-vs-python#what-do-shell-scripts-and-python-have-in-common (0.85); shell-scripting-vs-python#shell-scripting-vs-python-the-short-answer (0.84); shell-scripting-vs-python#quick-reference (0.84) |
| c10 | concept | 1 | ✓ | 0.847 | roboshop-ai-gateway#how-it-differs-from-an-ingress-a-proxy-and-an-api-gateway (0.85); four-ai-systems-one-cluster#the-ai-gateway (0.82); roboshop-ai-microservices#how-responsibilities-are-divided (0.79) |
| c11 | concept | 2 | ✓ | 0.815 | system-design-evolution-cloud-native-ai-2026#is-a-monolith-still-a-good-choice-in-2026 (0.82); system-design-evolution-1990s-to-microservices#monolith-or-microservices (0.78); system-design-evolution-1990s-to-microservices#monolithic-applications (0.75) |
| c12 | concept | 2 | ✓ | 0.848 | istio-service-mesh-minikube-features-setup-troubleshooting#1-what-a-service-mesh-is-and-why-istio (0.85); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#istio-or-linkerd (0.83); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#11-linkerd-the-lightweight-service-mesh (0.80) |
| c13 | concept | 1 | ✓ | 0.900 | python-vs-typescript#why-none-is-not-the-same-as-null-and-undefined (0.90); python-vs-typescript#functions-and-return-values (0.83); learning-typescript-real-project-jithendar-com#null-undefined-and-unions (0.82) |
| c14 | concept | 1 | ✓ | 0.783 | four-ai-systems-one-cluster# (0.78); four-ai-systems-one-cluster#the-platform (0.78); four-ai-systems-one-cluster#shared-patterns (0.76) |
| h01 | how-to | 1 | ✓ | 0.849 | github-actions-authenticate-minikube# (0.85); github-actions-authenticate-minikube#7-building-the-kubeconfig-in-the-job (0.83); github-actions-authenticate-minikube# (0.81) |
| h02 | how-to | 1 | ✓ | 0.779 | istio-service-mesh-minikube-features-setup-troubleshooting#61-permissive-to-strict-without-guessing (0.78); istio-service-mesh-minikube-features-setup-troubleshooting#conclusion (0.75); how-i-built-jithendar-com#edge-and-networking-istio-is-the-edge-not-kong (0.75) |
| h03 | how-to | 1 | ✓ | 0.877 | cloudflare-turnstile-nextjs-bot-protection#path-1-the-contact-form (0.88); cloudflare-turnstile-nextjs-bot-protection#path-1-the-contact-form (0.87); cloudflare-turnstile-nextjs-bot-protection#path-1-the-contact-form (0.87) |
| h04 | how-to | 1 | ✓ | 0.868 | mermaid-diagrams-on-jithendar-com#step-2-draw-the-diagram-in-the-browser (0.87); mermaid-diagrams-on-jithendar-com#three-ways-to-render-mermaid (0.86); mermaid-diagrams-on-jithendar-com#three-ways-to-render-mermaid (0.85) |
| h05 | how-to | 1 | ✓ | 0.796 | dependabot-setup-five-repositories#how-do-i-stop-getting-so-many-prs (0.80); dependabot-setup-five-repositories#will-grouping-hide-a-broken-update (0.72); dependabot-setup-five-repositories#12-recap (0.72) |
| h06 | how-to | 1 | ✓ | 0.890 | deploy-roboshop-ai-amazon-eks# (0.89); deploy-roboshop-ai-amazon-eks#prerequisites-and-tested-versions (0.88); deploy-roboshop-ai-amazon-eks#troubleshooting (0.87) |
| h07 | how-to | 1 | ✓ | 0.784 | cloudnativepg-postgres-cluster-minikube-terraform#how-do-i-rotate-an-applications-password (0.78); cloudnativepg-postgres-cluster-minikube-terraform#44-one-database-and-one-role-per-application (0.76); cloudnativepg-postgres-cluster-minikube-terraform#44-one-database-and-one-role-per-application (0.74) |
| h08 | how-to | 1 | ✓ | 0.824 | learning-typescript-real-project-jithendar-com#runtime-validation-with-zod (0.82); learning-typescript-real-project-jithendar-com#what-typescript-is-and-what-it-is-not (0.81); learning-typescript-real-project-jithendar-com#declaring-a-type-is-not-checking-the-data (0.81) |
| h09 | how-to | 1 | ✓ | 0.820 | logging-tracing-observability-jithendar-com#2-the-tools (0.82); logging-tracing-observability-jithendar-com#across-the-one-internal-service-boundary (0.79); logging-tracing-observability-jithendar-com#initialization (0.77) |
| h10 | how-to | 1 | ✓ | 0.859 | fastapi-and-fastmcp-ai-projects#how-tools-are-registered (0.86); roboshop-ai-mcp-server#why-not-use-the-official-sdk-directly-instead-of-fastmcp (0.77); fastapi-and-fastmcp-ai-projects#how-tools-are-registered (0.77) |
| h11 | how-to | 1 | ✓ | 0.821 | devops-interview-preparation-guide#how-long-does-devops-interview-preparation-take (0.82); devops-interview-preparation-guide#a-7-week-roadmap (0.80); devops-interview-preparation-guide#how-to-use-this-devops-interview-preparation-guide (0.76) |
| h12 | how-to | 1 |  | 0.834 | kiali-minikube-service-mesh-observability#our-environment (0.83); kiali-minikube-service-mesh-observability#why-we-added-a-mesh-and-why-kiali (0.81); kiali-minikube-service-mesh-observability#summary (0.79) |
| e01 | exact-term | 1 | ✓ | 0.796 | dependabot-setup-five-repositories#what-is-versioning-strategy-increase (0.80); dependabot-setup-five-repositories#do-i-need-dependabotyml-for-security-updates (0.76); dependabot-setup-five-repositories#1-what-i-have-running (0.75) |
| e02 | exact-term | 1 | ✓ | 0.851 | shell-scripting-vs-python#set--e-set--u-and-set--o-pipefail-one-at-a-time (0.85); shell-scripting-vs-python#set--e-set--u-and-set--o-pipefail-one-at-a-time (0.85); shell-scripting-vs-python#set--e-set--u-and-set--o-pipefail-one-at-a-time (0.82) |
| e03 | exact-term | 1 | ✓ | 0.681 | istio-service-mesh-minikube-features-setup-troubleshooting#envoy-response-flags (0.68); istio-service-mesh-minikube-features-setup-troubleshooting#sources (0.66); istio-service-mesh-minikube-features-setup-troubleshooting#7-observability (0.60) |
| e04 | exact-term | 1 | ✓ | 0.914 | learning-terraform-real-project-tools-repository#sensitive--true-does-not-keep-a-value-out-of-state (0.91); learning-terraform-real-project-tools-repository#state-is-sensitive (0.85); learning-terraform-real-project-tools-repository#what-this-repository-actually-does (0.79) |
| e05 | exact-term | 1 | ✓ | 0.845 | learning-terraform-real-project-tools-repository#refactoring-with-moved (0.85); learning-terraform-real-project-tools-repository#import-adopting-something-that-already-exists (0.76); learning-terraform-real-project-tools-repository#locals-name-a-value-once (0.76) |
| e06 | exact-term | 1 | ✓ | 0.819 | dependabot-setup-five-repositories#what-are-the-useful-pr-comment-commands (0.82); dependabot-setup-five-repositories#12-recap (0.76); dependabot-setup-five-repositories#will-grouping-hide-a-broken-update (0.73) |
| e07 | exact-term | 1 | ✓ | 0.724 | cloudnativepg-postgres-cluster-minikube-terraform#fatal-too-many-connections-for-role (0.72); roboshop-ai-gateway#timeouts-retries-and-overload (0.62); devops-interview-preparation-guide#scenario-an-agent-closed-40-tickets-after-reading-one (0.62) |
| e08 | exact-term | 1 | ✓ | 0.850 | learning-terraform-real-project-tools-repository#known-after-apply (0.85); learning-terraform-real-project-tools-repository#reading-a-plan (0.73); learning-terraform-real-project-tools-repository#the-full-sequence (0.72) |
| e09 | exact-term | 1 | ✓ | 0.744 | valkey-redis-sentinel-minikube-terraform#oom-command-not-allowed-when-used-memory--maxmemory (0.74); valkey-redis-sentinel-minikube-terraform#43-memory-durability-and-a-shared-server (0.72); valkey-redis-sentinel-minikube-terraform#45-one-acl-user-and-database-range-per-application (0.69) |
| e10 | exact-term | 1 | ✓ | 0.810 | shell-scripting-vs-python#subprocessrun-with-an-argument-list (0.81); shell-scripting-vs-python#why-shelltrue-and-eval-change-the-rules (0.80); shell-scripting-vs-python#functions (0.77) |
| e11 | exact-term | 1 | ✓ | 0.811 | learning-terraform-real-project-tools-repository#where-values-come-from-and-which-wins (0.81); learning-terraform-real-project-tools-repository#what-this-repository-actually-does (0.80); learning-terraform-real-project-tools-repository#import-adopting-something-that-already-exists (0.78) |
| t01 | troubleshooting | 1 | ✓ | 0.792 | 15-essential-kubernetes-tools-devops-engineers-2026-part-1#2-argo-cd-gitops-continuous-delivery (0.79); 15-essential-kubernetes-tools-devops-engineers-2026-part-1#argo-cd-application-is-outofsync (0.79); kiali-minikube-service-mesh-observability#our-environment (0.71) |
| t02 | troubleshooting | 1 | ✓ | 0.790 | 15-essential-kubernetes-tools-devops-engineers-2026-part-2#istio-calls-fail-after-enabling-strict-mtls (0.79); istio-service-mesh-minikube-features-setup-troubleshooting#61-permissive-to-strict-without-guessing (0.78); istio-service-mesh-minikube-features-setup-troubleshooting#62-authorizationpolicy-dry-run-first (0.76) |
| t03 | troubleshooting | 1 | ✓ | 0.728 | cloudnativepg-postgres-cluster-minikube-terraform#an-application-breaks-behind-pgbouncer (0.73); pytorch-rag-reranking-moks-sre-agent#bounded-capacity-deadlines-and-cancellation (0.64); cloudnativepg-postgres-cluster-minikube-terraform#why-session-mode-pgbouncer (0.63) |
| t04 | troubleshooting | 1 | ✓ | 0.755 | valkey-redis-sentinel-minikube-terraform#queue-workers-or-subscribers-disconnect-every-30-seconds (0.75); valkey-redis-sentinel-minikube-terraform#53-what-healthy-looks-like (0.67); valkey-redis-sentinel-minikube-terraform#44-the-haproxy-post-renderer (0.66) |
| t05 | troubleshooting | 1 | ✓ | 0.821 | 15-essential-kubernetes-tools-devops-engineers-2026-part-2#karpenter-cannot-provision-nodes-for-pending-pods (0.82); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#8-karpenter-just-in-time-nodes (0.78); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#8-karpenter-just-in-time-nodes (0.78) |
| t06 | troubleshooting | 1 | ✓ | 0.781 | 15-essential-kubernetes-tools-devops-engineers-2026-part-2#cert-manager-fails-to-issue-or-renew-a-certificate (0.78); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#how-does-cert-manager-renew-certificates (0.76); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#13-cert-manager-certificate-lifecycle-automation (0.74) |
| t07 | troubleshooting | 1 | ✓ | 0.784 | roboshop-ai-gateway#chat-fails-with-503-feature-unavailable (0.78); roboshop-ai-gateway#the-widget-returns-502-but-the-store-is-fine (0.75); roboshop-ai-gateway#following-one-chat-request (0.73) |
| t08 | troubleshooting | 1 | ✓ | 0.858 | devops-interview-preparation-guide#scenario-a-rollout-is-stuck-and-pods-are-crash-looping (0.86); devops-interview-preparation-guide#scenario-a-rollout-is-stuck-and-pods-are-crash-looping (0.85); devops-interview-preparation-guide#top-kubernetes-questions-and-model-answers (0.81) |
| t09 | troubleshooting | 1 | ✓ | 0.854 | dependabot-setup-five-repositories#why-didnt-dependabot-open-a-pr-for-my-alert (0.85); dependabot-setup-five-repositories#what-happened-this-week (0.74); dependabot-setup-five-repositories#how-i-triage-an-alert (0.73) |
| t10 | troubleshooting | 1 | ✓ | 0.842 | cloudnativepg-postgres-cluster-minikube-terraform#psql-fails-with-server-certificate-does-not-match-host-name (0.84); cloudnativepg-postgres-cluster-minikube-terraform#psql-says-invalid-connection-option-sslnegotiation-or-hangs-at-the-gateway (0.74); cloudnativepg-postgres-cluster-minikube-terraform#postgres-answers-rbac-access-denied-or-psql-is-cut-off-immediately (0.73) |
| n01 | no-answer | — |  | 0.683 | 15-essential-kubernetes-tools-devops-engineers-2026-part-2#9-keda-event-driven-autoscaling (0.68); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#9-keda-event-driven-autoscaling (0.65); roboshop-ai-eks-system-design#scaling-keda-for-pods-karpenter-for-nodes (0.65) |
| n02 | no-answer | — |  | 0.523 | shell-scripting-vs-python#running-an-external-command (0.52); shell-scripting-vs-python#standard-output-versus-standard-error (0.52); shell-scripting-vs-python#2-the-jithendarcom-smoke-test-bash (0.52) |
| n03 | no-answer | — |  | 0.625 | cloudflare-turnstile-nextjs-bot-protection#using-the-component-in-a-form (0.63); cloudflare-turnstile-nextjs-bot-protection#rendering-the-widget-and-receiving-the-token (0.62); cloudflare-turnstile-nextjs-bot-protection#2-what-cloudflare-turnstile-is (0.61) |
| n04 | no-answer | — |  | 0.702 | learning-typescript-real-project-jithendar-com#generics (0.70); learning-typescript-real-project-jithendar-com#api-requests-and-asynchronous-code (0.70); learning-typescript-real-project-jithendar-com#api-requests-and-asynchronous-code (0.70) |
| n05 | no-answer | — |  | 0.706 | devops-interview-preparation-guide#top-ai-system-design-questions-and-model-answers (0.71); rag-evaluation-ask-the-blog-jithendar-com#3-every-sunday-watch-the-live-index (0.70); pytorch-rag-reranking-moks-sre-agent#moks-integration-and-fallback (0.70) |
| n06 | no-answer | — |  | 0.630 | logging-tracing-observability-jithendar-com#6-metrics-dashboards-and-alerts (0.63); kiali-minikube-service-mesh-observability#tracing-wizards-and-ambient-mode (0.61); kiali-minikube-service-mesh-observability#traffic-graph (0.61) |
| n07 | no-answer | — |  | 0.686 | github-actions-authenticate-minikube#6-getting-the-values-into-github (0.69); github-actions-authenticate-minikube#7-building-the-kubeconfig-in-the-job (0.68); github-actions-authenticate-minikube#10-what-i-would-change-next (0.67) |
| n08 | no-answer | — |  | 0.686 | moks-observability-logging-tracing-ai-agent-monitoring#how-it-was-deployed-and-what-was-verified (0.69); moks-observability-logging-tracing-ai-agent-monitoring#the-event-stream (0.68); moks-observability-logging-tracing-ai-agent-monitoring#structured-logging-and-correlation (0.68) |
| x01 | concept | 1 | ✓ | 0.737 | cloudflare-turnstile-nextjs-bot-protection#1-why-a-website-needs-bot-protection (0.74); cloudflare-turnstile-nextjs-bot-protection#path-1-the-contact-form (0.69); cloudflare-turnstile-nextjs-bot-protection#8-handling-failures-gracefully (0.69) |
| x02 | how-to | 3 | ✓ | 0.702 | valkey-redis-sentinel-minikube-terraform#45-one-acl-user-and-database-range-per-application (0.70); devops-interview-preparation-guide#scenario-an-app-in-a-private-subnet-cant-reach-s3 (0.70); github-actions-authenticate-minikube#9-security-boundaries-and-weak-spots (0.69) |
| x03 | concept | 1 | ✓ | 0.651 | dependabot-setup-five-repositories#how-do-i-stop-getting-so-many-prs (0.65); roboshop-ai-microservices#how-a-product-page-request-travels (0.65); roboshop-ai-microservices#when-a-modular-monolith-would-be-simpler (0.65) |
| x04 | concept | 1 | ✓ | 0.671 | dependabot-setup-five-repositories#5-cooldown-let-new-releases-settle-first (0.67); ssg-isr-nextjs-jithendar-com#trade-offs (0.66); dependabot-setup-five-repositories#why-didnt-dependabot-open-a-pr-for-my-alert (0.63) |
| x05 | how-to | 2 | ✓ | 0.695 | opa-gatekeeper-kubernetes-policies-jithendar-com#a-shared-node-is-a-shared-risk (0.70); cloudnativepg-postgres-cluster-minikube-terraform#44-one-database-and-one-role-per-application (0.69); cloudnativepg-postgres-cluster-minikube-terraform#what-we-wanted (0.66) |
| x06 | concept | — |  | 0.676 | caching-isr-ssg-image-optimisation-nextjs#step-3-understand-what-isr-does-over-time (0.68); caching-isr-ssg-image-optimisation-nextjs#the-hard-part-invalidation-across-replicas (0.67); caching-isr-ssg-image-optimisation-nextjs#wiring-the-bus-to-the-page-cache (0.67) |
| x07 | concept | 1 | ✓ | 0.621 | four-ai-systems-one-cluster#the-evidence-ledger-and-claim-validation (0.62); four-ai-systems-one-cluster#action-plans-approvals-and-at-most-once-execution (0.60); four-ai-systems-one-cluster#the-opt-in-crewai-flow (0.60) |
| x08 | concept | 2 |  | 0.602 | roboshop-ai-shopping-agent#actions-with-side-effects (0.60); four-ai-systems-one-cluster#the-evidence-ledger-and-claim-validation (0.60); devops-interview-preparation-guide#scenario-an-agent-closed-40-tickets-after-reading-one (0.59) |
| x09 | concept | — |  | 0.642 | four-ai-systems-one-cluster#the-evidence-ledger-and-claim-validation (0.64); rag-evaluation-ask-the-blog-jithendar-com#what-ask-the-blog-does-with-a-question (0.64); rag-evaluation-ask-the-blog-jithendar-com#reading-the-numbers-honestly (0.63) |
| x10 | troubleshooting | 2 | ✓ | 0.717 | four-ai-systems-one-cluster#the-investigation-loop (0.72); pytorch-rag-reranking-moks-sre-agent#moks-integration-and-fallback (0.69); pytorch-rag-reranking-moks-sre-agent#security-and-operational-boundaries (0.69) |
| x11 | how-to | 1 | ✓ | 0.742 | mermaid-diagrams-on-jithendar-com#why-diagrams-matter-for-a-technical-blog (0.74); mermaid-diagrams-on-jithendar-com#why-diagrams-matter-for-a-technical-blog (0.71); mermaid-diagrams-on-jithendar-com#conclusion (0.69) |
| x12 | concept | 1 | ✓ | 0.729 | mermaid-diagrams-on-jithendar-com#why-the-svg-is-safe-to-insert (0.73); caching-isr-ssg-image-optimisation-nextjs# (0.67); caching-isr-ssg-image-optimisation-nextjs#what-image-optimisation-means (0.66) |
| x13 | concept | 1 | ✓ | 0.728 | python-vs-go-vs-typescript#mutable-default-arguments-in-python (0.73); python-tutorial-beginners-real-projects#the-mutable-default-argument-mistake (0.72); python-tutorial-beginners-real-projects#18-common-beginner-mistakes (0.70) |
| x14 | troubleshooting | 4 | ✓ | 0.692 | ssg-isr-nextjs-jithendar-com#1-a-cache-handler-with-a-generation-counter (0.69); ssg-isr-nextjs-jithendar-com#results (0.69); ssg-isr-nextjs-jithendar-com#what-id-tell-someone-doing-the-same (0.69) |
| x15 | how-to | — |  | 0.644 | roboshop-ai-gateway#the-assistant-says-it-is-busy (0.64); python-tutorial-beginners-real-projects#15-python-in-ai-and-automation (0.64); roboshop-ai-gateway#a-rate-limit-problem-worth-knowing-about (0.63) |
| x16 | how-to | — |  | 0.663 | roboshop-ai-microservices#what-the-boundaries-buy-and-the-conditions-behind-it (0.66); opa-gatekeeper-kubernetes-policies-jithendar-com#two-enforcement-paths-one-surprise (0.66); cloudflare-turnstile-nextjs-bot-protection#10-security-boundaries-and-gaps (0.65) |
| x17 | concept | 4 | ✓ | 0.759 | istio-service-mesh-minikube-features-setup-troubleshooting#2-architecture (0.76); kiali-minikube-service-mesh-observability#troubleshooting-what-we-hit (0.73); istio-service-mesh-minikube-features-setup-troubleshooting#common-issues-and-fixes (0.73) |
| x18 | concept | 1 | ✓ | 0.659 | roboshop-ai-architecture#can-a-shopper-buy-something-through-the-assistant (0.66); roboshop-ai-shopping-agent#actions-with-side-effects (0.64); roboshop-ai-microservices#how-checkout-and-order-events-work (0.62) |
| x19 | how-to | 2 | ✓ | 0.728 | ansible-explained-roboshop-repository#keeping-secrets (0.73); python-tutorial-beginners-real-projects#logging-and-keeping-secrets-out-of-logs (0.71); python-tutorial-beginners-real-projects#logging-and-keeping-secrets-out-of-logs (0.69) |
| x20 | concept | 1 | ✓ | 0.837 | roboshop-ai-mcp-server# (0.84); roboshop-ai-architecture#does-the-assistant-use-the-mcp-server (0.82); four-ai-systems-one-cluster#the-mcp-server (0.82) |
| x21 | concept | 1 |  | 0.784 | roboshop-ai-eks-system-design# (0.78); roboshop-ai-microservices-architecture#the-eks-design (0.78); roboshop-ai-eks-system-design#next (0.77) |
| x22 | concept | 1 |  | 0.729 | logging-tracing-observability-jithendar-com# (0.73); logging-tracing-observability-jithendar-com#1-what-the-site-needs-from-observability (0.70); moks-observability-logging-tracing-ai-agent-monitoring#a-refused-request-on-every-model-call (0.69) |
| x23 | concept | 3 | ✓ | 0.799 | roboshop-ai-eks-system-design#mesh-identity-per-workload-nothing-replayed (0.80); roboshop-ai-eks-system-design#benefits-and-trade-offs (0.80); istio-service-mesh-minikube-features-setup-troubleshooting#5-on-my-cluster-the-istio-gateway-is-the-only-edge (0.79) |
| x24 | troubleshooting | 1 | ✓ | 0.715 | cloudnativepg-postgres-cluster-minikube-terraform#52-the-first-install-has-to-be-staged (0.71); valkey-redis-sentinel-minikube-terraform#why-valkey-instead-of-redis (0.71); cloudnativepg-postgres-cluster-minikube-terraform#what-we-wanted (0.71) |
| x25 | concept | 4 |  | 0.782 | roboshop-ai-architecture#the-services-and-what-each-one-owns (0.78); roboshop-ai-architecture# (0.76); roboshop-ai-architecture#the-services-and-what-each-one-owns (0.76) |
| x26 | concept | 1 |  | 0.804 | python-vs-go-vs-typescript#where-each-language-appears-in-my-projects (0.80); python-vs-go-vs-typescript#where-each-language-appears-in-my-projects (0.75); roboshop-ai-microservices-architecture# (0.74) |
| x27 | exact-term | 1 | ✓ | 0.769 | valkey-redis-sentinel-minikube-terraform#wrongpass-invalid-username-password-pair (0.77); roboshop-ai-gateway#chat-fails-with-503-feature-unavailable (0.63); cloudflare-turnstile-nextjs-bot-protection#path-2-sign-in-and-sign-up-through-better-auth (0.63) |
| x28 | exact-term | 1 | ✓ | 0.770 | valkey-redis-sentinel-minikube-terraform#oom-command-not-allowed-when-used-memory--maxmemory (0.77); opa-gatekeeper-kubernetes-policies-jithendar-com#memory-limits-protect-the-sites-neighbours-and-the-site (0.65); how-i-built-jithendar-com#what-broke (0.64) |
| x29 | exact-term | 1 | ✓ | 0.746 | valkey-redis-sentinel-minikube-terraform#noperm--has-no-permissions-to-access-database (0.75); valkey-redis-sentinel-minikube-terraform#45-one-acl-user-and-database-range-per-application (0.62); ansible-explained-roboshop-repository#keeping-secrets (0.62) |
| x30 | exact-term | 1 | ✓ | 0.786 | cloudnativepg-postgres-cluster-minikube-terraform#a-replica-is-stuck-at-waiting-for-checkpoint-to-complete (0.79); 15-essential-kubernetes-tools-devops-engineers-2026-part-1#helm-upgrade-blocked-by-a-stuck-release (0.65); caching-isr-ssg-image-optimisation-nextjs#the-hard-part-invalidation-across-replicas (0.64) |
| x31 | exact-term | 1 | ✓ | 0.855 | cloudnativepg-postgres-cluster-minikube-terraform#psql-says-invalid-connection-option-sslnegotiation-or-hangs-at-the-gateway (0.85); cloudnativepg-postgres-cluster-minikube-terraform#psql-fails-with-server-certificate-does-not-match-host-name (0.69); cloudnativepg-postgres-cluster-minikube-terraform#postgres-answers-rbac-access-denied-or-psql-is-cut-off-immediately (0.69) |
| x32 | exact-term | 1 | ✓ | 0.856 | cloudnativepg-postgres-cluster-minikube-terraform#plan-fails-with-no-matches-for-kind-cluster-or-database (0.86); cloudnativepg-postgres-cluster-minikube-terraform#52-the-first-install-has-to-be-staged (0.84); cloudnativepg-postgres-cluster-minikube-terraform#provider-produced-inconsistent-result-after-apply-on-the-operator-release (0.79) |
| x33 | exact-term | 1 | ✓ | 0.781 | cloudnativepg-postgres-cluster-minikube-terraform#provider-produced-inconsistent-result-after-apply-on-the-operator-release (0.78); cloudnativepg-postgres-cluster-minikube-terraform#provider-produced-inconsistent-result-after-apply-on-the-operator-release (0.68); devops-interview-preparation-guide#scenario-the-rag-assistant-started-giving-wrong-answers-last-week (0.65) |
| x34 | exact-term | 1 | ✓ | 0.796 | shell-scripting-vs-python#reading-lines-safely-with-ifs-read--r (0.80); shell-scripting-vs-python#reading-files-line-by-line (0.75); python-tutorial-beginners-real-projects#where-this-appears-in-moks-2 (0.71) |
| x35 | exact-term | 1 | ✓ | 0.810 | learning-terraform-real-project-tools-repository#removing-from-terraform-without-deleting-the-removed-block (0.81); learning-terraform-real-project-tools-repository#lifecycle-settings (0.80); learning-terraform-real-project-tools-repository#refactoring-with-moved (0.74) |
| x36 | exact-term | 4 | ✓ | 0.686 | build-train-llm-jax-deeplearning-ai-course# (0.69); build-train-llm-jax-deeplearning-ai-course#a-mini-llm-training-pipeline-in-about-100-lines (0.68); build-train-llm-jax-deeplearning-ai-course#a-mini-llm-training-pipeline-in-about-100-lines (0.68) |
| x37 | exact-term | 1 | ✓ | 0.860 | valkey-redis-sentinel-minikube-terraform#terraform-cannot-pull-the-chart-error-getting-credentials (0.86); valkey-redis-sentinel-minikube-terraform#51-checks-before-anything-touches-the-cluster (0.75); valkey-redis-sentinel-minikube-terraform#why-the-cloudpirates-chart (0.74) |
| x38 | no-answer | — |  | 0.778 | 15-essential-kubernetes-tools-devops-engineers-2026-part-2#14-velero-backup-and-disaster-recovery (0.78); devops-interview-preparation-guide#lab-a-failure-zoo-on-minikube (0.76); 15-essential-kubernetes-tools-devops-engineers-2026-part-2#14-velero-backup-and-disaster-recovery (0.76) |
| x39 | no-answer | — |  | 0.721 | cloudnativepg-postgres-cluster-minikube-terraform#53-what-a-healthy-first-start-looks-like (0.72); cloudnativepg-postgres-cluster-minikube-terraform#2-architecture (0.71); cloudnativepg-postgres-cluster-minikube-terraform#46-reaching-it-from-outside (0.70) |
| x40 | no-answer | — |  | 0.728 | 15-essential-kubernetes-tools-devops-engineers-2026-part-2#8-karpenter-just-in-time-nodes (0.73); devops-interview-preparation-guide#lab-a-failure-zoo-on-minikube (0.71); build-train-llm-jax-deeplearning-ai-course#what-this-means-for-production-ai-engineering (0.71) |
