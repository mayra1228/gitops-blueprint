from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.projects.models import Project
from app.domain.projects.repository import ProjectRepository


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(self) -> List[dict]:
        repo = ProjectRepository(self.db)
        projects = await repo.list_all()
        return [p.to_dict() for p in projects]

    async def create_project(self, name: str, github_org: str, github_repo: str, terraform_root: str = "infra", git_adapter: Optional[str] = None, git_config: Optional[dict] = None, execution_adapter: Optional[str] = None, execution_config: Optional[dict] = None) -> dict:
        slug = name.lower().replace(" ", "-").replace("_", "-")
        repo = ProjectRepository(self.db)
        existing = await repo.get_by_slug(slug)
        if existing:
            raise ValueError(f"project with slug '{slug}' already exists")
        project = await repo.create(name=name, slug=slug, github_org=github_org, github_repo=github_repo, terraform_root=terraform_root, git_adapter=git_adapter, git_config=git_config, execution_adapter=execution_adapter, execution_config=execution_config)
        return project.to_dict()

    async def get_project(self, project_id: str) -> Optional[dict]:
        repo = ProjectRepository(self.db)
        project = await repo.get_by_id(project_id)
        return project.to_dict() if project else None

    async def delete_project(self, project_id: str) -> bool:
        repo = ProjectRepository(self.db)
        return await repo.delete(project_id)

    async def update_project_config(
        self,
        project_id: str,
        *,
        terraform_root: Optional[str] = None,
        git_adapter: Optional[str] = None,
        git_config: Optional[dict] = None,
        execution_adapter: Optional[str] = None,
        execution_config: Optional[dict] = None,
    ) -> Optional[dict]:
        repo = ProjectRepository(self.db)
        project = await repo.update_config(
            project_id,
            terraform_root=terraform_root,
            git_adapter=git_adapter,
            git_config=git_config,
            execution_adapter=execution_adapter,
            execution_config=execution_config,
        )
        return project.to_dict() if project else None
