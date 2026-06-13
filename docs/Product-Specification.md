# GitOps Blueprint Platform — Product Specification (Consolidated)

> **Version**: 1.0 — Jun 13, 2026
> **Sources**: Obsidian wiki (blueprint-platform, devops-platform), Gemini brainstorm, `.claude/` specs, ROADMAP.md

---

## 1. Product Positioning

**AI-Native Terraform GitOps Control Plane** — The platform reads existing Terraform/K8S projects, visualizes their desired-state architecture, generates standard IaC skeletons for projects without Terraform, manages governed change lifecycles (Draft → Plan → Approve → Apply), and integrates AI-assisted review and diagnostics through a pluggable LLM Gateway.

### One-sentence Positioning

> Read existing Terraform projects, visualize their desired-state architecture, generate standard Terraform skeletons, execute governed changes through platform-native CI/CD (terraform/kubectl), and provide AI-assisted review — all within a unified control plane with enterprise safety boundaries.

### Core Design: Platform as CI/CD Engine

```
┌─ GitOps Platform (Control Plane + CI/CD Engine) ──────────┐
│                                                            │
│  ① Git Clone / Branch / Commit / Push                      │
│  ② Resource Discovery · Topology Visualization             │
│  ③ Draft → Validation → Plan → Approve → Apply            │
│     ├─ terraform fmt / init / validate                     │
│     ├─ terraform plan (upload artifact)                    │
│     └─ terraform apply (kind-gitops-sandbox only)          │
│  ④ kubectl apply (K8S direct execution)                    │
│  ⑤ AI Agent: Review · Impact Analysis · Approval Advice   │
│  ⑥ Audit · SRE Evidence · Compliance                      │
│                                                            │
│  Safety Boundary: only kind-gitops-sandbox is mutable      │
└────────────────────────────────────────────────────────────┘
```

### Two Onboarding Modes

| Mode | Description |
|------|-------------|
| **A: Existing GitOps Project** | Register repo → scan Terraform → platform takes over CI/CD |
| **B: New Project via Skeleton** | Select template → fill params → generate standard .tf → push to repo → enters Mode A |

### Product Principles

1. **Terraform repo is source of truth** — desired state comes from Git.
2. **Platform is a control plane** — visualize, validate, approve, execute through adapters.
3. **Adapters are the integration boundary** — CI/CD, infra execution, approvals, policy are adapter-backed.
4. **All changes are proposal-first** — no direct main edits, no unapproved execution.
5. **Skeleton and existing Terraform share the same lifecycle**.
6. **AI is read-only advisory** — never triggers state transitions or mutations.
7. **Local-first AI** — default to Ollama/local models for enterprise data privacy.

---

## 2. Target Users & Core Problems

| User | Current Problem | Platform Value |
|------|----------------|----------------|
| **SRE / Oncall** | Alerts scattered, SLA risk unclear, debugging requires multi-tool jumping | Unified governance, SLA dashboard, incident correlation, AI diagnostics |
| **Platform Engineer** | IaC configs spread across repos, no product-level visibility | Resource catalog, governed change workflow, adapter orchestration |
| **App Owner** | Unclear which alerts/SLA/certs/middleware apply to their service | Service profile + risk list + self-service change entry |
| **Reviewer / Approver** | Hard to judge change impact without context | AI review, impact analysis, historical evidence, audit trail |
| **Manager** | No quick view of reliability, cost, and risk trends | KPI dashboards, risk radar, governance reports |

---

## 3. Module Architecture (Information Architecture)

```
GitOps Blueprint Platform
├── Dashboard / Command Center
├── Discovery (Resource Topology)
├── Resource Management (Change Workspace)
├── Standards & Templates (Skeleton + Template Catalog)
├── Change History
├── Delivery / Adapters
├── Governance / SRE Evidence
└── Admin / Settings
```

### Module Responsibilities

