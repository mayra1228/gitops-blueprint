# Runbook: GitHub Actions CICD for kind-gitops-sandbox

## 1. 目标与边界
1. 目标: 通过平台触发 GitHub Actions，执行 Terraform plan/apply，完成对 kind-gitops-sandbox 的受控变更。
2. 安全边界: 仅允许 sandbox 环境 + kind-gitops-sandbox 集群进行可变更执行。
3. 约束: 禁止操作任何非 kind-gitops-sandbox 资源。

## 2. 前置条件
1. 已有 GitHub 仓库，且默认分支包含 workflow 文件: .github/workflows/terraform-plan-apply.yml。
2. 平台可访问 GitHub API，并已配置 GITHUB_TOKEN。
3. 若需要变更本地 kind 集群，必须使用可访问该集群的 self-hosted runner。
4. runner 机器已安装 terraform、kubectl，并具备可用 kubeconfig/context。

## 3. GitHub 侧配置
### 3.1 启用 Actions
1. 打开仓库 Settings -> Actions -> General。
2. 允许仓库执行 Actions workflow。
3. 确认 workflow_dispatch 已启用（当前 workflow 已支持）。

### 3.2 配置 Environment
1. 打开仓库 Settings -> Environments。
2. 创建环境 sandbox。
3. 可选但推荐: 配置 Required reviewers 作为 apply 审批闸口。

### 3.3 配置 Token 权限
1. 使用 Fine-grained PAT（推荐）供平台调用 GitHub API。
2. 至少开启以下仓库权限:
- Actions: Read and write
- Contents: Read and write
- Pull requests: Read and write
3. 将该 token 配置到平台环境变量 GITHUB_TOKEN。

### 3.4 Secrets 与变量
1. 在仓库或 Environment(sandbox) 下配置 Terraform 所需 Secrets。
2. 根据你的 provider 补齐凭据，例如 AWS/GCP/Azure/Backend 认证。
3. 若 workflow 依赖额外变量（如 TF_VAR_*），在 Variables 中补齐。

### 3.5 Runner 配置（关键）
1. 本地 kind 集群场景必须使用 self-hosted runner。
2. runner 标签建议包含: self-hosted, linux, kind-sandbox。
3. runner 上验证:
- kubectl config current-context 返回 kind-gitops-sandbox
- terraform version 可用
- kubectl get ns 可连通

## 4. 平台侧配置
1. 项目配置 git_config:
- org: GitHub 组织或用户
- repo: 仓库名
2. 项目配置 execution_config:
- workflow_id: terraform-plan-apply.yml
- cluster_name: kind-gitops-sandbox
3. terraform_root 与仓库目录一致（默认 infra）。

## 5. 首次联调步骤
1. 在平台导入/注册项目，确认 inventory 与 change 流程可用。
2. 创建 Draft 并通过 Validate 与 Plan。
3. 提交审批并 Approve，状态到 Approved。
4. 执行 Execute，mode 选择 github_actions。
5. 观察执行结果:
- 平台 execution 状态有 run_id/url
- GitHub Actions 出现 workflow run
- workflow 先执行 fmt/validate/plan，再按条件执行 apply

## 6. 验收检查清单
1. 后端防护生效:
- 非 kind-gitops-sandbox 时触发失败
- apply + 非 sandbox 时触发失败
2. workflow 防护生效:
- Guard cluster boundary 失败能阻断
- Guard apply conditions 失败能阻断
3. 产物完整:
- tfplan 与 tfplan.txt 上传成功
4. 审计可追踪:
- 平台有 execution_prepared 审计事件

## 7. 常见故障与处理
### 7.1 Dispatch 失败
1. 现象: 平台返回 dispatch_failed 或 error。
2. 排查:
- 检查 GITHUB_TOKEN 是否存在
- 检查 token 权限是否含 Actions write
- 检查 org/repo/workflow_id 是否正确

### 7.2 找不到 workflow run
1. 现象: dispatch 后无 run 链接。
2. 排查:
- workflow_id 文件名是否一致
- ref 分支是否存在
- 仓库 Actions 是否被策略禁用

### 7.3 Terraform init/plan 失败
1. 现象: workflow 在 init/plan 步骤失败。
2. 排查:
- terraform_root 是否正确
- provider/backend secrets 是否齐全
- runner 网络是否可达依赖端点

### 7.4 无法操作本地 kind 集群
1. 现象: apply 成功但集群无变更，或 kubectl 连接失败。
2. 排查:
- 是否误用 GitHub-hosted runner
- self-hosted runner 是否持有正确 kubeconfig
- current-context 是否为 kind-gitops-sandbox

### 7.5 分支与 PR 相关失败
1. 现象: push 或 create PR 失败。
2. 排查:
- token 是否具备 Contents/PR 写权限
- 分支保护是否阻断自动化提交
- 平台创建分支名 cr-change_id 是否符合规则

## 8. 回滚与应急
1. 代码回滚: 在 GitHub 回退对应 PR 或 revert commit。
2. 变更冻结: 临时禁用 workflow_dispatch 或收紧 Environment 审批。
3. 平台阻断: 将执行模式切回 skeleton，暂停 github_actions 执行。
4. 集群止损: 仅在 kind-gitops-sandbox 内执行人工修复，不跨集群操作。

## 9. 日常操作建议
1. 先小变更验证链路，再放大范围。
2. 每次执行前确认目标: environment=sandbox, cluster_name=kind-gitops-sandbox。
3. 保留 run 链接、plan artifact、平台审计记录，便于复盘。
4. 定期轮换 PAT，避免长期凭据泄露风险。
