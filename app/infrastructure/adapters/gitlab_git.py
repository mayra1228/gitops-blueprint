from pathlib import Path

from app.config import settings
from app.infrastructure.adapters.base import GitAdapter
from app.infrastructure.adapters.types import PRResult
from app.infrastructure.git_repo_service import GitRepoService
from app.infrastructure.gitlab_client import GitLabClient


class GitLabGitAdapter(GitAdapter):
    name = "gitlab"

    def __init__(self, storage_root: str, token: str = ""):
        self._git_svc = GitRepoService(storage_root, token or settings.gitlab_token, provider="gitlab")
        self._token = token or settings.gitlab_token
        self._client: GitLabClient | None = None

    def _get_client(self) -> GitLabClient:
        if self._client is None:
            self._client = GitLabClient(self._token)
        return self._client

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
        return await self._get_client().create_mr(
            owner=config.get("org", config.get("namespace", "")),
            repo=config["repo"],
            branch=branch,
            title=title,
            body=body,
            base_branch=base_branch,
        )

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
