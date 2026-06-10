import pytest

from app.infrastructure.adapters.github_actions_execution import GitHubActionsExecutionAdapter


class _FakeClient:
    async def dispatch_workflow(self, owner, repo, workflow_id, ref, inputs):
        return {"status": "dispatched"}

    async def get_workflow_runs(self, owner, repo, workflow_id, ref=None, per_page=1):
        return [{"id": 123456, "html_url": "https://example.com/run/123456"}]


@pytest.mark.asyncio
async def test_trigger_blocks_non_allowed_cluster():
    adapter = GitHubActionsExecutionAdapter(github_client=_FakeClient())
    result = await adapter.trigger(
        {"org": "o", "repo": "r"},
        {"action": "apply", "environment": "sandbox", "cluster_name": "kind-other"},
    )
    assert result.status == "failed"
    assert "Cluster boundary violation" in (result.details or {}).get("message", "")


@pytest.mark.asyncio
async def test_trigger_blocks_apply_for_non_sandbox():
    adapter = GitHubActionsExecutionAdapter(github_client=_FakeClient())
    result = await adapter.trigger(
        {"org": "o", "repo": "r"},
        {"action": "apply", "environment": "prod", "cluster_name": "kind-gitops-sandbox"},
    )
    assert result.status == "failed"
    assert "only allowed for sandbox" in (result.details or {}).get("message", "")


@pytest.mark.asyncio
async def test_trigger_dispatches_when_guardrails_pass(monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "github_token", "test-token")
    adapter = GitHubActionsExecutionAdapter(github_client=_FakeClient())
    result = await adapter.trigger(
        {"org": "o", "repo": "r", "workflow_id": "terraform-plan-apply.yml"},
        {"action": "apply", "environment": "sandbox", "cluster_name": "kind-gitops-sandbox"},
    )
    assert result.status == "running"
    assert result.execution_id == "123456"
