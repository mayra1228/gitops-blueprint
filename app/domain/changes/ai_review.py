"""AI Review service — integrates LLM Gateway into the change lifecycle.

Integration patterns:
- pr-agent: Jinja2 prompt templates, structured output, prompt privacy masking
- k8sgpt: "filter first, then AI" — pre-filter errors before sending to LLM

Workflow integration points:
1. AI Review  — after PlanReady, before submit_for_approval (read-only artifact)
2. AI Diagnostics — after execution failure (advisory only)
3. PR Review  — after PR creation, post AI comment (Phase 3: pr-agent lib)
"""

import hashlib
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, Optional

from app.infrastructure.adapters.llm import LLMGateway, ReviewResult, DiagnosticResult

PROMPTS_DIR = Path(__file__).parent / "prompts"

# k8sgpt pattern: sensitive key parts for masking
_SENSITIVE_KEY_PARTS = [
    "password", "secret", "token", "access_key", "secret_key",
    "private_key", "credential", "api_key", "auth", "connection_string",
]

# k8sgpt pattern: pre-filter keywords for error extraction
_ERROR_KEYWORDS = [
    "error", "Error", "ERROR", "failed", "Failed", "FAILED",
    "fatal", "Fatal", "FATAL", "denied", "refused", "timeout",
    "CrashLoopBackOff", "ImagePullBackOff", "OOMKilled",
    "CreateContainerConfigError", "ErrImagePull", "InvalidImageName",
    "forbidden", "unauthorized", "not found",
]


def mask_sensitive_values(data: Any) -> Any:
    """Mask sensitive values before prompt construction (always enforced)."""
    if isinstance(data, dict):
        return {
            k: "***REDACTED***" if any(part in k.lower() for part in _SENSITIVE_KEY_PARTS) else mask_sensitive_values(v)
            for k, v in data.items()
        }
    if isinstance(data, str):
        # Mask inline patterns like key=value or key: value
        for part in _SENSITIVE_KEY_PARTS:
            data = re.sub(
                rf'({part}\s*[=:]\s*)("[^"]*"|\'[^\']*\'|\S+)',
                rf'\1***REDACTED***',
                data,
                flags=re.IGNORECASE,
            )
        return data
    if isinstance(data, list):
        return [mask_sensitive_values(item) for item in data]
    return data


def filter_error_lines(log_text: str, max_lines: int = 50) -> str:
    """k8sgpt pattern: extract only error-relevant lines, not full log."""
    if not log_text:
        return ""
    lines = log_text.split("\n")
    filtered = []
    for i, line in enumerate(lines):
        if any(kw in line for kw in _ERROR_KEYWORDS):
            # Include 2 lines of context before and after
            start = max(0, i - 2)
            end = min(len(lines), i + 3)
            for ctx_line in lines[start:end]:
                if ctx_line not in filtered:
                    filtered.append(ctx_line)
    return "\n".join(filtered[:max_lines]) if filtered else "\n".join(lines[-20:])


def select_prompt_template(change_type: str, resource_type: str = "") -> str:
    """Select domain-specific prompt template based on change/resource type."""
    if resource_type.startswith("k8s_") or change_type in ("k8s_resource_update",):
        template_file = "k8s_manifest_audit.txt"
    elif change_type.startswith("terraform_") or resource_type.startswith("aws_") or resource_type.startswith("alicloud_"):
        template_file = "terraform_hcl_audit.txt"
    else:
        template_file = "k8s_manifest_audit.txt"  # default

    path = PROMPTS_DIR / template_file
    if path.exists():
        return path.read_text(encoding="utf-8")
    return "Review the following infrastructure change and identify security risks.\n\n{{ change_diff }}"


def render_prompt(template: str, context: Dict[str, Any]) -> str:
    """Simple Jinja2-style {{ var }} rendering."""
    rendered = template
    for key, value in context.items():
        rendered = rendered.replace("{{ " + key + " }}", str(value))
    return rendered


def build_review_prompt(change: Dict[str, Any]) -> str:
    """Build a complete review prompt from change data (with masking)."""
    change_type = change.get("change_type", "")
    object_id = change.get("object_id", "")
    resource_type = object_id.split("/")[0] if "/" in object_id else object_id

    # Mask sensitive data before prompt construction
    artifacts = mask_sensitive_values(change.get("artifacts", {}))
    diff = artifacts.get("field_diff_text", "") or artifacts.get("yaml_diff", "") or ""
    plan_summary = ""
    plan = artifacts.get("plan", {})
    if isinstance(plan, dict):
        plan_summary = plan.get("stdout", "")[:1000]

    template = select_prompt_template(change_type, resource_type)

    return render_prompt(template, {
        "change_diff": diff[:3000],  # Token budget: max 3000 chars of diff
        "plan_summary": plan_summary,
        "change_type": change_type,
        "object_id": object_id,
        "env": change.get("env", "unknown"),
    })


def build_diagnostics_prompt(change: Dict[str, Any], error_log: str) -> str:
    """Build a diagnostics prompt from execution failure (with pre-filtering)."""
    # k8sgpt pattern: filter first, then AI
    filtered_error = filter_error_lines(mask_sensitive_values(error_log))

    template_path = PROMPTS_DIR / "execution_failure_diagnosis.txt"
    template = template_path.read_text(encoding="utf-8") if template_path.exists() else (
        "Analyze the following error and provide root cause and remediation.\n\n{{ filtered_error }}"
    )

    scope = change.get("scope", {})
    return render_prompt(template, {
        "filtered_error": filtered_error,
        "execution_mode": change.get("artifacts", {}).get("execution", {}).get("mode", "unknown"),
        "object_id": change.get("object_id", ""),
        "cluster_name": scope.get("cluster_name", "unknown"),
        "env": change.get("env", "unknown"),
    })


async def run_ai_review(gateway: LLMGateway, change: Dict[str, Any]) -> Dict[str, Any]:
    """Execute AI Review — called after PlanReady, produces read-only artifact.

    Integration point: ChangeService.submit_for_approval() or dedicated API endpoint.
    Returns artifact dict ready to store in change['artifacts']['ai_review'].
    """
    prompt = build_review_prompt(change)
    context = {"change_type": change.get("change_type"), "object_id": change.get("object_id")}

    try:
        result = await gateway.review(prompt, context)
        return {
            "type": "ai_review",
            "status": "completed",
            **asdict(result),
        }
    except Exception as e:
        return {
            "type": "ai_review",
            "status": "failed",
            "error": str(e),
            "risk_level": "unknown",
            "summary": f"AI Review failed: {e}",
            "findings": [],
        }


async def run_ai_diagnostics(gateway: LLMGateway, change: Dict[str, Any], error_log: str) -> Dict[str, Any]:
    """Execute AI Diagnostics — called after execution failure.

    Integration point: ChangeService._execute_k8s_apply() or _execute_github_actions() on failure.
    Returns artifact dict ready to store in change['artifacts']['ai_diagnostics'].
    """
    prompt = build_diagnostics_prompt(change, error_log)
    context = {"execution_mode": change.get("artifacts", {}).get("execution", {}).get("mode")}

    try:
        result = await gateway.diagnose(prompt, context)
        return {
            "type": "ai_diagnostics",
            "status": "completed",
            **asdict(result),
        }
    except Exception as e:
        return {
            "type": "ai_diagnostics",
            "status": "failed",
            "error": str(e),
            "root_cause": f"AI Diagnostics failed: {e}",
            "remediation": "",
            "confidence": "low",
        }
