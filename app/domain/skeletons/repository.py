from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.db_models import ScaffoldRunModel, _new_id


class ScaffoldRepository:
    """Persistence layer for scaffold/skeleton apply runs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, record_dict: Dict[str, Any]) -> Dict[str, Any]:
        model = ScaffoldRunModel(
            id=_new_id(),
            project_id=record_dict.get("project_id", ""),
            template_id=record_dict.get("template_id", ""),
            template_name=record_dict.get("template_name", ""),
            provider=record_dict.get("provider", ""),
            render_mode=record_dict.get("render_mode", ""),
            capability_id=record_dict.get("capability_id"),
            params=record_dict.get("params", {}),
            author=record_dict.get("author", "ui-user"),
            status=record_dict.get("status", "applied"),
            pr_url=record_dict.get("pr_url"),
            branch=record_dict.get("branch"),
            commit_sha=record_dict.get("commit_sha"),
            files_generated=record_dict.get("files_generated"),
            error_message=record_dict.get("error_message"),
        )
        self.db.add(model)
        await self.db.flush()
        return record_dict

    async def list_by_project(self, project_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        stmt = (
            select(ScaffoldRunModel)
            .where(ScaffoldRunModel.project_id == project_id)
            .order_by(ScaffoldRunModel.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._to_dict(m) for m in models]

    async def list_all(self, limit: int = 50) -> List[Dict[str, Any]]:
        stmt = (
            select(ScaffoldRunModel)
            .order_by(ScaffoldRunModel.created_at.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._to_dict(m) for m in models]

    @staticmethod
    def _to_dict(model: ScaffoldRunModel) -> Dict[str, Any]:
        return {
            "id": model.id,
            "project_id": model.project_id,
            "template_id": model.template_id,
            "template_name": model.template_name,
            "provider": model.provider,
            "render_mode": model.render_mode,
            "capability_id": model.capability_id,
            "params": model.params or {},
            "author": model.author,
            "status": model.status,
            "pr_url": model.pr_url,
            "branch": model.branch,
            "commit_sha": model.commit_sha,
            "files_generated": model.files_generated,
            "error_message": model.error_message,
            "created_at": str(model.created_at) if model.created_at else None,
        }
