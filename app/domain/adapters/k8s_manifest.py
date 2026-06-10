from typing import Any, Dict, List

from app.domain.adapters.base import ResourceTypeAdapter
from app.domain.inventory.models import InventoryObject, SourceFile


class K8SManifestAdapter(ResourceTypeAdapter):
    resource_type = "k8s_manifest"
    aliases = ["k8s_configmap", "k8s_deployment", "k8s_hpa", "k8s_service"]
    category = "workload"
    label = "K8s Manifest"

    def supports(self, source: SourceFile, document: Dict[str, Any]) -> bool:
        return "apiVersion" in document and "kind" in document

    def parse_inventory(self, source: SourceFile, document: Dict[str, Any]) -> List[InventoryObject]:
        kind = document.get("kind", "Unknown")
        metadata = document.get("metadata", {})
        name = metadata.get("name", "unknown")
        namespace = metadata.get("namespace", source.env or "default")
        labels = metadata.get("labels", {})

        resource_type = f"k8s_{kind.lower()}"
        scope = {
            "boundary": source.boundary or "k8s",
            "component": source.component or kind.lower(),
            "env": source.env or namespace,
            "namespace": namespace,
            "kind": kind,
        }

        spec = document.get("spec", {})
        data = document.get("data", {})

        return [InventoryObject(
            id=f"{source.boundary}/{kind.lower()}/{namespace}/{name}",
            resource_type=resource_type,
            category=self.category,
            display_name=f"{kind}/{name}",
            source=source,
            scope=scope,
            spec={**spec, **({"data": data} if data else {})},
            labels=labels,
            source_pointer=f"/{kind}/{name}",
        )]

    def resource_definitions(self):
        for kind in ("Deployment", "HPA", "ConfigMap", "Service", "Secret", "Namespace"):
            yield {
                "resource_type": f"k8s_{kind.lower()}",
                "category": self.category,
                "label": f"K8s {kind}",
                "aliases": [],
            }
        yield {
            "resource_type": self.resource_type,
            "category": self.category,
            "label": self.label,
            "aliases": list(self.aliases),
        }
