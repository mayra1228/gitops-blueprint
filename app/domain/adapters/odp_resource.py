from typing import Any, Dict, List

from app.domain.adapters.base import ResourceTypeAdapter
from app.domain.inventory.models import InventoryObject, SourceFile


class ODPResourceAdapter(ResourceTypeAdapter):
    resource_type = "k8s_service"
    aliases = ["odp_service"]
    category = "workload"
    label = "K8s Service"

    def supports(self, source: SourceFile, document: Dict[str, Any]) -> bool:
        return document.get("boundary") == "ODP" and document.get("component") == "resources" and isinstance(document.get("services"), list)

    def parse_inventory(self, source: SourceFile, document: Dict[str, Any]) -> List[InventoryObject]:
        if not self.supports(source, document):
            return []
        objects = []
        env = document.get("env") or source.env
        name = document.get("name") or "unknown"
        for index, service in enumerate(document.get("services", [])):
            if not isinstance(service, dict):
                continue
            service_name = service.get("serviceName") or service.get("name") or f"service-{index}"
            objects.append(InventoryObject(
                id=f"ODP/resources/{env}/{name}/{service_name}",
                resource_type=self.resource_type,
                category=self.category,
                display_name=service_name,
                source=source,
                scope={
                    "boundary": "ODP",
                    "component": "resources",
                    "env": env,
                    "cluster_id": document.get("clusterID"),
                    "namespace": document.get("namespace"),
                    "service_id": name,
                },
                spec=dict(service),
                source_pointer=f"/services/{index}",
            ))
        return objects
