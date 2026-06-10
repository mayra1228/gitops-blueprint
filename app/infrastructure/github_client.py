import base64
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


class GitHubClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        self.base_url = "https://api.github.com"
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30.0,
        )

    async def close(self):
        await self._client.aclose()

    async def create_pr(
        self,
        owner: str,
        repo: str,
        branch: str,
        file_path: str,
        file_content: str,
        commit_message: str,
        pr_title: str,
        pr_body: str,
        base_branch: str = "main",
    ) -> PRResult:
        if not self.token:
            return PRResult(url="mock://pr", number=0, branch=branch, status="mock_no_token")

        # Get the default branch SHA
        ref_url = f"/repos/{owner}/{repo}/git/refs/heads/{base_branch}"
        ref_resp = await self._client.get(ref_url)
        ref_resp.raise_for_status()
        base_sha = ref_resp.json()["object"]["sha"]

        # Create a new branch
        new_ref = f"refs/heads/{branch}"
        create_ref_resp = await self._client.post(
            f"/repos/{owner}/{repo}/git/refs",
            json={"ref": new_ref, "sha": base_sha},
        )
        create_ref_resp.raise_for_status()

        # Create/update the file on the new branch
        content_b64 = base64.b64encode(file_content.encode()).decode()
        put_file_resp = await self._client.put(
            f"/repos/{owner}/{repo}/contents/{file_path}",
            json={
                "message": commit_message,
                "content": content_b64,
                "branch": branch,
            },
        )
        put_file_resp.raise_for_status()

        # Create the PR
        pr_resp = await self._client.post(
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": pr_title,
                "body": pr_body,
                "head": branch,
                "base": base_branch,
            },
        )
        pr_resp.raise_for_status()
        pr_data = pr_resp.json()
        return PRResult(url=pr_data["html_url"], number=pr_data["number"], branch=branch, status="created")

    async def create_pr_from_existing_branch(
        self,
        owner: str,
        repo: str,
        branch: str,
        title: str,
        body: str,
        base_branch: str = "main",
    ) -> PRResult:
        """Create a PR for an already-pushed branch (no file upload needed)."""
        if not self.token:
            return PRResult(url="mock://pr", number=0, branch=branch, status="mock_no_token")

        pr_resp = await self._client.post(
            f"/repos/{owner}/{repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": branch,
                "base": base_branch,
            },
        )
        pr_resp.raise_for_status()
        pr_data = pr_resp.json()
        return PRResult(url=pr_data["html_url"], number=pr_data["number"], branch=branch, status="created")

    async def merge_pr(self, owner: str, repo: str, pr_number: int) -> dict:
        if not self.token:
            return {"merged": False, "message": "mock_no_token"}
        resp = await self._client.put(
            f"/repos/{owner}/{repo}/pulls/{pr_number}/merge",
            json={"merge_method": "merge"},
        )
        resp.raise_for_status()
        return resp.json()

    async def get_pr_status(self, owner: str, repo: str, pr_number: int) -> dict:
        if not self.token:
            return {"state": "open", "merged": False}
        resp = await self._client.get(f"/repos/{owner}/{repo}/pulls/{pr_number}")
        resp.raise_for_status()
        data = resp.json()
        return {"state": data["state"], "merged": data.get("merged", False)}

    async def dispatch_workflow(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        ref: str,
        inputs: dict | None = None,
    ) -> dict:
        """Trigger a workflow_dispatch event."""
        if not self.token:
            return {"status": "mock_no_token", "run_id": None}
        resp = await self._client.post(
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/dispatches",
            json={"ref": ref, "inputs": inputs or {}},
        )
        if resp.status_code == 204:
            return {"status": "dispatched", "run_id": None}
        resp.raise_for_status()
        return {"status": "error", "detail": resp.text}

    async def get_workflow_runs(
        self,
        owner: str,
        repo: str,
        workflow_id: str,
        branch: str | None = None,
        per_page: int = 5,
    ) -> list[dict]:
        """List recent workflow runs."""
        if not self.token:
            return []
        params = {"per_page": per_page}
        if branch:
            params["branch"] = branch
        resp = await self._client.get(
            f"/repos/{owner}/{repo}/actions/workflows/{workflow_id}/runs",
            params=params,
        )
        resp.raise_for_status()
        data = resp.json()
        return [
            {
                "id": r["id"],
                "run_number": r.get("run_number"),
                "status": r.get("status"),
                "conclusion": r.get("conclusion"),
                "head_branch": r.get("head_branch"),
                "html_url": r.get("html_url"),
                "created_at": r.get("created_at"),
                "updated_at": r.get("updated_at"),
            }
            for r in data.get("workflow_runs", [])
        ]

    async def get_workflow_run(
        self, owner: str, repo: str, run_id: int,
    ) -> dict:
        """Get a single workflow run's status."""
        if not self.token:
            return {"status": "mock_no_token", "conclusion": None}
        resp = await self._client.get(
            f"/repos/{owner}/{repo}/actions/runs/{run_id}",
        )
        resp.raise_for_status()
        r = resp.json()
        return {
            "id": r["id"],
            "run_number": r.get("run_number"),
            "status": r.get("status"),
            "conclusion": r.get("conclusion"),
            "head_branch": r.get("head_branch"),
            "html_url": r.get("html_url"),
            "created_at": r.get("created_at"),
            "updated_at": r.get("updated_at"),
        }

    async def get_workflow_run_logs(
        self, owner: str, repo: str, run_id: int,
    ) -> dict:
        """Get workflow run logs URL."""
        if not self.token:
            return {"logs_url": None}
        resp = await self._client.get(
            f"/repos/{owner}/{repo}/actions/runs/{run_id}/logs",
            follow_redirects=False,
        )
        return {
            "logs_url": resp.headers.get("Location", "") if resp.status_code == 302 else None,
        }

    async def add_pr_comment(
        self, owner: str, repo: str, pr_number: int, body: str,
    ) -> dict:
        """Add a comment to a PR (used for posting terraform plan output)."""
        if not self.token:
            return {"status": "mock_no_token"}
        resp = await self._client.post(
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            json={"body": body},
        )
        resp.raise_for_status()
        return {"id": resp.json()["id"], "url": resp.json()["html_url"]}
