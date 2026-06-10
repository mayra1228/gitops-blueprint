from typing import Any, Dict, Iterable, List


class ResourceTypeAdapter:
    resource_type = "generic"
    aliases: List[str] = []
    category = "generic"
    label = "Generic"

    def supports(self, source, document: Dict[str, Any]) -> bool:
        return False

    def parse_inventory(self, source, document: Dict[str, Any]) -> List[Any]:
        return []

    def resource_definitions(self) -> Iterable[Dict[str, Any]]:
        yield {
            "resource_type": self.resource_type,
            "category": self.category,
            "label": self.label,
            "aliases": list(self.aliases),
        }
