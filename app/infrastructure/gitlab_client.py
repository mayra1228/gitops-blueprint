from dataclasses import dataclass
from typing import Optional

import httpx

from app.config import settings


@dataclass
class PRResult:
    url: str
    number: int
    branch: str
    status: str


class GitLabClient:
    def __init__(self, token: str = ""):
        self.token = token or settings.gitlab_token
        self.base_url = "https://gitlab.com/api/v4"
        headers = {"Accept": "application/json"}
        if self.token:
            headers["PRIVATE-TOKEN"] = self.token
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0)

    async def close(self):
        await self._client.aclose()

    async def create_mr(
        self, owner: str, repo: str, branch: str, title: str, body: str, base_branch: str = "main",
    ) -> PRResult:
        if not self.token:
            return PRResult(url="mock://pr", number=0, branch=branch, status="mock_no_token")

        project_id = f"{owner}%2F{repo}"
        resp = await self._client.post(
            f"/projects/{project_id}/merge_requests",
            json={
                "source_branch": branch,
                "target_branch": base_branch,
                "title": title,
                "description": body,
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return PRResult(
            url=data["web_url"],
            number=data["iid"],
            branch=branch,
            status="created",
        )
