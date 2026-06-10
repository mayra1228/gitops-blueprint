from app.domain.capabilities.registry import build_default_capability_registry
from app.ui.adapter_page import adapter_page_script, render_adapter_page_html
from app.ui.admin_settings import admin_settings_script, render_admin_settings_html
from app.ui.assets import global_styles, shared_scripts
from app.ui.capability_page import capability_page_script, render_capability_page_html
from app.ui.dashboard import dashboard_script, render_dashboard_html
from app.ui.governance import governance_script, render_governance_html
from app.ui.header import render_header_html
from app.ui.import_wizard import import_wizard_script, render_import_wizard_html
from app.ui.inventory_dashboard import inventory_dashboard_script, render_inventory_dashboard_html, render_dashboard_kpi_html
from app.ui.orchestration import page_orchestration_script
from app.ui.skeleton_wizard import render_skeleton_wizard_html, skeleton_wizard_script
from app.ui.template_catalog import render_template_catalog_html, template_catalog_script
from app.ui.terraform_control_plane import render_terraform_control_plane_html, terraform_control_plane_script


_HISTORY_HTML = """<section><div class="card" style="height:auto"><div class="toolbar"><div><h2>History</h2><p>Change & scaffold history across all statuses</p></div><div style="display:flex;align-items:center;gap:8px"><label for="historyTypeFilter" style="font-size:12px;color:var(--muted)">Type:</label><select id="historyTypeFilter" style="background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:12px"><option value="">All</option><option value="change">Changes</option><option value="scaffold">Scaffolds</option></select></div></div><div class="tableMeta"><span id="historyCount">Loading...</span></div><div class="tableWrap"><table class="table"><thead><tr><th>Type</th><th>Name</th><th>Status</th><th>Detail</th><th>Time</th></tr></thead><tbody id="historyRows"><tr><td colspan="5" class="empty">Loading...</td></tr></tbody></table></div></div></section>"""

_capabilities = build_default_capability_registry().list_all()

# Build sidebar nav items for capabilities
_CAP_SIDEBAR_ITEMS = "\n".join(
    f'        <a class="sidebar-item{" active" if i == 0 else ""}" data-nav="capability-{c.id}" onclick="navigateTo(\'capability-{c.id}\')"><span class="nav-icon">&#9678;</span>{c.name}</a>'
    for i, c in enumerate(_capabilities)
)

# Build capability panels
_CAP_PANELS = []
for i, c in enumerate(_capabilities):
    cap_dict = {
        "id": c.id, "name": c.name, "description": c.description,
        "resource_types": c.resource_types, "change_types": c.change_types,
        "template_ids": c.template_ids, "object_id_prefix": c.object_id_prefix,
    }
    html = render_capability_page_html(cap_dict)
    active = ' active' if i == 0 else ''
    _CAP_PANELS.append(f'    <div id="tab-capability-{c.id}" class="tab-panel{active}">\n{html}\n    </div>')

_CAP_PANELS_HTML = "\n".join(_CAP_PANELS)
_CAP_SCRIPTS_COMBINED = "\n".join(capability_page_script({
    "id": c.id, "name": c.name, "description": c.description,
    "resource_types": c.resource_types, "change_types": c.change_types,
    "template_ids": c.template_ids, "object_id_prefix": c.object_id_prefix,
}) for c in _capabilities)

_PAGE_HTML = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>GitOps Platform -- Terraform Control Plane</title>
  <link href="https://fonts.googleapis.com/css2?family=Rubik:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
  <style>
{{GLOBAL_STYLES}}
  </style>
