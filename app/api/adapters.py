from fastapi import APIRouter, Depends

from app.api.deps import get_project_id
from app.domain.adapters.registry import build_default_registry

router = APIRouter()


@router.get("")
async def list_adapters(project_id: str = Depends(get_project_id)):
    registry = build_default_registry()
    return {"items": registry.list_types()}
