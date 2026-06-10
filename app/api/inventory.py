from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_project_id
from app.config import settings
from app.domain.adapters.registry import AdapterRegistry, build_default_registry
from app.domain.inventory.service import InventoryService
from app.infrastructure.database import get_db

router = APIRouter()


def _get_registry() -> AdapterRegistry:
    return build_default_registry()


@router.get("/summary")
async def inventory_summary(
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = InventoryService(db, project_id, _get_registry())
    return await svc.summary()


@router.get("/overview")
async def inventory_overview(
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = InventoryService(db, project_id, _get_registry())
    objects = await svc.list_objects()
    resource_types = {}
    envs = {}
    for item in objects:
        rt = item.get("resource_type", "unknown")
        resource_types[rt] = resource_types.get(rt, 0) + 1
        env = (item.get("scope", {}).get("env") or "unknown")
        envs[env] = envs.get(env, 0) + 1
    return {
        "top_resource_types": [{"resource_type": k, "count": v} for k, v in sorted(resource_types.items(), key=lambda x: -x[1])[:12]],
        "env_distribution": [{"env": k, "count": v} for k, v in envs.items()],
    }


@router.get("/objects")
async def list_objects(
    resource_type: Optional[str] = Query(None),
    env: Optional[str] = Query(None),
    boundary: Optional[str] = Query(None),
    component: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
    resource_type_prefix: Optional[str] = Query(None),
    limit: Optional[int] = Query(None, ge=1, le=2000),
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = InventoryService(db, project_id, _get_registry())
    prefixes = [p.strip() for p in (resource_type_prefix or "").split(",") if p.strip()]
    items = await svc.list_objects(
        resource_type=resource_type or "",
        env=env or "",
        boundary=boundary or "",
        component=component or "",
        q=q or "",
        resource_type_prefixes=prefixes,
    )
    if limit is not None:
        items = items[:limit]
    return {"total": len(items), "items": items}


@router.get("/objects/{object_id:path}")
async def get_object(
    object_id: str,
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = InventoryService(db, project_id, _get_registry())
    try:
        return await svc.get_object(object_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"object not found: {object_id}")


@router.post("/scan")
async def scan_inventory(
    project_id: str = Depends(get_project_id),
    db: AsyncSession = Depends(get_db),
):
    svc = InventoryService(db, project_id, _get_registry())

    from app.domain.projects.service import ProjectService
    proj_svc = ProjectService(db)
    project = await proj_svc.get_project(project_id)

    # Support pre-cloned local repo path via git_config["local_path"]
    if project:
        git_config = project.get("git_config") or {}
        local_path = git_config.get("local_path")
        if local_path and Path(local_path).exists():
            result = await svc.scan(local_path, git_ref="local")
            return {
                "status": result.status,
                "summary": result.summary,
                "objects_found": len(result.objects),
                "errors": len(result.errors),
                "git_ref": "local",
            }

    if settings.github_token and project:
        from app.api.deps import get_infra_registry

        infra = get_infra_registry()
        git_adapter = infra.get_git_adapter(project.get("git_adapter", "github"))
        if git_adapter:
            try:
                git_config = project.get("git_config", {})
                repo_path = await git_adapter.ensure_cloned(git_config)
                git_ref = await git_adapter.get_head_sha(git_config)
                result = await svc.scan(str(repo_path), git_ref=git_ref)
                return {
                    "status": result.status,
                    "summary": result.summary,
                    "objects_found": len(result.objects),
                    "errors": len(result.errors),
                    "git_ref": git_ref,
                }
            except Exception:
                pass  # Fall back to demo_data on git failure

    root = settings.demo_data_root or "."
    result = await svc.scan(root)
    return {
        "status": result.status,
        "summary": result.summary,
        "objects_found": len(result.objects),
        "errors": len(result.errors),
    }
