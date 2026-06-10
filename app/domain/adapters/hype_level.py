from typing import Any, Dict, List

from app.domain.adapters.base import ResourceTypeAdapter
from app.domain.inventory.models import InventoryObject, SourceFile


class HypeLevelAdapter(ResourceTypeAdapter):
    resource_type = "k8s_hype_profile"
    aliases = ["odp_hype_level"]
    category = "capacity"
    label = "K8s Hype Level Profile"

    def supports(self, source: SourceFile, document: Dict[str, Any]) -> bool:
        return document.get("boundary") == "ODP" and document.get("component") == "hypelevel" and isinstance(document.get("services"), list)

    def parse_inventory(self, source: SourceFile, document: Dict[str, Any]) -> List[InventoryObject]:
        if not self.supports(source, document):
            return []
        objects = []
        profile_name = document.get("name") or "unknown"
        for index, service in enumerate(document.get("services", [])):
            if not isinstance(service, dict):
                continue
            service_name = service.get("serviceName") or service.get("name") or f"service-{index}"
            objects.append(InventoryObject(
                id=f"ODP/hypelevel/{profile_name}/{service_name}",
                resource_type=self.resource_type,
                category=self.category,
                display_name=service_name,
                source=source,
                scope={
                    "boundary": "ODP",
                    "component": "hypelevel",
                    "profile": profile_name,
                    "cluster_id": document.get("clusterID"),
                    "namespace": document.get("namespace"),
                    "current_level": document.get("currentLevel"),
                },
                spec=dict(service),
                source_pointer=f"/services/{index}",
            ))
        return objects
