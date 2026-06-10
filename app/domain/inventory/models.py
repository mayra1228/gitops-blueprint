from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


_SENSITIVE_KEY_PARTS = ("password", "secret", "token", "access_key", "secret_key")


def _redact_sensitive(value: Any, key: str = "") -> Any:
    if isinstance(value, dict):
        return {item_key: _redact_sensitive(item_value, item_key) for item_key, item_value in value.items()}
    if isinstance(value, list):
        return [_redact_sensitive(item) for item in value]
    lowered = key.lower()
    if any(part in lowered for part in _SENSITIVE_KEY_PARTS):
        return "[REDACTED]"
    return value


@dataclass
class SourceFile:
    repo: str
    ref: str
    path: str
    boundary: str
    component: str
    env: str
    schema_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class InventoryObject:
    id: str
    resource_type: str
    category: str
    display_name: str
    source: SourceFile
    scope: Dict[str, Any] = field(default_factory=dict)
    spec: Dict[str, Any] = field(default_factory=dict)
    labels: Dict[str, str] = field(default_factory=dict)
    relationships: List[Dict[str, Any]] = field(default_factory=list)
    source_pointer: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["spec"] = _redact_sensitive(data.get("spec", {}))
        return data


@dataclass
class InventoryScanRun:
    status: str
    summary: Dict[str, Any]
    errors: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class ResourceTypeDefinition:
    resource_type: str
    category: str
    label: str
    aliases: List[str] = field(default_factory=list)
