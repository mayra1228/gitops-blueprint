# CLAUDE.md

## SDD 工作流（Specification-Driven Development）

本项目采用规格驱动开发。所有实现工作必须遵循以下流程：

1. **规格优先**：在任何代码修改前，先阅读 `.claude/requirements.md` 和 `.claude/architecture.md` 了解上下文
2. **验收标准即合约**：每个任务必须满足 `requirements.md` 中定义的 acceptance criteria
3. **修改后同步规格**：代码变更后，同步更新架构/需求文档，保持规格与实现一致
4. **任务拆解**：大任务必须先写入 `.claude/architecture.md` 的 dependency graph，再按顺序实现
5. **测试对齐**：测试用例必须覆盖 `requirements.md` 中的 acceptance criteria

## 项目技术栈
- FastAPI (Python async)
- SQLAlchemy async + PostgreSQL 14
- Vanilla JS SPA (前端)
- Docker Compose 部署
- GitHub REST API (PR 创建)

## 项目结构
- `app/api/` - 路由处理层
- `app/domain/` - 业务逻辑层
- `app/infrastructure/` - 基础设施层（DB、GitHub client）
- `app/ui/` - 服务端渲染的 SPA
- `.claude/` - 项目规格目录（architecture.md + requirements.md）