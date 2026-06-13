# AI Integration Plan

## Context

Jun 13, 2026 — Brainstorm on integrating AI-assisted review and diagnostics into the GitOps platform, inspired by:

- **[pr-agent](https://github.com/Codium-ai/pr-agent)** (CodiumAI) — Automated PR review with structured prompt engineering for code/config diffs.
- **[k8sgpt](https://github.com/k8sgpt-ai/k8sgpt)** (CNCF) — K8s runtime diagnostics with local model support (Ollama/Llama3).
- **ArgoCD community** — Discussions on preventing AI-generated "sync storms" (out-of-sync loops).

---

## Implementation Steps

### Step 1: LLM Gateway Abstraction (AC 16–17)

| Task | File/Location |
|------|---------------|
| `LLMGateway` abstract base class | `app/infrastructure/adapters/llm/base.py` |
| Ollama backend (local models) | `app/infrastructure/adapters/llm/ollama.py` |
| OpenAI/Azure backend | `app/infrastructure/adapters/llm/openai_compat.py` |
| `ai_config` field on Project model | `app/domain/projects/models.py`, `app/domain/db_models.py` |
| Expose `ai_config` in project CRUD APIs | `app/api/projects.py` |
| Register gateway in adapter registry | `app/infrastructure/adapters/registry.py` |
| Data privacy: block non-localhost when `no_external` | Gateway base class |

### Step 2: AI Review in Change Lifecycle (AC 18–20)

| Task | File/Location |
|------|---------------|
| Prompt constructor (diff + context + scope) | `app/domain/changes/ai_review.py` |
| Sensitive value masking (reuse `_SENSITIVE_KEY_PARTS`) | Prompt constructor |
| `ai_review()` method on ChangeService | `app/domain/changes/service.py` |
| `artifacts["ai_review"]` production | ChangeService |
| `ai_review_completed` audit event | ChangeService |
| `POST /changes/{id}/ai-review` endpoint | `app/api/changes.py` |
| AI review card in Change Workspace UI | `app/ui/change_workspace.py` |

### Step 3: Safety Guardrails (AC 21)

| Task | File/Location |
|------|---------------|
| Per-object suggestion rate limiter (5/hour default) | Gateway base class |
| Validate suggested change_types against supported set | AI review module |
| Out-of-sync loop detection + auto-pause | ChangeService |
| Architectural enforcement: AI never calls mutating methods | By design |

### Step 4: Execution Failure Diagnostics (AC 22)

| Task | File/Location |
|------|---------------|
| Collect k8s_apply error context (stderr, events) | `app/domain/changes/service.py` |
| Collect GitHub Actions failure logs (via API) | `app/infrastructure/github_client.py` |
| Truncate & pass to LLM Gateway | Diagnostics module |
| `artifacts["ai_diagnostics"]` storage | ChangeService |
| Diagnostics card in Change Workspace UI | `app/ui/change_workspace.py` |

---

## Priority & Sequencing

| Step | Priority | Est. Effort | Depends On |
|------|----------|-------------|------------|
| 1 — LLM Gateway | P0 | 2–3 days | — |
| 2 — AI Review | P0 | 3–4 days | Step 1 |
| 3 — Safety Guardrails | P0 | 1–2 days | Step 2 |
| 4 — Failure Diagnostics | P1 | 2–3 days | Step 1 |

> Steps 1→2→3 are sequential. Step 4 can start after Step 1 in parallel with 2–3.

---

## System Prompt — K8S Manifest Audit

The following is the base system prompt used by the AI Review step when auditing Kubernetes manifests. It is injected as the `system` role message before the user context (diff + object metadata).

```
你是一个资深的 DevSecOps 专家和 GitOps 平台审计员。
请对以下提交的 Kubernetes Manifest 进行严格的架构与安全审计。

你的审查标准包括：
1. 是否存在特权容器（Privileged Container）。
2. 是否配置了合理的 Resource Requests 和 Limits（防止单容器耗尽节点资源导致 OOM）。
3. 镜像 Tag 是否为 'latest'（GitOps 严禁使用 latest，必须使用不可变的标准 Tag）。
4. 是否缺少健康检查（Liveness/Readiness Probes）。

请以 Markdown 表格形式输出风险等级（High/Medium/Low）、问题描述及修改后的推荐 YAML。
```

> **Extensibility**: This prompt covers K8S manifests. Terraform HCL and AWS resource audits will use separate domain-specific system prompts following the same structure. All system prompts are stored in `app/domain/changes/prompts/` as plain-text templates with `{context}` placeholders.

---

## Key Design Decisions

1. **Read-only advisory** — AI never triggers state transitions or mutations.
2. **Local-first** — Default to Ollama (local models) for enterprise data privacy.
3. **Always mask** — Sensitive values are masked in prompts regardless of `data_policy`.
4. **Consistent patterns** — LLM adapter registry follows the same pattern as `InfrastructureAdapterRegistry`.
5. **Auditable** — Every AI call is logged with prompt hash, model, tokens, latency.
