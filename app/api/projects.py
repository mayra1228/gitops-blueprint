from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_infra_registry
from app.config import settings
from app.domain.adapters.registry import build_default_registry
from app.domain.imports.service import ProjectImportService, parse_repo_url
from app.domain.projects.service import ProjectService
from app.infrastructure.adapters.registry import InfrastructureAdapterRegistry
from app.infrastructure.database import get_db
from app.infrastructure.git_repo_service import GitRepoService, GitError

router = APIRouter()


class CreateProjectRequest(BaseModel):
    name: str
    github_org: str
    github_repo: str
    terraform_root: str = "infra"
    git_adapter: Optional[str] = None
    git_config: Optional[dict] = None
    execution_adapter: Optional[str] = None
    execution_config: Optional[dict] = None


class ImportProjectRequest(BaseModel):
    repo_url: str
    provider: str = ""
    git_adapter: str = ""
    execution_adapter: str = ""


class RegisterImportRequest(BaseModel):
    project_name: str
    repo_url: str
    provider: str = ""
    git_adapter: str = ""
    execution_adapter: str = ""
    terraform_root: str = "infra"
    workflow_id: str = "terraform-plan-apply.yml"
    cluster_name: str = "kind-gitops-sandbox"


class UpdateProjectConfigRequest(BaseModel):
    terraform_root: Optional[str] = None
    git_adapter: Optional[str] = None
    git_config: Optional[dict] = None
    execution_adapter: Optional[str] = None
    execution_config: Optional[dict] = None


@router.get("")
async def list_projects(db: AsyncSession = Depends(get_db)):
    svc = ProjectService(db)
    projects = await svc.list_projects()
    return {"total": len(projects), "items": projects}


@router.post("")
async def create_project(body: CreateProjectRequest, db: AsyncSession = Depends(get_db)):
    svc = ProjectService(db)
    try:
        project = await svc.create_project(
            name=body.name,
            github_org=body.github_org,
            github_repo=body.github_repo,
            terraform_root=body.terraform_root,
            git_adapter=body.git_adapter,
            git_config=body.git_config,
            execution_adapter=body.execution_adapter,
            execution_config=body.execution_config,
        )
        return project
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}")
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = ProjectService(db)
    project = await svc.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.delete("/{project_id}")
async def delete_project(project_id: str, db: AsyncSession = Depends(get_db)):
    svc = ProjectService(db)
    deleted = await svc.delete_project(project_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="project not found")
    return {"status": "deleted"}


@router.put("/{project_id}")
async def update_project_config(
    project_id: str,
    body: UpdateProjectConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = ProjectService(db)
    updated = await svc.update_project_config(
        project_id,
        terraform_root=body.terraform_root,
        git_adapter=body.git_adapter,
        git_config=body.git_config,
        execution_adapter=body.execution_adapter,
        execution_config=body.execution_config,
    )
    if not updated:
        raise HTTPException(status_code=404, detail="project not found")
    return updated


def _build_import_service(db: AsyncSession, registry: InfrastructureAdapterRegistry) -> ProjectImportService:
    git_service = GitRepoService(
        storage_root=settings.repo_storage_root,
        github_token=settings.github_token,
    )
    domain_registry = build_default_registry()
    return ProjectImportService(
        db=db,
        git_service=git_service,
        infra_registry=registry,
        domain_registry=domain_registry,
    )


@router.post("/import")
async def import_project_discover(
    body: ImportProjectRequest,
    db: AsyncSession = Depends(get_db),
    registry: InfrastructureAdapterRegistry = Depends(get_infra_registry),
):
    """Step 1→2: Connect & Discover — clone repo and scan for IaC files."""
    svc = _build_import_service(db, registry)
    try:
        result = await svc.discover(body.repo_url, body.provider)
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GitError as e:
        raise HTTPException(status_code=502, detail=str(e))


@router.post("/import/register")
async def import_project_register(
    body: RegisterImportRequest,
    db: AsyncSession = Depends(get_db),
    registry: InfrastructureAdapterRegistry = Depends(get_infra_registry),
):
    """Step 3→4: Register — create project and persist inventory scan."""
    svc = _build_import_service(db, registry)
    try:
        result = await svc.register(
            project_name=body.project_name,
            repo_url=body.repo_url,
            provider=body.provider,
            git_adapter=body.git_adapter,
            execution_adapter=body.execution_adapter,
            terraform_root=body.terraform_root,
            execution_config={
                "workflow_id": body.workflow_id,
                "cluster_name": body.cluster_name,
            },
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except GitError as e:
        raise HTTPException(status_code=502, detail=str(e))
