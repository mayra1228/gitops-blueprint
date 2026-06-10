from typing import Any, Dict, Iterable, List

from app.domain.adapters.base import ResourceTypeAdapter


class AdapterRegistry:
    def __init__(self, adapters: Iterable[ResourceTypeAdapter]):
        self.adapters = list(adapters)
        self._by_name: Dict[str, ResourceTypeAdapter] = {}
        for adapter in self.adapters:
            self._by_name[adapter.resource_type] = adapter
            for alias in getattr(adapter, "aliases", []):
                self._by_name[alias] = adapter
            for definition in adapter.resource_definitions():
                self._by_name.setdefault(definition["resource_type"], adapter)

    def get(self, name: str) -> ResourceTypeAdapter | None:
        return self._by_name.get(name)

    def list_types(self) -> List[Dict[str, object]]:
        items = []
        seen = set()
        for adapter in self.adapters:
            for definition in adapter.resource_definitions():
                resource_type = definition["resource_type"]
                if resource_type not in seen:
                    seen.add(resource_type)
                    items.append(definition)
        return items



def build_default_registry() -> AdapterRegistry:
    from app.domain.adapters.cloudwatch_alarm import CloudWatchAlarmAdapter
    from app.domain.adapters.generic_list import GenericListAdapter
    from app.domain.adapters.hype_level import HypeLevelAdapter
    from app.domain.adapters.k8s_manifest import K8SManifestAdapter
    from app.domain.adapters.odp_resource import ODPResourceAdapter
    from app.domain.adapters.terraform_resource import TerraformResourceAdapter

    return AdapterRegistry([
        TerraformResourceAdapter(),
        ODPResourceAdapter(),
        HypeLevelAdapter(),
        CloudWatchAlarmAdapter(),
        K8SManifestAdapter(),
        GenericListAdapter(),
    ])
