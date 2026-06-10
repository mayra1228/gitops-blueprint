from typing import Any, Dict, Iterable, List

from app.domain.adapters.base import ResourceTypeAdapter
from app.domain.inventory.models import InventoryObject, SourceFile


class CloudWatchAlarmAdapter(ResourceTypeAdapter):
    resource_type = "cloudwatch_metric_alarm"
    aliases = []
    category = "alert"
    label = "CloudWatch Metric Alarm"
    _list_keys = {
        "metric_alarm": ("cloudwatch_metric_alarm", "CloudWatch Metric Alarm"),
        "expression_alarm": ("cloudwatch_expression_alarm", "CloudWatch Expression Alarm"),
    }

    def supports(self, source: SourceFile, document: Dict[str, Any]) -> bool:
        return document.get("boundary") == "aws" and document.get("component") == "cloudwatch" and any(
            isinstance(document.get(key), list) for key in self._list_keys
        )

    def parse_inventory(self, source: SourceFile, document: Dict[str, Any]) -> List[InventoryObject]:
        if not self.supports(source, document):
            return []
        objects = []
        for key, (resource_type, _label) in self._list_keys.items():
            for index, alarm in enumerate(document.get(key) or []):
                if not isinstance(alarm, dict):
                    continue
                display_name = alarm.get("alarm_name") or alarm.get("name") or f"{key}-{index}"
                objects.append(InventoryObject(
                    id=f"aws/cloudwatch/{document.get('env')}/{document.get('name', key)}/{display_name}",
                    resource_type=resource_type,
                    category=self.category,
                    display_name=display_name,
                    source=source,
                    scope={
                        "boundary": "aws",
                        "component": "cloudwatch",
                        "env": document.get("env") or source.env,
                        "city": document.get("city"),
                        "region": document.get("region"),
                    },
                    spec=dict(alarm),
                    source_pointer=f"/{key}/{index}",
                ))
        return objects

    def resource_definitions(self) -> Iterable[Dict[str, object]]:
        for resource_type, label in self._list_keys.values():
            yield {"resource_type": resource_type, "category": self.category, "label": label, "aliases": []}
