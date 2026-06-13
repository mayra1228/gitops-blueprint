# Change Log

## Jun 13

### AI Integration Brainstorm

Collected inspiration from Gemini on integrating AI capabilities into the GitOps platform.

**Reference projects:**
- **pr-agent** (CodiumAI) — Automated PR review; valuable for prompt engineering patterns around IaC diffs.
- **k8sgpt** (CNCF) — K8s runtime diagnostics with local model support (Ollama/Llama3).
- **ArgoCD community** — Discussions on preventing AI-generated "sync storms."

**Key decisions:**
- Add a pluggable **Local LLM Gateway** supporting Ollama (local) and OpenAI/Azure (cloud).
- Default to local models for enterprise data privacy.
- AI Review as a **read-only** audit step after Plan, before Approval.
- All AI interactions fully auditable (prompt hash, model, tokens, latency).
- Anti-sync-storm safeguards: rate limiting, no auto-mutations, out-of-sync detection.

→ See [AI Integration Plan](AI-Integration-Plan.md) and [PRD](PRD.md) AC 16–22 for full spec.

---

## Jun 09

### GitHub Actions CI/CD Integration

- K8S environment: local kind cluster (`kind-gitops-sandbox`)
- Git provider: GitHub Actions
- Implemented Terraform plan/apply workflow via `workflow_dispatch`
- Safety boundary: only `kind-gitops-sandbox` cluster is mutable
- Runbook: see [Runbook](Runbook-GitHub-Actions-Kind.md)

---

## Jun 08

### Bug Fixes & UI Refinements

- Fixed project registration clone errors (GITHUB_TOKEN / terminal prompts)
- Resource Topology scoped to AWS/K8S only (removed terraform_output noise)
- Infrastructure Resources renamed to Change Workspace
- Navigation: removed numbering, adjusted fonts, Discovery → Resource Management flow
- Resource Management: removed embedded Change History, streamlined layout
- Fixed `unsupported Terraform object_id` and `source YAML not found` errors
