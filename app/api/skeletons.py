from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_infra_registry, get_project_id
from app.domain.skeletons.registry import build_default_skeleton_registry
from app.domain.skeletons.repository import ScaffoldRepository
from app.domain.skeletons.service import SkeletonService
from app.domain.skeletons.validation import ParameterValidator
from app.infrastructure.database import get_db

router = APIRouter()


class SkeletonPreviewRequest(BaseModel):
    template_id: str
    params: dict


class SkeletonApplyRequest(BaseModel):
    template_id: str
    params: dict
    author: str = "sre-user"


class SkeletonValidateParamsRequest(BaseModel):
    template_id: str
    params: dict


def _get_registry():
    return build_default_skeleton_registry()


@router.get("/templates")
async def list_skeleton_templates(
    provider: Optional[str] = Query(None),
    render_mode: Optional[str] = Query(None),
    capability: Optional[str] = Query(None),
    project_id: str = Depends(get_project_id),
):
    registry = _get_registry()
    if provider:
        templates = registry.list_by_provider(provider)
    elif render_mode:
        templates = registry.list_by_render_mode(render_mode)
    elif capability:
        templates = registry.list_by_capability(capability)
    else:
        templates = registry.list_all()
    return {"total": len(templates), "items": [t.to_dict() for t in templates]}


@router.get("/templates/{template_id}")
async def get_skeleton_template(template_id: str, project_id: str = Depends(get_project_id)):
    registry = _get_registry()
    template = registry.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"skeleton template not found: {template_id}")
    return template.to_dict()


@router.post("/preview")
async def preview_skeleton(body: SkeletonPreviewRequest, project_id: str = Depends(get_project_id)):
    registry = _get_registry()
    infra = get_infra_registry()
    svc = SkeletonService(registry, infra)
    try:
        preview = svc.preview(body.template_id, body.params)
        return {"files": preview.files}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/apply")
async def apply_skeleton(
    body: SkeletonApplyRequest,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    registry = _get_registry()
    infra = get_infra_registry()
    svc = SkeletonService(registry, infra, db)
    try:
        result = await svc.apply(body.template_id, body.params, project_id, body.author)
        return {
            "success": result.success,
            "pr_url": result.pr_url,
            "branch": result.branch,
            "commit_sha": result.commit_sha,
            "capability_id": result.capability_id,
            "files": result.preview.files if result.preview else [],
            "error": result.error,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/validate-params")
async def validate_skeleton_params(
    body: SkeletonValidateParamsRequest,
    project_id: str = Depends(get_project_id),
):
    registry = _get_registry()
    template = registry.get(body.template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"skeleton template not found: {body.template_id}")
    validator = ParameterValidator()
    result = validator.validate(template.parameter_schema, body.params)
    return {
        "valid": result.valid,
        "errors": result.errors,
        "template_id": body.template_id,
    }


@router.get("/history")
async def list_scaffold_history(
    limit: int = Query(50),
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    repo = ScaffoldRepository(db)
    items = await repo.list_by_project(project_id, limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/history/all")
async def list_all_scaffold_history(
    limit: int = Query(50),
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    repo = ScaffoldRepository(db)
    items = await repo.list_all(limit=limit)
    return {"items": items, "total": len(items)}


@router.get("/templates/{template_id}/schema")
async def get_skeleton_schema(template_id: str, project_id: str = Depends(get_project_id)):
    registry = _get_registry()
    template = registry.get(template_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"template not found: {template_id}")
    return {
        "template_id": template.id,
        "template_name": template.name,
        "render_mode": template.render_mode,
        "provider": template.provider,
        "capability_id": template.capability_id,
        "parameter_schema": template.parameter_schema,
    }
