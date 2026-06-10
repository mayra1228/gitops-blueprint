import logging
from uuid import uuid4

from app.config import settings
from app.infrastructure.adapters.base import ExecutionAdapter
from app.infrastructure.adapters.types import ExecutionResult, ExecutionStatus
from app.infrastructure.k8s_client import KubernetesClient

logger = logging.getLogger(__name__)


class K8SExecutionAdapter(ExecutionAdapter):
    name = "k8s"

    def __init__(self, client: KubernetesClient | None = None):
        self._client = client

    def _get_client(self) -> KubernetesClient:
        if self._client:
            return self._client
        return KubernetesClient.from_config(
            kubeconfig=settings.kubeconfig_path or None,
            context=settings.k8s_context or None,
        )

    async def trigger(self, config: dict, params: dict) -> ExecutionResult:
        manifest = params.get("manifest", "")
        dry_run = config.get("dry_run", False)
        namespace = config.get("namespace", "default")
        execution_id = f"k8s-{uuid4().hex[:8]}"

        if not manifest:
            return ExecutionResult(
                execution_id=execution_id,
                status="failed",
                details={"mode": "k8s", "message": "No manifest content provided"},
            )

        if dry_run:
            client = self._get_client()
            result = client.validate_manifest(manifest)
            return ExecutionResult(
                execution_id=execution_id,
                status="validated" if result.success else "validation_failed",
                details={
                    "mode": "k8s_dry_run",
                    "exit_code": result.exit_code,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                },
            )

        client = self._get_client()
        result = client.apply_manifest(manifest)
        return ExecutionResult(
            execution_id=execution_id,
            status="applied" if result.success else "failed",
            details={
                "mode": "k8s_apply",
                "namespace": namespace,
                "exit_code": result.exit_code,
                "stdout": result.stdout,
                "stderr": result.stderr,
            },
        )

    async def get_status(self, config: dict, execution_id: str) -> ExecutionStatus:
        return ExecutionStatus(execution_id=execution_id, status="applied")
