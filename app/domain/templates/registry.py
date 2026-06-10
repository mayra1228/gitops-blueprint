from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional


@dataclass(frozen=True)
class TemplateDefinition:
    id: str
    name: str
    resource_type: str
    provider: str
    source_schema_path: str
    desired_state_path_rule: str
    terraform_template_path: Optional[str] = None
    validation_profile: str = "schema"
    approval_policy: str = "dev_sandbox_only"
    owner: str = "platform-engineering"
    version: str = "0.1.0"
    status: str = "active"
    capabilities: List[str] = field(default_factory=list)
    notes: str = ""
    skeleton_enabled: bool = False

    def to_dict(self) -> Dict[str, object]:
        return {
            "id": self.id, "name": self.name, "resource_type": self.resource_type,
            "provider": self.provider, "source_schema_path": self.source_schema_path,
            "desired_state_path_rule": self.desired_state_path_rule,
            "terraform_template_path": self.terraform_template_path,
            "validation_profile": self.validation_profile,
            "approval_policy": self.approval_policy, "owner": self.owner,
            "version": self.version, "status": self.status,
            "capabilities": list(self.capabilities), "notes": self.notes,
            "skeleton_enabled": self.skeleton_enabled,
        }


class TemplateRegistry:
    def __init__(self, templates: Iterable[TemplateDefinition]):
        self._templates = list(templates)
        self._by_id = {template.id: template for template in self._templates}

    def list_templates(self, filters: Optional[Dict[str, str]] = None) -> List[Dict[str, object]]:
        filters = filters or {}
        items = self._templates
        provider = filters.get("provider")
        resource_type = filters.get("resource_type")
        status = filters.get("status")
        capability = filters.get("capability")
        if provider:
            items = [item for item in items if item.provider.lower() == provider.lower()]
        if resource_type:
            items = [item for item in items if item.resource_type == resource_type]
        if status:
            items = [item for item in items if item.status == status]
        if capability:
            items = [item for item in items if capability in item.capabilities]
        return [item.to_dict() for item in items]

    def get_template(self, template_id: str) -> Optional[Dict[str, object]]:
        template = self._by_id.get(template_id)
        if template is None:
            return None
        return template.to_dict()



