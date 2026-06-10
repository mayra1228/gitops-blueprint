from typing import Iterable, List, Optional

from app.domain.skeletons.models import SkeletonDirectory, SkeletonFile, SkeletonTemplate


class SkeletonRegistry:
    def __init__(self, templates: Iterable[SkeletonTemplate]):
        self._templates = list(templates)
        self._by_id: dict[str, SkeletonTemplate] = {t.id: t for t in self._templates}

    def get(self, template_id: str) -> Optional[SkeletonTemplate]:
        return self._by_id.get(template_id)

    def list_all(self) -> List[SkeletonTemplate]:
        return list(self._templates)

    def list_by_provider(self, provider: str) -> List[SkeletonTemplate]:
        return [t for t in self._templates if t.provider.lower() == provider.lower()]

    def list_by_render_mode(self, mode: str) -> List[SkeletonTemplate]:
        return [t for t in self._templates if t.render_mode == mode]

    def list_by_capability(self, capability_id: str) -> List[SkeletonTemplate]:
        return [t for t in self._templates if t.capability_id == capability_id]

    def get_by_linked_template(self, template_id: str) -> Optional[SkeletonTemplate]:
        for t in self._templates:
            if t.linked_template_id == template_id:
                return t
        return None



def build_default_skeleton_registry() -> SkeletonRegistry:
    return SkeletonRegistry([
        SkeletonTemplate(
            id="standard-terraform-service",
            name="Standard Terraform Service",
            provider="AWS",
            render_mode="terraform",
            capability_id="terraform_infra",
            description="标准 Terraform 项目结构 — 多环境 (dev/sit/prod) + backend + CI/CD workflow",
            parameter_schema={
                "type": "object",
                "properties": {
                    "service_name": {"type": "string", "title": "Service Name", "description": "Terraform project/service name", "default": "my-service"},
                    "aws_region": {"type": "string", "title": "AWS Region", "default": "ap-southeast-1"},
                    "tf_version": {"type": "string", "title": "Terraform Version", "default": "1.6.0"},
                    "environments": {"type": "string", "title": "Environments (comma-separated)", "default": "dev,sit,prod"},
                    "backend_bucket": {"type": "string", "title": "S3 Backend Bucket", "default": "my-tfstate-bucket"},
                    "cicd_platform": {"type": "string", "title": "CI/CD Platform", "enum": ["github_actions", "jenkins", "gitlab_ci"], "default": "github_actions"},
                },
                "required": ["service_name", "aws_region"],
            },
            directories=[
                SkeletonDirectory(
                    path_template="{{service_name}}",
                    files=[
                        SkeletonFile(
                            filename_template="README.md",
                            content_template='# {{service_name}}\n\nTerraform infrastructure for **{{service_name}}**.\n\n## Environments\n\n- `dev` — Development\n- `sit` — System Integration Testing\n- `prod` — Production\n\n## Usage\n\n```bash\ncd envs/dev\nterraform init -backend-config=backend.hcl\nterraform plan\nterraform apply\n```\n\n## Requirements\n\n- Terraform >= {{tf_version}}\n- AWS CLI configured\n',
                            file_type="text",
                        ),
                        SkeletonFile(
                            filename_template="versions.tf",
                            content_template='terraform {\n  required_version = ">= {{tf_version}}"\n\n  required_providers {\n    aws = {\n      source  = "hashicorp/aws"\n      version = "~> 5.0"\n    }\n  }\n}\n',
                            file_type="terraform",
                        ),
                        SkeletonFile(
                            filename_template="providers.tf",
                            content_template='provider "aws" {\n  region = var.aws_region\n\n  default_tags {\n    tags = {\n      Project     = "{{service_name}}"\n      ManagedBy   = "terraform"\n      Environment = var.environment\n    }\n  }\n}\n',
                            file_type="terraform",
                        ),
                        SkeletonFile(
                            filename_template="variables.tf",
                            content_template='variable "aws_region" {\n  description = "AWS region"\n  type        = string\n  default     = "{{aws_region}}"\n}\n\nvariable "environment" {\n  description = "Deployment environment (dev/sit/prod)"\n  type        = string\n}\n\nvariable "service_name" {\n  description = "Service name"\n  type        = string\n  default     = "{{service_name}}"\n}\n',
                            file_type="terraform",
                        ),
                        SkeletonFile(
                            filename_template="outputs.tf",
                            content_template='output "service_name" {\n  description = "Service name"\n  value       = var.service_name\n}\n\noutput "environment" {\n  description = "Deployment environment"\n  value       = var.environment\n}\n',
                            file_type="terraform",
                        ),
                    ],
                ),
                SkeletonDirectory(
                    path_template="{{service_name}}/modules",
                    files=[SkeletonFile(filename_template=".gitkeep", content_template="", file_type="text")],
                ),
                SkeletonDirectory(
                    path_template="{{service_name}}/envs/dev",
                    files=[
                        SkeletonFile(
                            filename_template="main.tf",
                            content_template='# Dev environment entrypoint\n# Add your resource definitions here\n\n# Example: uncomment to add an S3 bucket\n# resource "aws_s3_bucket" "main" {\n#   bucket = "{{service_name}}-dev-data"\n# }\n',
                            file_type="terraform",
                        ),
                        SkeletonFile(
                            filename_template="terraform.tfvars",
                            content_template='environment  = "dev"\naws_region   = "{{aws_region}}"\nservice_name = "{{service_name}}"\n',
                            file_type="terraform",
                        ),
                        SkeletonFile(
                            filename_template="backend.hcl",
                            content_template='bucket         = "{{backend_bucket or "my-tfstate-bucket"}}"\nkey            = "{{service_name}}/dev/terraform.tfstate"\nregion         = "{{aws_region}}"\nencrypt        = true\n',
                            file_type="terraform",
                        ),
                    ],
                ),
                SkeletonDirectory(
                    path_template="{{service_name}}/envs/sit",
                    files=[
                        SkeletonFile(filename_template="main.tf", content_template='# SIT environment entrypoint\n', file_type="terraform"),
                        SkeletonFile(filename_template="terraform.tfvars", content_template='environment  = "sit"\naws_region   = "{{aws_region}}"\nservice_name = "{{service_name}}"\n', file_type="terraform"),
                        SkeletonFile(filename_template="backend.hcl", content_template='bucket         = "{{backend_bucket or "my-tfstate-bucket"}}"\nkey            = "{{service_name}}/sit/terraform.tfstate"\nregion         = "{{aws_region}}"\nencrypt        = true\n', file_type="terraform"),
                    ],
                ),
                SkeletonDirectory(
                    path_template="{{service_name}}/envs/prod",
                    files=[
                        SkeletonFile(filename_template="main.tf", content_template='# Prod environment entrypoint\n', file_type="terraform"),
                        SkeletonFile(filename_template="terraform.tfvars", content_template='environment  = "prod"\naws_region   = "{{aws_region}}"\nservice_name = "{{service_name}}"\n', file_type="terraform"),
                        SkeletonFile(filename_template="backend.hcl", content_template='bucket         = "{{backend_bucket or "my-tfstate-bucket"}}"\nkey            = "{{service_name}}/prod/terraform.tfstate"\nregion         = "{{aws_region}}"\nencrypt        = true\n', file_type="terraform"),
                    ],
                ),
                SkeletonDirectory(
                    path_template="{{service_name}}/.github/workflows",
                    files=[
                        SkeletonFile(
                            filename_template="terraform-plan.yml",
                            content_template='name: Terraform Plan\n\non:\n  pull_request:\n    branches: [main]\n    paths:\n      - "envs/**"\n      - "modules/**"\n      - "*.tf"\n\npermissions:\n  contents: read\n  pull-requests: write\n\njobs:\n  terraform-plan:\n    name: Terraform Plan\n    runs-on: ubuntu-latest\n    strategy:\n      matrix:\n        environment: [dev, sit]\n    steps:\n      - uses: actions/checkout@v4\n\n      - uses: hashicorp/setup-terraform@v3\n        with:\n          terraform_version: "{{tf_version}}"\n\n      - name: Terraform Init\n        working-directory: envs/${{ matrix.environment }}\n        run: terraform init -backend-config=backend.hcl\n\n      - name: Terraform Plan\n        working-directory: envs/${{ matrix.environment }}\n        run: terraform plan -out=tfplan\n        env:\n          AWS_REGION: "{{aws_region}}"\n',
                            file_type="yaml",
                        ),
                    ],
                ),
            ],
            tags=["terraform", "aws", "multi-env", "github-actions"],
            linked_template_id="aws_ec2",
        ),
        SkeletonTemplate(
            id="aws-ec2-module",
            name="AWS EC2 Module",
            provider="AWS",
            render_mode="terraform",
            capability_id="terraform_infra",
            description="单个 AWS EC2 资源模块 — 适合快速添加到现有 Terraform 项目",
            parameter_schema={
                "type": "object",
                "properties": {
                    "resource_name": {"type": "string", "title": "Resource Name", "default": "web-server"},
                    "instance_type": {"type": "string", "title": "Instance Type", "default": "t3.micro"},
                    "env": {"type": "string", "title": "Environment", "enum": ["dev", "sit", "uat", "prod"], "default": "dev"},
                    "aws_region": {"type": "string", "title": "AWS Region", "default": "ap-southeast-1"},
                },
                "required": ["resource_name", "env"],
            },
            directories=[
                SkeletonDirectory(
                    path_template="modules/{{resource_name}}",
                    files=[
                        SkeletonFile(
                            filename_template="main.tf",
                            content_template='resource "aws_instance" "{{resource_name}}" {\n  ami           = var.ami_id\n  instance_type = "{{instance_type}}"\n\n  tags = {\n    Name        = "{{resource_name}}-{{env}}"\n    Environment = "{{env}}"\n    ManagedBy   = "terraform"\n  }\n}\n',
                            file_type="terraform",
                        ),
                        SkeletonFile(
                            filename_template="variables.tf",
                            content_template='variable "ami_id" {\n  description = "AMI ID for the EC2 instance"\n  type        = string\n}\n\nvariable "instance_type" {\n  description = "EC2 instance type"\n  type        = string\n  default     = "{{instance_type}}"\n}\n',
                            file_type="terraform",
                        ),
                        SkeletonFile(
                            filename_template="outputs.tf",
                            content_template='output "instance_id" {\n  description = "EC2 instance ID"\n  value       = aws_instance.{{resource_name}}.id\n}\n\noutput "public_ip" {\n  description = "Public IP address"\n  value       = aws_instance.{{resource_name}}.public_ip\n}\n',
                            file_type="terraform",
                        ),
                    ],
                ),
            ],
            tags=["terraform", "aws", "ec2", "module"],
            linked_template_id="aws_ec2",
        ),
        SkeletonTemplate(
            id="odp_hype_level",
            name="ODP Hype Level Profile",
            provider="ODP",
            render_mode="yaml",
            capability_id="hype_level",
            description="Generate a standardized ODP hype level profile YAML with capacity tiers (low/medium/high) for K8S services",
            parameter_schema={
                "type": "object",
                "properties": {
                    "profile": {"type": "string", "title": "Profile Name", "description": "Hype level profile identifier", "default": "ecp"},
                    "env": {"type": "string", "title": "Environment", "description": "Target environment", "default": "dev"},
                    "cluster_id": {"type": "string", "title": "Cluster ID", "description": "K8S cluster identifier", "default": "aks-dev-01"},
                    "namespace": {"type": "string", "title": "Namespace", "description": "K8S namespace", "default": "default"},
                    "description": {"type": "string", "title": "Description", "description": "Profile purpose description"},
                    "current_level": {"type": "string", "title": "Initial Level", "description": "Starting capacity level", "enum": ["low", "medium", "high"], "default": "low"},
                },
                "required": ["profile", "env", "cluster_id"],
            },
            directories=[
                SkeletonDirectory(
                    path_template="infra/ODP/hypelevel",
                    files=[
                        SkeletonFile(
                            filename_template="{{profile}}.yaml",
                            content_template='version: "1.0"\nplatform: infra\nboundary: ODP\ncomponent: hypelevel\nname: {{profile}}\nenv: {{env}}\ncluster_id: {{cluster_id}}\nnamespace: {{namespace}}\ndescription: "{{description or \'Hype level capacity profile\'}}"\ncurrentLevel: {{current_level or \'low\'}}\n\nservices:\n  - serviceName: example-service\n    low: 2\n    medium: 5\n    high: 10\n    max: 15\n    is_keda_scaled: false\n    is_statefulset: false\n',
                            file_type="yaml",
                        ),
                        SkeletonFile(
                            filename_template="README.md",
                            content_template="# {{profile}} — Hype Level Profile\n\n**Provider:** ODP\n**Environment:** {{env}}\n**Cluster:** {{cluster_id}}\n**Initial Level:** {{current_level or 'low'}}\n\n## Description\n{{description or 'Capacity tier management for K8S services.'}}\n\n## Usage\n\nAdd services to the `services` list in `{{profile}}.yaml`. Each service defines replica counts for `low`, `medium`, `high`, and `max` capacity tiers.\n\n## Generated by\n\nGitOps Platform Skeleton · {{profile}}",
                            file_type="text",
                        ),
                    ],
                ),
            ],
            tags=["capacity", "k8s", "odp"],
            linked_template_id="odp_hype_level",
        ),
        SkeletonTemplate(
            id="odp_resource",
            name="ODP Resource Configuration",
            provider="ODP",
            render_mode="yaml",
            capability_id="odp_resource",
            description="Generate K8S resource specification YAML (HPA, CPU, Memory) for ODP services",
            parameter_schema={
                "type": "object",
                "properties": {
                    "component": {"type": "string", "title": "Component Name", "description": "ODP component identifier", "default": "ecp"},
                    "env": {"type": "string", "title": "Environment", "description": "Deployment environment", "default": "dev"},
                    "cluster_id": {"type": "string", "title": "Cluster ID", "description": "Target K8S cluster", "default": "aks-dev-01"},
                    "namespace": {"type": "string", "title": "Namespace", "description": "K8S namespace", "default": "default"},
                    "service_name": {"type": "string", "title": "Service Name", "description": "Primary service to configure", "default": "example-svc"},
                    "min_replicas": {"type": "integer", "title": "Min Replicas", "description": "Minimum pod count", "default": 2},
                    "max_replicas": {"type": "integer", "title": "Max Replicas", "description": "Maximum pod count", "default": 8},
                    "target_cpu": {"type": "integer", "title": "Target CPU %", "description": "HPA CPU target utilization", "default": 70},
                },
                "required": ["component", "env", "cluster_id"],
            },
            directories=[
                SkeletonDirectory(
                    path_template="infra/ODP/resources/{{env}}",
                    files=[
                        SkeletonFile(
                            filename_template="{{component}}.yaml",
                            content_template='version: "1.0"\nplatform: infra\nboundary: ODP\ncomponent: resources\nname: {{component}}\nenv: {{env}}\ncluster_id: {{cluster_id}}\nnamespace: {{namespace}}\n\nservices:\n  - serviceName: {{service_name or "example-svc"}}\n    minReplicas: {{min_replicas or 2}}\n    maxReplicas: {{max_replicas or 8}}\n    requestCPU: 250m\n    limitCPU: 500m\n    requestMem: 256Mi\n    limitMem: 512Mi\n    targetCPU: {{target_cpu or 70}}\n    targetMem: 80\n    initialDelaySeconds: 30\n',
                            file_type="yaml",
                        ),
                        SkeletonFile(
                            filename_template="README.md",
                            content_template='# {{component}} — ODP Resource Configuration\n\n**Provider:** ODP\n**Environment:** {{env}}\n**Cluster:** {{cluster_id}}\n\n## Description\nK8S resource specification (HPA, CPU, Memory) for ODP services.\n\n## Services\n\n- `{{service_name or \'example-svc\'}}`: {{min_replicas or 2}}–{{max_replicas or 8}} replicas, CPU target {{target_cpu or 70}}%\n\n## Generated by\n\nGitOps Platform Skeleton · {{component}}',
                            file_type="text",
                        ),
                    ],
                ),
            ],
            tags=["resources", "k8s", "hpa", "odp"],
            linked_template_id="odp_resource",
        ),
        SkeletonTemplate(
            id="aws_ec2",
            name="AWS EC2 Instance",
            provider="AWS",
            render_mode="hcl",
            capability_id="aws_ec2",
            description="Generate a complete Terraform EC2 module with standardized structure: main.tf, variables.tf, outputs.tf, terraform.tfvars, README",
            parameter_schema={
                "type": "object",
                "properties": {
                    "city": {"type": "string", "title": "City / Region Alias", "description": "Deployment city code", "default": "shanghai"},
                    "env": {"type": "string", "title": "Environment", "description": "Deployment environment", "default": "dev"},
                    "instance_name": {"type": "string", "title": "Instance Name", "description": "EC2 instance Name tag", "default": "web-server"},
                    "instance_type": {"type": "string", "title": "Instance Type", "description": "EC2 instance size", "enum": ["t3.micro", "t3.small", "t3.medium", "t3.large", "m5.large", "m5.xlarge"], "default": "t3.micro"},
                    "ami_id": {"type": "string", "title": "AMI ID", "description": "Amazon Machine Image ID (region-specific)", "default": "ami-0c55b159cbfafe1f0"},
                    "subnet_id": {"type": "string", "title": "Subnet ID", "description": "VPC subnet identifier", "default": "subnet-abc123"},
                    "key_name": {"type": "string", "title": "SSH Key Name", "description": "EC2 key pair name", "default": "default-key"},
                    "root_volume_size": {"type": "integer", "title": "Root Volume Size (GB)", "description": "EBS root volume size in GB", "default": 20},
                },
                "required": ["city", "env", "instance_name", "instance_type"],
            },
            directories=[
                SkeletonDirectory(
                    path_template="infra/aws/{{city}}/{{env}}/ec2",
                    files=[
                        SkeletonFile(
                            filename_template="main.tf",
                            content_template='terraform {\n  required_version = ">= 1.3.0"\n  required_providers {\n    aws = {\n      source  = "hashicorp/aws"\n      version = "~> 5.0"\n    }\n  }\n}\n\nprovider "aws" {\n  region = var.aws_region\n}\n\nresource "aws_instance" "{{instance_name}}" {\n  ami           = var.ami_id\n  instance_type = var.instance_type\n  subnet_id     = var.subnet_id\n  key_name      = var.key_name\n\n  root_block_device {\n    volume_size = var.root_volume_size\n    volume_type = "gp3"\n  }\n\n  tags = {\n    Name        = var.instance_name\n    Environment = var.env\n    City        = var.city\n    ManagedBy   = "gitops-platform"\n  }\n}\n',
                            file_type="hcl",
                        ),
                        SkeletonFile(
                            filename_template="variables.tf",
                            content_template='variable "aws_region" {\n  description = "AWS region"\n  type        = string\n  default     = "us-east-1"\n}\n\nvariable "city" {\n  description = "Deployment city code"\n  type        = string\n  default     = "{{city}}"\n}\n\nvariable "env" {\n  description = "Deployment environment"\n  type        = string\n  default     = "{{env}}"\n}\n\nvariable "instance_name" {\n  description = "EC2 instance Name tag"\n  type        = string\n  default     = "{{instance_name}}"\n}\n\nvariable "instance_type" {\n  description = "EC2 instance type"\n  type        = string\n  default     = "{{instance_type}}"\n}\n\nvariable "ami_id" {\n  description = "AMI ID"\n  type        = string\n  default     = "{{ami_id}}"\n}\n\nvariable "subnet_id" {\n  description = "VPC subnet ID"\n  type        = string\n  default     = "{{subnet_id}}"\n}\n\nvariable "key_name" {\n  description = "SSH key pair name"\n  type        = string\n  default     = "{{key_name}}"\n}\n\nvariable "root_volume_size" {\n  description = "EBS root volume size in GB"\n  type        = number\n  default     = {{root_volume_size}}\n}\n',
                            file_type="hcl",
                        ),
                        SkeletonFile(
                            filename_template="outputs.tf",
                            content_template='output "instance_id" {\n  description = "EC2 instance ID"\n  value       = aws_instance.{{instance_name}}.id\n}\n\noutput "instance_public_ip" {\n  description = "EC2 public IP address"\n  value       = aws_instance.{{instance_name}}.public_ip\n}\n\noutput "instance_private_ip" {\n  description = "EC2 private IP address"\n  value       = aws_instance.{{instance_name}}.private_ip\n}\n\noutput "instance_arn" {\n  description = "EC2 instance ARN"\n  value       = aws_instance.{{instance_name}}.arn\n}\n',
                            file_type="hcl",
                        ),
                        SkeletonFile(
                            filename_template="terraform.tfvars",
                            content_template='aws_region       = "us-east-1"\ncity             = "{{city}}"\nenv              = "{{env}}"\ninstance_name    = "{{instance_name}}"\ninstance_type    = "{{instance_type}}"\nami_id           = "{{ami_id}}"\nsubnet_id        = "{{subnet_id}}"\nkey_name         = "{{key_name}}"\nroot_volume_size = {{root_volume_size}}\n',
                            file_type="hcl",
                        ),
                        SkeletonFile(
                            filename_template="README.md",
                            content_template="# AWS EC2 — {{instance_name}}\n\n**Provider:** AWS\n**City:** {{city}}\n**Environment:** {{env}}\n**Instance Type:** {{instance_type}}\n\n## Module Structure\n\n```\ninfra/aws/{{city}}/{{env}}/ec2/\n├── main.tf          # EC2 instance resource + provider\n├── variables.tf     # Input variable declarations\n├── outputs.tf       # Output values (id, IPs, ARN)\n├── terraform.tfvars # Per-environment variable values\n└── README.md        # This file\n```\n\n## Usage\n\n```bash\ncd infra/aws/{{city}}/{{env}}/ec2\nterraform init\nterraform plan\nterraform apply\n```\n\n## Generated by\n\nGitOps Platform Skeleton · AWS EC2 · {{env}}",
                            file_type="text",
                        ),
                    ],
                ),
            ],
            tags=["compute", "aws", "ec2", "terraform"],
            linked_template_id="aws_ec2",
        ),
    ])
