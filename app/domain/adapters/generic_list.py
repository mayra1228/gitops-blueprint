from typing import Any, Dict, List

from app.domain.adapters.base import ResourceTypeAdapter
from app.domain.inventory.models import InventoryObject, SourceFile


_METADATA_KEYS = {"version", "platform", "boundary", "component", "env", "name", "region", "city", "clusterID", "namespace"}


class GenericListAdapter(ResourceTypeAdapter):
    resource_type = "generic_list"
    aliases = []
    category = "generic"
    label = "Generic List"

    def supports(self, source: SourceFile, document: Dict[str, Any]) -> bool:
        return any(key not in _METADATA_KEYS and isinstance(value, list) for key, value in document.items())

    def parse_inventory(self, source: SourceFile, document: Dict[str, Any]) -> List[InventoryObject]:
        objects = []
        boundary = document.get("boundary") or source.boundary
        component = document.get("component") or source.component
        env = document.get("env") or source.env
        doc_name = document.get("name") or component
        for key, value in document.items():
            if key in _METADATA_KEYS or not isinstance(value, list):
                continue
            resource_type = f"{boundary}_{key}"
            for index, item in enumerate(value):
                spec = dict(item) if isinstance(item, dict) else {"value": item}
                display_name = str(spec.get("name") or spec.get("alarm_name") or spec.get("serviceName") or f"{key}-{index}")
                objects.append(InventoryObject(
                    id=f"{boundary}/{component}/{env}/{doc_name}/{display_name}",
                    resource_type=resource_type,
                    category=self.category,
                    display_name=display_name,
                    source=source,
                    scope={
                        "boundary": boundary,
                        "component": component,
                        "env": env,
                        "city": document.get("city"),
                        "region": document.get("region"),
                        "namespace": document.get("namespace"),
                    },
                    spec=spec,
                    source_pointer=f"/{key}/{index}",
                ))
        return objects
