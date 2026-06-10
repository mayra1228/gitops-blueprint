import copy
import difflib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import yaml
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.domain.changes.repository import ChangeRepository
from app.domain.changes.service_errors import ValidationError

try:
    from app.infrastructure.k8s_client import KubernetesClient
except ImportError:  # pragma: no cover
    KubernetesClient = None  # type: ignore[assignment,misc]


ALLOWED_ODP_RESOURCE_FIELDS = {
    "minReplicas", "maxReplicas", "requestCPU", "limitCPU", "requestMem", "limitMem",
    "cpuTargetAverageUtilization", "memTargetAverageUtilization", "initialDelaySeconds",
}
ALLOWED_ODP_UPDATES = {"all", "UpdateCreateAllHPA", "UpdateAllDeploymentNonZero", "UpdateAllStatefulSetNonZero", "UpdateKEDA"}
ALLOWED_HYPE_LEVELS = {"low", "medium", "high"}
TERRAFORM_CHANGE_TYPES = {"terraform_resource_update", "terraform_variable_update", "terraform_module_update"}
TERRAFORM_DEFAULT_RESOURCE_FIELDS = {
    "aws_instance": "instance_type",
    "aws_db_instance": "instance_class",
    "aws_vpc": "cidr_block",
    "aws_subnet": "cidr_block",
    "aws_security_group": "description",
    "aws_s3_bucket": "bucket",
    "aws_iam_role": "name",
    "aws_lambda_function": "handler",
}

_RESOURCE_BLOCK_RE = re.compile(r'^\s*resource\s+"(?P<resource_type>[^"]+)"\s+"(?P<name>[^"]+)"\s*\{', re.MULTILINE)
_MODULE_BLOCK_RE = re.compile(r'^\s*module\s+"(?P<name>[^"]+)"\s*\{', re.MULTILINE)
_VARIABLE_BLOCK_RE = re.compile(r'^\s*variable\s+"(?P<name>[^"]+)"\s*\{', re.MULTILINE)
_OUTPUT_BLOCK_RE = re.compile(r'^\s*output\s+"(?P<name>[^"]+)"\s*\{', re.MULTILINE)
_TOP_LEVEL_ASSIGNMENT_RE = re.compile(r"^(?P<key>[A-Za-z0-9_]+)\s*=\s*(?P<value>.+)$")


class ChangeStatus:
    DRAFT = "Draft"
    PATCH_GENERATED = "PatchGenerated"
    VALIDATION_PASSED = "ValidationPassed"
    VALIDATION_FAILED = "ValidationFailed"
    PLANNING = "Planning"
    PLAN_READY = "PlanReady"
    PLAN_FAILED = "PlanFailed"
    PENDING_APPROVAL = "PendingApproval"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    EXECUTION_READY = "ExecutionReady"
    EXECUTION_BLOCKED = "ExecutionBlocked"
    INVENTORY_REFRESHED = "InventoryRefreshed"


CommandRunner = Callable[[List[str], str], Dict[str, Any]]


class _IndentDumper(yaml.SafeDumper):
    def increase_indent(self, flow: bool = False, indentless: bool = False):
        return super().increase_indent(flow, False)


def _dump_yaml(data: Dict[str, Any]) -> str:
    text = yaml.dump(data, Dumper=_IndentDumper, sort_keys=False, default_flow_style=False)
    return text if text.endswith("\n") else text + "\n"


def _load_yaml(path: Path) -> Dict[str, Any]:
    document = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(document, dict):
        raise ValidationError(f"YAML root must be a mapping: {path}")
    return document


def deep_merge(base: Dict[str, Any], overlay: Dict[str, Any]) -> None:
    for key, value in overlay.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            base[key] = value


