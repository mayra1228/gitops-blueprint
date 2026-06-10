import json
from typing import List

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.db_models import ScanRunModel, InventoryObjectModel
from app.domain.inventory.scanner import InventoryScanResult


class InventoryRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_scan(self, project_id: str, result: InventoryScanResult) -> None:
        # Delete old objects for this project before inserting new ones
        await self.db.execute(delete(InventoryObjectModel).where(InventoryObjectModel.project_id == project_id))

        scan_run = ScanRunModel(
            project_id=project_id,
            status=result.status,
            summary=result.summary,
            errors=result.errors,
        )
        self.db.add(scan_run)

        for inv_obj in result.objects:
            db_obj = InventoryObjectModel(
                project_id=project_id,
                object_id=inv_obj.id,
                resource_type=inv_obj.resource_type,
                category=inv_obj.category,
                display_name=inv_obj.display_name,
                source_path=inv_obj.source.path,
                scope=inv_obj.scope,
                spec=inv_obj.spec,
                labels=inv_obj.labels,
            )
            self.db.add(db_obj)

    async def latest_scan(self, project_id: str) -> InventoryScanResult | None:
        stmt = select(ScanRunModel).where(ScanRunModel.project_id == project_id).order_by(ScanRunModel.scanned_at.desc()).limit(1)
        result = await self.db.execute(stmt)
        row = result.scalar_one_or_none()
        if row is None:
            return None
        return InventoryScanResult(
            status=row.status,
            summary=row.summary,
            errors=row.errors or [],
        )

    async def objects(self, project_id: str) -> List[dict]:
        stmt = select(InventoryObjectModel).where(InventoryObjectModel.project_id == project_id)
        result = await self.db.execute(stmt)
        rows = result.scalars().all()
        return [
            {
                "id": row.object_id,
                "resource_type": row.resource_type,
                "category": row.category,
                "display_name": row.display_name,
                "source": {"path": row.source_path},
                "scope": row.scope or {},
                "spec": row.spec or {},
                "labels": row.labels or {},
            }
            for row in rows
        ]
