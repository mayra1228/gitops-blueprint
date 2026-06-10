
平台应该做：

1. Repo 接入
  • 注册 Git repo。
  • 扫描 Terraform 文件。
  • 识别 module、resource、variable、output、backend、provider、env layout。

2. 可视化
  • 项目视图：Project / Env / Module / Resource。
  • 资源拓扑：VPC、Subnet、EC2、RDS、Security Group、IAM 等关系。
  • 变量与参数视图：哪些值来自 tfvars / workspace / CI variable / secret。
  • Drift / runtime state 未来可以通过 adapter 接入。

3. 变更流程
  • 用户不是直接改云资源，而是产生：
    • Terraform patch
    • plan preview
    • approval request
    • CI/CD trigger proposal
  • 审批通过后复用现有平台 CICD，不在平台里硬编码 Jenkins/GitHub Actions/Argo 等。

4. Adapter 概念
  • CICDAdapter
    • Jenkins
    • GitHub Actions
    • GitLab CI
    • Azure DevOps
    • Internal pipeline
  • InfraAdapter
    • Terraform CLI
    • Terraform Cloud
    • Atlantis
    • Spacelift
    • Internal IaC executor
  • RepoAdapter
    • GitHub
    • GitLab
    • Bitbucket
    • Internal Git
  • ApprovalAdapter
    • ServiceNow
    • Jira
    • GitHub PR review
    • Internal approval platform

这个方向是对的：平台不应该替代现有 CICD，而应该作为 control plane，把 repo、approval、plan、pipeline 串起来。

2. 未启用 Terraform 的项目：Skeleton + Template 快速生成

这个是第二个核心场景：

  ─ text
  Project without Terraform
          ↓
  选择 Skeleton
          ↓
  填写参数
          ↓
  生成标准 Terraform repo structure
          ↓
  提交到目标 repo
          ↓
  进入同一套 Terraform 可视化 / Plan / Approval / CICD 流程

我建议这里把概念拆清楚：

Template

Template 是“资源或模块模板”。

例如：

• aws_ec2
• aws_rds
• aws_s3
• eks_service_account
• vpc_baseline
• cloudwatch_alarm
• iam_role
• odp_hype_level 这种非 Terraform 的也可以保留为 legacy / domain-specific template

Template 关注：

─ text
我要创建什么资源？
需要哪些参数？
会生成哪些 .tf / .tfvars / README / policy 文件？

Skeleton

Skeleton 是“项目结构模板”。

例如：

─ text
standard-terraform-service
├── README.md
├── versions.tf
├── providers.tf
├── backend.tf
├── variables.tf
├── outputs.tf
├── modules/
├── envs/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── terraform.tfvars
│   │   └── backend.hcl
│   ├── sit/
│   └── prod/
└── .github/workflows/
    └── terraform-plan.yml

Skeleton 关注：

─ text
这个项目应该长什么样？
目录结构是什么？
环境怎么分？
backend 怎么放？
CICD 文件是否一起生成？
审批策略如何声明？

Flow 建议

─ text
Template Catalog
     ↓
Skeleton Wizard
     ↓
Generated Files Preview
     ↓
GitOps Proposal
     ↓
Approval
     ↓
Commit / Branch / PR
     ↓
Existing Terraform Visualization Flow

重点是：Skeleton 生成之后，不应该另起一套流程，而是复用已有 Terraform visualization + change flow。

0. Overview / Command Center
1. Project Registry
2. Terraform Control Plane
3. Bootstrap / Templates
4. Change Workspace
5. Delivery / Adapters
6. Governance / SRE Evidence
7. Admin / Settings