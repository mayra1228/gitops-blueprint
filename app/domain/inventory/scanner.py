from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import yaml

from app.domain.adapters.generic_list import GenericListAdapter
from app.domain.adapters.registry import AdapterRegistry
from app.domain.adapters.terraform_resource import TerraformResourceAdapter
from app.domain.inventory.models import InventoryObject, SourceFile
from app.domain.inventory.schema_linker import infer_schema_path
from app.domain.inventory.terraform_scanner import TerraformFileScanner


@dataclass
class InventoryScanResult:
    status: str
    summary: Dict[str, object]
    objects: List[InventoryObject] = field(default_factory=list)
    errors: List[Dict[str, object]] = field(default_factory=list)



def _build_source(root: Path, path: Path, document: Dict[str, object], git_ref: str = "local") -> SourceFile:
    rel = path.relative_to(root).as_posix()
    parts = Path(rel).parts
    boundary = str(document.get("boundary") or (parts[1] if len(parts) > 1 else ""))
    if boundary == "ODP" and len(parts) > 2:
        component = str(document.get("component") or parts[2])
    elif boundary == "aws" and len(parts) > 4:
        component = str(document.get("component") or parts[4])
    else:
        component = str(document.get("component") or "")
    if boundary == "ODP" and len(parts) > 3:
        env = str(document.get("env") or parts[3])
    elif boundary == "aws" and len(parts) > 3:
        env = str(document.get("env") or parts[3])
    else:
        env = str(document.get("env") or "")
    return SourceFile(
        repo=root.name,
        ref=git_ref,
        path=rel,
        boundary=boundary,
        component=component,
        env=env,
        schema_path=infer_schema_path(rel),
    )



_KNOWN_ENVS = ['dev', 'sit', 'stg', 'uat', 'prf', 'prod', 'sandbox', 'staging', 'production']

def _detect_tf_env(path: str) -> str:
    normalized = path.replace('\\', '/')
    # Check explicit envs/ prefix pattern first
    for env in _KNOWN_ENVS:
        if f'envs/{env}/' in normalized:
            return env
    # Check segment-based pattern: any path segment matching a known env
    for segment in normalized.split('/'):
        if segment in _KNOWN_ENVS:
            return segment
    return 'default'


class InventoryScanner:
    def __init__(self, registry: AdapterRegistry):
        self.registry = registry
        self._last_terraform_errors: List[Dict[str, object]] = []

    def scan(self, root, git_ref: str = "local") -> InventoryScanResult:
        root_path = Path(root)
        objects: List[InventoryObject] = []
        errors: List[Dict[str, object]] = []
        for path in sorted(root_path.glob("infra/**/*.yaml")):
            try:
                document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                if not isinstance(document, dict):
                    continue
                source = _build_source(root_path, path, document, git_ref=git_ref)
                parsed = self._parse_document(source, document)
                objects.extend(parsed)
            except Exception as exc:
                errors.append({"path": path.relative_to(root_path).as_posix(), "message": str(exc)})

        objects.extend(self.scan_terraform(root_path, git_ref=git_ref))
        errors.extend(self._last_terraform_errors)

        by_resource_type = dict(Counter(obj.resource_type for obj in objects))
        by_env = dict(Counter(obj.scope.get("env") for obj in objects if obj.scope.get("env")))
        return InventoryScanResult(
            status="partial" if errors and objects else ("failed" if errors else "success"),
            summary={"total_objects": len(objects), "by_resource_type": by_resource_type, "by_env": by_env, "errors": len(errors)},
            objects=objects,
            errors=errors,
        )

    def scan_terraform(self, root: Path, git_ref: str = "local") -> List[InventoryObject]:
        scanner = TerraformFileScanner()
        adapter = TerraformResourceAdapter()
        scan_result = scanner.scan(root)
        env_layout = {file_info.path: _detect_tf_env(file_info.path) for file_info in scan_result.files}
        objects = adapter.parse_inventory_from_tf_scan(scan_result, root, env_layout)
        for obj in objects:
            obj.source.ref = git_ref
        self._last_terraform_errors = list(scan_result.errors)
        return objects

    def _parse_document(self, source: SourceFile, document: Dict[str, object]) -> List[InventoryObject]:
        generic = None
        for adapter in self.registry.adapters:
            if isinstance(adapter, GenericListAdapter):
                generic = adapter
                continue
            if adapter.supports(source, document):
                return adapter.parse_inventory(source, document)
        if generic and generic.supports(source, document):
            return generic.parse_inventory(source, document)
        return []
