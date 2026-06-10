# Terraform GitOps Backend Requirements

## Scope
Implement Terraform-aware backend domain behavior for inventory, templates, skeletons, and change previews while preserving existing ODP/K8S workflows.

## Acceptance Criteria
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
