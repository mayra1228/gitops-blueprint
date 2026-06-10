from pathlib import Path

from app.infrastructure.adapters.base import GitAdapter
from app.infrastructure.adapters.types import PRResult
from app.infrastructure.github_client import GitHubClient
from app.infrastructure.git_repo_service import GitRepoService


class GitHubGitAdapter(GitAdapter):
    name = "github"

    def __init__(self, storage_root: str, token: str = ""):
        self._git_svc = GitRepoService(storage_root, token)
        self._gh_token = token
        self._gh_client: GitHubClient | None = None

    def _get_client(self) -> GitHubClient:
        if self._gh_client is None:
            self._gh_client = GitHubClient(self._gh_token)
        return self._gh_client

    async def ensure_cloned(self, config: dict) -> Path:
        return await self._git_svc.ensure_cloned(config["org"], config["repo"])

    async def create_feature_branch(self, config: dict, branch: str, base: str = "main") -> Path:
        return await self._git_svc.create_feature_branch(config["org"], config["repo"], branch, base)

    async def apply_and_commit(self, config: dict, branch: str, file_path: str, content: str, message: str) -> str:
        return await self._git_svc.apply_and_commit(config["org"], config["repo"], branch, file_path, content, message)

    async def push(self, config: dict, branch: str) -> None:
        return await self._git_svc.push(config["org"], config["repo"], branch)

    async def get_head_sha(self, config: dict) -> str:
        return await self._git_svc.get_head_sha(config["org"], config["repo"])

    async def create_pr(self, config: dict, branch: str, title: str, body: str, base_branch: str = "main") -> PRResult:
        return await self._get_client().create_pr_from_existing_branch(
            owner=config["org"],
            repo=config["repo"],
            branch=branch,
            title=title,
            body=body,
            base_branch=base_branch,
        )

    async def close(self) -> None:
        if self._gh_client is not None:
            await self._gh_client.close()
