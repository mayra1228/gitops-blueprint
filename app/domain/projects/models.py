from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Project:
    id: str
    name: str
    slug: str
    github_org: str
    github_repo: str
    terraform_root: str = "infra"
    created_at: Optional[datetime] = None
    git_adapter: Optional[str] = None
    git_config: Optional[dict] = None
    execution_adapter: Optional[str] = None
    execution_config: Optional[dict] = None
    ai_config: Optional[dict] = None

    def to_dict(self) -> dict:
        git_cfg = self.git_config or {"org": self.github_org, "repo": self.github_repo}
        exec_cfg = self.execution_config or {
            "job_name": "gitops-deploy",
            "workflow_id": "terraform-plan-apply.yml",
            "cluster_name": "kind-gitops-sandbox",
        }
        ai_cfg = self.ai_config or {
            "provider": "ollama",
            "model": "deepseek-r1",
            "endpoint": "http://localhost:11434",
            "data_policy": "no_external",
        }
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "github_org": self.github_org,
            "github_repo": self.github_repo,
            "terraform_root": self.terraform_root,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "git_adapter": self.git_adapter or "github",
            "git_config": git_cfg,
            "execution_adapter": self.execution_adapter or "jenkins",
            "execution_config": exec_cfg,
            "ai_config": ai_cfg,
        }
