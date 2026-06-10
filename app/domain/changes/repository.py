import copy
import json
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.changes.service_errors import ValidationError
from app.domain.db_models import ChangeModel, AuditEventModel


class ChangeRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def add(self, project_id: str, change: Dict[str, Any]) -> Dict[str, Any]:
        # Sanitize object_id: keep only last path segment for the ID, strip special chars
        raw_name = (change.get('object_id') or 'unknown').split('/')[-1]
        slug = re.sub(r'[^a-zA-Z0-9_-]', '_', raw_name)[:16]
        change_id = f"chg_{slug}_{id(change) & 0xffffffffffff:012x}"
        stored = copy.deepcopy(change)
        stored["id"] = change_id
        model = ChangeModel(
            id=change_id,
            project_id=project_id,
            object_id=stored.get("object_id", ""),
            change_type=stored.get("change_type", ""),
            status=stored.get("status", "Draft"),
            env=stored.get("env"),
            source_path=stored.get("source_path"),
            yaml_pointer=stored.get("yaml_pointer"),
            scope=stored.get("scope"),
            current_spec=stored.get("current_spec"),
            proposed_spec=stored.get("proposed_spec"),
            artifacts=stored.get("artifacts", {}),
            reason=stored.get("reason", ""),
            created_by=stored.get("created_by", ""),
        )
        self.db.add(model)
        await self.db.flush()
        return stored

    async def get(self, change_id: str) -> Dict[str, Any]:
        stmt = select(ChangeModel).where(ChangeModel.id == change_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValidationError(f"unknown change_id: {change_id}")
        return self._to_dict(model)

    async def update(self, change_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        stmt = select(ChangeModel).where(ChangeModel.id == change_id)
        result = await self.db.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise ValidationError(f"unknown change_id: {change_id}")

        if "artifacts" in updates:
            current_artifacts = {**(model.artifacts or {})}
            current_artifacts.update(updates.pop("artifacts"))
            updates["artifacts"] = current_artifacts

        for key, value in updates.items():
            if hasattr(model, key):
                setattr(model, key, value)
        model.updated_at = None  # trigger onupdate
        await self.db.flush()
        return self._to_dict(model)

    async def list(self, project_id: str = "", filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        stmt = select(ChangeModel)
        if project_id:
            stmt = stmt.where(ChangeModel.project_id == project_id)
        filters = filters or {}
        for key in ("status", "object_id", "env"):
            if filters.get(key):
                stmt = stmt.where(getattr(ChangeModel, key) == filters[key])
        result = await self.db.execute(stmt)
        models = result.scalars().all()
        return [self._to_dict(m) for m in models]

    async def add_audit_event(self, change_id: str, event: Dict[str, Any]) -> Dict[str, Any]:
        model = AuditEventModel(
            change_id=change_id,
            sequence=event.get("sequence", 1),
            event_type=event.get("type", ""),
            actor=event.get("actor", ""),
            message=event.get("message", ""),
            event_metadata=event.get("metadata"),
        )
        self.db.add(model)
        await self.db.flush()
        return event

    async def get_audit_trail(self, change_id: str) -> List[Dict[str, Any]]:
        stmt = select(AuditEventModel).where(AuditEventModel.change_id == change_id).order_by(AuditEventModel.sequence)
        result = await self.db.execute(stmt)
        events = result.scalars().all()
        return [
            {
                "event_id": f"audit_{e.sequence:04d}",
                "sequence": e.sequence,
                "type": e.event_type,
                "actor": e.actor,
                "message": e.message,
                "metadata": e.event_metadata,
            }
            for e in events
        ]

    def _to_dict(self, model: ChangeModel) -> Dict[str, Any]:
        return {
            "id": model.id,
            "object_id": model.object_id,
            "change_type": model.change_type,
            "status": model.status,
            "env": model.env,
            "source_path": model.source_path,
            "yaml_pointer": model.yaml_pointer,
            "scope": model.scope or {},
            "current_spec": model.current_spec or {},
            "proposed_spec": model.proposed_spec or {},
            "artifacts": model.artifacts or {},
            "reason": model.reason or "",
            "created_by": model.created_by or "",
        }
