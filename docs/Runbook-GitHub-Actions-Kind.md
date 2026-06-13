# Runbook: GitHub Actions + Kind

## 1. 目标与边界

1. **目标**: 通过平台触发 GitHub Actions，执行 Terraform plan/apply，完成对 kind-gitops-sandbox 的受控变更。
2. **安全边界**: 仅允许 sandbox 环境 + kind-gitops-sandbox 集群进行可变更执行。
3. **约束**: 禁止操作任何非 kind-gitops-sandbox 资源。

## 2. 前置条件

1. 已有 GitHub 仓库，且默认分支包含 workflow 文件: `.github/workflows/terraform-plan-apply.yml`
2. 平台可访问 GitHub API，并已配置 `GITHUB_TOKEN`
3. 若需要变更本地 kind 集群，必须使用可访问该集群的 self-hosted runner
4. Runner 机器已安装 terraform、kubectl，并具备可用 kubeconfig/context

## 3. GitHub 侧配置

### 3.1 启用 Actions
1. 打开仓库 Settings → Actions → General
2. 允许仓库执行 Actions workflow
3. 确认 `workflow_dispatch` 已启用

### 3.2 配置 Environment
1. 打开仓库 Settings → Environments
2. 创建环境 `sandbox`
3. 可选但推荐: 配置 Required reviewers 作为 apply 审批闸口

### 3.3 配置 Token 权限
1. 使用 Fine-grained PAT（推荐）
2. 至少开启以下仓库权限:
   - Actions: Read and write
   - Contents: Read and write
   - Pull requests: Read and write
3. 将 token 配置到平台环境变量 `GITHUB_TOKEN`

### 3.4 Runner 配置（关键）
1. 本地 kind 集群场景必须使用 self-hosted runner
2. Runner 标签建议: `self-hosted, linux, kind-sandbox`
3. 验证:
   - `kubectl config current-context` → `kind-gitops-sandbox`
   - `terraform version` 可用
   - `kubectl get ns` 可连通

## 4. 平台侧配置

1. `git_config`: `{ "org": "<GitHub org/user>", "repo": "<repo name>" }`
2. `execution_config`: `{ "workflow_id": "terraform-plan-apply.yml", "cluster_name": "kind-gitops-sandbox" }`
3. `terraform_root` 与仓库目录一致（默认 `infra`）

## 5. 执行流程

```
用户点击 Execute (mode=github_actions)
  → API: /changes/{change_id}/execute
  → 检查 Approved 状态 + artifacts 完整性
  → ChangeService.prepare_execution
  → GitHubActionsExecutionAdapter.trigger (安全校验)
  → GitHubClient.dispatch_workflow
  → 查询 workflow run → 回写 execution artifact + 审计事件
```

## 6. 安全边界（双重防护）

1. **平台后端**: adapter 层阻断非 `kind-gitops-sandbox` / 非 sandbox apply
2. **GitHub Actions**: workflow 步骤再次阻断越界 cluster 或非法 apply 环境

## 7. 验收检查清单

- [ ] 非 `kind-gitops-sandbox` 时触发失败
- [ ] apply + 非 sandbox 时触发失败
- [ ] Guard cluster boundary 失败能阻断
- [ ] Guard apply conditions 失败能阻断
- [ ] tfplan 与 tfplan.txt 上传成功
- [ ] 平台有 `execution_prepared` 审计事件

## 8. 常见故障处理

| 故障 | 排查方向 |
|------|----------|
| Dispatch 失败 | 检查 GITHUB_TOKEN、token 权限、org/repo/workflow_id |
| 找不到 workflow run | workflow_id 文件名、ref 分支、Actions 是否禁用 |
| Terraform init/plan 失败 | terraform_root、provider secrets、runner 网络 |
| 无法操作 kind 集群 | 是否误用 GitHub-hosted runner、kubeconfig、current-context |
| 分支/PR 失败 | token Contents/PR 权限、分支保护规则 |
