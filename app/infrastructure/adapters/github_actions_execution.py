import logging
from uuid import uuid4

from app.config import settings
from app.infrastructure.adapters.base import ExecutionAdapter
from app.infrastructure.adapters.types import ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


class GitHubActionsExecutionAdapter(ExecutionAdapter):
    name = "github_actions"

    def __init__(self, github_client=None):
        self._client = github_client

    def _get_client(self):
        if self._client:
            return self._client
        from app.infrastructure.github_client import GitHubClient
        return GitHubClient()

    async def trigger(self, config: dict, params: dict) -> ExecutionResult:
        execution_id = f"gha-{uuid4().hex[:8]}"

        owner = config.get("org", "")
        repo = config.get("repo", "")
        workflow_id = config.get("workflow_id", "terraform-plan-apply.yml")
        ref = params.get("branch", "main")
        inputs = {
            "environment": params.get("environment", "sandbox"),
            "terraform_root": params.get("terraform_root", "infra"),
            "action": params.get("action", "plan"),
            "change_id": params.get("change_id", ""),
            "cluster_name": params.get("cluster_name", settings.k8s_allowed_cluster),
        }
        action = inputs["action"]
        environment = inputs["environment"]
        cluster_name = str(inputs["cluster_name"])

        if not owner or not repo:
            return ExecutionResult(
                execution_id=execution_id,
                status="failed",
                details={"mode": "github_actions", "message": "Missing org/repo in config"},
            )
        if action not in {"plan", "apply"}:
            return ExecutionResult(
                execution_id=execution_id,
                status="failed",
                details={"mode": "github_actions", "message": f"Unsupported action: {action}"},
            )
        if cluster_name != settings.k8s_allowed_cluster:
            return ExecutionResult(
                execution_id=execution_id,
                status="failed",
                details={
                    "mode": "github_actions",
                    "message": (
                        f"Cluster boundary violation: cluster_name={cluster_name}, "
                        f"allowed={settings.k8s_allowed_cluster}"
                    ),
                },
            )
        if action == "apply" and environment != "sandbox":
            return ExecutionResult(
                execution_id=execution_id,
                status="failed",
                details={
                    "mode": "github_actions",
                    "message": "Apply is only allowed for sandbox environment",
                },
            )

        client = self._get_client()
        if not settings.github_token:
            return ExecutionResult(
                execution_id=execution_id,
                status="mock_no_token",
                details={
                    "mode": "github_actions",
                    "message": "No GITHUB_TOKEN configured — workflow dispatch skipped",
                    "workflow_id": workflow_id,
                    "ref": ref,
                    "inputs": inputs,
                },
            )

        try:
            result = await client.dispatch_workflow(owner, repo, workflow_id, ref, inputs)
            status = result.get("status", "error")

            if status == "dispatched":
                runs = await client.get_workflow_runs(owner, repo, workflow_id, ref, per_page=1)
                run_id = runs[0]["id"] if runs else None
                return ExecutionResult(
                    execution_id=str(run_id) if run_id else execution_id,
                    status="running",
                    external_url=runs[0].get("html_url") if runs else None,
                    details={
                        "mode": "github_actions",
                        "dispatch_status": status,
                        "workflow_id": workflow_id,
                        "ref": ref,
                        "inputs": inputs,
                        "run_id": run_id,
                    },
                )
            else:
                return ExecutionResult(
                    execution_id=execution_id,
                    status="dispatch_failed",
                    details={"mode": "github_actions", "dispatch_result": result},
                )
        except Exception as exc:
            logger.exception("GitHub Actions dispatch failed")
            return ExecutionResult(
                execution_id=execution_id,
                status="error",
                details={"mode": "github_actions", "error": str(exc)},
            )

    async def get_status(self, config: dict, execution_id: str) -> ExecutionStatus:
        owner = config.get("org", "")
        repo = config.get("repo", "")

        if not owner or not repo or not settings.github_token:
            return ExecutionStatus(execution_id=execution_id, status="unknown")

        try:
            client = self._get_client()
            run_id = int(execution_id)
            run = await client.get_workflow_run(owner, repo, run_id)
            logs = await client.get_workflow_run_logs(owner, repo, run_id)
            return ExecutionStatus(
                execution_id=execution_id,
                status=run.get("status", "unknown"),
                logs_url=logs.get("logs_url"),
            )
        except (ValueError, Exception):
            return ExecutionStatus(execution_id=execution_id, status="unknown")
