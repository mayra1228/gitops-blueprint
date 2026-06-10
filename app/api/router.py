from fastapi import APIRouter

from app.api import auth, projects, inventory, changes, templates, adapters, skeletons, github, bitbucket, gitlab, infra_adapters

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/api/auth", tags=["auth"])
api_router.include_router(projects.router, prefix="/api/projects", tags=["projects"])
api_router.include_router(inventory.router, prefix="/api/{project_id}/inventory", tags=["inventory"])
api_router.include_router(changes.router, prefix="/api/{project_id}/changes", tags=["changes"])
api_router.include_router(templates.router, prefix="/api/{project_id}/templates", tags=["templates"])
api_router.include_router(skeletons.router, prefix="/api/{project_id}/skeletons", tags=["skeletons"])
api_router.include_router(adapters.router, prefix="/api/{project_id}/adapters", tags=["adapters"])
api_router.include_router(github.router, prefix="/api/webhooks/github", tags=["webhooks"])
api_router.include_router(bitbucket.router, prefix="/api/webhooks/bitbucket", tags=["webhooks"])
api_router.include_router(gitlab.router, prefix="/api/webhooks/gitlab", tags=["webhooks"])
api_router.include_router(infra_adapters.router, prefix="/api/infrastructure-adapters", tags=["infrastructure-adapters"])
