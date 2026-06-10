from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.adapters.registry import AdapterRegistry
from app.infrastructure.adapters.registry import InfrastructureAdapterRegistry, build_default_infra_registry
from app.infrastructure.database import get_db

_infra_registry: InfrastructureAdapterRegistry | None = None


def get_infra_registry() -> InfrastructureAdapterRegistry:
    global _infra_registry
    if _infra_registry is None:
        _infra_registry = build_default_infra_registry()
    return _infra_registry


async def get_current_user(
    x_user: Optional[str] = Header(None, alias="X-User"),
) -> str:
    return x_user or "anonymous"


async def get_project_id(request: Request) -> str:
    project_id = request.path_params.get("project_id", "")
    if not project_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="project_id required")
    return project_id
