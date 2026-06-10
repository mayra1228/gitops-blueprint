import logging
from uuid import uuid4

from app.infrastructure.adapters.base import ExecutionAdapter
from app.infrastructure.adapters.types import ExecutionResult, ExecutionStatus

logger = logging.getLogger(__name__)


class JenkinsExecutionAdapter(ExecutionAdapter):
    name = "jenkins"

    async def trigger(self, config: dict, params: dict) -> ExecutionResult:
        job = config.get("job_name", "unknown")
        endpoint = config.get("endpoint", "https://jenkins.example.com")
        logger.info("Jenkins stub: would trigger job %s with params %s", job, params)
        return ExecutionResult(
            execution_id=f"jenkins-mock-{uuid4().hex[:8]}",
            status="running",
            external_url=f"{endpoint}/job/{job}",
            details={"mode": "stub", "message": "No real Jenkins call performed"},
        )

    async def get_status(self, config: dict, execution_id: str) -> ExecutionStatus:
        return ExecutionStatus(execution_id=execution_id, status="running", logs_url=None)
