# Architecture

## Dependency Graph

### Phase 1 — Core Platform (complete)

| Step | Component |
|------|-----------|
| 1 | demo_data Terraform fixtures |
| 2 | Terraform inventory adapter |
| 3 | Adapter registry wiring |
| 4 | Inventory scanner Terraform merge |
| 5 | Template registry Terraform catalog |
| 6 | Skeleton registry Terraform scaffolds |
| 7 | Change service Terraform draft/patch/plan handling |
| 8 | Regression validation |

### Phase 2 — AI-Assisted Review & Diagnostics

| Step | Component | Acceptance Criteria |
|------|-----------|---------------------|
| 9 | LLM Gateway abstraction + Ollama backend | AC 16–17 |
| 10 | AI Review integration in change lifecycle | AC 18–20 |
| 11 | Anti-sync-storm safeguards & rate limiting | AC 21 |
| 12 | Execution failure AI diagnostics | AC 22 |

---

## Design Notes — Core Platform

- `TerraformFileScanner` remains the parser for `.tf` discovery; `TerraformResourceAdapter` converts scan metadata into `InventoryObject` records.
- `InventoryScanner.scan()` merges YAML-derived objects with Terraform-derived objects and reports combined summary counts.
- Template and skeleton registries stay backward compatible by retaining legacy ODP entries while adding Terraform-focused catalog entries.
- `ChangeService` uses lightweight HCL block matching to locate Terraform resources/modules/variables and generate unified diffs without mutating source files.
- Terraform validation/plan steps stay mock-safe in the current domain slice so the existing Draft → Patch → Plan → Approval flow remains usable.
- UI responsibility split: Resource Topology is read-only discovery for AWS/K8S/CloudWatch resource families; Resource Management is the canonical workspace for resource operations and changes.
- Navigation flow is linear and unnumbered: Discovery → Resource Management → Standards & Templates → Change Records → Delivery/Governance/Admin.
- Resource Management layout excludes embedded Change History and the workflow rail; it keeps the change creation/action surfaces while Change History owns list-oriented review.
- Resource Management inventory is intentionally scoped to AWS and K8S resource families using server-side `resource_type_prefix` filtering plus client-side category filtering.
- Cross-page context flow: Resource Topology stores selected object metadata and calls `capApplyTransfer_terraform_infra()` so Resource Management can filter inventory, preload current spec, and show a Back to Topology banner.
- Execution safety boundary is centralized in change execution and workflow dispatch: mutable actions are blocked unless target cluster is `kind-gitops-sandbox`.
- GitHub Actions Terraform workflow is treated as controlled CICD: dispatch uses project-scoped org/repo/workflow config plus runtime inputs, always performs `fmt`/`validate`/`plan`, uploads plan artifacts, and gates apply to sandbox + allowed cluster only.
- Project configuration is the ownership boundary for execution metadata: `projects.git_config` and `projects.execution_config` store repo identity and execution routing and can be updated through project APIs.
- Change Workspace surfaces execution context derived from project + change scope so operators can verify destination before triggering execution.

---

## Design Notes — AI Layer

### LLM Gateway

- Lives in `app/infrastructure/adapters/llm/` with a base class `LLMGateway` defining `async review(context) -> ReviewResult` and `async diagnose(error_context) -> DiagnosisResult`.
- Concrete backends: `llm_openai.py` (OpenAI/Azure), `llm_ollama.py` (local Ollama).
- Follows the same singleton pattern as `InfrastructureAdapterRegistry`: created at startup, backend selected from project `ai_config.provider`.

### Project AI Config

- Project model gains `ai_config: Optional[dict]` alongside existing `git_config` / `execution_config`.
- Default: `{"provider": "ollama", "model": "deepseek-r1", "endpoint": "http://localhost:11434", "data_policy": "no_external"}`.

### AI Review Integration

```
Change Lifecycle:
  Draft → Patch → Validate → Plan → [AI Review] → Submit Approval → Approve → Execute
                                         │
                                   Read-only artifact
                                   artifacts["ai_review"]
```

- Architecturally a read-only artifact producer, similar to how `plan` produces the plan artifact.
- Prompt construction follows pr-agent patterns: structured diff context + resource metadata + safety scope, adapted for HCL/YAML semantics since `patched_yaml` and `field_diff` are already structured.

### Data Privacy Boundary

- When `data_policy` is `no_external`, the gateway refuses to call any non-localhost endpoint.
- Prompt construction masks values matching `_SENSITIVE_KEY_PARTS` (password, secret, token, access_key, secret_key) **regardless** of data_policy setting.

### Anti-Sync-Storm Safeguards

- AI suggestions are inert data in `artifacts`; they cannot call `ChangeService` mutating methods.
- Per-object rate limiter (default 5 suggestions/hour) enforced at the gateway layer.
- If the platform detects repeated out-of-sync for the same object within a window, AI suggestion generation is paused for that object.

### Execution Failure Diagnostics

- Inspired by k8sgpt: on `k8s_apply` failure or GitHub Actions workflow failure, the platform collects error output (stderr, K8s events, workflow logs) and passes a truncated summary to the LLM Gateway.
- Response stored as `artifacts["ai_diagnostics"]` and surfaced in Change Workspace detail.

### System Prompt Strategy

- System prompts are domain-specific plain-text templates stored in `app/domain/changes/prompts/` (e.g. `k8s_manifest_audit.txt`, `terraform_hcl_audit.txt`).
- The K8S manifest audit prompt enforces: privileged container detection, resource requests/limits, immutable image tags (no `latest`), and liveness/readiness probes — output as risk-level table with recommended YAML fixes.
- Prompt selection is automatic based on `change_type` and `resource_type`: K8S resources use the manifest audit prompt; Terraform resources use the HCL audit prompt.
- All prompts use `{context}` placeholders filled at runtime with masked diff + object metadata.