| Module | Purpose | Key Capabilities |
|--------|---------|-------------------|
| **Dashboard** | Status + next action | Project summary, IaC coverage, open changes, risk highlights, workflow shortcuts |
| **Discovery** | Read-only resource topology | AWS/K8S resource families, env tree, type distribution, drill-down to object detail |
| **Resource Management** | Canonical operations workspace | Inventory filter, create draft, validate/plan/approve/execute, object detail, audit |
| **Standards & Templates** | Bootstrap + standardization | Skeleton catalog, template catalog, parameter form, file preview, create proposal |
| **Change History** | List-oriented change review | All changes across types, status filter, scaffold history |
| **Delivery / Adapters** | Integration boundaries | Git/CI-CD/Infra/Approval/Policy/Editor adapter registry, policy gates |
| **Governance** | SRE evidence & compliance | Inventory explorer, service profiles, alert governance, ownership gaps |
| **Admin** | Configuration & diagnostics | API surface, safety boundary display, feature flags, project config (ai_config, git_config, execution_config) |

### Navigation Design

- **Directory-style sidebar** with module → sub-function hierarchy
- Each module is its own page — no single-scroll dashboard
- Hash routing: `#/discovery`, `#/changes/draft`, `#/delivery/adapters`
- Module landing cards explain purpose, current capabilities, and safety boundary

---

## 4. Acceptance Criteria

### Core Platform (AC 1–15)

1. Inventory scanning reads existing YAML inventory and `.tf` files under `infra/`.
2. Terraform scanner output adapted into `InventoryObject` records for resources, modules, variables, outputs.
3. Adapter registry exposes Terraform resource definitions without removing legacy adapters.
4. Template catalog includes Terraform-first AWS templates with `aws_ec2` mapped to `aws_instance`.
5. Skeleton registry includes Terraform service/module scaffolds and keeps legacy skeletons usable.
6. Change service accepts `terraform_resource_update`, `terraform_variable_update`, `terraform_module_update` and generates HCL diffs.
7. Demo Terraform data exists for dev/prod AWS paths.
8. Existing automated tests continue to pass.
9. Resource Topology is read-only discovery for AWS/K8S/CloudWatch resources.
10. Resource Management is the canonical workspace: inventory + create draft + action/result + object detail/audit.
11. Resource Management inventory scoped to AWS (`aws_*`, `cloudwatch_*`) and K8S (`k8s_*`) families.
12. Cluster safety boundary: only `kind-gitops-sandbox` for mutable execution.
13. Terraform CICD workflow: `fmt` → `validate` → `plan` → artifact upload → apply (sandbox only).
14. Project-level `git_config` and `execution_config` queryable/updatable via APIs.
15. Change Workspace exposes execution target context before execute.

### AI-Assisted Review & Diagnostics (AC 16–22)

16. **LLM Gateway**: unified adapter interface supporting OpenAI, Azure OpenAI, and Ollama (local); backend selected via project `ai_config`.
17. **Project AI Config**: `provider`, `model`, `endpoint`, `data_policy` (allow_external / no_external) queryable and updatable via APIs.
18. **AI Review**: read-only audit step after Plan, before Submit Approval; produces `ai_review` artifact with risk level, summary, per-field findings; NO state transitions.
19. **Prompt Privacy**: sensitive values masked via `_SENSITIVE_KEY_PARTS` before prompt construction.
20. **AI Audit Trail**: prompt hash, model identifier, token count, latency, response hash in artifacts and as `ai_review_completed` audit event.
21. **Anti-Sync-Storm**: suggestions within supported `change_types` only; no auto state transitions; per-object rate limit (5/hour default); out-of-sync loop detection.
22. **Execution Failure Diagnostics**: LLM Gateway invoked with error logs → human-readable root-cause + remediation in `artifacts["ai_diagnostics"]`; advisory only.

---

## 5. Supported Resources (Phase 1)

