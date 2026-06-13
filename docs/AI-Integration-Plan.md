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

## Key Design Decisions

1. **Read-only advisory** — AI never triggers state transitions or mutations.
2. **Local-first** — Default to Ollama (local models) for enterprise data privacy.
3. **Always mask** — Sensitive values are masked in prompts regardless of `data_policy`.
4. **Consistent patterns** — LLM adapter registry follows the same pattern as `InfrastructureAdapterRegistry`.
5. **Auditable** — Every AI call is logged with prompt hash, model, tokens, latency.
