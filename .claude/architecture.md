# Terraform GitOps Backend Architecture

> Consolidated product spec: `docs/Product-Specification.md`

## Dependency Graph
### Phase 1 — Core Platform (complete)
1. demo_data Terraform fixtures
2. Terraform inventory adapter
3. Adapter registry wiring
4. Inventory scanner Terraform merge
5. Template registry Terraform catalog
6. Skeleton registry Terraform scaffolds
7. Change service Terraform draft/patch/plan handling
8. Regression validation

### Phase 2 — AI-Assisted Review & Diagnostics
9. LLM Gateway abstraction + Ollama backend (AC 16–17)
10. AI Review integration in change lifecycle (AC 18–20)
11. Anti-sync-storm safeguards & rate limiting (AC 21)
12. Execution failure AI diagnostics (AC 22)

## Design Notes
- `TerraformFileScanner` remains the parser for `.tf` discovery; `TerraformResourceAdapter` converts scan metadata into `InventoryObject` records.
- `InventoryScanner.scan()` merges YAML-derived objects with Terraform-derived objects and reports combined summary counts.
- Template and skeleton registries stay backward compatible by retaining legacy ODP entries while adding Terraform-focused catalog entries.
- `ChangeService` uses lightweight HCL block matching to locate Terraform resources/modules/variables and generate unified diffs without mutating source files.
- Terraform validation/plan steps stay mock-safe in the current domain slice so the existing Draft → Patch → Plan → Approval flow remains usable.
- UI responsibility split: Resource Topology is read-only discovery for AWS/K8S/CloudWatch resource families; Resource Management is the canonical workspace for resource operations and changes.
- Navigation flow is linear and unnumbered: Discovery → Resource Management → Standards & Templates → Change Records → Delivery/Governance/Admin.
- Resource Management layout excludes embedded Change History and the workflow rail; it keeps the change creation/action surfaces while Change History owns list-oriented review.
- Resource Management inventory is intentionally scoped to AWS and K8S resource families using server-side `resource_type_prefix` filtering plus client-side category filtering; broader imported Terraform outputs/modules/variables stay in their dedicated pages.
- Cross-page context flow: Resource Topology stores selected object metadata (`object_id`, `resource_type`, `env`, `display_name`) and calls `capApplyTransfer_terraform_infra()` so Resource Management can filter inventory, preload current spec, and show a Back to Topology banner.
- Execution safety boundary is centralized in change execution and workflow dispatch: mutable actions are blocked unless target cluster is `kind-gitops-sandbox`; non-matching contexts/inputs return explicit blocked/failed results.
- GitHub Actions Terraform workflow is treated as controlled CICD: dispatch uses project-scoped org/repo/workflow config plus runtime inputs (including `terraform_root`), always performs `fmt`/`validate`/`plan`, uploads plan artifacts, and gates apply to sandbox + allowed cluster only. Canonical workflow file: `.github/workflows/terraform-plan-apply.yml`.
- Project configuration is the ownership boundary for execution metadata: `projects.git_config` and `projects.execution_config` store repo identity and execution routing (`workflow_id`, `cluster_name`) and can be updated through project APIs.
- Change Workspace surfaces execution context derived from project + change scope (target cluster, namespace, workflow) so operators can verify destination before triggering execution.

### AI Layer Design Notes
- LLM Gateway lives in `app/infrastructure/adapters/llm/` with a base class `LLMGateway` defining `async review(context) -> ReviewResult` and `async diagnose(error_context) -> DiagnosisResult`; concrete backends (`llm_openai.py`, `llm_ollama.py`) implement the transport.
- Project model gains `ai_config: Optional[dict]` alongside existing `git_config` / `execution_config`; defaults to `{"provider": "ollama", "model": "deepseek-r1", "endpoint": "http://localhost:11434", "data_policy": "no_external"}`.
- AI Review is architecturally a read-only artifact producer, similar to how `plan` produces the plan artifact. It slots between PlanReady and PendingApproval: `Plan → [AI Review] → Submit Approval`. The review artifact is advisory; operators see it but are not blocked by it.
- Prompt construction follows pr-agent patterns: structured diff context + resource metadata + safety scope, but adapted for HCL/YAML semantics since `patched_yaml` and `field_diff` are already structured (richer than raw git diff).
- Data privacy boundary: when `data_policy` is `no_external`, the gateway refuses to call any non-localhost endpoint. Prompt construction masks values matching `_SENSITIVE_KEY_PARTS` (password, secret, token, access_key, secret_key) regardless of data_policy.
- Anti-sync-storm: AI suggestions are inert data in `artifacts`; they cannot call `ChangeService` mutating methods. A per-object rate limiter (default 5 suggestions/hour) is enforced at the gateway layer. If the platform detects repeated out-of-sync for the same object within a window, AI suggestion generation is paused for that object.
- Execution failure diagnostics (inspired by k8sgpt): on `k8s_apply` failure or GitHub Actions workflow failure, the platform collects error output (stderr, K8s events, workflow logs) and passes a truncated summary to the LLM Gateway. The response is stored as `artifacts["ai_diagnostics"]` and surfaced in Change Workspace detail alongside the execution result.
- The LLM adapter registry follows the same pattern as `InfrastructureAdapterRegistry`: a singleton created at startup, selecting the concrete backend from project `ai_config.provider`.
- System prompts are domain-specific templates in `app/domain/changes/prompts/`; K8S manifest audit enforces privileged container detection, resource limits, immutable image tags (no `latest`), and liveness/readiness probes; Terraform HCL audit uses a separate prompt. Prompt selection is automatic based on `change_type` / `resource_type`.
