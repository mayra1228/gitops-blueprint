_ADAPTER_PAGE_HTML = """<section data-component="adapter-page">
<div class="card" style="margin-bottom:18px;background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.035));border-color:rgba(194,239,78,.22)">
<div class="toolbar"><div><div class="eyebrow">Delivery / Adapters</div><h2 style="font-size:28px">Adapter Management</h2><p>CICD · Infrastructure · Repository · Approval — 四类适配器配置</p></div></div>
</div>

<div class="grid4" style="margin-bottom:18px">
<div class="kpi"><span>CICD Adapters</span><strong id="kpiCicdCount">-</strong><small>pipeline triggers</small></div>
<div class="kpi"><span>Infra Adapters</span><strong id="kpiInfraCount">-</strong><small>TF executors</small></div>
<div class="kpi"><span>Repo Adapters</span><strong id="kpiRepoCount">-</strong><small>git providers</small></div>
<div class="kpi"><span>Approval Adapters</span><strong id="kpiApprovalCount">-</strong><small>review workflows</small></div>
</div>

<div class="card" style="margin-bottom:18px">
<div class="eyebrow" style="margin-bottom:10px">&#9654; CICD Adapters <small style="color:var(--muted2);font-size:10px;margin-left:8px">Jenkins · GitHub Actions · GitLab CI · Azure DevOps · Internal Pipeline</small></div>
<div class="tableWrap"><table class="table"><thead><tr><th>Name</th><th>Platform</th><th>Trigger Method</th><th>Auth</th><th>Status</th></tr></thead><tbody id="adpCicdRows"><tr><td colspan="5" class="empty">Loading...</td></tr></tbody></table></div>
</div>

<div class="card" style="margin-bottom:18px">
<div class="eyebrow" style="margin-bottom:10px">&#9654; Infrastructure Adapters <small style="color:var(--muted2);font-size:10px;margin-left:8px">Terraform CLI · Terraform Cloud · Atlantis · Spacelift · Internal IaC</small></div>
<div class="tableWrap"><table class="table"><thead><tr><th>Name</th><th>Platform</th><th>Plan Method</th><th>Apply Method</th><th>Status</th></tr></thead><tbody id="adpInfraRows"><tr><td colspan="5" class="empty">Loading...</td></tr></tbody></table></div>
</div>

<div class="card" style="margin-bottom:18px">
<div class="eyebrow" style="margin-bottom:10px">&#9654; Repository Adapters <small style="color:var(--muted2);font-size:10px;margin-left:8px">GitHub · GitLab · Bitbucket · Internal Git</small></div>
<div class="tableWrap"><table class="table"><thead><tr><th>Name</th><th>Platform</th><th>PR Creation</th><th>Auth Method</th><th>Status</th></tr></thead><tbody id="adpRepoRows"><tr><td colspan="5" class="empty">Loading...</td></tr></tbody></table></div>
</div>

<div class="card" style="margin-bottom:18px">
<div class="eyebrow" style="margin-bottom:10px">&#9654; Approval Adapters <small style="color:var(--muted2);font-size:10px;margin-left:8px">ServiceNow · Jira · GitHub PR Review · Internal Approval</small></div>
<div class="tableWrap"><table class="table"><thead><tr><th>Name</th><th>Platform</th><th>Workflow</th><th>Status</th></tr></thead><tbody id="adpApprovalRows"><tr><td colspan="4" class="empty">Loading...</td></tr></tbody></table></div>
</div>
</section>"""

_CICD_PLATFORMS = [
    {"name": "GitHub Actions", "platform": "github_actions", "trigger": "workflow_dispatch", "auth": "GITHUB_TOKEN"},
    {"name": "Jenkins", "platform": "jenkins", "trigger": "REST API / webhook", "auth": "API Token"},
    {"name": "GitLab CI", "platform": "gitlab_ci", "trigger": "pipeline trigger", "auth": "CI Token"},
    {"name": "Azure DevOps", "platform": "azure_devops", "trigger": "REST API", "auth": "PAT"},
]
_INFRA_PLATFORMS = [
    {"name": "Terraform CLI", "platform": "terraform_cli", "plan": "terraform plan", "apply": "terraform apply"},
    {"name": "Terraform Cloud", "platform": "terraform_cloud", "plan": "API run", "apply": "API run"},
    {"name": "Atlantis", "platform": "atlantis", "plan": "PR comment", "apply": "PR comment"},
    {"name": "Spacelift", "platform": "spacelift", "plan": "stack run", "apply": "stack run"},
]
_REPO_PLATFORMS = [
    {"name": "GitHub", "platform": "github", "pr": "REST API", "auth": "GITHUB_TOKEN"},
    {"name": "GitLab", "platform": "gitlab", "pr": "Merge Request API", "auth": "Private Token"},
    {"name": "Bitbucket", "platform": "bitbucket", "pr": "REST API", "auth": "App Password"},
]
_APPROVAL_PLATFORMS = [
    {"name": "GitHub PR Review", "platform": "github_pr", "workflow": "PR review + merge gate"},
    {"name": "ServiceNow", "platform": "servicenow", "workflow": "Change Request ticket"},
    {"name": "Jira Approval", "platform": "jira", "workflow": "Jira issue approval flow"},
    {"name": "Internal Platform", "platform": "internal", "workflow": "Custom approval API"},
]

