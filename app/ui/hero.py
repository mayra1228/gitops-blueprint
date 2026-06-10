_HERO_HTML = """    <section class="hero" data-component="hero-overview"><div class="card heroCard"><div class="eyebrow">Terraform GitOps · Control Plane</div><h1>标准化的 Terraform 基础设施变更管理</h1><p>统一的可视化工作流：Git 仓库扫描 → 变更 Draft 创建 → Terraform Patch 预览 → 校验 → Plan Dry-Run → 审批 → CI/CD Trigger，全程审计追踪</p><div class="flow"><div class="flowNode"><b class="flowNum">1</b><span>Register &amp; Scan</span><small>注册 Repo / 扫描 TF</small></div><div class="flowArrow">→</div><div class="flowNode"><b class="flowNum">2</b><span>Patch &amp; Plan</span><small>Diff + terraform plan</small></div><div class="flowArrow">→</div><div class="flowNode"><b class="flowNum">3</b><span>Approve &amp; Trigger</span><small>Approval + CICD PR</small></div></div><div class="heroActions"><button class="btn" onclick="navigateTo('dashboard')">Command Center</button><button class="btn" onclick="navigateTo('capability-terraform_infra')">New TF Change</button></div></div><div class="card"><div class="eyebrow">Recent Activity</div><div class="activityFeed" id="activityFeed"><div class="empty">Loading...</div></div></div></section>
"""


def render_hero_html():
    return _HERO_HTML
