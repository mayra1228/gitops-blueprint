import uuid
from datetime import datetime

from sqlalchemy import Column, String, Integer, DateTime, func, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.infrastructure.database import Base


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class ProjectModel(Base):
    __tablename__ = "projects"

    id = Column(String, primary_key=True, default=_new_id)
    name = Column(String, nullable=False)
    slug = Column(String, nullable=False, unique=True)
    github_org = Column(String, nullable=False)
    github_repo = Column(String, nullable=False)
    terraform_root = Column(String, nullable=False, default="infra")
    git_adapter = Column(String, nullable=True, default=None)
    git_config = Column(JSON, nullable=True, default=None)
    execution_adapter = Column(String, nullable=True, default=None)
    execution_config = Column(JSON, nullable=True, default=None)
    created_at = Column(DateTime, server_default=func.now())


class ScanRunModel(Base):
    __tablename__ = "scan_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)
    summary = Column(JSON, nullable=False)
    errors = Column(JSON, nullable=False)
    scanned_at = Column(DateTime, server_default=func.now())


class InventoryObjectModel(Base):
    __tablename__ = "inventory_objects"

    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=False, index=True)
    object_id = Column(String, nullable=False, index=True)
    resource_type = Column(String, nullable=False)
    category = Column(String, nullable=False)
    display_name = Column(String, nullable=False)
    source_path = Column(String, nullable=False)
    scope = Column(JSON, nullable=False)
    spec = Column(JSON, nullable=False)
    labels = Column(JSON, nullable=False)
    scanned_at = Column(DateTime, server_default=func.now())


class ChangeModel(Base):
    __tablename__ = "changes"

    id = Column(String, primary_key=True)
    project_id = Column(String, nullable=False, index=True)
    object_id = Column(String, nullable=False)
    change_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="Draft")
    env = Column(String, nullable=True)
    source_path = Column(String, nullable=True)
    yaml_pointer = Column(String, nullable=True)
    scope = Column(JSON, nullable=True)
    current_spec = Column(JSON, nullable=True)
    proposed_spec = Column(JSON, nullable=True)
    artifacts = Column(JSON, nullable=True, default=dict)
    reason = Column(String, nullable=True)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    audit_events = relationship("AuditEventModel", back_populates="change", order_by="AuditEventModel.sequence")


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id = Column(Integer, primary_key=True, autoincrement=True)
    change_id = Column(String, ForeignKey("changes.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    event_type = Column(String, nullable=False)
    actor = Column(String, nullable=False)
    message = Column(String, nullable=True)
    event_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    change = relationship("ChangeModel", back_populates="audit_events")


class ScaffoldRunModel(Base):
    __tablename__ = "scaffold_runs"

    id = Column(String, primary_key=True, default=_new_id)
    project_id = Column(String, nullable=False, index=True)
    template_id = Column(String, nullable=False)
    template_name = Column(String, nullable=False)
    provider = Column(String, nullable=False)
    render_mode = Column(String, nullable=False)
    capability_id = Column(String, nullable=True)
    params = Column(JSON, nullable=False)
    author = Column(String, nullable=False, default="ui-user")
    status = Column(String, nullable=False, default="applied")
    pr_url = Column(String, nullable=True)
    branch = Column(String, nullable=True)
    commit_sha = Column(String, nullable=True)
    files_generated = Column(JSON, nullable=True)
    error_message = Column(String, nullable=True)
    created_at = Column(DateTime, server_default=func.now())