| Provider | Resource Types |
|----------|---------------|
| **AWS** (32) | `aws_instance`, `aws_db_instance`, `aws_vpc`, `aws_subnet`, `aws_security_group`, `aws_s3_bucket`, `aws_iam_role`, `aws_iam_policy`, `aws_eks_cluster`, `aws_eks_node_group`, `aws_elasticache_cluster`, `aws_lb`, `aws_lb_listener`, `aws_lb_target_group`, `aws_route53_record`, `aws_sqs_queue`, `aws_sns_topic`, `aws_lambda_function`, `aws_rds_cluster`, `aws_ecr_repository`, `aws_ecs_cluster`, `aws_ecs_service`, `aws_autoscaling_group`, `aws_launch_template`, `aws_internet_gateway`, `aws_route_table`, `aws_nat_gateway`, `aws_eip`, `aws_kms_key`, `aws_secretsmanager_secret`, `cloudwatch_metric_alarm` |
| **Aliyun** (9) | `alicloud_instance`, `alicloud_db_instance`, `alicloud_vpc`, `alicloud_vswitch`, `alicloud_security_group`, `alicloud_slb`, `alicloud_oss_bucket`, `alicloud_kvstore_instance`, `alicloud_cs_kubernetes` |
| **K8S** (2) | `k8s_deployment` (HPA/CPU/Memory), `k8s_ingress` (Nginx/HTTPRoute) |

---

## 6. Change Lifecycle

```
Draft → PatchGenerated → ValidationPassed → PlanReady
                                              ↓
                                         [AI Review]  ← NEW (read-only artifact)
                                              ↓
                                        PendingApproval
                                       ↙              ↘
                                  Approved          Rejected
                                     ↓
                                ExecutionReady
                                     ↓
                              InventoryRefreshed
```

### CI/CD Execution Engines

| Engine | Description | Status |
|--------|-------------|:------:|
| **Platform K8S** | Direct `kubectl validate/apply` to kind cluster | ✅ |
| **Platform Terraform** | Clone → `fmt/init/validate/plan/apply` | ⚡ |
| **GitHub Actions** | `workflow_dispatch` to `.github/workflows/terraform-plan-apply.yml` | ✅ |
| **Jenkins** | Trigger Jenkins Pipeline | ⚡ |

### Execution Safety Boundary (Dual Guard)

1. **Platform backend**: adapter blocks non-`kind-gitops-sandbox` / non-sandbox apply
2. **GitHub Actions workflow**: steps re-validate cluster boundary and apply conditions

---

## 7. AI Integration Architecture

### LLM Gateway

```
app/infrastructure/adapters/llm/
├── base.py              # LLMGateway abstract: review(), diagnose()
├── ollama.py            # Local models (DeepSeek-R1, Llama3)
└── openai_compat.py     # OpenAI / Azure OpenAI
```

Default project `ai_config`:
```json
{
  "provider": "ollama",
  "model": "deepseek-r1",
  "endpoint": "http://localhost:11434",
  "data_policy": "no_external"
}
```

### System Prompts

Domain-specific templates stored in `app/domain/changes/prompts/`:

**K8S Manifest Audit** (`k8s_manifest_audit.txt`):
```
你是一个资深的 DevSecOps 专家和 GitOps 平台审计员。
请对以下提交的 Kubernetes Manifest 进行严格的架构与安全审计。

你的审查标准包括：
1. 是否存在特权容器（Privileged Container）。
2. 是否配置了合理的 Resource Requests 和 Limits。
3. 镜像 Tag 是否为 'latest'（GitOps 严禁使用 latest）。
4. 是否缺少健康检查（Liveness/Readiness Probes）。

请以 Markdown 表格形式输出风险等级（High/Medium/Low）、问题描述及修改后的推荐 YAML。
```

Prompt selection: automatic based on `change_type` / `resource_type`.

### AI Agent Capabilities (Roadmap)

