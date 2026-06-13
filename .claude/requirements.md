# Terraform GitOps Backend Requirements

## Scope
Implement Terraform-aware backend domain behavior for inventory, templates, skeletons, and change previews while preserving existing ODP/K8S workflows. Integrate AI-assisted review and diagnostics through a pluggable LLM Gateway that supports both cloud and local/private model backends.

## Acceptance Criteria

### Core Platform (AC 1–15)
1. Inventory scanning reads existing YAML inventory and `.tf` files under `infra/`.
2. Terraform scanner output is adapted into `InventoryObject` records for resources, modules, variables, and outputs.
3. Adapter registry exposes Terraform resource definitions without removing legacy adapters.
4. Template catalog includes Terraform-first AWS templates with `aws_ec2` mapped to `aws_instance`.
5. Skeleton registry includes Terraform service/module scaffolds and keeps legacy skeletons usable.
6. Change service accepts `terraform_resource_update`, `terraform_variable_update`, and `terraform_module_update` and generates textual HCL diffs for draft preview.
7. Demo Terraform data exists for dev/prod AWS paths so inventory scan and patch preview have real inputs.
8. Existing automated tests continue to pass.
9. Resource Topology is a read-only discovery view for AWS/K8S/CloudWatch resources: users inspect resource families, drill down to resource types, filter by env/type, and open object details before choosing to manage a resource.
10. Resource Management is the canonical resource operations workspace: it accepts topology context, filters the inventory by env/type, preloads the selected object, exposes currently supported change coverage, and focuses the page on Inventory + Create Draft + Action/Result + Object Detail/Audit; full change lists live in Change History.
11. Resource Management Inventory only includes AWS and K8S resource families; AWS includes `aws_*` and AWS-owned service prefixes such as `cloudwatch_*`, while K8S includes `k8s_*`.
12. Any executable change operation must enforce a cluster safety boundary: only `kind-gitops-sandbox` can be targeted for mutable execution paths (`k8s_apply` and GitHub Actions apply dispatch).
13. Terraform CICD workflow must run `fmt`, `validate`, and `plan` before apply, persist plan artifacts, and permit apply only for sandbox environment on `kind-gitops-sandbox`.
14. Project-level asset configuration (`git_config`, `execution_config`) must be queryable and updatable via project APIs, and support at least `workflow_id` and `cluster_name` for execution routing.
15. Change Workspace detail must expose execution target context (cluster, namespace, workflow) before execute is triggered.

### AI-Assisted Review & Diagnostics (AC 16–22)
16. LLM Gateway must provide a unified adapter interface (`LLMGateway`) supporting at least OpenAI-compatible API, Azure OpenAI, and Ollama (local) backends; the active backend is selected via project-level `ai_config`.
17. Project-level `ai_config` must be queryable and updatable via project APIs, supporting at least `provider` (openai / azure / ollama), `model`, `endpoint`, and `data_policy` (allow_external / no_external) fields.
18. AI Review is a read-only audit step inserted after Plan and before Submit Approval in the change lifecycle; it produces an `ai_review` artifact containing risk level (low/medium/high/critical), review summary, and per-field findings; it must NOT trigger any state transition or mutation.
19. AI Review input context must include: patched diff (or field_diff), object metadata (object_id, resource_type, env), cluster/namespace scope, and current spec; sensitive values identified by `_SENSITIVE_KEY_PARTS` must be masked before prompt construction.
20. All AI interactions must be fully auditable: each call records prompt hash, model identifier, token count, latency, and response hash in `artifacts["ai_review"]` and as an `ai_review_completed` audit event.
21. Anti-sync-storm safeguards: AI may only produce suggestions within platform-supported `change_types`; AI output never triggers automatic state transitions; per-object AI suggestion rate is limited (configurable, default 5/hour); out-of-sync loop detection halts further AI suggestions for the affected object.
22. Execution failure diagnostics: when a change execution fails (k8s_apply error, GitHub Actions workflow failure), the platform may invoke the LLM Gateway with error logs/events to produce a human-readable root-cause summary and remediation suggestions stored in `artifacts["ai_diagnostics"]`; this is advisory only and does not alter change status.
