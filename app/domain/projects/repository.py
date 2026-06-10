from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.db_models import ProjectModel
from app.domain.projects.models import Project


class ProjectRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> List[Project]:
        stmt = select(ProjectModel).order_by(ProjectModel.created_at.desc())
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._to_domain(m) for m in models]

    async def get_by_id(self, project_id: str) -> Optional[Project]:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def get_by_slug(self, slug: str) -> Optional[Project]:
        stmt = select(ProjectModel).where(ProjectModel.slug == slug)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        return self._to_domain(model) if model else None

    async def create(self, name: str, slug: str, github_org: str, github_repo: str, terraform_root: str = "infra", git_adapter: Optional[str] = None, git_config: Optional[dict] = None, execution_adapter: Optional[str] = None, execution_config: Optional[dict] = None) -> Project:
        model = ProjectModel(name=name, slug=slug, github_org=github_org, github_repo=github_repo, terraform_root=terraform_root, git_adapter=git_adapter, git_config=git_config, execution_adapter=execution_adapter, execution_config=execution_config)
        self.db.add(model)
        await self.db.flush()
        return self._to_domain(model)

    async def delete(self, project_id: str) -> bool:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model:
            await self.db.delete(model)
            await self.db.flush()
            return True
        return False

    async def update_config(
        self,
        project_id: str,
        *,
        terraform_root: Optional[str] = None,
        git_adapter: Optional[str] = None,
        git_config: Optional[dict] = None,
        execution_adapter: Optional[str] = None,
        execution_config: Optional[dict] = None,
    ) -> Optional[Project]:
        stmt = select(ProjectModel).where(ProjectModel.id == project_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            return None

        if terraform_root is not None:
            model.terraform_root = terraform_root
        if git_adapter is not None:
            model.git_adapter = git_adapter
        if git_config is not None:
            model.git_config = git_config
        if execution_adapter is not None:
            model.execution_adapter = execution_adapter
        if execution_config is not None:
            model.execution_config = execution_config

        await self.db.flush()
        return self._to_domain(model)

    def _to_domain(self, model: ProjectModel) -> Project:
        return Project(
            id=model.id,
            name=model.name,
            slug=model.slug,
            github_org=model.github_org,
            github_repo=model.github_repo,
            terraform_root=model.terraform_root,
            created_at=model.created_at,
            git_adapter=model.git_adapter,
            git_config=model.git_config,
            execution_adapter=model.execution_adapter,
            execution_config=model.execution_config,
        )
