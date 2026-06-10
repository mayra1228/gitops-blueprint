"""Terraform (.tf) file scanner — regex-based HCL block extraction for MVP.

Extracts resource, module, provider, variable, and output blocks from .tf files.
No external HCL parser dependency — uses regex patterns that match standard
Terraform block syntax. Upgradable to python-hcl2 later.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List


@dataclass
class TerraformFileInfo:
    path: str
    resources: List[Dict[str, str]] = field(default_factory=list)
    modules: List[Dict[str, str]] = field(default_factory=list)
    providers: List[str] = field(default_factory=list)
    variables: List[Dict[str, Any]] = field(default_factory=list)
    outputs: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "path": self.path,
            "resources": self.resources,
            "modules": self.modules,
            "providers": self.providers,
            "variables": self.variables,
            "outputs": self.outputs,
        }


@dataclass
class TerraformScanResult:
    status: str
    files: List[TerraformFileInfo] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    errors: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "files": [f.to_dict() for f in self.files],
            "summary": self.summary,
            "errors": self.errors,
        }


# Regex patterns for HCL block extraction
# These match the standard Terraform block syntax: <keyword> "type" "name" { ... }
_RE_RESOURCE = re.compile(
    r'^\s*resource\s+"(?P<type>[^"]+)"\s+"(?P<name>[^"]+)"\s*\{',
    re.MULTILINE,
)
_RE_MODULE = re.compile(
    r'^\s*module\s+"(?P<name>[^"]+)"\s*\{',
    re.MULTILINE,
)
_RE_PROVIDER = re.compile(
    r'^\s*provider\s+"(?P<name>[^"]+)"\s*\{',
    re.MULTILINE,
)
_RE_VARIABLE = re.compile(
    r'^\s*variable\s+"(?P<name>[^"]+)"\s*\{',
    re.MULTILINE,
)
_RE_OUTPUT = re.compile(
    r'^\s*output\s+"(?P<name>[^"]+)"\s*\{',
    re.MULTILINE,
)
_RE_VARIABLE_DEFAULT = re.compile(
    r'^\s*default\s*=\s*(?P<value>.+)',
    re.MULTILINE,
)
_RE_MODULE_SOURCE = re.compile(
    r'^\s*source\s*=\s*"(?P<source>[^"]+)"',
    re.MULTILINE,
)
_RE_PROVIDER_SOURCE = re.compile(
    r'^\s*source\s*=\s*"(?P<source>[^"]+)"',
    re.MULTILINE,
)
_RE_BLOCK_BODY = re.compile(
    r'\{([^}]*(?:\{[^}]*\}[^}]*)*)\}',
    re.DOTALL,
)


def _extract_block_body(text: str, match_end: int) -> str:
    """Extract the body of a block starting after match_end, handling nested braces."""
    depth = 1
    i = match_end
    start = match_end
    while i < len(text) and depth > 0:
        ch = text[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                return text[start:end]
        i += 1
    return ""


class TerraformFileScanner:
    """Scans a directory tree for .tf files and extracts structured metadata."""

    def scan(self, root: str | Path) -> TerraformScanResult:
        root_path = Path(root)
        files: List[TerraformFileInfo] = []
        errors: List[Dict[str, str]] = []

        tf_files = sorted(root_path.glob("**/*.tf"))
        for tf_path in tf_files:
            try:
                content = tf_path.read_text(encoding="utf-8")
                info = self._parse_file(content, tf_path.relative_to(root_path).as_posix())
                if info.resources or info.modules or info.providers or info.variables or info.outputs:
                    files.append(info)
            except Exception as exc:
                errors.append({
                    "path": tf_path.relative_to(root_path).as_posix(),
                    "message": str(exc),
                })

        summary = self._build_summary(files)
        status = "partial" if errors and files else ("failed" if errors and not files else "success")
        return TerraformScanResult(status=status, files=files, summary=summary, errors=errors)

    def _parse_file(self, content: str, rel_path: str) -> TerraformFileInfo:
        info = TerraformFileInfo(path=rel_path)

        info.resources = [
            {"type": m.group("type"), "name": m.group("name")}
            for m in _RE_RESOURCE.finditer(content)
        ]

        info.modules = []
        for m in _RE_MODULE.finditer(content):
            module_name = m.group("name")
            body = _extract_block_body(content, m.end())
            source_match = _RE_MODULE_SOURCE.search(body) if body else None
            info.modules.append({
                "name": module_name,
                "source": source_match.group("source") if source_match else "",
            })

        info.providers = list(set(
            m.group("name") for m in _RE_PROVIDER.finditer(content)
        ))

        info.variables = []
        for m in _RE_VARIABLE.finditer(content):
            var_name = m.group("name")
            body = _extract_block_body(content, m.end())
            default_match = _RE_VARIABLE_DEFAULT.search(body) if body else None
            info.variables.append({
                "name": var_name,
                "default": default_match.group("value").strip().strip('"') if default_match else None,
            })

        info.outputs = [
            {"name": m.group("name")}
            for m in _RE_OUTPUT.finditer(content)
        ]

        return info

    def _build_summary(self, files: List[TerraformFileInfo]) -> Dict[str, Any]:
        all_resources = []
        for f in files:
            for r in f.resources:
                all_resources.append(r["type"])

        resource_types = dict(Counter(all_resources))
        total_modules = sum(len(f.modules) for f in files)
        total_variables = sum(len(f.variables) for f in files)
        total_outputs = sum(len(f.outputs) for f in files)
        all_providers = sorted(set(
            p for f in files for p in f.providers
        ))

        return {
            "total_files": len(files),
            "total_resources": len(all_resources),
            "resource_types": resource_types,
            "total_modules": total_modules,
            "total_variables": total_variables,
            "total_outputs": total_outputs,
            "providers": all_providers,
        }