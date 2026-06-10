# Terraform GitOps Backend Architecture

## Dependency Graph
1. demo_data Terraform fixtures
2. Terraform inventory adapter
3. Adapter registry wiring
4. Inventory scanner Terraform merge
5. Template registry Terraform catalog
6. Skeleton registry Terraform scaffolds
7. Change service Terraform draft/patch/plan handling
8. Regression validation

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
