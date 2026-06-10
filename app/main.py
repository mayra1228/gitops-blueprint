from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from app.api.router import api_router
from app.domain.db_models import (
    ProjectModel,
    ScanRunModel,
    InventoryObjectModel,
    ChangeModel,
    AuditEventModel,
    ScaffoldRunModel,
)
from app.infrastructure.database import engine, Base
from app.ui.page_shell import render_page_html

_ = (ProjectModel, ScanRunModel, InventoryObjectModel, ChangeModel, AuditEventModel, ScaffoldRunModel)


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield


app = FastAPI(
    title="GitOps Platform",
    description="Terraform GitOps Control Plane - K8S Resource Change Management",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "mode": "gitops-platform"}


@app.get("/", response_class=HTMLResponse)
async def index():
    return render_page_html()