</head>
<body><div class="shell">
{{HEADER_HTML}}
  <div class="app-body">
    <nav class="sidebar">
      <div class="sidebar-section">
        <div class="sidebar-heading">Overview</div>
        <a class="sidebar-item active" data-nav="dashboard" onclick="navigateTo('dashboard')"><span class="nav-icon">&#9783;</span>Command Center</a>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-heading">Project Registry</div>
        <a class="sidebar-item" data-nav="import" onclick="navigateTo('import')"><span class="nav-icon">&#8623;</span>Register Project</a>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-heading">Discovery</div>
        <a class="sidebar-item" data-nav="tf-control-plane" onclick="navigateTo('tf-control-plane')"><span class="nav-icon">&#9678;</span>Resource Topology</a>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-heading">Resource Management</div>
{{CAP_SIDEBAR_ITEMS}}
      </div>
      <div class="sidebar-section">
        <div class="sidebar-heading">Standards &amp; Templates</div>
        <a class="sidebar-item" data-nav="skeleton" onclick="navigateTo('skeleton')"><span class="nav-icon">&#9733;</span>Skeleton Wizard</a>
        <a class="sidebar-item" data-nav="template-catalog" onclick="navigateTo('template-catalog')"><span class="nav-icon">&#9744;</span>Template Catalog</a>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-heading">Change Records</div>
        <a class="sidebar-item" data-nav="history" onclick="navigateTo('history')"><span class="nav-icon">&#8986;</span>Change History</a>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-heading">Delivery</div>
        <a class="sidebar-item" data-nav="adapter" onclick="navigateTo('adapter')"><span class="nav-icon">&#9881;</span>Adapters</a>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-heading">Governance</div>
        <a class="sidebar-item" data-nav="governance" onclick="navigateTo('governance')"><span class="nav-icon">&#9745;</span>SRE Evidence</a>
      </div>
      <div class="sidebar-section">
        <div class="sidebar-heading">Admin</div>
        <a class="sidebar-item" data-nav="admin" onclick="navigateTo('admin')"><span class="nav-icon">&#9881;</span>Settings</a>
      </div>
    </nav>
    <main class="content">
{{CAP_PANELS_HTML}}
    <div id="tab-tf-control-plane" class="tab-panel">
      {{TF_CONTROL_PLANE_HTML}}
    </div>
    <div id="tab-import" class="tab-panel">
      {{IMPORT_PAGE_HTML}}
    </div>
    <div id="tab-adapter" class="tab-panel">
      {{ADAPTER_PAGE_HTML}}
    </div>
    <div id="tab-skeleton" class="tab-panel">
      {{SKELETON_PAGE_HTML}}
    </div>
    <div id="tab-template-catalog" class="tab-panel">
      {{TEMPLATE_CATALOG_HTML}}
    </div>
    <div id="tab-dashboard" class="tab-panel active">
      {{DASHBOARD_HTML}}
    </div>
    <div id="tab-history" class="tab-panel">
      {{HISTORY_HTML}}
    </div>
    <div id="tab-governance" class="tab-panel">
      {{GOVERNANCE_HTML}}
    </div>
    <div id="tab-admin" class="tab-panel">
      {{ADMIN_SETTINGS_HTML}}
    </div>
    <div class="footerNote">GitOps Platform · Terraform Control Plane · Powered by FastAPI + PostgreSQL</div>
    </main>
  </div>
  {{SKELETON_WIZARD_HTML}}
</div><script>
{{SHARED_SCRIPTS}}{{DASHBOARD_SCRIPT}}{{IMPORT_WIZARD_SCRIPT}}{{ADAPTER_PAGE_SCRIPT}}{{SKELETON_WIZARD_SCRIPT}}{{TEMPLATE_CATALOG_SCRIPT}}{{CAP_SCRIPTS}}{{TF_CONTROL_PLANE_SCRIPT}}{{GOVERNANCE_SCRIPT}}{{ADMIN_SETTINGS_SCRIPT}}{{PAGE_ORCHESTRATION_SCRIPT}}</script></body></html>"""

_PAGE_HTML = (_PAGE_HTML
    .replace("{{GLOBAL_STYLES}}", global_styles())
    .replace("{{SHARED_SCRIPTS}}", shared_scripts())
    .replace("{{HEADER_HTML}}", render_header_html())
    .replace("{{CAP_SIDEBAR_ITEMS}}", _CAP_SIDEBAR_ITEMS)
    .replace("{{CAP_PANELS_HTML}}", _CAP_PANELS_HTML)
    .replace("{{TF_CONTROL_PLANE_HTML}}", render_terraform_control_plane_html())
    .replace("{{TF_CONTROL_PLANE_SCRIPT}}", terraform_control_plane_script())
    .replace("{{IMPORT_PAGE_HTML}}", render_import_wizard_html())
    .replace("{{IMPORT_WIZARD_SCRIPT}}", import_wizard_script())
    .replace("{{ADAPTER_PAGE_HTML}}", render_adapter_page_html())
    .replace("{{ADAPTER_PAGE_SCRIPT}}", adapter_page_script())
    .replace("{{DASHBOARD_HTML}}", render_dashboard_html())
    .replace("{{DASHBOARD_SCRIPT}}", dashboard_script())
    .replace("{{SKELETON_PAGE_HTML}}", render_skeleton_wizard_html())
    .replace("{{SKELETON_WIZARD_SCRIPT}}", skeleton_wizard_script())
    .replace("{{TEMPLATE_CATALOG_HTML}}", render_template_catalog_html())
    .replace("{{TEMPLATE_CATALOG_SCRIPT}}", template_catalog_script())
    .replace("{{GOVERNANCE_HTML}}", render_governance_html())
    .replace("{{GOVERNANCE_SCRIPT}}", governance_script())
    .replace("{{ADMIN_SETTINGS_HTML}}", render_admin_settings_html())
    .replace("{{ADMIN_SETTINGS_SCRIPT}}", admin_settings_script())
    .replace("{{CAP_SCRIPTS}}", _CAP_SCRIPTS_COMBINED)
    .replace("{{HISTORY_HTML}}", _HISTORY_HTML)
    .replace("{{PAGE_ORCHESTRATION_SCRIPT}}", page_orchestration_script())
)


def render_page_html():
    return _PAGE_HTML