def build_default_template_registry() -> TemplateRegistry:
    terraform_capabilities = ["terraform_onboarding", "schema_form", "plan_preview", "approval_required"]
    return TemplateRegistry([
        TemplateDefinition(
            id="aws_ec2", name="AWS EC2 Instance",
            resource_type="aws_instance", provider="AWS",
            source_schema_path="schema/aws/ec2/instance.yaml",
            desired_state_path_rule="infra/aws/{env}/compute/main.tf",
            terraform_template_path="templates/aws/ec2/main.tf",
            approval_policy="peer_review",
            capabilities=terraform_capabilities,
            notes="Terraform EC2 instance resource. Generates main.tf with aws_instance block.",
            skeleton_enabled=True,
        ),
        TemplateDefinition(
            id="aws_rds", name="AWS RDS Database",
            resource_type="aws_db_instance", provider="AWS",
            source_schema_path="schema/aws/rds/instance.yaml",
            desired_state_path_rule="infra/aws/{env}/database/main.tf",
            terraform_template_path="templates/aws/rds/main.tf",
            approval_policy="dual_approval",
            capabilities=terraform_capabilities,
            notes="Terraform RDS instance resource. Requires dual approval for production.",
            skeleton_enabled=False,
        ),
        TemplateDefinition(
            id="aws_vpc_baseline", name="AWS VPC Baseline",
            resource_type="aws_vpc", provider="AWS",
            source_schema_path="schema/aws/vpc/baseline.yaml",
            desired_state_path_rule="infra/aws/{env}/network/main.tf",
            terraform_template_path="templates/aws/vpc/main.tf",
            approval_policy="dual_approval",
            capabilities=terraform_capabilities,
            notes="VPC with public/private subnets, IGW, NAT gateway, and route tables.",
            skeleton_enabled=True,
        ),
        TemplateDefinition(
            id="aws_s3_bucket", name="AWS S3 Bucket",
            resource_type="aws_s3_bucket", provider="AWS",
            source_schema_path="schema/aws/s3/bucket.yaml",
            desired_state_path_rule="infra/aws/{env}/storage/main.tf",
            terraform_template_path="templates/aws/s3/main.tf",
            approval_policy="peer_review",
            capabilities=terraform_capabilities,
            notes="S3 bucket with versioning, encryption, and lifecycle policies.",
            skeleton_enabled=False,
        ),
        TemplateDefinition(
            id="aws_iam_role", name="AWS IAM Role",
            resource_type="aws_iam_role", provider="AWS",
            source_schema_path="schema/aws/iam/role.yaml",
            desired_state_path_rule="infra/aws/{env}/iam/main.tf",
            terraform_template_path="templates/aws/iam/main.tf",
            approval_policy="dual_approval",
            capabilities=terraform_capabilities,
            notes="IAM Role with assume_role_policy. Requires dual approval (security-sensitive).",
            skeleton_enabled=False,
        ),
        TemplateDefinition(
            id="aws_security_group", name="AWS Security Group",
            resource_type="aws_security_group", provider="AWS",
            source_schema_path="schema/aws/sg/group.yaml",
            desired_state_path_rule="infra/aws/{env}/network/security_groups.tf",
            terraform_template_path="templates/aws/sg/main.tf",
            approval_policy="peer_review",
            capabilities=terraform_capabilities,
            notes="Security Group with ingress/egress rules.",
            skeleton_enabled=False,
        ),
        TemplateDefinition(
            id="aws_eks_service_account", name="EKS Service Account",
            resource_type="aws_iam_role", provider="AWS",
            source_schema_path="schema/aws/eks/service_account.yaml",
            desired_state_path_rule="infra/aws/{env}/eks/service_accounts.tf",
            terraform_template_path="templates/aws/eks/service_account.tf",
            approval_policy="peer_review",
            capabilities=terraform_capabilities,
            notes="IRSA (IAM Role for Service Account) for EKS workloads.",
            skeleton_enabled=False,
        ),
        TemplateDefinition(
            id="cloudwatch_alarm", name="CloudWatch Alarm",
            resource_type="aws_cloudwatch_metric_alarm", provider="AWS",
            source_schema_path="schema/aws/cloudwatch/alarm.yaml",
            desired_state_path_rule="infra/aws/{env}/monitoring/alarms.tf",
            terraform_template_path="templates/aws/cloudwatch/alarm.tf",
            approval_policy="dev_sandbox_only",
            capabilities=["terraform_onboarding", "schema_form", "plan_preview"],
            notes="CloudWatch metric alarm with SNS action.",
            skeleton_enabled=False,
        ),
        TemplateDefinition(
            id="odp_hype_level", name="ODP Hype Level (Legacy)",
            resource_type="k8s_hype_profile", provider="ODP",
            source_schema_path="test/schema/ODP/hypelevel.yaml",
            desired_state_path_rule="infra/ODP/hypelevel/{profile}.yaml",
            validation_profile="schema:test/schema/ODP/hypelevel.yaml",
            approval_policy="dev_sandbox_only",
            capabilities=["patch_preview", "schema_form", "plan_preview", "approval_required"],
            notes="Legacy ODP template retained for backward compatibility.",
            skeleton_enabled=True,
        ),
        TemplateDefinition(
            id="odp_resource", name="ODP Resource Config (Legacy)",
            resource_type="k8s_service", provider="ODP",
            source_schema_path="test/schema/ODP/resources.yaml",
            desired_state_path_rule="infra/ODP/resources/{env}/{component}.yaml",
            validation_profile="schema:test/schema/ODP/resources.yaml",
            approval_policy="dev_sandbox_only",
            capabilities=["schema_form", "plan_preview", "approval_required"],
            notes="Legacy ODP YAML resource template retained for backward compatibility.",
            skeleton_enabled=True,
        ),
    ])
