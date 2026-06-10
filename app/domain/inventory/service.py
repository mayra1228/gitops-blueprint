from typing import Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.adapters.registry import AdapterRegistry
from app.domain.inventory.repository import InventoryRepository
from app.domain.inventory.scanner import InventoryScanner


class InventoryService:
    def __init__(self, db: AsyncSession, project_id: str, registry: AdapterRegistry):
        self.db = db
        self.project_id = project_id
        self.registry = registry

    async def scan(self, root: str, git_ref: str = "local"):
        result = InventoryScanner(self.registry).scan(root, git_ref=git_ref)
        repo = InventoryRepository(self.db)
        await repo.save_scan(self.project_id, result)
        return result

    async def summary(self) -> Dict[str, object]:
        repo = InventoryRepository(self.db)
        scan = await repo.latest_scan(self.project_id)
        summary = scan.summary if scan else {"total_objects": 0, "by_resource_type": {}, "by_env": {}, "errors": 0}
        return {
            "kpis": {
                "total_objects": summary.get("total_objects", 0),
                "resource_types": len(summary.get("by_resource_type", {})),
                "environments": len(summary.get("by_env", {})),
                "errors": summary.get("errors", 0),
            },
            "by_resource_type": summary.get("by_resource_type", {}),
            "by_env": summary.get("by_env", {}),
        }

    async def list_objects(
        self,
        resource_type: str = "",
        env: str = "",
        boundary: str = "",
        component: str = "",
        service_id: str = "",
        namespace: str = "",
        source_path: str = "",
        q: str = "",
        resource_type_prefixes: Optional[List[str]] = None,
    ) -> List[Dict[str, object]]:
        repo = InventoryRepository(self.db)
        items = await repo.objects(self.project_id)
        prefixes = [p for p in (resource_type_prefixes or []) if p]

        def matches(item: dict) -> bool:
            scope = item.get("scope", {})
            source = item.get("source", {})
            if resource_type and item.get("resource_type") != resource_type:
                return False
            if prefixes and not any(str(item.get("resource_type", "")).startswith(prefix) for prefix in prefixes):
                return False
            if env and scope.get("env") != env:
                return False
            if boundary and scope.get("boundary") != boundary and source.get("boundary") != boundary:
                return False
            if component and scope.get("component") != component and source.get("component") != component:
                return False
            if service_id and scope.get("service_id") != service_id:
                return False
            if namespace and scope.get("namespace") != namespace:
                return False
            if source_path and source.get("path") != source_path:
                return False
            if q:
                haystack = f"{item.get('id')} {item.get('display_name')} {item.get('resource_type')}".lower()
                if str(q).lower() not in haystack:
                    return False
            return True

        return [item for item in items if matches(item)]

    async def get_object(self, object_id: str) -> Dict[str, object]:
        repo = InventoryRepository(self.db)
        items = await repo.objects(self.project_id)
        for obj in items:
            if obj["id"] == object_id:
                return obj
        raise KeyError(object_id)
