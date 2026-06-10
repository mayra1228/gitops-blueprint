_IMPORT_PAGE_HTML = """<section data-component="import-page">
<div class="card" style="margin-bottom:18px;background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.035));border-color:rgba(194,239,78,.22)">
<div class="toolbar"><div><div class="eyebrow">Import — Onboarding</div><h2 style="font-size:28px">Import Existing Project</h2><p>Connect an existing Terraform or infrastructure repository to the platform. The platform will scan for .tf and .yaml files, then register the project for visualization, CI/CD, and approval workflows.</p></div></div>
</div>

<div class="importWizard">
<div class="importStepIndicator">
<div class="importStep active" id="importStepConnect"><span class="importStepNum">1</span>Connect</div>
<div class="importStepArrow">→</div>
<div class="importStep" id="importStepDiscover"><span class="importStepNum">2</span>Discover</div>
<div class="importStepArrow">→</div>
<div class="importStep" id="importStepReview"><span class="importStepNum">3</span>Review</div>
</div>

<div class="importWizardBody">
<div class="importFormPanel" id="importConnectPanel">
<h3>Connect Repository</h3>
<p class="muted">Enter the Git repository URL and select adapters for your project.</p>
<form id="importConnectForm" class="importForm">
<label>Repository URL<span class="muted">e.g. https://github.com/my-org/terraform-infra</span><input id="importRepoUrl" type="text" placeholder="https://github.com/org/repo" /></label>
<label>Project Name (optional)<span class="muted">Auto-detected from repo if empty</span><input id="importProjectName" type="text" placeholder="my-terraform-infra" /></label>
<label>Git Provider<select id="importGitAdapter"></select></label>
<label>Execution Adapter<select id="importExecAdapter"></select></label>
<label>Terraform Root<span class="muted">Root directory for Terraform files</span><input id="importTerraformRoot" type="text" value="infra" /></label>
<label>Workflow ID<span class="muted">GitHub Actions workflow file</span><input id="importWorkflowId" type="text" value="terraform-plan-apply.yml" /></label>
<label>Target Cluster<span class="muted">Allowed mutable target cluster</span><input id="importClusterName" type="text" value="kind-gitops-sandbox" /></label>
<div class="draftActions" style="margin-top:16px">
<button class="btn" type="button" id="importDiscoverBtn">Discover & Scan</button>
<span id="importConnectStatus" class="muted" style="font-size:12px"></span>
</div>
</form>
</div>

<div class="importFormPanel" id="importDiscoverPanel" style="display:none">
<h3>Scan Results</h3>
<p class="muted" id="importDiscoverRepo">Scanning repository...</p>
<div class="grid4" style="margin-top:12px">
<div class="kpi"><span>Terraform Files</span><strong id="kpiImportTfFiles">-</strong><small>.tf files found</small></div>
<div class="kpi"><span>Terraform Resources</span><strong id="kpiImportTfResources">-</strong><small>resource blocks</small></div>
<div class="kpi"><span>ODP YAML Objects</span><strong id="kpiImportOdpObjects">-</strong><small>.yaml files</small></div>
<div class="kpi"><span>Providers</span><strong id="kpiImportProviders">-</strong><small>detected</small></div>
</div>
<div class="analytics" style="margin-top:14px">
<div class="card">
<div class="eyebrow">Terraform Resource Types</div>
<div class="bars" id="importTfResourceBars"><div class="empty">No terraform resources found</div></div>
</div>
<div class="card">
<div class="eyebrow">Terraform Modules</div>
<div id="importTfModules"><div class="empty">No modules found</div></div>
</div>
</div>
<div id="importErrors" style="display:none;margin-top:12px">
<div class="eyebrow" style="color:var(--pink)">Scan Errors</div>
<div id="importErrorsList"></div>
</div>
<div class="draftActions" style="margin-top:16px">
<button class="btn" type="button" id="importBackToConnectBtn" style="background:var(--muted)">← Back</button>
<button class="btn" type="button" id="importRegisterBtn">Register Project</button>
<span id="importRegisterStatus" class="muted" style="font-size:12px"></span>
</div>
</div>

<div class="importFormPanel" id="importDonePanel" style="display:none">
<div class="skeletonSuccess" style="margin-bottom:16px">
<b>&#10003; Project imported!</b>
<span id="importDoneProjectName"></span>
<button class="btn" id="importDoneViewBtn" onclick="navigateTo('dashboard')">View Dashboard</button>
</div>
<div class="grid4" style="margin-top:12px">
<div class="kpi"><span>Total Objects</span><strong id="kpiImportDoneObjects">-</strong><small>in inventory</small></div>
<div class="kpi"><span>Resource Types</span><strong id="kpiImportDoneTypes">-</strong><small>normalized</small></div>
<div class="kpi"><span>Environments</span><strong id="kpiImportDoneEnvs">-</strong><small>detected</small></div>
<div class="kpi"><span>Scan Status</span><strong id="kpiImportDoneStatus">-</strong><small>import result</small></div>
</div>
</div>
</div>
</div>
</section>"""

