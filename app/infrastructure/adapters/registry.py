from app.config import settings
from app.infrastructure.adapters.base import ExecutionAdapter, GitAdapter, WebhookAdapter


class InfrastructureAdapterRegistry:
    def __init__(self, git_adapters: list[GitAdapter], execution_adapters: list[ExecutionAdapter], webhook_adapters: list[WebhookAdapter]):
        self._git: dict[str, GitAdapter] = {a.name: a for a in git_adapters}
        self._execution: dict[str, ExecutionAdapter] = {a.name: a for a in execution_adapters}
        self._webhook: dict[str, WebhookAdapter] = {a.name: a for a in webhook_adapters}

    def get_git_adapter(self, name: str) -> GitAdapter | None:
        return self._git.get(name)

    def get_execution_adapter(self, name: str) -> ExecutionAdapter | None:
        return self._execution.get(name)

    def get_webhook_adapter(self, name: str) -> WebhookAdapter | None:
        return self._webhook.get(name)

    def list_adapters(self) -> dict:
        return {
            "git": [{"name": a.name, "label": a.name.capitalize()} for a in self._git.values()],
            "execution": [{"name": a.name, "label": a.name.capitalize()} for a in self._execution.values()],
            "webhook": [{"name": a.name, "label": f"{a.name.capitalize()} Webhook"} for a in self._webhook.values()],
        }


def build_default_infra_registry() -> InfrastructureAdapterRegistry:
    from app.infrastructure.adapters.bitbucket_git import BitBucketGitAdapter
    from app.infrastructure.adapters.bitbucket_webhook import BitBucketWebhookAdapter
    from app.infrastructure.adapters.github_git import GitHubGitAdapter
    from app.infrastructure.adapters.github_webhook import GitHubWebhookAdapter
    from app.infrastructure.adapters.gitlab_git import GitLabGitAdapter
    from app.infrastructure.adapters.gitlab_webhook import GitLabWebhookAdapter
    from app.infrastructure.adapters.github_actions_execution import GitHubActionsExecutionAdapter
    from app.infrastructure.adapters.jenkins_execution import JenkinsExecutionAdapter
    from app.infrastructure.adapters.k8s_execution import K8SExecutionAdapter

    return InfrastructureAdapterRegistry(
        git_adapters=[
            GitHubGitAdapter(storage_root=settings.repo_storage_root, token=settings.github_token),
            BitBucketGitAdapter(storage_root=settings.repo_storage_root),
            GitLabGitAdapter(storage_root=settings.repo_storage_root),
        ],
        execution_adapters=[JenkinsExecutionAdapter(), K8SExecutionAdapter(), GitHubActionsExecutionAdapter()],
        webhook_adapters=[
            GitHubWebhookAdapter(),
            BitBucketWebhookAdapter(),
            GitLabWebhookAdapter(),
        ],
    )