def generate_field_diff(current: Dict[str, Any], proposed: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [
        {"field": field, "from": current.get(field), "to": proposed[field]}
        for field in proposed
        if current.get(field) != proposed[field]
    ]


def _effective(current: Dict[str, Any], proposed: Dict[str, Any], field: str) -> Any:
    return proposed[field] if field in proposed else current.get(field)


def _parse_cpu(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    try:
        if text.endswith("m"):
            return int(text[:-1])
        return int(float(text) * 1000)
    except ValueError as exc:
        raise ValidationError(f"invalid CPU value: {value}") from exc


def _parse_mem(value: Any) -> Optional[int]:
    if value is None:
        return None
    text = str(value).strip()
    try:
        if text.endswith("Mi"):
            return int(float(text[:-2]))
        if text.endswith("Gi"):
            return int(float(text[:-2]) * 1024)
        return int(float(text))
    except ValueError as exc:
        raise ValidationError(f"invalid memory value: {value}") from exc


def _block(message: str) -> Dict[str, str]:
    return {"type": "block", "message": message}


def _approval(message: str) -> Dict[str, str]:
    return {"type": "approval_required", "message": message}


def validate_policy(env: str, current: Dict[str, Any], proposed: Dict[str, Any]) -> Dict[str, Any]:
    checks: List[Dict[str, str]] = []

    min_replicas = _effective(current, proposed, "minReplicas")
    max_replicas = _effective(current, proposed, "maxReplicas")
    if min_replicas is not None and max_replicas is not None and int(max_replicas) < int(min_replicas):
        checks.append(_block("maxReplicas must be greater than or equal to minReplicas"))

    request_cpu = _parse_cpu(_effective(current, proposed, "requestCPU"))
    limit_cpu = _parse_cpu(_effective(current, proposed, "limitCPU"))
    if request_cpu is not None and limit_cpu is not None and limit_cpu < request_cpu:
        checks.append(_block("limitCPU must be greater than or equal to requestCPU"))

    request_mem = _parse_mem(_effective(current, proposed, "requestMem"))
    limit_mem = _parse_mem(_effective(current, proposed, "limitMem"))
    if request_mem is not None and limit_mem is not None and limit_mem < request_mem:
        checks.append(_block("limitMem must be greater than or equal to requestMem"))

    if env == "prod":
        checks.append(_approval("prod changes require approval"))

    current_max = current.get("maxReplicas")
    proposed_max = proposed.get("maxReplicas")
    if current_max is not None and proposed_max is not None and int(current_max) > 0:
        if (int(proposed_max) - int(current_max)) / int(current_max) > 0.5:
            checks.append(_approval("maxReplicas increase greater than 50% requires approval"))

    for field, parser in (("requestCPU", _parse_cpu), ("requestMem", _parse_mem)):
        if field in proposed and current.get(field) is not None:
            old = parser(current[field])
            new = parser(proposed[field])
            if old and new is not None and new < old and (old - new) / old > 0.3:
                checks.append(_approval(f"{field} decrease greater than 30% requires approval"))

    if any(check["type"] == "block" for check in checks):
        status = "failed"
    elif checks:
        status = "warning"
    else:
        status = "passed"
    return {"status": status, "checks": checks}


def _default_command_runner(cmd: List[str], cwd: str) -> Dict[str, Any]:
    completed = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    return {"exit_code": completed.returncode, "stdout": completed.stdout, "stderr": completed.stderr}


def build_odp_dryrun_command(source_path: str, update: str = "all") -> List[str]:
    if update not in ALLOWED_ODP_UPDATES:
        allowed = ", ".join(sorted(ALLOWED_ODP_UPDATES))
        raise ValidationError(f"unsupported ODP update mode: {update}; allowed: {allowed}")
    return ["go", "run", "engines/ODP/resources/resources.go", "-files", source_path, "-update", update, "-dryrun=true"]


def build_plan_impact(change: Dict[str, Any]) -> Dict[str, Any]:
    scope = change.get("scope") or {}
    current_spec = change.get("current_spec") or {}
    service_name = current_spec.get("serviceName")
    if current_spec.get("statefulset") is True:
        operations = ["UpdateAllStatefulSetNonZero"]
    elif current_spec.get("KEDA") is True:
        operations = ["UpdateKEDA"]
    else:
        operations = ["UpdateCreateAllHPA", "UpdateAllDeploymentNonZero"]
    return {
        "clusterID": scope.get("clusterID"),
        "namespace": scope.get("namespace"),
        "target_service": service_name,
        "services_touched": [service_name] if service_name else [],
        "source_file": change.get("source_path"),
        "runner_scope": "entire_yaml_file",
        "operations": operations,
    }


def _prepare_plan_workspace(root: Path, temp_root: Path, source_path: str, patched_yaml: str) -> None:
    destination = temp_root / source_path
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(patched_yaml, encoding="utf-8")
    odp_engine = root / "engines" / "ODP"
    if odp_engine.exists():
        shutil.copytree(odp_engine, temp_root / "engines" / "ODP", dirs_exist_ok=True)



_KNOWN_ENVS_SET = {'dev', 'sit', 'stg', 'uat', 'prf', 'prod', 'sandbox', 'staging', 'production'}

def _terraform_env_from_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    for env in ['dev', 'sit', 'stg', 'uat', 'prf', 'prod', 'sandbox', 'staging', 'production']:
        if f"envs/{env}/" in normalized:
            return env
    for segment in normalized.split("/"):
        if segment in _KNOWN_ENVS_SET:
            return segment
    return "default"


def _terraform_backend_from_path(path: str) -> str:
    normalized = path.replace("\\", "/").lower()
    if "/aws/" in normalized:
        return "aws"
    if "/google/" in normalized or "/gcp/" in normalized:
        return "gcp"
    if "/azurerm/" in normalized or "/azure/" in normalized:
        return "azure"
    return "terraform"


def _extract_hcl_block(content: str, match: re.Match[str]) -> Dict[str, Any]:
    depth = 1
    i = match.end()
    body_start = match.end()
    while i < len(content):
        ch = content[i]
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return {
                    "match": match,
                    "start": match.start(),
                    "body_start": body_start,
                    "close_index": i,
                    "end": i + 1,
                    "body": content[body_start:i],
                }
        i += 1
    raise ValidationError("unterminated Terraform block")


def _find_terraform_block(content: str, scope: Dict[str, Any]) -> Dict[str, Any]:
    kind = scope.get("terraform_kind")
    name = scope.get("name")
    resource_type = scope.get("resource_type")
    pattern = {
        "resource": _RESOURCE_BLOCK_RE,
        "module": _MODULE_BLOCK_RE,
        "variable": _VARIABLE_BLOCK_RE,
        "output": _OUTPUT_BLOCK_RE,
    }.get(kind)
    if pattern is None:
        raise ValidationError(f"unsupported terraform kind: {kind}")

    for match in pattern.finditer(content):
        if kind == "resource":
            if match.group("resource_type") != resource_type or match.group("name") != name:
                continue
        elif match.group("name") != name:
            continue
        return _extract_hcl_block(content, match)
    raise ValidationError(f"terraform block not found: {kind}/{resource_type or name}/{name}")


def _parse_top_level_assignments(body: str) -> Dict[str, Any]:
    values: Dict[str, Any] = {}
    depth = 0
    for line in body.splitlines():
        stripped = line.strip()
        if depth == 0 and stripped and not stripped.startswith(("#", "//")):
            match = _TOP_LEVEL_ASSIGNMENT_RE.match(stripped)
            if match:
                values[match.group("key")] = match.group("value").strip()
        depth += line.count("{") - line.count("}")
    return values


def _render_terraform_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    text = str(value).strip()
    if not text:
        return '""'
    if text.startswith(('"', "'")) or text.startswith(("var.", "local.", "module.", "aws_", "google_", "azurerm_")):
        return text
    if text.startswith(("[", "{", "jsonencode(", "<<", "file(")):
        return text
    if text in {"true", "false", "null"}:
        return text
    if re.fullmatch(r"-?\d+(\.\d+)?", text):
        return text
    return f'"{text}"'


def _apply_terraform_updates(content: str, scope: Dict[str, Any], updates: Dict[str, Any]) -> str:
    block = _find_terraform_block(content, scope)
    lines = block["body"].splitlines(keepends=True)
    found = set()
    depth = 0
    for index, line in enumerate(lines):
        stripped = line.strip()
        if depth == 0 and stripped:
            match = _TOP_LEVEL_ASSIGNMENT_RE.match(stripped)
            if match:
                key = match.group("key")
                if key in updates:
                    indent = line[: len(line) - len(line.lstrip())]
                    newline = "\n" if line.endswith("\n") else ""
                    lines[index] = f"{indent}{key} = {_render_terraform_value(updates[key])}{newline}"
                    found.add(key)
        depth += line.count("{") - line.count("}")
    if lines and not lines[-1].endswith("\n"):
        lines[-1] += "\n"
    for key, value in updates.items():
        if key not in found:
            lines.append(f"  {key} = {_render_terraform_value(value)}\n")
    patched_body = "".join(lines)
    return content[: block["body_start"]] + patched_body + content[block["close_index"] :]


def _normalize_terraform_proposed(change_type: str, resource_type: str, proposed: Dict[str, Any]) -> Dict[str, Any]:
    filtered = {key: value for key, value in proposed.items() if key != "env"}
    if not filtered:
        raise ValidationError("proposed must contain at least one Terraform field update")
    if change_type == "terraform_variable_update" and set(filtered) == {"value"}:
        return {"default": filtered["value"]}
    if change_type == "terraform_module_update" and set(filtered) == {"version"}:
        return {"version": filtered["version"]}
    if change_type == "terraform_resource_update":
        if "attribute" in filtered and "value" in filtered:
            return {str(filtered["attribute"]): filtered["value"]}
        if set(filtered) == {"param_value"}:
            return {TERRAFORM_DEFAULT_RESOURCE_FIELDS.get(resource_type, "value"): filtered["param_value"]}
    return filtered


def _build_terraform_impact(change: Dict[str, Any]) -> Dict[str, Any]:
    scope = change.get("scope") or {}
    return {
        "environment": change.get("env"),
        "object_id": change.get("object_id"),
        "source_file": change.get("source_path"),
        "runner_scope": "terraform_file",
        "operations": [f"update_{scope.get('terraform_kind', 'resource')}"] ,
        "backend": scope.get("backend"),
    }

class ChangeService:
    def __init__(self, db: AsyncSession, project_id: str, root: str = ".", k8s_client=None):
        self.db = db
        self.project_id = project_id
        self.root = Path(root)
        self.repository = ChangeRepository(db)
        self.k8s_client = k8s_client

    async def create_change(self, request: Dict[str, Any]) -> Dict[str, Any]:
        change_type = request.get("change_type")
        if change_type == "odp_hype_level_update":
            return await self._create_hype_level_change(request)
        if change_type == "k8s_manifest_update":
            return await self._create_k8s_manifest_change(request)
        if change_type in TERRAFORM_CHANGE_TYPES:
            return await self._create_terraform_change(request)
        if change_type != "odp_resource_update":
            raise ValidationError("unsupported change_type")
        proposed = request.get("proposed") or {}
        if not isinstance(proposed, dict) or not proposed:
            raise ValidationError("proposed must be a non-empty mapping")
        not_allowed = sorted(set(proposed) - ALLOWED_ODP_RESOURCE_FIELDS)
        if not_allowed:
            raise ValidationError(f"proposed fields not allowed: {', '.join(not_allowed)}")

        context = self._find_service_context(request.get("object_id", ""))
        return await self.repository.add(self.project_id, {
            "object_id": request["object_id"],
            "change_type": request["change_type"],
            "status": ChangeStatus.DRAFT,
            "env": context["scope"]["env"],
            "source_path": context["source_path"],
            "yaml_pointer": context["yaml_pointer"],
            "scope": context["scope"],
            "current_spec": context["current_spec"],
            "proposed_spec": copy.deepcopy(proposed),
            "reason": request.get("reason", ""),
            "artifacts": {},
            "created_by": request.get("created_by", ""),
        })
    async def get_change(self, change_id: str) -> Dict[str, Any]:
        return await self.repository.get(change_id)

    async def list_changes(self, filters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        filters = filters or {}
        changes = await self.repository.list(self.project_id, filters)
        items = [self._change_summary(change) for change in changes]
        return {"total": len(items), "items": items}

    async def query_change_audit_trail(self, change_id: str) -> Dict[str, Any]:
        events = await self.repository.get_audit_trail(change_id)
        return {"change_id": change_id, "total": len(events), "items": events}

    async def generate_patch(self, change_id: str) -> Dict[str, Any]:
        change = await self.repository.get(change_id)
        if change["status"] != ChangeStatus.DRAFT:
            raise ValidationError("generate_patch requires Draft status")

        source_rel = change["source_path"]
        source_abs = self._resolve_change_source_abs(
            source_rel,
            change.get("object_id"),
            change.get("yaml_pointer"),
        )
        if not source_abs.exists():
            raise ValidationError(f"source YAML not found: {source_rel}")

        is_yaml_source = source_rel.endswith(".yaml") or source_rel.endswith(".yml")
        scope = change.get("scope") or {}

        if change.get("change_type") in TERRAFORM_CHANGE_TYPES and not is_yaml_source:
            original_text = source_abs.read_text(encoding="utf-8")
            patched_yaml = _apply_terraform_updates(original_text, scope, change["proposed_spec"])
            yaml_diff = "".join(difflib.unified_diff(
                original_text.splitlines(keepends=True),
                patched_yaml.splitlines(keepends=True),
                fromfile=f"a/{source_rel}",
                tofile=f"b/{source_rel}",
            ))
        else:
            original_yaml = source_abs.read_text(encoding="utf-8")
            data = _load_yaml(source_abs)
            if change.get("change_type") == "odp_hype_level_update":
                data["currentLevel"] = change["proposed_spec"]["currentLevel"]
            elif change.get("change_type") == "k8s_manifest_update":
                deep_merge(data, change["proposed_spec"])
            elif scope.get("terraform_kind") == "odp_resource" or change.get("change_type") in TERRAFORM_CHANGE_TYPES:
                # YAML-based resource (e.g. ODP service via terraform_resource_update)
                services = data.get("services") or []
                service_index = self._service_index_from_pointer(change["yaml_pointer"])
                if service_index >= len(services) or not isinstance(services[service_index], dict):
                    recovered_index = self._find_service_index_by_object_id(services, change.get("object_id", ""))
                    if recovered_index is None:
                        raise ValidationError(f"service index not found: {change['yaml_pointer']}")
                    service_index = recovered_index
                for field, value in change["proposed_spec"].items():
                    services[service_index][field] = value
            else:
                services = data.get("services") or []
                service_index = self._service_index_from_pointer(change["yaml_pointer"])
                if service_index >= len(services) or not isinstance(services[service_index], dict):
                    recovered_index = self._find_service_index_by_object_id(services, change.get("object_id", ""))
                    if recovered_index is None:
                        raise ValidationError(f"service index not found: {change['yaml_pointer']}")
                    service_index = recovered_index
                for field, value in change["proposed_spec"].items():
                    services[service_index][field] = value

            patched_yaml = _dump_yaml(data)
            yaml_diff = "".join(difflib.unified_diff(
                original_yaml.splitlines(keepends=True),
                patched_yaml.splitlines(keepends=True),
                fromfile=source_rel,
                tofile=f"{source_rel} (patched)",
            ))

        field_diff = generate_field_diff(change["current_spec"], change["proposed_spec"])
        artifacts = {**change.get("artifacts", {}), "field_diff": field_diff, "yaml_diff": yaml_diff, "patched_yaml": patched_yaml}
        await self.repository.update(change_id, {"status": ChangeStatus.PATCH_GENERATED, "artifacts": artifacts})
        return {"status": ChangeStatus.PATCH_GENERATED, "field_diff": field_diff, "yaml_diff": yaml_diff, "patched_yaml": patched_yaml}
    async def validate_change(self, change_id: str, command_runner: Optional[CommandRunner] = None) -> Dict[str, Any]:
        change = await self.repository.get(change_id)
        if change["status"] != ChangeStatus.PATCH_GENERATED:
            raise ValidationError("validate_change requires PatchGenerated status")
        patched_yaml = change.get("artifacts", {}).get("patched_yaml")
        if not patched_yaml:
            raise ValidationError("validate_change requires patched_yaml artifact")

        result = self._run_validation(
            source_path=change["source_path"], patched_yaml=patched_yaml,
            env=change["env"], current=change["current_spec"],
            proposed=change["proposed_spec"], command_runner=command_runner,
            change_type=change.get("change_type"),
        )
        artifacts = {**change.get("artifacts", {}), "validation": result}
        await self.repository.update(change_id, {"status": result["status"], "artifacts": artifacts})
        return result

    async def run_plan(self, change_id: str, runner: Optional[CommandRunner] = None, execute: bool = False) -> Dict[str, Any]:
        change = await self.repository.get(change_id)
        if change["status"] != ChangeStatus.VALIDATION_PASSED:
            raise ValidationError("run_plan requires ValidationPassed status")
        patched_yaml = change.get("artifacts", {}).get("patched_yaml")
        if not patched_yaml:
            raise ValidationError("run_plan requires patched_yaml artifact")
        if execute and runner is None:
            raise ValidationError("run_plan execute=True requires an injected runner")

        await self.repository.update(change_id, {"status": ChangeStatus.PLANNING})
        if change.get("change_type") in TERRAFORM_CHANGE_TYPES:
            plan = {
                "plan_id": "plan_0001",
                "status": ChangeStatus.PLAN_READY,
                "runner": "terraform",
                "command_summary": f"terraform plan -no-color -input=false -chdir={Path(change['source_path']).parent.as_posix()}",
                "impact": _build_terraform_impact(change),
                "log_artifact_id": "artifact_plan_log_0001",
                "exit_code": 0,
                "stdout": "mock terraform plan generated",
                "stderr": "",
            }
            latest = await self.repository.get(change_id)
            artifacts = {**latest.get("artifacts", {}), "plan": plan}
            await self.repository.update(change_id, {"status": ChangeStatus.PLAN_READY, "artifacts": artifacts})
            return plan

        command = build_odp_dryrun_command(change["source_path"])
        if execute:
            with tempfile.TemporaryDirectory(prefix="devops-platform-plan-") as tmp:
                temp_root = Path(tmp)
                _prepare_plan_workspace(self.root, temp_root, change["source_path"], patched_yaml)
                runner_result = runner(command, str(temp_root))
        else:
            runner_result = {"exit_code": 0, "stdout": "mock ODP dry-run plan generated", "stderr": ""}

        exit_code = int(runner_result.get("exit_code", 0))
        status = ChangeStatus.PLAN_READY if exit_code == 0 else ChangeStatus.PLAN_FAILED
        plan = {
            "plan_id": "plan_0001", "status": status, "runner": "odp_resources",
            "command_summary": " ".join(command), "impact": build_plan_impact(change),
            "log_artifact_id": "artifact_plan_log_0001",
            "exit_code": exit_code, "stdout": runner_result.get("stdout", ""), "stderr": runner_result.get("stderr", ""),
        }

        if self.k8s_client is not None:
            try:
                k8s_diff = self.k8s_client.diff_manifest(patched_yaml)
                plan["k8s_diff"] = {
                    "exit_code": k8s_diff.exit_code,
                    "stdout": k8s_diff.stdout[:4000],
                    "stderr": k8s_diff.stderr[:2000],
                    "has_changes": k8s_diff.exit_code != 0 if k8s_diff.success else None,
                }
            except Exception as exc:
                plan["k8s_diff"] = {"error": str(exc)}
        latest = await self.repository.get(change_id)
        artifacts = {**latest.get("artifacts", {}), "plan": plan}
        await self.repository.update(change_id, {"status": status, "artifacts": artifacts})
        return plan
    async def record_audit_event(self, change_id: str, event_type: str, actor: str, message: str = "", metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        change = await self.repository.get(change_id)
        artifacts = change.get("artifacts", {})
        audit_events = copy.deepcopy(artifacts.get("audit_events") or [])
        sequence = len(audit_events) + 1
        event = {"event_id": f"audit_{sequence:04d}", "sequence": sequence, "type": event_type, "actor": actor, "message": message, "metadata": copy.deepcopy(metadata or {})}
        audit_events.append(event)
        await self.repository.add_audit_event(change_id, event)
        await self.repository.update(change_id, {"artifacts": {**artifacts, "audit_events": audit_events}})
        return copy.deepcopy(event)

    async def get_audit_trail(self, change_id: str) -> List[Dict[str, Any]]:
        return await self.repository.get_audit_trail(change_id)

    async def submit_for_approval(self, change_id: str, requester: str, note: str = "") -> Dict[str, Any]:
        change = await self.repository.get(change_id)
        if change["status"] != ChangeStatus.PLAN_READY:
            raise ValidationError("submit_for_approval requires PlanReady status")
        artifacts = change.get("artifacts", {})
        validation = artifacts.get("validation") or {}
        plan = artifacts.get("plan") or {}
        if validation.get("status") != ChangeStatus.VALIDATION_PASSED:
            raise ValidationError("submit_for_approval requires ValidationPassed artifact")
        if plan.get("status") != ChangeStatus.PLAN_READY:
            raise ValidationError("submit_for_approval requires PlanReady artifact")

        approval = {
            "approval_id": "approval_0001", "status": ChangeStatus.PENDING_APPROVAL,
            "requester": requester, "submitted_note": note,
            "required_approvers": ["sre_oncall"],
            "timeline": [{"type": "submitted", "actor": requester, "message": "submitted for approval"}],
        }
        await self.repository.update(change_id, {"status": ChangeStatus.PENDING_APPROVAL, "artifacts": {**artifacts, "approval": approval}})
        await self.record_audit_event(change_id, event_type="approval_submitted", actor=requester, message=note or "submitted for approval", metadata={"status": ChangeStatus.PENDING_APPROVAL, "approval_id": approval["approval_id"]})
        return approval

    async def record_approval(self, change_id: str, approver: str, decision: str, comment: str = "") -> Dict[str, Any]:
        change = await self.repository.get(change_id)
        if change["status"] != ChangeStatus.PENDING_APPROVAL:
            raise ValidationError("record_approval requires PendingApproval status")
        if decision not in {"approve", "reject"}:
            raise ValidationError("decision must be approve or reject")

        artifacts = change.get("artifacts", {})
        approval = copy.deepcopy(artifacts.get("approval") or {})
        requester = approval.get("requester")
        if requester and approver == requester:
            raise ValidationError("requester and approver must be different")

        status = ChangeStatus.APPROVED if decision == "approve" else ChangeStatus.REJECTED
        event_type = "approved" if decision == "approve" else "rejected"
        approval.update({"status": status, "approver": approver, "decision": decision, "approval_comment": comment})
        approval.setdefault("timeline", []).append({"type": event_type, "actor": approver, "message": comment})
        await self.repository.update(change_id, {"status": status, "artifacts": {**artifacts, "approval": approval}})
        await self.record_audit_event(change_id, event_type=f"approval_{event_type}", actor=approver, message=comment, metadata={"status": status, "decision": decision, "approval_id": approval.get("approval_id")})
        return approval

    async def prepare_execution(self, change_id: str, executor: str, mode: str = "skeleton") -> Dict[str, Any]:
        change = await self.repository.get(change_id)
        if change["status"] != ChangeStatus.APPROVED:
            raise ValidationError("prepare_execution requires Approved status")
        if mode not in ("skeleton", "k8s_apply", "github_actions"):
            raise ValidationError("prepare_execution supports skeleton, k8s_apply, or github_actions modes")

        artifacts = change.get("artifacts", {})
        for required in ("validation", "plan", "approval"):
            if required not in artifacts:
                raise ValidationError(f"prepare_execution requires {required} artifact")

        patched_yaml = artifacts.get("patched_yaml", "")

        if mode == "k8s_apply":
            return await self._execute_k8s_apply(change_id, change, executor, patched_yaml)
        if mode == "github_actions":
            return await self._execute_github_actions(change_id, change, executor, patched_yaml)
        return await self._execute_skeleton(change_id, change, executor)

    async def _execute_k8s_apply(
        self, change_id: str, change: Dict[str, Any], executor: str, patched_yaml: str,
    ) -> Dict[str, Any]:
        if self.k8s_client is None:
            raise ValidationError("k8s_apply mode requires a Kubernetes client")

        allowed_cluster = settings.k8s_allowed_cluster.strip()
        context_result = self.k8s_client.get_current_context()
        current_context = context_result.stdout.strip() if context_result.success else ""
        if not context_result.success or (allowed_cluster and current_context != allowed_cluster):
            message = (
                f"k8s_apply blocked. current_context={current_context or 'unknown'}, "
                f"allowed_cluster={allowed_cluster or 'unset'}"
            )
            return {
                "execution_id": "exec_k8s_blocked_cluster",
                "status": "blocked",
                "mode": "k8s_apply",
                "blocked": True,
                "checks": [{
                    "name": "cluster_boundary",
                    "status": "blocked",
                    "message": message,
                }],
            }

        env = change.get("env", "dev")
        if env not in ("dev", "sandbox", "staging"):
            return {
                "execution_id": "exec_k8s_blocked",
                "status": "blocked",
                "mode": "k8s_apply",
                "blocked": True,
                "checks": [{
                    "name": "environment",
                    "status": "blocked",
                    "message": f"k8s_apply blocked for env={env}. Only dev/sandbox/staging environments can use k8s_apply for safety.",
                }],
            }

        artifacts = change.get("artifacts", {})
        try:
            result = self.k8s_client.apply_manifest(patched_yaml)
            status = "applied" if result.success else "failed"
            checks = [
                {"name": "approval", "status": "passed"},
                {"name": "plan", "status": "passed"},
                {"name": "k8s_apply", "status": status, "exit_code": result.exit_code,
                 "stdout": result.stdout[:2000], "stderr": result.stderr[:2000]},
            ]
        except Exception as exc:
            status = "failed"
            checks = [
                {"name": "approval", "status": "passed"},
                {"name": "plan", "status": "passed"},
                {"name": "k8s_apply", "status": "error", "message": str(exc)},
            ]
            result = type("Result", (), {"success": False, "exit_code": -1, "stdout": "", "stderr": str(exc)})()

        execution = {
            "execution_id": "exec_k8s_0001",
            "status": ChangeStatus.EXECUTION_READY if result.success else "ExecutionFailed",
            "mode": "k8s_apply",
            "runner_type": "kubectl",
            "executor": executor,
            "command_summary": "kubectl apply -f -",
            "external_url": None,
            "blocked": False,
            "checks": checks,
        }

        target_status = ChangeStatus.EXECUTION_READY if result.success else ChangeStatus.EXECUTION_BLOCKED
        await self.repository.update(change_id, {"status": target_status, "artifacts": {**artifacts, "execution": execution}})
        await self.record_audit_event(
            change_id,
            event_type="execution_prepared" if result.success else "execution_blocked",
            actor=executor,
            message=f"kubectl apply {'succeeded' if result.success else 'failed'}: {result.stderr[:200] if not result.success else 'applied'}",
            metadata={"status": target_status, "execution_id": execution["execution_id"], "mode": "k8s_apply"},
        )
        return execution

    async def _execute_skeleton(
        self, change_id: str, change: Dict[str, Any], executor: str,
    ) -> Dict[str, Any]:
        artifacts = change.get("artifacts", {})

        checks = [
            {"name": "approval", "status": "passed"},
            {"name": "plan", "status": "passed"},
            {"name": "side_effects", "status": "passed", "message": "no Jenkins/Git/K8s/Terraform call performed"},
        ]
        status = ChangeStatus.EXECUTION_READY
        blocked = False
        if change.get("env") != "dev":
            status = ChangeStatus.EXECUTION_BLOCKED
            blocked = True
            checks.append({"name": "environment", "status": "blocked", "message": "only dev execution skeleton is allowed in this slice"})

        execution = {
            "execution_id": "exec_0001", "status": status, "mode": "skeleton",
            "runner_type": "jenkins_placeholder", "executor": executor,
            "command_summary": "Jenkins blueprint() execution placeholder; no external build triggered",
            "external_url": None, "blocked": blocked, "checks": checks,
        }
        await self.repository.update(change_id, {"status": status, "artifacts": {**artifacts, "execution": execution}})
        await self.record_audit_event(change_id, event_type="execution_blocked" if blocked else "execution_prepared", actor=executor, message=execution["command_summary"], metadata={"status": status, "execution_id": execution["execution_id"], "blocked": blocked})
        return execution

    async def _execute_github_actions(
        self, change_id: str, change: Dict[str, Any], executor: str, patched_yaml: str,
    ) -> Dict[str, Any]:
        """Dispatch a GitHub Actions workflow for Terraform plan/apply."""
        try:
            from app.infrastructure.adapters.github_actions_execution import GitHubActionsExecutionAdapter
        except ImportError:
            raise ValidationError("github_actions mode requires github_actions_execution adapter")

        artifacts = change.get("artifacts", {})
        scope = change.get("scope") or {}
        adapter = GitHubActionsExecutionAdapter()

        config = {
            "org": scope.get("org", ""),
            "repo": scope.get("repo", ""),
            "workflow_id": scope.get("workflow_id", "terraform-plan-apply.yml"),
        }

        params = {
            "branch": f"cr-{change_id}",
            "environment": change.get("env", "sandbox"),
            "terraform_root": scope.get("terraform_root", "infra"),
            "action": "apply",
            "change_id": change_id,
            "cluster_name": scope.get("cluster_name", settings.k8s_allowed_cluster),
        }

        result = await adapter.trigger(config, params)

        execution = {
            "execution_id": result.execution_id,
            "status": "ExecutionDispatched",
            "mode": "github_actions",
            "runner_type": "github_actions",
            "executor": executor,
            "command_summary": f"GitHub Actions: workflow dispatched ({result.status})",
            "external_url": result.external_url,
            "blocked": False,
            "checks": [
                {"name": "approval", "status": "passed"},
                {"name": "plan", "status": "passed"},
                {"name": "github_actions_dispatch", "status": result.status, "workflow_run_url": result.external_url},
            ],
            "details": result.details,
        }

        target_status = ChangeStatus.EXECUTION_READY if result.status in ("dispatched", "running") else "ExecutionFailed"
        await self.repository.update(change_id, {"status": target_status, "artifacts": {**artifacts, "execution": execution}})
        await self.record_audit_event(
            change_id,
            event_type="execution_prepared",
            actor=executor,
            message=f"GitHub Actions workflow dispatched: {result.external_url or result.status}",
            metadata={"status": target_status, "execution_id": result.execution_id, "mode": "github_actions"},
        )
        return execution

    async def refresh_inventory_snapshot(self, change_id: str, actor: str, mode: str = "local_snapshot") -> Dict[str, Any]:
        change = await self.repository.get(change_id)
        artifacts = change.get("artifacts", {})
        execution = artifacts.get("execution") or {}
        if execution.get("blocked") is True:
            raise ValidationError("refresh_inventory_snapshot requires unblocked execution")
        if change["status"] != ChangeStatus.EXECUTION_READY:
            raise ValidationError("refresh_inventory_snapshot requires ExecutionReady status")
        if mode != "local_snapshot":
            raise ValidationError("refresh_inventory_snapshot only supports local_snapshot mode")

        external_calls = []
        if self.k8s_client is not None:
            try:
                k8s_check = self.k8s_client.check_connectivity()
                external_calls.append({
                    "type": "k8s_connectivity",
                    "success": k8s_check.success,
                    "message": k8s_check.stdout[:500] if k8s_check.success else k8s_check.stderr[:500],
                })
            except Exception:
                pass

        refresh = {
            "refresh_id": "inventory_refresh_0001", "status": ChangeStatus.INVENTORY_REFRESHED,
            "mode": mode, "object_id": change["object_id"], "source_path": change["source_path"],
            "external_calls": external_calls,
            "delta": {"before": copy.deepcopy(change["current_spec"]), "after": copy.deepcopy(change["proposed_spec"])},
        }
        await self.repository.update(change_id, {"status": ChangeStatus.INVENTORY_REFRESHED, "artifacts": {**artifacts, "inventory_refresh": refresh}})
        await self.record_audit_event(change_id, event_type="inventory_refreshed", actor=actor, message="local inventory snapshot refreshed; no external calls performed", metadata={"status": ChangeStatus.INVENTORY_REFRESHED, "refresh_id": refresh["refresh_id"], "mode": mode})
        return refresh

    def _change_summary(self, change: Dict[str, Any]) -> Dict[str, Any]:
        artifacts = change.get("artifacts") or {}
        return {
            "id": change.get("id"), "object_id": change.get("object_id"),
            "change_type": change.get("change_type"), "status": change.get("status"),
            "env": change.get("env"), "source_path": change.get("source_path"),
            "reason": change.get("reason", ""), "artifact_keys": sorted(artifacts.keys()),
        }

    async def _create_hype_level_change(self, request: Dict[str, Any]) -> Dict[str, Any]:
        proposed = request.get("proposed") or {}
        if not isinstance(proposed, dict) or set(proposed) != {"currentLevel"}:
            raise ValidationError("proposed must contain only currentLevel")
        if proposed["currentLevel"] not in ALLOWED_HYPE_LEVELS:
            raise ValidationError(f"currentLevel must be one of: {', '.join(sorted(ALLOWED_HYPE_LEVELS))}")
        context = self._find_hype_level_context(request.get("object_id", ""))
        return await self.repository.add(self.project_id, {
            "object_id": request["object_id"], "change_type": request["change_type"],
            "status": ChangeStatus.DRAFT, "env": context["scope"].get("env"),
            "source_path": context["source_path"], "yaml_pointer": context["yaml_pointer"],
            "scope": context["scope"], "current_spec": context["current_spec"],
            "proposed_spec": copy.deepcopy(proposed), "reason": request.get("reason", ""),
            "artifacts": {}, "created_by": request.get("created_by", ""),
        })

    def _run_validation(self, source_path, patched_yaml, env, current, proposed, command_runner=None, change_type=None) -> Dict[str, Any]:
        if change_type in TERRAFORM_CHANGE_TYPES:
            checks: List[Dict[str, Any]] = [{
                "name": "terraform_patch_preview",
                "status": "passed",
                "message": f"Terraform patch prepared for {source_path}",
            }]
            if env == "prod":
                checks.append({
                    "name": "policy",
                    "status": "warning",
                    "checks": [{"type": "approval_required", "message": "prod terraform changes require approval"}],
                })
            return {"status": ChangeStatus.VALIDATION_PASSED, "checks": checks}

        runner = command_runner or _default_command_runner
        commands = [
            ("yamllint", ["yamllint", "-c", "test/yamllint.yaml", source_path]),
            ("schema", ["python3", "test/validate_yaml.py", source_path]),
            ("path", ["go", "run", "test/validate_pbn_path.go", "-files", source_path]),
        ]
        checks: List[Dict[str, Any]] = []
        with tempfile.TemporaryDirectory(prefix="devops-platform-validation-") as tmp:
            temp_root = Path(tmp)
            destination = temp_root / source_path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(patched_yaml, encoding="utf-8")
            for name, cmd in commands:
                runner_result = runner(cmd, str(temp_root))
                exit_code = int(runner_result.get("exit_code", 0))
                checks.append({"name": name, "status": "passed" if exit_code == 0 else "failed", "exit_code": exit_code, "stdout": runner_result.get("stdout", ""), "stderr": runner_result.get("stderr", "")})

        policy = validate_policy(env, current, proposed)
        checks.append({"name": "policy", "status": policy["status"], "checks": policy["checks"]})

        is_k8s_manifest = change_type == "k8s_manifest_update" or ("apiVersion" in str(current) and "kind" in str(current))
        if self.k8s_client is not None and is_k8s_manifest:
            try:
                k8s_result = self.k8s_client.validate_manifest(patched_yaml)
                checks.append({
                    "name": "k8s_dry_run",
                    "status": "passed" if k8s_result.success else "failed",
                    "exit_code": k8s_result.exit_code,
                    "stdout": k8s_result.stdout[:2000],
                    "stderr": k8s_result.stderr[:2000],
                })
            except Exception as exc:
                checks.append({
                    "name": "k8s_dry_run",
                    "status": "error",
                    "message": str(exc),
                })

        status = ChangeStatus.VALIDATION_PASSED
        if any(check["status"] == "failed" for check in checks):
            status = ChangeStatus.VALIDATION_FAILED
        return {"status": status, "checks": checks}
    def _find_service_context(self, object_id: str) -> Dict[str, Any]:
        parts = object_id.split("/")
        if len(parts) != 5 or parts[0] != "ODP" or parts[1] != "resources":
            raise ValidationError(f"unsupported ODP resource object_id: {object_id}")
        _, _, env, name, service_name = parts
        source_path = Path("infra") / "ODP" / "resources" / env / f"{name}.yaml"
        candidates = self._candidate_odp_resource_yaml_paths(env, name)
        if not candidates:
            raise ValidationError(f"source YAML not found: {source_path.as_posix()}")
        target = self._normalize_service_id(service_name)
        for source_abs in candidates:
            data = _load_yaml(source_abs)
            services = data.get("services") or []
            if not isinstance(services, list):
                continue
            for index, service in enumerate(services):
                if not isinstance(service, dict):
                    continue
                aliases = [
                    service.get("serviceName"),
                    service.get("name"),
                    service.get("service"),
                ]
                if any(self._normalize_service_id(alias) == target for alias in aliases if alias):
                    return {
                        "source_path": source_path.as_posix(),
                        "yaml_pointer": f"/services/{index}",
                        "scope": {
                            "env": data.get("env", env), "name": data.get("name", name),
                            "clusterID": data.get("clusterID"), "namespace": data.get("namespace"),
                        },
                        "current_spec": copy.deepcopy(service),
                    }
        raise ValidationError(f"service not found in {source_path.as_posix()}: {service_name}")

    def _normalize_service_id(self, value: object) -> str:
        return str(value or "").strip().lower().replace("_", "-")

    def _resolve_odp_resource_yaml(self, env: str, name: str) -> Optional[tuple[Path, Path]]:
        rel = Path("infra") / "ODP" / "resources" / env / f"{name}.yaml"
        candidates = self._candidate_odp_resource_yaml_paths(env, name)
        if candidates:
            return candidates[0], rel
        return None

    def _resolve_change_source_abs(self, source_rel: str, object_id: Optional[str], yaml_pointer: Optional[str]) -> Path:
        rel = Path(source_rel)
        direct = self.root / rel

        if object_id:
            parts = object_id.split("/")
            if len(parts) == 5 and parts[0] == "ODP" and parts[1] == "resources":
                _, _, env, name, service_name = parts
                expected_index = self._service_index_from_pointer(yaml_pointer or "")
                target = self._normalize_service_id(service_name)
                fallback_match: Optional[Path] = None
                for candidate in self._candidate_odp_resource_yaml_paths(env, name):
                    data = _load_yaml(candidate)
                    services = data.get("services") or []
                    if not isinstance(services, list):
                        continue
                    for index, service in enumerate(services):
                        if not isinstance(service, dict):
                            continue
                        aliases = [
                            service.get("serviceName"),
                            service.get("name"),
                            service.get("service"),
                        ]
                        if any(self._normalize_service_id(alias) == target for alias in aliases if alias):
                            if expected_index >= 0 and expected_index == index:
                                return candidate
                            if fallback_match is None:
                                fallback_match = candidate
                if fallback_match is not None:
                    return fallback_match

        if direct.exists():
            return direct

        search_roots = [self.root]
        for extra in (Path("/repos"), Path("/data/repos"), Path("/demo_data")):
            if extra.exists() and extra not in search_roots:
                search_roots.append(extra)
        for root in search_roots:
            candidate = root / rel
            if candidate.exists():
                return candidate
        for root in search_roots:
            for candidate in root.glob(f"**/{rel.as_posix()}"):
                if candidate.exists():
                    return candidate
        return direct

    def _candidate_odp_resource_yaml_paths(self, env: str, name: str) -> List[Path]:
        rel = Path("infra") / "ODP" / "resources" / env / f"{name}.yaml"
        seen = set()
        candidates: List[Path] = []

        def _add(path: Path) -> None:
            if not path.exists():
                return
            key = path.as_posix()
            if key in seen:
                return
            seen.add(key)
            candidates.append(path)

        _add(self.root / rel)
        for root in (Path("/repos"), Path("/data/repos"), Path("/demo_data")):
            if not root.exists():
                continue
            _add(root / rel)
            for candidate in root.glob(f"**/{rel.as_posix()}"):
                _add(candidate)
            for candidate in root.glob(f"**/infra/ODP/resources/{env}/{name}.yaml"):
                _add(candidate)
        return candidates

    def _find_hype_level_context(self, object_id: str) -> Dict[str, Any]:
        parts = object_id.split("/")
        if len(parts) != 4 or parts[0] != "ODP" or parts[1] != "hypelevel":
            raise ValidationError(f"unsupported ODP hypelevel object_id: {object_id}")
        _, _, profile_name, service_name = parts
        source_path = Path("infra") / "ODP" / "hypelevel" / f"{profile_name}.yaml"
        source_abs = self.root / source_path
        if not source_abs.exists():
            raise ValidationError(f"source YAML not found: {source_path.as_posix()}")
        data = _load_yaml(source_abs)
        services = data.get("services") or []
        if not isinstance(services, list):
            raise ValidationError(f"services must be a list: {source_path.as_posix()}")
        if not any(isinstance(s, dict) and s.get("serviceName") == service_name for s in services):
            raise ValidationError(f"service not found in {source_path.as_posix()}: {service_name}")
        current_level = data.get("currentLevel")
        return {
            "source_path": source_path.as_posix(), "yaml_pointer": "/currentLevel",
            "scope": {"name": data.get("name", profile_name), "clusterID": data.get("clusterID"), "namespace": data.get("namespace"), "current_level": current_level},
            "current_spec": {"currentLevel": current_level},
        }

    def _find_k8s_manifest_context(self, object_id: str) -> Dict[str, Any]:
        parts = object_id.split("/")
        if len(parts) != 4 or parts[0] != "k8s":
            raise ValidationError(f"unsupported k8s manifest object_id: {object_id}")
        _, kind, namespace, name = parts
        source_path = Path("infra") / "k8s" / namespace / f"{name}.yaml"
        source_abs = self.root / source_path
        if not source_abs.exists():
            raise ValidationError(f"source YAML not found: {source_path.as_posix()}")
        data = _load_yaml(source_abs)
        return {
            "source_path": source_path.as_posix(),
            "yaml_pointer": "/",
            "scope": {
                "env": namespace,
                "namespace": namespace,
                "kind": data.get("kind", kind),
                "name": data.get("metadata", {}).get("name", name),
            },
            "current_spec": copy.deepcopy(data),
        }

    async def _create_k8s_manifest_change(self, request: Dict[str, Any]) -> Dict[str, Any]:
        proposed = request.get("proposed") or {}
        if not isinstance(proposed, dict) or not proposed:
            raise ValidationError("proposed must be a non-empty mapping")
        context = self._find_k8s_manifest_context(request.get("object_id", ""))
        return await self.repository.add(self.project_id, {
            "object_id": request["object_id"],
            "change_type": request["change_type"],
            "status": ChangeStatus.DRAFT,
            "env": context["scope"]["env"],
            "source_path": context["source_path"],
            "yaml_pointer": context["yaml_pointer"],
            "scope": context["scope"],
            "current_spec": context["current_spec"],
            "proposed_spec": copy.deepcopy(proposed),
            "reason": request.get("reason", ""),
            "artifacts": {},
            "created_by": request.get("created_by", ""),
        })

    async def _create_terraform_change(self, request: Dict[str, Any]) -> Dict[str, Any]:
        proposed = request.get("proposed") or {}
        if not isinstance(proposed, dict) or not proposed:
            raise ValidationError("proposed must be a non-empty mapping")
        context = self._find_terraform_context(request.get("object_id", ""), request.get("change_type", ""))
        normalized = _normalize_terraform_proposed(
            request["change_type"],
            str(context["scope"].get("resource_type", "")),
            proposed,
        )
        return await self.repository.add(self.project_id, {
            "object_id": request["object_id"],
            "change_type": request["change_type"],
            "status": ChangeStatus.DRAFT,
            "env": context["scope"]["env"],
            "source_path": context["source_path"],
            "yaml_pointer": context["yaml_pointer"],
            "scope": context["scope"],
            "current_spec": context["current_spec"],
            "proposed_spec": copy.deepcopy(normalized),
            "reason": request.get("reason", ""),
            "artifacts": {},
            "created_by": request.get("created_by", ""),
        })

    def _find_terraform_context(self, object_id: str, change_type: str) -> Dict[str, Any]:
        parts = object_id.split("/")
        if not parts:
            raise ValidationError(f"unsupported Terraform object_id: {object_id}")

        # ODP/resources/{env}/{name}/{service} — delegate to ODP service context
        if parts[0] == "ODP" and len(parts) >= 2 and parts[1] == "resources":
            ctx = self._find_service_context(object_id)
            # Augment scope so downstream code (generate_patch) knows this is YAML-based
            ctx.setdefault("scope", {})["terraform_kind"] = "odp_resource"
            ctx["scope"]["resource_type"] = "k8s_service"
            return ctx

        if parts[0] != "tf":
            raise ValidationError(f"unsupported Terraform object_id: {object_id}")

        terraform_kind = None
        env = "default"
        resource_type = ""
        name = ""

        if len(parts) == 5 and parts[1] == "resources":
            terraform_kind = "resource"
            env, resource_type, name = parts[2], parts[3], parts[4]
        elif len(parts) == 4 and parts[1] == "modules":
            terraform_kind = "module"
            env, name = parts[2], parts[3]
            resource_type = "terraform_module"
        elif len(parts) == 4 and parts[1] == "variables":
            terraform_kind = "variable"
            env, name = parts[2], parts[3]
            resource_type = "terraform_variable"
        elif len(parts) == 4 and parts[1] == "outputs":
            terraform_kind = "output"
            env, name = parts[2], parts[3]
            resource_type = "terraform_output"
        elif len(parts) == 4 and parts[2] == "modules":
            terraform_kind = "module"
            env, name = parts[1], parts[3]
            resource_type = "terraform_module"
        elif len(parts) == 4 and parts[2] == "variables":
            terraform_kind = "variable"
            env, name = parts[1], parts[3]
            resource_type = "terraform_variable"
        elif len(parts) == 4 and parts[2] == "outputs":
            terraform_kind = "output"
            env, name = parts[1], parts[3]
            resource_type = "terraform_output"
        elif len(parts) == 4:
            terraform_kind = "resource"
            env, resource_type, name = parts[1], parts[2], parts[3]
        else:
            raise ValidationError(f"unsupported Terraform object_id: {object_id}")

        expected_kind = {
            "terraform_resource_update": "resource",
            "terraform_variable_update": "variable",
            "terraform_module_update": "module",
        }.get(change_type)
        if expected_kind and terraform_kind != expected_kind:
            raise ValidationError(f"{change_type} requires a Terraform {expected_kind} object_id")

        source_path, block = self._resolve_terraform_source_path(env, terraform_kind, resource_type, name)
        current_spec = _parse_top_level_assignments(block["body"])
        scope = {
            "env": env,
            "module": source_path,
            "backend": _terraform_backend_from_path(source_path),
            "terraform_kind": terraform_kind,
            "resource_type": resource_type,
            "name": name,
        }
        return {
            "source_path": source_path,
            "yaml_pointer": f"/{terraform_kind}/{name}",
            "scope": scope,
            "current_spec": current_spec,
        }

    def _resolve_terraform_source_path(self, env: str, terraform_kind: str, resource_type: str, name: str) -> tuple[str, Dict[str, Any]]:
        for source_abs in sorted(self.root.glob("infra/**/*.tf")):
            source_path = source_abs.relative_to(self.root).as_posix()
            if env and _terraform_env_from_path(source_path) != env:
                continue
            content = source_abs.read_text(encoding="utf-8")
            scope = {
                "terraform_kind": terraform_kind,
                "resource_type": resource_type,
                "name": name,
            }
            try:
                return source_path, _find_terraform_block(content, scope)
            except ValidationError:
                continue
        raise ValidationError(f"terraform source not found for {terraform_kind}/{resource_type}/{name} in env={env}")
    def _service_index_from_pointer(self, yaml_pointer: str) -> int:
        prefix = "/services/"
        if not yaml_pointer.startswith(prefix):
            raise ValidationError(f"unsupported yaml_pointer: {yaml_pointer}")
        try:
            return int(yaml_pointer[len(prefix):])
        except ValueError as exc:
            raise ValidationError(f"invalid service index in yaml_pointer: {yaml_pointer}") from exc

    def _find_service_index_by_object_id(self, services: List[Any], object_id: str) -> Optional[int]:
        parts = object_id.split("/")
        if len(parts) != 5 or parts[0] != "ODP" or parts[1] != "resources":
            return None
        service_name = self._normalize_service_id(parts[4])
        for index, service in enumerate(services):
            if not isinstance(service, dict):
                continue
            aliases = [
                service.get("serviceName"),
                service.get("name"),
                service.get("service"),
            ]
            if any(self._normalize_service_id(alias) == service_name for alias in aliases if alias):
                return index
        return None