_IMPORT_SCRIPT = """// --- Import Wizard ---
let _importDiscoveredRepo = null;

function renderBarRows(items, labelKey, countKey) {
  const max = Math.max(1, ...items.map(x => x[countKey||'count']));
  return items.map(x => `<div class="barRow"><div class="barLabel" title="${esc(x[labelKey])}">${esc(x[labelKey])}</div><div class="barTrack"><div class="barFill" style="width:${Math.max(5, Math.round(x[countKey||'count'] / max * 100))}%"></div></div><div class="barCount">${x[countKey||'count']}</div></div>`).join('') || '<div class="empty">No data</div>';
}

async function loadImportAdapters() {
  try {
    const res = await fetch('/api/infrastructure-adapters');
    const data = await res.json();
    const gitSel = document.getElementById('importGitAdapter');
    const execSel = document.getElementById('importExecAdapter');
    gitSel.innerHTML = (data.git || []).map(a => `<option value="${esc(a.name)}">${esc(a.label)}</option>`).join('');
    execSel.innerHTML = (data.execution || []).map(a => `<option value="${esc(a.name)}">${esc(a.label)}</option>`).join('');
  } catch(e) {
    console.error('Failed to load adapters:', e);
  }
}

async function importDiscover() {
  const repoUrl = document.getElementById('importRepoUrl').value.trim();
  if (!repoUrl) {
    document.getElementById('importConnectStatus').textContent = 'Please enter a repository URL';
    return;
  }
  const provider = document.getElementById('importGitAdapter').value;
  const btn = document.getElementById('importDiscoverBtn');
  const status = document.getElementById('importConnectStatus');
  btn.disabled = true;
  btn.textContent = 'Scanning...';
  status.textContent = 'Cloning and scanning repository...';

  try {
    const res = await fetch('/api/projects/import', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        repo_url: repoUrl,
        provider: provider,
        git_adapter: document.getElementById('importGitAdapter').value,
        execution_adapter: document.getElementById('importExecAdapter').value,
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      status.textContent = data.detail || 'Import failed';
      btn.disabled = false;
      btn.textContent = 'Discover & Scan';
      return;
    }
    _importDiscoveredRepo = data;
    showDiscoverResults(data);
  } catch(e) {
    status.textContent = 'Network error: ' + e.message;
    btn.disabled = false;
    btn.textContent = 'Discover & Scan';
  }
}

function showDiscoverResults(data) {
  // Switch panels
  document.getElementById('importConnectPanel').style.display = 'none';
  document.getElementById('importDiscoverPanel').style.display = 'block';
  document.getElementById('importDonePanel').style.display = 'none';

  // Update step indicators
  document.getElementById('importStepConnect').classList.remove('active');
  document.getElementById('importStepDiscover').classList.add('active');
  document.getElementById('importStepReview').classList.remove('active');

  const repo = data.repo || {};
  document.getElementById('importDiscoverRepo').textContent = `${repo.org || '?'}/${repo.repo || '?'}`;

  const summary = data.summary || {};
  document.getElementById('kpiImportTfFiles').textContent = summary.terraform_files || 0;
  document.getElementById('kpiImportTfResources').textContent = summary.terraform_resources || 0;
  document.getElementById('kpiImportOdpObjects').textContent = summary.odp_yaml_objects || 0;
  document.getElementById('kpiImportProviders').textContent = (summary.terraform_providers || []).length;

  // Resource type bars
  const resourceTypes = summary.resource_types || {};
  const barItems = Object.entries(resourceTypes).map(([k, v]) => ({ resource_type: k, count: v }));
  document.getElementById('importTfResourceBars').innerHTML = barItems.length
    ? renderBarRows(barItems, 'resource_type', 'count')
    : '<div class="empty">No terraform resources found</div>';

  // Modules
  const tfScan = data.terraform_scan || {};
  const tfFiles = tfScan.files || [];
  const allModules = [];
  tfFiles.forEach(f => { (f.modules || []).forEach(m => allModules.push(m)); });
  document.getElementById('importTfModules').innerHTML = allModules.length
    ? allModules.map(m => `<div class="chip" style="margin:4px">${esc(m.name)} <b style="font-size:10px;color:var(--muted2)">${esc(m.source || '')}</b></div>`).join('')
    : '<div class="empty">No modules found</div>';

  // Errors
  const errors = data.errors || [];
  const errDiv = document.getElementById('importErrors');
  if (errors.length > 0) {
    errDiv.style.display = 'block';
    document.getElementById('importErrorsList').innerHTML = errors.map(e => `<div style="color:var(--pink);font-size:12px;margin:4px 0">${esc(e.type||'')}: ${esc(e.message)}</div>`).join('');
  } else {
    errDiv.style.display = 'none';
  }

  document.getElementById('importDiscoverBtn').disabled = false;
  document.getElementById('importDiscoverBtn').textContent = 'Discover & Scan';
  document.getElementById('importConnectStatus').textContent = '';
}

async function importRegister() {
  if (!_importDiscoveredRepo) return;
  const repo = _importDiscoveredRepo.repo || {};
  const repoUrl = document.getElementById('importRepoUrl').value.trim();
  let projectName = document.getElementById('importProjectName').value.trim();
  if (!projectName) projectName = repo.repo || 'imported-project';

  const btn = document.getElementById('importRegisterBtn');
  const status = document.getElementById('importRegisterStatus');
  btn.disabled = true;
  btn.textContent = 'Registering...';
  status.textContent = 'Creating project and persisting inventory...';

  try {
    const res = await fetch('/api/projects/import/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        project_name: projectName,
        repo_url: repoUrl,
        provider: repo.provider || '',
        git_adapter: document.getElementById('importGitAdapter').value,
        execution_adapter: document.getElementById('importExecAdapter').value,
        terraform_root: document.getElementById('importTerraformRoot').value || 'infra',
        workflow_id: document.getElementById('importWorkflowId').value || 'terraform-plan-apply.yml',
        cluster_name: document.getElementById('importClusterName').value || 'kind-gitops-sandbox',
      }),
    });
    const data = await res.json();
    if (!res.ok) {
      status.textContent = data.detail || 'Registration failed';
      btn.disabled = false;
      btn.textContent = 'Register Project';
      return;
    }
    showDoneResults(data);
  } catch(e) {
    status.textContent = 'Network error: ' + e.message;
    btn.disabled = false;
    btn.textContent = 'Register Project';
  }
}

function showDoneResults(data) {
  document.getElementById('importConnectPanel').style.display = 'none';
  document.getElementById('importDiscoverPanel').style.display = 'none';
  document.getElementById('importDonePanel').style.display = 'block';

  document.getElementById('importStepConnect').classList.remove('active');
  document.getElementById('importStepDiscover').classList.remove('active');
  document.getElementById('importStepReview').classList.add('active');

  const project = data.project || {};
  document.getElementById('importDoneProjectName').textContent = project.name || 'Imported Project';

  const scanSummary = data.scan_summary || {};
  document.getElementById('kpiImportDoneObjects').textContent = scanSummary.total_objects || 0;
  document.getElementById('kpiImportDoneTypes').textContent = Object.keys(scanSummary.by_resource_type || {}).length;
  document.getElementById('kpiImportDoneEnvs').textContent = Object.keys(scanSummary.by_env || {}).length;
  document.getElementById('kpiImportDoneStatus').textContent = scanSummary.errors > 0 ? 'partial' : 'success';

  // Update global project if needed
  if (project.id) {
    window.currentProject = project.id;
  }
}

function importGoBack() {
  document.getElementById('importConnectPanel').style.display = 'block';
  document.getElementById('importDiscoverPanel').style.display = 'none';
  document.getElementById('importDonePanel').style.display = 'none';
  document.getElementById('importStepConnect').classList.add('active');
  document.getElementById('importStepDiscover').classList.remove('active');
  document.getElementById('importStepReview').classList.remove('active');
  document.getElementById('importDiscoverBtn').disabled = false;
  document.getElementById('importDiscoverBtn').textContent = 'Discover & Scan';
  document.getElementById('importConnectStatus').textContent = '';
}

// Bind events
document.getElementById('importDiscoverBtn').addEventListener('click', importDiscover);
document.getElementById('importRegisterBtn').addEventListener('click', importRegister);
document.getElementById('importBackToConnectBtn').addEventListener('click', importGoBack);
document.getElementById('importRepoUrl').addEventListener('keydown', function(e) { if (e.key === 'Enter') { e.preventDefault(); importDiscover(); } });

// Load adapters on page init
loadImportAdapters();
"""


def render_import_wizard_html():
    return _IMPORT_PAGE_HTML


def import_wizard_script():
    return _IMPORT_SCRIPT