| Capability | Description | Phase |
|------------|-------------|:-----:|
| **AI Review (read-only)** | Risk-level table + per-field findings after Plan | Phase 2 ✅ |
| **Execution Failure Diagnostics** | Root-cause + remediation from error logs | Phase 2 |
| **Natural Language Change** | "Upgrade dev RDS to db.r5.xlarge" → prefilled draft | Phase 3 |
| **Impact Analysis** | Upstream/downstream resource dependency analysis | Phase 3 |
| **Plan Result Interpretation** | `terraform plan` → human-readable summary | Phase 3 |
| **Approval Advice** | Risk-based approval recommendation from history | Phase 3 |
| **Auto Rollback Plan** | Generate rollback HCL for every change | Phase 3 |
| **Conflict Detection** | Parallel draft state conflict detection | Phase 3 |
| **Autonomous Change Loop** | Alert → AI draft → Plan → auto-approve (low risk) → Apply | Phase 3 |
| **Cross-Resource Orchestration** | "Friday 2AM downscale all dev RDS" → multi-change | Phase 3 |
| **Knowledge Graph Q&A** | "Which EC2 depends on this SG?" → topology answer | Phase 3 |
| **Cost Optimization** | Scan utilization → downsizing / RI suggestions | Phase 3 |
| **Compliance Self-Check** | Pre-change policy check against compliance library | Phase 3 |

### Anti-Sync-Storm Safeguards

- AI output is inert data in `artifacts` — cannot call mutating ChangeService methods
- Per-object rate limiter (5/hour default) at gateway layer
- Out-of-sync loop detection pauses AI suggestions for affected object
- Suggestions limited to platform-supported `change_types`

### Data Privacy Boundary

- `data_policy: no_external` → gateway blocks non-localhost endpoints
- Prompt construction **always** masks `_SENSITIVE_KEY_PARTS` (password, secret, token, access_key, secret_key)
- Full audit trail: prompt hash, model, tokens, latency, response hash

---

## 8. Adapter Registry

| Adapter Category | Responsibility | Examples |
|------------------|----------------|----------|
| **GitAdapter** | Branch, commit, PR, source links | GitHub, GitLab, Bitbucket |
| **CICDAdapter** | Trigger/observe CI pipelines | Jenkins, GitHub Actions, GitLab CI |
| **InfraAdapter** | Terraform plan/apply backend | Platform-native, Terraform Cloud, Atlantis |
| **ApprovalAdapter** | Approval workflow | ServiceNow, Jira, GitHub Review |
| **PolicyAdapter** | Policy/guardrail evaluation | OPA, Sentinel, internal policy |
| **EditorAdapter** | Open-in-editor deep links | VS Code, github.dev, Codespaces |
| **LLMAdapter** | AI review/diagnostics | Ollama, OpenAI, Azure OpenAI |
| **ExecutionAdapter** | Execution safety enforcement | GitHubActionsExecution, K8SExecution |

---

## 9. K8S Management via Terraform — Scenarios

### Scenario A: New App Onboarding
```
Skeleton: k8s_namespace → k8s_workload → k8s_ingress → k8s_monitoring
Output: infra/k8s/{cluster}/{env}/{service}/ with main.tf + variables.tf + tfvars
```

### Scenario B: Elastic Scaling (HPA Tuning)
```
Change Request: maxReplicas 10→20, targetCPU 70→60%
Flow: Inventory → Change Draft → Policy (>50% warning) → Approval → Apply
```

### Scenario C: Cluster Upgrade
```
Change: kubernetes_version 1.28→1.29, max_surge 33%
Gate: 2-person approval for cluster changes
```

### Scenario D: Multi-Cluster Multi-Env
```
infra/k8s/
├── aks-dev-01/dev/      → auto-apply on merge
├── aks-staging-01/staging/ → auto-apply on merge
├── aks-prod-01/prod/    → manual gate + apply
└── aks-prod-02/prod/    → manual gate + apply (DR)
```

---

## 10. Roadmap

### Phase 1 — Core Platform (Complete ✅)

- Terraform inventory scanner + adapter registry
- Template/skeleton catalog with HCL rendering
- Change lifecycle: Draft → Patch → Validate → Plan → Approve → Execute
- GitHub Actions CI/CD integration
- K8S direct execution (kubectl apply)
- Platform-native safety boundaries
- Audit trail + delivery trace

### Phase 2 — AI + Execution Engine (In Progress ⚡)

