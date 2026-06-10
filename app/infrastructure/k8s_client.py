import json
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class K8SResult:
    success: bool
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    command: List[str] = field(default_factory=list)


class KubernetesClient:
    def __init__(self, kubeconfig: Optional[str] = None, context: Optional[str] = None):
        self._kubeconfig = kubeconfig
        self._context = context

    def _base_cmd(self) -> List[str]:
        cmd = ["kubectl"]
        if self._kubeconfig:
            cmd.extend(["--kubeconfig", self._kubeconfig])
        if self._context:
            cmd.extend(["--context", self._context])
        return cmd

    def _run(self, cmd: List[str], stdin: Optional[str] = None, timeout: int = 60) -> K8SResult:
        full_cmd = self._base_cmd() + cmd
        logger.info("kubectl: %s", " ".join(full_cmd))
        try:
            completed = subprocess.run(
                full_cmd, input=stdin, text=True, capture_output=True, timeout=timeout,
            )
            return K8SResult(
                success=completed.returncode == 0,
                exit_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                command=full_cmd,
            )
        except subprocess.TimeoutExpired:
            return K8SResult(
                success=False, exit_code=-1, stderr="kubectl command timed out", command=full_cmd,
            )
        except FileNotFoundError:
            return K8SResult(
                success=False, exit_code=-1, stderr="kubectl not found in PATH", command=full_cmd,
            )

    def validate_manifest(self, yaml_content: str) -> K8SResult:
        """Run kubectl --dry-run=server apply to validate manifests without applying."""
        return self._run(["apply", "--dry-run=server", "-f", "-"], stdin=yaml_content)

    def diff_manifest(self, yaml_content: str) -> K8SResult:
        """Run kubectl diff to show what would change."""
        return self._run(["diff", "-f", "-"], stdin=yaml_content)

    def apply_manifest(self, yaml_content: str, dry_run: bool = False) -> K8SResult:
        """Apply manifests to the cluster. Set dry_run=True for server-side dry run only."""
        cmd = ["apply", "-f", "-"]
        if dry_run:
            cmd.append("--dry-run=server")
        return self._run(cmd, stdin=yaml_content)

    def get_resources(
        self, namespace: str, kind: Optional[str] = None, labels: Optional[Dict[str, str]] = None,
    ) -> K8SResult:
        """Get resources from a namespace, optionally filtered by kind and labels."""
        resources = kind or "all"
        cmd = ["get", resources, "-n", namespace, "-o", "json"]
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in labels.items())
            cmd.extend(["-l", label_str])
        return self._run(cmd)

    def get_resource(
        self, kind: str, name: str, namespace: str,
    ) -> K8SResult:
        """Get a single resource by kind, name, and namespace."""
        return self._run(["get", kind, name, "-n", namespace, "-o", "json"])

    def check_connectivity(self) -> K8SResult:
        """Check if the cluster is reachable."""
        return self._run(["cluster-info"], timeout=10)

    def get_namespaces(self) -> K8SResult:
        """List all namespaces."""
        return self._run(["get", "namespaces", "-o", "json"])

    def get_current_context(self) -> K8SResult:
        """Return current kubectl context name."""
        return self._run(["config", "current-context"], timeout=10)

    @classmethod
    def from_config(
        cls, kubeconfig: Optional[str] = None, context: Optional[str] = None,
    ) -> "KubernetesClient":
        return cls(kubeconfig=kubeconfig, context=context)
