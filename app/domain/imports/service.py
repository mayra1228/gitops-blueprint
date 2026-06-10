"""Project import service — orchestrates clone → scan → register flow.

Onboards existing Terraform/infrastructure repos into the GitOps platform.
"""

import re
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.adapters.registry import AdapterRegistry
from app.domain.inventory.scanner import InventoryScanner
from app.domain.inventory.terraform_scanner import TerraformFileScanner, TerraformScanResult
from app.domain.inventory.service import InventoryService
from app.domain.projects.service import ProjectService
from app.infrastructure.adapters.registry import InfrastructureAdapterRegistry
from app.infrastructure.git_repo_service import GitRepoService, GitError

logger = logging.getLogger(__name__)

# URL patterns for common Git hosting services
_RE_GITHUB = re.compile(r"github\.com/(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$")
_RE_GITLAB = re.compile(r"gitlab\.com/(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$")
_RE_BITBUCKET = re.compile(r"bitbucket\.org/(?P<org>[^/]+)/(?P<repo>[^/]+?)(?:\.git)?$")


@dataclass
class DiscoverResult:
    """Result of the discover step — repo metadata + scan summaries."""
    status: str
    repo: Dict[str, str]
    summary: Dict[str, Any] = field(default_factory=dict)
    terraform_scan: Optional[Dict[str, Any]] = None
    odp_scan: Optional[Dict[str, Any]] = None
    errors: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "repo": self.repo,
            "summary": self.summary,
            "terraform_scan": self.terraform_scan,
            "odp_scan": self.odp_scan,
            "errors": self.errors,
        }


def parse_repo_url(repo_url: str, provider: str = "") -> Dict[str, str]:
    """Parse a Git repo URL into org, repo, and detected provider."""
    clean = repo_url.rstrip("/").removesuffix(".git")

    detected = ""
    for name, pattern in [("github", _RE_GITHUB), ("gitlab", _RE_GITLAB), ("bitbucket", _RE_BITBUCKET)]:
        m = pattern.search(clean)
        if m:
            detected = name
            return {
                "org": m.group("org"),
                "repo": m.group("repo"),
                "provider": provider or detected,
                "url": repo_url,
            }

    # Fallback: try generic URL parsing
    parsed = urlparse(repo_url)
    parts = parsed.path.strip("/").split("/")
    if len(parts) >= 2:
        return {
            "org": parts[0],
            "repo": parts[1],
            "provider": provider or "github",
            "url": repo_url,
        }

    raise ValueError(f"Unable to parse repo URL: {repo_url}")


class ProjectImportService:
    """Orchestrates the import flow: clone → scan → register.

    Uses:
    - GitRepoService for cloning
    - InventoryScanner for ODP .yaml files
    - TerraformFileScanner for .tf files
    - ProjectService for creating project records
    - InventoryService for persisting scan results
    """

    def __init__(
        self,
        db: AsyncSession,
        git_service: GitRepoService,
        infra_registry: InfrastructureAdapterRegistry,
        domain_registry: AdapterRegistry,
    ):
        self.db = db
        self.git_service = git_service
        self.infra_registry = infra_registry
        self.domain_registry = domain_registry

    async def discover(self, repo_url: str, provider: str = "") -> DiscoverResult:
        """Step 1→2: Clone repo and scan for IaC files.

        Returns a DiscoverResult with repo metadata, terraform scan summary,
        and ODP scan summary. Does NOT persist anything to DB.
        """
        repo = parse_repo_url(repo_url, provider)
        errors: List[Dict[str, str]] = []

        # Clone
        repo_path: Optional[Path] = None
        try:
            repo_path = await self.git_service.ensure_cloned(
                repo["org"], repo["repo"]
            )
        except GitError as exc:
            return DiscoverResult(
                status="clone_failed",
                repo=repo,
                errors=[{"type": "clone", "message": str(exc)}],
            )

        # Terraform scan
        tf_result: Optional[TerraformScanResult] = None
        try:
            tf_scanner = TerraformFileScanner()
            tf_result = tf_scanner.scan(repo_path)
            errors.extend(tf_result.errors)
        except Exception as exc:
            errors.append({"type": "terraform_scan", "message": str(exc)})

        # ODP YAML scan
        odp_result = None
        try:
            odp_scanner = InventoryScanner(self.domain_registry)
            odp_result = odp_scanner.scan(str(repo_path))
            odp_errors = odp_result.errors
            if isinstance(odp_errors, list):
                errors.extend(odp_errors)
        except Exception as exc:
            errors.append({"type": "odp_scan", "message": str(exc)})

        # Build combined summary
        tf_summary = tf_result.summary if tf_result else {}
        odp_summary = odp_result.summary if odp_result else {}
        summary = {
            "total_files": (tf_summary.get("total_files", 0) +
                            int(odp_summary.get("total_objects", 0))),
            "terraform_files": tf_summary.get("total_files", 0),
            "terraform_resources": tf_summary.get("total_resources", 0),
            "odp_yaml_objects": int(odp_summary.get("total_objects", 0)),
            "resource_types": tf_summary.get("resource_types", {}),
            "terraform_providers": tf_summary.get("providers", []),
            "terraform_modules": tf_summary.get("total_modules", 0),
            "odp_envs": list(odp_summary.get("by_env", {}).keys()) if odp_summary else [],
        }

        status = "success"
        if errors and not tf_result and not odp_result:
            status = "scan_failed"

        return DiscoverResult(
            status=status,
            repo=repo,
            summary=summary,
            terraform_scan=tf_result.to_dict() if tf_result else None,
            odp_scan={
                "status": odp_result.status if odp_result else "skipped",
                "summary": odp_summary,
                "errors": odp_result.errors if odp_result else [],
            } if odp_result else None,
            errors=errors,
        )

    async def register(
        self,
        project_name: str,
        repo_url: str,
        provider: str = "",
        git_adapter: str = "",
        execution_adapter: str = "",
        terraform_root: str = "infra",
        execution_config: Optional[dict] = None,
    ) -> Dict[str, Any]:
        """Step 3→4: Create project record and persist inventory scan.

        Returns the created project dict with scan summary.
        """
        repo = parse_repo_url(repo_url, provider)

        # Create the project
        project_svc = ProjectService(self.db)
        project = await project_svc.create_project(
            name=project_name,
            github_org=repo["org"],
            github_repo=repo["repo"],
            terraform_root=terraform_root,
            git_adapter=git_adapter or repo["provider"],
            execution_adapter=execution_adapter or "jenkins",
            execution_config=execution_config,
        )

        # Ensure repo is cloned and scan
        repo_path = await self.git_service.ensure_cloned(repo["org"], repo["repo"])

        # Run inventory scan and persist
        inv_svc = InventoryService(self.db, project["id"], self.domain_registry)
        scan_result = await inv_svc.scan(str(repo_path))

        return {
            "project": project,
            "scan_summary": scan_result.summary,
        }