import asyncio
import logging
import os
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class GitError(Exception):
    """Base error for git operations."""


class GitAuthError(GitError):
    """Authentication failed. Check GITHUB_TOKEN."""


class GitConflictError(GitError):
    """Merge conflict detected."""


class GitRepoService:
    """Manages local git working copies for GitOps operations.

    clone / pull / branch / commit / push — all via git CLI subprocess.
    """

    def __init__(self, storage_root: str, github_token: str = "", provider: str = "github"):
        self.storage_root = Path(storage_root)
        self.github_token = github_token
        self.provider = provider

    def repo_path(self, org: str, repo: str) -> Path:
        return self.storage_root / org / repo

    def _remote_url(self, org: str, repo: str) -> str:
        if self.provider == "bitbucket":
            if self.github_token:
                return f"https://x-token-auth:{self.github_token}@bitbucket.org/{org}/{repo}.git"
            return f"https://bitbucket.org/{org}/{repo}.git"
        if self.provider == "gitlab":
            if self.github_token:
                return f"https://oauth2:{self.github_token}@gitlab.com/{org}/{repo}.git"
            return f"https://gitlab.com/{org}/{repo}.git"
        if self.github_token:
            return f"https://x-access-token:{self.github_token}@github.com/{org}/{repo}.git"
        return f"https://github.com/{org}/{repo}.git"

    async def _run(self, *args: str, cwd: Optional[Path] = None, timeout: int = 120) -> str:
        """Run a git command and return stdout. Raises GitError on failure."""
        cmd = ["git"] + list(args)
        logger.info("git: %s (cwd=%s)", " ".join(cmd), cwd)
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=str(cwd) if cwd else None,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            raise GitError(f"git {' '.join(cmd)} timed out after {timeout}s")

        out = stdout.decode("utf-8", errors="replace").strip()
        err = stderr.decode("utf-8", errors="replace").strip()

        if proc.returncode != 0:
            combined = f"{out}\n{err}".strip()
            if "Authentication failed" in combined or "could not read Password" in combined:
                raise GitAuthError(f"GitHub authentication failed. Check GITHUB_TOKEN.\n{combined}")
            if "CONFLICT" in combined or "Merge conflict" in combined:
                raise GitConflictError(f"Merge conflict.\n{combined}")
            raise GitError(f"git {' '.join(cmd)} failed (exit {proc.returncode}):\n{combined}")

        return out

    async def ensure_cloned(self, org: str, repo: str) -> Path:
        """Clone if not exists, otherwise fetch + checkout main + pull."""
        path = self.repo_path(org, repo)
        if (path / ".git").exists():
            await self._run("fetch", "origin", cwd=path)
            await self._run("checkout", "main", cwd=path)
            await self._run("pull", "origin", "main", cwd=path)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            url = self._remote_url(org, repo)
            await self._run("clone", "--depth", "1", url, str(path.name), cwd=path.parent)
        return path

    async def create_feature_branch(self, org: str, repo: str, branch: str, base: str = "main") -> Path:
        """Checkout base, pull, then create feature branch. If branch exists, reset it."""
        path = self.repo_path(org, repo)
        await self._run("fetch", "origin", cwd=path)
        await self._run("checkout", base, cwd=path)
        await self._run("pull", "origin", base, cwd=path)

        # Check if branch already exists
        try:
            existing = await self._run("branch", "--list", branch, cwd=path)
            if existing:
                await self._run("checkout", branch, cwd=path)
                await self._run("reset", "--hard", f"origin/{base}", cwd=path)
                return path
        except GitError:
            pass

        await self._run("checkout", "-b", branch, cwd=path)
        return path

    async def apply_and_commit(self, org: str, repo: str, branch: str, file_path: str, content: str, message: str) -> str:
        """Write file, git add, git commit. Returns commit SHA."""
        path = self.repo_path(org, repo)
        dest = path / file_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(content, encoding="utf-8")
        await self._run("add", file_path, cwd=path)
        await self._run("commit", "-m", message, cwd=path)
        return await self.get_head_sha(org, repo)

    async def push(self, org: str, repo: str, branch: str) -> None:
        path = self.repo_path(org, repo)
        await self._run("push", "origin", branch, cwd=path)

    async def get_head_sha(self, org: str, repo: str) -> str:
        path = self.repo_path(org, repo)
        return await self._run("rev-parse", "HEAD", cwd=path)

    async def get_file_sha(self, org: str, repo: str, file_path: str) -> str:
        path = self.repo_path(org, repo)
        return await self._run("hash-object", str(path / file_path), cwd=path)
