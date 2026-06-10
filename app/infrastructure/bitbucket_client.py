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


class BitBucketClient:
    def __init__(self, username: str = "", app_password: str = ""):
        self.username = username or settings.bitbucket_username
        self.app_password = app_password or settings.bitbucket_app_password
        self.base_url = "https://api.bitbucket.org/2.0"
        headers = {"Accept": "application/json"}
        if self.username and self.app_password:
            import base64
            creds = base64.b64encode(f"{self.username}:{self.app_password}".encode()).decode()
            headers["Authorization"] = f"Basic {creds}"
        self._client = httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=30.0)

    async def close(self):
        await self._client.aclose()

    async def create_pr_from_existing_branch(
        self, owner: str, repo: str, branch: str, title: str, body: str, base_branch: str = "main",
    ) -> PRResult:
        if not self.username or not self.app_password:
            return PRResult(url="mock://pr", number=0, branch=branch, status="mock_no_token")

        resp = await self._client.post(
            f"/repositories/{owner}/{repo}/pullrequests",
            json={
                "title": title,
                "description": body,
                "source": {"branch": {"name": branch}},
                "destination": {"branch": {"name": base_branch}},
            },
        )
        resp.raise_for_status()
        data = resp.json()
        return PRResult(
            url=data["links"]["html"]["href"],
            number=data["id"],
            branch=branch,
            status="created",
        )
