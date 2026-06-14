from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_project_id
from app.config import settings
from app.domain.changes.service import ChangeService, ValidationError
from app.infrastructure.database import get_db

router = APIRouter()


class CreateChangeRequest(BaseModel):
    change_type: str
    object_id: str
    proposed: dict
    reason: str = ""
    created_by: str = ""


class ApprovalRequest(BaseModel):
    approver: str
    decision: str
    comment: str = ""


class SubmitRequest(BaseModel):
    requester: str
    note: str = ""


class ExecuteRequest(BaseModel):
    executor: str
    mode: str = "skeleton"


def _create_llm_gateway(ai_config: dict):
    """Factory: create LLM Gateway from project ai_config."""
    from app.infrastructure.adapters.llm.ollama import OllamaGateway
    from app.infrastructure.adapters.llm.openai_compat import OpenAICompatGateway

    provider = ai_config.get("provider", "ollama")
    endpoint = ai_config.get("endpoint", "http://localhost:11434")
    model = ai_config.get("model", "deepseek-r1")
    data_policy = ai_config.get("data_policy", "no_external")

    # Enforce data_policy: block non-localhost for no_external
    if data_policy == "no_external" and provider != "ollama":
        if not any(h in endpoint for h in ("localhost", "127.0.0.1", "host.docker.internal")):
            raise ValidationError(f"data_policy=no_external blocks external endpoint: {endpoint}")

    if provider == "ollama":
        return OllamaGateway(endpoint=endpoint, model=model)
    return OpenAICompatGateway(
        endpoint=endpoint, model=model,
        api_key=ai_config.get("api_key", ""),
    )


async def _load_project(db: AsyncSession, project_id: str) -> Optional[dict]:
    from app.domain.projects.service import ProjectService

    proj_svc = ProjectService(db)
    return await proj_svc.get_project(project_id)


def _enrich_change_scope_with_project(change: dict, project: Optional[dict]) -> dict:
    if not project:
        return change
    scope = change.get("scope") or {}
    git_config = project.get("git_config") or {}
    execution_config = project.get("execution_config") or {}
    change["scope"] = {
        **scope,
        "org": scope.get("org") or git_config.get("org") or project.get("github_org", ""),
        "repo": scope.get("repo") or git_config.get("repo") or project.get("github_repo", ""),
        "workflow_id": scope.get("workflow_id") or execution_config.get("workflow_id", "terraform-plan-apply.yml"),
        "terraform_root": scope.get("terraform_root") or project.get("terraform_root", "infra"),
        "cluster_name": scope.get("cluster_name") or execution_config.get("cluster_name", settings.k8s_allowed_cluster),
        "target_namespace": scope.get("target_namespace") or execution_config.get("namespace") or scope.get("namespace", ""),
    }
    return change


def _make_service(db: AsyncSession, project_id: str) -> ChangeService:
    k8s_client = None
    if settings.kubeconfig_path:
        try:
            from app.infrastructure.k8s_client import KubernetesClient
            k8s_client = KubernetesClient.from_config(
                kubeconfig=settings.kubeconfig_path,
                context=settings.k8s_context or None,
            )
        except Exception:
            pass
    return ChangeService(db, project_id, root=settings.demo_data_root, k8s_client=k8s_client)


async def _make_service_with_root(db: AsyncSession, project_id: str) -> ChangeService:
    """Create ChangeService using the project's local_path if available, falling back to demo_data_root."""
    k8s_client = None
    if settings.kubeconfig_path:
        try:
            from app.infrastructure.k8s_client import KubernetesClient
            k8s_client = KubernetesClient.from_config(
                kubeconfig=settings.kubeconfig_path,
                context=settings.k8s_context or None,
            )
        except Exception:
            pass
    root = settings.demo_data_root
    try:
        from pathlib import Path
        from app.domain.projects.service import ProjectService
        proj_svc = ProjectService(db)
        project = await proj_svc.get_project(project_id)
        if project:
            git_config = project.get("git_config") or {}
            local_path = git_config.get("local_path")
            if local_path and Path(local_path).exists():
                root = local_path
    except Exception:
        pass
    return ChangeService(db, project_id, root=root, k8s_client=k8s_client)


