from dataclasses import dataclass, field
from typing import Iterable, List, Optional


@dataclass(frozen=True)
class CapabilityDefinition:
    id: str
    name: str
    description: str = ""
    resource_types: List[str] = field(default_factory=list)
    change_types: List[str] = field(default_factory=list)
    template_ids: List[str] = field(default_factory=list)
    object_id_prefix: str = ""


class CapabilityRegistry:
    def __init__(self, capabilities: Iterable[CapabilityDefinition]):
        self._capabilities = list(capabilities)
        self._by_id: dict[str, CapabilityDefinition] = {c.id: c for c in self._capabilities}

    def list_all(self) -> List[CapabilityDefinition]:
        return list(self._capabilities)

    def get(self, cap_id: str) -> Optional[CapabilityDefinition]:
        return self._by_id.get(cap_id)


def build_default_capability_registry() -> CapabilityRegistry:
    return CapabilityRegistry([
        CapabilityDefinition(
            id="terraform_infra",
            name="Resource Management",
            description="资源管理工作区 — 仅管理 AWS 与 K8S 资源，创建 Draft、预览 Diff、校验、Plan、审批与执行",
            resource_types=[],  # empty = show all, use category chips to filter by provider
            change_types=["terraform_resource_update"],
            template_ids=["aws_ec2", "aws_rds", "aws_s3", "aws_vpc_baseline", "aws_iam_role"],
            object_id_prefix="tf/",
        ),
        CapabilityDefinition(
            id="terraform_module",
            name="Module Management",
            description="Terraform 模块管理 — 添加/升级模块版本、调整模块参数",
            resource_types=["terraform_module"],
            change_types=["terraform_module_update"],
            template_ids=["vpc_baseline", "eks_service_account", "cloudwatch_alarm"],
            object_id_prefix="tf/modules/",
        ),
        CapabilityDefinition(
            id="terraform_variables",
            name="Variable Management",
            description="变量与参数管理 — tfvars / workspace variables / CI variables / secrets",
            resource_types=["terraform_variable", "terraform_output", "terraform_backend"],
            change_types=["terraform_variable_update"],
            template_ids=[],
            object_id_prefix="tf/variables/",
        ),
    ])
