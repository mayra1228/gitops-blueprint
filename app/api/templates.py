from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_project_id
from app.domain.templates.registry import build_default_template_registry

router = APIRouter()


def _get_registry():
    return build_default_template_registry()


@router.get("")
async def list_templates(
    provider: Optional[str] = Query(None),
    resource_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
    project_id: str = Depends(get_project_id),
):
    registry = _get_registry()
    items = registry.list_templates({
        "provider": provider or "",
        "resource_type": resource_type or "",
        "status": status or "",
        "capability": capability or "",
    })
    return {"total": len(items), "items": items}


@router.get("/{template_id}")
async def get_template(
    template_id: str,
    project_id: str = Depends(get_project_id),
):
    registry = _get_registry()
    template = registry.get_template(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"template not found: {template_id}")
    return template