import json as _json

_ADAPTER_PAGE_SCRIPT = (
    "var _CICD_PLATFORMS=" + _json.dumps(_CICD_PLATFORMS) + ";"
    "var _INFRA_PLATFORMS=" + _json.dumps(_INFRA_PLATFORMS) + ";"
    "var _REPO_PLATFORMS=" + _json.dumps(_REPO_PLATFORMS) + ";"
    "var _APPROVAL_PLATFORMS=" + _json.dumps(_APPROVAL_PLATFORMS) + ";"
    + """
async function loadAdapterPage(){
  try{
    var infra=await api('/api/infrastructure-adapters');
    var gitAdapters=infra.git||[];
    var execAdapters=infra.execution||[];

    // CICD adapters: merge registered execution adapters + known platforms
    var cicdRegistered=execAdapters.map(function(a){return {name:a.name,platform:a.label||'custom',trigger:'blueprint()',auth:'configured'};});
    var cicdAll=cicdRegistered.length?cicdRegistered:_CICD_PLATFORMS;
    document.getElementById('kpiCicdCount').textContent=cicdAll.length;
    document.getElementById('adpCicdRows').innerHTML=cicdAll.map(function(a){
      var isRegistered=cicdRegistered.some(function(r){return r.name===a.name;});
      return '<tr><td><div class="cellMain"><b>'+esc(a.name)+'</b></div></td><td><span class="chip">'+esc(a.platform)+'</span></td><td><code class="mono" style="font-size:11px">'+esc(a.trigger||a.trigger||'')+'</code></td><td><code class="mono" style="font-size:11px">'+esc(a.auth||'-')+'</code></td><td><span class="chip '+(isRegistered?'primary':'')+'">'+esc(isRegistered?'registered':'available')+'</span></td></tr>';
    }).join('');

    // Infra adapters: show known platforms
    document.getElementById('kpiInfraCount').textContent=_INFRA_PLATFORMS.length;
    document.getElementById('adpInfraRows').innerHTML=_INFRA_PLATFORMS.map(function(a){
      return '<tr><td><div class="cellMain"><b>'+esc(a.name)+'</b></div></td><td><span class="chip">'+esc(a.platform)+'</span></td><td><code class="mono" style="font-size:11px">'+esc(a.plan)+'</code></td><td><code class="mono" style="font-size:11px">'+esc(a.apply)+'</code></td><td><span class="chip" style="border-color:rgba(250,127,170,.35);background:rgba(250,127,170,.12);color:#ffc0d3">adapter</span></td></tr>';
    }).join('');

    // Repo adapters: merge registered git adapters + known platforms
    var repoRegistered=gitAdapters.map(function(a){return {name:a.name,platform:a.label||'git',pr:'create_pr',auth:'token-based',registered:true};});
    var repoAll=repoRegistered.length?repoRegistered.concat(_REPO_PLATFORMS.filter(function(p){return !repoRegistered.some(function(r){return r.platform===p.platform;});})):_REPO_PLATFORMS;
    document.getElementById('kpiRepoCount').textContent=repoAll.length;
    document.getElementById('adpRepoRows').innerHTML=repoAll.map(function(a){
      return '<tr><td><div class="cellMain"><b>'+esc(a.name)+'</b></div></td><td><span class="chip">'+esc(a.platform)+'</span></td><td><code class="mono" style="font-size:11px">'+esc(a.pr||a.pr||'')+'</code></td><td><code class="mono" style="font-size:11px">'+esc(a.auth||'-')+'</code></td><td><span class="chip '+(a.registered?'primary':'')+'">'+esc(a.registered?'registered':'available')+'</span></td></tr>';
    }).join('');

    // Approval adapters
    document.getElementById('kpiApprovalCount').textContent=_APPROVAL_PLATFORMS.length;
    document.getElementById('adpApprovalRows').innerHTML=_APPROVAL_PLATFORMS.map(function(a){
      return '<tr><td><div class="cellMain"><b>'+esc(a.name)+'</b></div></td><td><span class="chip">'+esc(a.platform)+'</span></td><td><code class="mono" style="font-size:11px">'+esc(a.workflow)+'</code></td><td><span class="chip" style="border-color:rgba(250,127,170,.35);background:rgba(250,127,170,.12);color:#ffc0d3">adapter</span></td></tr>';
    }).join('');
  }catch(e){
    ['adpCicdRows','adpInfraRows','adpRepoRows','adpApprovalRows'].forEach(function(id){
      var el=document.getElementById(id);if(el)el.innerHTML='<tr><td colspan="5" class="empty">Failed to load adapters</td></tr>';
    });
  }
}"""
)


def render_adapter_page_html():
    return _ADAPTER_PAGE_HTML


def adapter_page_script():
    return _ADAPTER_PAGE_SCRIPT