@router.get("")
async def list_changes(
    status: Optional[str] = Query(None),
    object_id: Optional[str] = Query(None),
    env: Optional[str] = Query(None),
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    response = await svc.list_changes({"status": status, "object_id": object_id, "env": env})
    project = await _load_project(db, project_id)
    for item in response.get("items", []):
        _enrich_change_scope_with_project(item, project)
    return response


@router.post("")
async def create_change(
    body: CreateChangeRequest,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        request = body.model_dump()
        if not request.get("created_by"):
            request["created_by"] = user
        change = await svc.create_change(request)
        project = await _load_project(db, project_id)
        _enrich_change_scope_with_project(change, project)
        return change
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/draft-preview")
async def draft_preview(
    body: CreateChangeRequest,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        request = body.model_dump()
        if not request.get("created_by"):
            request["created_by"] = user
        change = await svc.create_change(request)
        project = await _load_project(db, project_id)
        _enrich_change_scope_with_project(change, project)
        patch_preview = await svc.generate_patch(change["id"])
        return {"change": change, "patch_preview": patch_preview}
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"draft preview failed: {e}")


@router.get("/{change_id:path}")
async def get_change(
    change_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        change = await svc.get_change(change_id)
        project = await _load_project(db, project_id)
        return _enrich_change_scope_with_project(change, project)
    except ValidationError:
        raise HTTPException(status_code=404, detail=f"change not found: {change_id}")


@router.post("/{change_id:path}/generate-patch")
async def generate_patch(
    change_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        return await svc.generate_patch(change_id)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{change_id:path}/validate")
async def validate_change(
    change_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        mock_runner = lambda cmd, cwd: {"exit_code": 0, "stdout": "mock validation pass", "stderr": ""}
        return await svc.validate_change(change_id, command_runner=mock_runner)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{change_id:path}/plan")
async def run_plan(
    change_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        return await svc.run_plan(change_id, execute=False)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{change_id:path}/submit")
async def submit_approval(
    change_id: str,
    body: SubmitRequest,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        # ── AI Review auto-trigger (before submit) ──
        # pr-agent pattern: review runs automatically, result is advisory only
        change = await svc.get_change(change_id)
        if change["status"] == "PlanReady" and not change.get("artifacts", {}).get("ai_review"):
            try:
                from app.domain.changes.ai_review import run_ai_review
                project = await _load_project(db, project_id)
                ai_config = (project or {}).get("ai_config", {})
                if ai_config.get("provider"):
                    gateway = _create_llm_gateway(ai_config)
                    ai_result = await run_ai_review(gateway, change)
                    artifacts = change.get("artifacts", {})
                    await svc.repository.update(change_id, {
                        "artifacts": {**artifacts, "ai_review": ai_result},
                    })
                    await svc.record_audit_event(
                        change_id, event_type="ai_review_completed", actor="ai_agent",
                        message=f"AI Review auto-triggered: risk_level={ai_result.get('risk_level', 'unknown')}",
                        metadata={"model": ai_result.get("model"), "provider": ai_result.get("provider"),
                                   "prompt_hash": ai_result.get("prompt_hash"), "token_count": ai_result.get("token_count")},
                    )
            except Exception:
                pass  # AI failure must not block the submit flow

        result = await svc.submit_for_approval(change_id, body.requester, body.note)

        # Attach ai_review to response if available
        updated = await svc.get_change(change_id)
        ai_review = updated.get("artifacts", {}).get("ai_review")
        if ai_review:
            result["ai_review"] = ai_review

        return result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{change_id:path}/approve")
async def approve_change(
    change_id: str,
    body: ApprovalRequest,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        return await svc.record_approval(change_id, body.approver, body.decision, body.comment)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{change_id:path}/execute")
async def execute_change(
    change_id: str,
    body: ExecuteRequest,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        change = await svc.get_change(change_id)
        project = await _load_project(db, project_id)
        _enrich_change_scope_with_project(change, project)
        if body.mode == "github_actions":
            if not project:
                raise ValidationError("project not found for github_actions execution")
            await svc.repository.update(change_id, {"scope": change.get("scope") or {}})

        result = await svc.prepare_execution(change_id, body.executor, mode=body.mode)

        # ── AI Diagnostics auto-trigger on execution failure ──
        # k8sgpt pattern: filter errors first, then send to LLM
        if result.get("status") in ("failed", "ExecutionFailed", "blocked"):
            try:
                from app.domain.changes.ai_review import run_ai_diagnostics
                project = await _load_project(db, project_id) if not project else project
                ai_config = (project or {}).get("ai_config", {})
                if ai_config.get("provider"):
                    error_log = ""
                    for check in result.get("checks", []):
                        if check.get("status") in ("failed", "error", "blocked"):
                            error_log += check.get("stderr", "") + "\n" + check.get("message", "") + "\n"
                    if error_log.strip():
                        gateway = _create_llm_gateway(ai_config)
                        updated_change = await svc.get_change(change_id)
                        diag_result = await run_ai_diagnostics(gateway, updated_change, error_log)
                        artifacts = updated_change.get("artifacts", {})
                        await svc.repository.update(change_id, {
                            "artifacts": {**artifacts, "ai_diagnostics": diag_result},
                        })
                        await svc.record_audit_event(
                            change_id, event_type="ai_diagnostics_completed", actor="ai_agent",
                            message=f"AI Diagnostics auto-triggered: {diag_result.get('root_cause', '')[:100]}",
                            metadata={"model": diag_result.get("model"), "provider": diag_result.get("provider")},
                        )
                        result["ai_diagnostics"] = diag_result
            except Exception:
                pass  # AI failure must not block the execution response

        if settings.github_token and change.get("artifacts", {}).get("patched_yaml"):
            from app.api.deps import get_infra_registry
            if project:
                infra = get_infra_registry()
                git_adapter = infra.get_git_adapter(project.get("git_adapter", "github"))
                if git_adapter:
                    try:
                        git_config = project.get("git_config", {})
                        branch = f"cr-{change_id}"
                        source_path = change.get("source_path", "unknown.yaml")
                        patched_yaml = change["artifacts"]["patched_yaml"]

                        await git_adapter.ensure_cloned(git_config)
                        await git_adapter.create_feature_branch(git_config, branch)
                        commit_sha = await git_adapter.apply_and_commit(
                            git_config, branch, source_path, patched_yaml,
                            f"chore: apply change {change_id}\n\n{change.get('reason', '')}",
                        )
                        await git_adapter.push(git_config, branch)

                        pr = await git_adapter.create_pr(
                            git_config, branch,
                            title=f"[GitOps] {change.get('reason', 'Change Request')}",
                            body=f"## Change Request\n\n- **ID**: {change_id}\n- **Object**: {change.get('object_id')}\n- **Reason**: {change.get('reason')}\n- **Commit**: {commit_sha}\n\nAuto-generated by GitOps Platform.",
                        )

                        result["external_url"] = pr.url
                        result["pr_number"] = pr.number
                        result["commit_sha"] = commit_sha
                        result["status"] = pr.status
                        await svc.repository.update(change_id, {
                            "artifacts": {**change.get("artifacts", {}), "pr": {"url": pr.url, "number": pr.number, "status": pr.status, "commit_sha": commit_sha}},
                        })
                    except Exception as e:
                        result["git_error"] = str(e)

        return result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{change_id:path}/workflow-status")
async def get_workflow_status(
    change_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        change = await svc.get_change(change_id)
        execution = change.get("artifacts", {}).get("execution", {})
        if execution.get("mode") != "github_actions":
            return {"status": "not_applicable", "message": "Execution mode is not github_actions"}

        if not settings.github_token:
            return {"status": "mock", "message": "No GitHub token — status check unavailable"}

        try:
            from app.infrastructure.github_client import GitHubClient
            from app.domain.projects.service import ProjectService

            proj_svc = ProjectService(db)
            project = await proj_svc.get_project(project_id)
            if not project:
                return {"status": "error", "message": "Project not found"}

            git_config = project.get("git_config", {})
            org = git_config.get("org", "")
            repo = git_config.get("repo", "")

            run_id_str = execution.get("execution_id", "")
            if not run_id_str or not run_id_str.startswith("gha-"):
                client = GitHubClient()
                runs = await client.get_workflow_runs(org, repo, "terraform-plan-apply.yml", per_page=3)
                return {"status": "recent_runs", "runs": runs}

            return {"status": "checking", "execution_id": run_id_str}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    except ValidationError:
        raise HTTPException(status_code=404, detail=f"change not found: {change_id}")


@router.post("/{change_id:path}/refresh-inventory")
async def refresh_inventory(
    change_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        return await svc.refresh_inventory_snapshot(change_id, user)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{change_id:path}/audit")
async def get_audit_trail(
    change_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = await _make_service_with_root(db, project_id)
    try:
        return await svc.query_change_audit_trail(change_id)
    except ValidationError:
        raise HTTPException(status_code=404, detail=f"change not found: {change_id}")


@router.post("/{change_id:path}/ai-review")
async def trigger_ai_review(
    change_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """AI Review — read-only artifact after PlanReady. Does NOT change status."""
    from app.domain.changes.ai_review import run_ai_review

    svc = await _make_service_with_root(db, project_id)
    try:
        change = await svc.get_change(change_id)
        if change["status"] not in ("PlanReady", "PendingApproval"):
            raise ValidationError("ai-review requires PlanReady or PendingApproval status")

        project = await _load_project(db, project_id)
        ai_config = (project or {}).get("ai_config", {})
        if not ai_config.get("provider"):
            ai_config = {"provider": "ollama", "model": "deepseek-r1", "endpoint": "http://localhost:11434", "data_policy": "no_external"}

        gateway = _create_llm_gateway(ai_config)
        ai_result = await run_ai_review(gateway, change)

        # Store as artifact (read-only, no status change)
        artifacts = change.get("artifacts", {})
        await svc.repository.update(change_id, {
            "artifacts": {**artifacts, "ai_review": ai_result},
        })
        await svc.record_audit_event(
            change_id, event_type="ai_review_completed", actor="ai_agent",
            message=f"AI Review completed: risk_level={ai_result.get('risk_level', 'unknown')}",
            metadata={"model": ai_result.get("model"), "provider": ai_result.get("provider"),
                       "prompt_hash": ai_result.get("prompt_hash"), "token_count": ai_result.get("token_count")},
        )
        return ai_result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Review failed: {e}")


@router.post("/{change_id:path}/ai-diagnostics")
async def trigger_ai_diagnostics(
    change_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
    user: str = Depends(get_current_user),
):
    """AI Diagnostics — analyze execution failure, advisory only."""
    from app.domain.changes.ai_review import run_ai_diagnostics

    svc = await _make_service_with_root(db, project_id)
    try:
        change = await svc.get_change(change_id)
        execution = change.get("artifacts", {}).get("execution", {})
        if execution.get("status") not in ("failed", "ExecutionFailed", "blocked"):
            raise ValidationError("ai-diagnostics requires a failed/blocked execution")

        # Extract error log from execution checks
        error_log = ""
        for check in execution.get("checks", []):
            if check.get("status") in ("failed", "error", "blocked"):
                error_log += check.get("stderr", "") + "\n" + check.get("message", "") + "\n"

        project = await _load_project(db, project_id)
        ai_config = (project or {}).get("ai_config", {})
        if not ai_config.get("provider"):
            ai_config = {"provider": "ollama", "model": "deepseek-r1", "endpoint": "http://localhost:11434", "data_policy": "no_external"}

        gateway = _create_llm_gateway(ai_config)
        diag_result = await run_ai_diagnostics(gateway, change, error_log)

        artifacts = change.get("artifacts", {})
        await svc.repository.update(change_id, {
            "artifacts": {**artifacts, "ai_diagnostics": diag_result},
        })
        await svc.record_audit_event(
            change_id, event_type="ai_diagnostics_completed", actor="ai_agent",
            message=f"AI Diagnostics completed: {diag_result.get('root_cause', '')[:100]}",
            metadata={"model": diag_result.get("model"), "provider": diag_result.get("provider")},
        )
        return diag_result
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Diagnostics failed: {e}")
