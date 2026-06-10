from pathlib import Path
from typing import Any, Dict, Iterable, List

from app.domain.adapters.base import ResourceTypeAdapter
from app.domain.inventory.models import InventoryObject, SourceFile
from app.domain.inventory.terraform_scanner import TerraformScanResult


KNOWN_TF_RESOURCE_TYPES = [
    "aws_instance", "aws_db_instance", "aws_vpc", "aws_subnet",
    "aws_security_group", "aws_s3_bucket", "aws_iam_role", "aws_iam_policy",
    "aws_iam_role_policy_attachment", "aws_eks_cluster", "aws_eks_node_group",
    "aws_elasticache_cluster", "aws_cloudwatch_metric_alarm", "aws_lb",
    "aws_lb_listener", "aws_lb_target_group", "aws_route53_record",
    "aws_sqs_queue", "aws_sns_topic", "aws_lambda_function",
    "aws_rds_cluster", "aws_ecr_repository", "aws_ecs_cluster",
    "aws_ecs_task_definition", "aws_ecs_service", "aws_autoscaling_group",
    "aws_launch_template", "aws_internet_gateway", "aws_route_table",
    "aws_nat_gateway", "aws_eip", "aws_kms_key", "aws_secretsmanager_secret",
    "google_compute_instance", "google_container_cluster", "google_sql_database_instance",
    "azurerm_virtual_machine", "azurerm_kubernetes_cluster",
    "terraform_module",
    "terraform_variable",
    "terraform_output",
]


def _infer_backend(path: str) -> str:
    normalized = path.replace('\\', '/').lower()
    if '/aws/' in normalized:
        return 'aws'
    if '/google/' in normalized or '/gcp/' in normalized:
        return 'gcp'
    if '/azure/' in normalized or '/azurerm/' in normalized:
        return 'azure'
    return 'terraform'


def _label_for_type(resource_type: str) -> str:
    if resource_type == 'terraform_module':
        return 'Terraform Module'
    if resource_type == 'terraform_variable':
        return 'Terraform Variable'
    if resource_type == 'terraform_output':
        return 'Terraform Output'
    return resource_type.replace('_', ' ').title().replace('Aws ', 'AWS ').replace('Iam ', 'IAM ').replace('Eks ', 'EKS ').replace('Ecs ', 'ECS ').replace('Ecr ', 'ECR ').replace('S3 ', 'S3 ').replace('Sqs ', 'SQS ').replace('Sns ', 'SNS ').replace('Db ', 'DB ').replace('Rds ', 'RDS ').replace('Kms ', 'KMS ').replace('Vpc', 'VPC').replace('Lb ', 'LB ')


def _category_for_type(resource_type: str) -> str:
    if resource_type == 'terraform_module':
        return 'module'
    if resource_type == 'terraform_variable':
        return 'configuration'
    if resource_type == 'terraform_output':
        return 'output'
    return 'infrastructure'


class TerraformResourceAdapter(ResourceTypeAdapter):
    resource_type = 'terraform_resource'
    aliases = ['terraform']
    category = 'infrastructure'
    label = 'Terraform Resource'

    def parse_inventory_from_tf_scan(
        self,
        scan_result: TerraformScanResult,
        root_path: str | Path,
        env_layout: Dict[str, str],
    ) -> List[InventoryObject]:
        root = Path(root_path)
        repo = root.name
        objects: List[InventoryObject] = []

        for file_info in scan_result.files:
            file_env = env_layout.get(file_info.path, 'default')
            backend = _infer_backend(file_info.path)
            source = SourceFile(
                repo=repo,
                ref='local',
                path=file_info.path,
                boundary='aws',
                component='terraform',
                env=file_env,
            )
            scope_base = {
                'env': file_env,
                'module': file_info.path,
                'backend': backend,
            }

            for index, resource in enumerate(file_info.resources):
                resource_type = resource.get('type') or self.resource_type
                resource_name = resource.get('name') or f'resource-{index}'
                objects.append(InventoryObject(
                    id=f'tf/{file_env}/{resource_type}/{resource_name}',
                    resource_type=resource_type,
                    category=_category_for_type(resource_type),
                    display_name=resource_name,
                    source=source,
                    scope={**scope_base, 'resource_type': resource_type},
                    spec={'type': resource_type, 'name': resource_name, 'path': file_info.path},
                    labels={'provider': resource_type.split('_', 1)[0]},
                    source_pointer=f'/resources/{index}',
                ))

            for index, module in enumerate(file_info.modules):
                module_name = module.get('name') or f'module-{index}'
                objects.append(InventoryObject(
                    id=f'tf/{file_env}/modules/{module_name}',
                    resource_type='terraform_module',
                    category=_category_for_type('terraform_module'),
                    display_name=module_name,
                    source=source,
                    scope={**scope_base, 'resource_type': 'terraform_module'},
                    spec={'name': module_name, 'source': module.get('source', ''), 'path': file_info.path},
                    labels={'provider': backend},
                    source_pointer=f'/modules/{index}',
                ))

            for index, variable in enumerate(file_info.variables):
                variable_name = variable.get('name') or f'variable-{index}'
                objects.append(InventoryObject(
                    id=f'tf/{file_env}/variables/{variable_name}',
                    resource_type='terraform_variable',
                    category=_category_for_type('terraform_variable'),
                    display_name=variable_name,
                    source=source,
                    scope={**scope_base, 'resource_type': 'terraform_variable'},
                    spec={'name': variable_name, 'default': variable.get('default'), 'path': file_info.path},
                    labels={'provider': backend},
                    source_pointer=f'/variables/{index}',
                ))

            for index, output in enumerate(file_info.outputs):
                output_name = output.get('name') or f'output-{index}'
                objects.append(InventoryObject(
                    id=f'tf/{file_env}/outputs/{output_name}',
                    resource_type='terraform_output',
                    category=_category_for_type('terraform_output'),
                    display_name=output_name,
                    source=source,
                    scope={**scope_base, 'resource_type': 'terraform_output'},
                    spec={'name': output_name, 'path': file_info.path},
                    labels={'provider': backend},
                    source_pointer=f'/outputs/{index}',
                ))

        return objects

    def resource_definitions(self) -> Iterable[Dict[str, Any]]:
        yield {
            'resource_type': self.resource_type,
            'category': self.category,
            'label': self.label,
            'aliases': list(self.aliases),
        }
        for resource_type in KNOWN_TF_RESOURCE_TYPES:
            yield {
                'resource_type': resource_type,
                'category': _category_for_type(resource_type),
                'label': _label_for_type(resource_type),
                'aliases': [],
            }