| Item | Priority | Status |
|------|----------|:------:|
| LLM Gateway abstraction (Ollama + OpenAI) | P0 | 🔲 |
| AI Review in change lifecycle | P0 | 🔲 |
| Anti-sync-storm safeguards | P0 | 🔲 |
| Execution failure AI diagnostics | P1 | 🔲 |
| Platform-native Terraform execution | P0 | ⚡ |
| Git clone auth fix (private repos) | P0 | ⚡ |
| UX: Module landing cards | P1 | 🔲 |
| E2E test coverage | P1 | 🔲 |

### Phase 3 — Enterprise Features (Planned)

- **Certificate Management**: ACME auto-renewal, ACM/Alibaba import, cert-manager, Ingress TLS
- **More Providers**: GCP (`google_compute_instance`, GKE), Azure (`azurerm_virtual_machine`, AKS)
- **Pluggable Execution Backends**: GitLab CI, Azure DevOps, Argo Workflows, Terraform Cloud, Atlantis
- **Approval Integrations**: ServiceNow, Jira
- **Drift Detection**: `terraform state` vs actual, AI root-cause analysis
- **Resource Topology Graph**: VPC → Subnet → EC2/RDS dependency DAG
- **Variable Panorama**: tfvars / workspace / CI / secret source tracking
- **Multi-Tenant RBAC**: Admin / Operator / Viewer role isolation
- **Policy as Code**: OPA / Sentinel in Plan stage
- **Cross-Project Command Center**: multi-project stats, environment health
- **Advanced AI**: autonomous change loops, cross-resource orchestration, cost optimization, compliance self-check

---

## 11. UX Design Principles

1. **Module first explains, then shows data** — landing card with purpose, users, capabilities, safety
2. **One screen serves one primary task** — no all-in-one scroll dashboard
3. **Placeholders clearly marked as future** — "planned capability" cards, not empty states
4. **Lower cognitive load** — sidebar highlights current module, progressive disclosure
5. **Safety boundary embedded at every action point** — not just in Admin
6. **Consistent action labels** — Inspect (read-only), Preview (artifact), Create Draft (local), Submit Approval (status change); avoid Apply/Deploy/Execute unless explicitly gated

---

## 12. Technology Stack

```
Browser (Vanilla JS SPA)
    ↓ fetch()
FastAPI (Python async)
    ↓ SQLAlchemy async
PostgreSQL 14
    ↓ (Execute phase)
GitHub REST API (PR creation)
Terraform CLI (plan/apply)
kubectl (K8S execution)
Ollama / OpenAI (AI review)
```

---

## 13. Project Structure

```
gitops-blueprint/
├── app/
│   ├── main.py                          # FastAPI entry point
│   ├── config.py                        # Settings (env-based)
│   ├── api/                             # Route handlers
│   ├── domain/
│   │   ├── changes/                     # Change state machine + AI review
│   │   │   └── prompts/                 # System prompt templates
│   │   ├── inventory/                   # YAML + Terraform scanner
│   │   ├── adapters/                    # Resource type adapters
│   │   ├── templates/                   # Template registry
│   │   ├── skeletons/                   # Skeleton registry + renderer
│   │   ├── capabilities/                # Capability registry
│   │   └── projects/                    # Multi-project support
│   ├── infrastructure/
│   │   ├── database.py                  # SQLAlchemy async engine
│   │   ├── github_client.py             # GitHub REST client
│   │   ├── git_repo_service.py          # Git CLI operations
│   │   ├── k8s_client.py                # kubectl wrapper
│   │   └── adapters/
│   │       ├── llm/                     # LLM Gateway (Ollama, OpenAI)
│   │       ├── github_actions_execution.py
│   │       ├── k8s_execution.py
│   │       └── registry.py
│   └── ui/                              # Server-rendered SPA
├── demo_data/                           # Sample YAML + .tf fixtures
├── docs/                                # Project documentation
├── scripts/                             # seed.py, demo.sh, setup_kind.sh
├── tests/                               # Integration + unit tests
├── .github/workflows/                   # terraform-plan-apply.yml
├── docker-compose.yml
└── Dockerfile
```
