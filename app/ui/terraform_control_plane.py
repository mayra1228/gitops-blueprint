_TERRAFORM_CONTROL_PLANE_HTML = """<section data-component="terraform-control-plane">
<div class="card" style="margin-bottom:18px;background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.035));border-color:rgba(194,239,78,.22)">
  <div class="toolbar">
    <div>
      <div class="eyebrow">Resource Topology</div>
      <h2 style="font-size:28px">AWS &amp; K8S Infrastructure View</h2>
      <p style="color:var(--muted2);font-size:13px">只读拓扑发现视图 · 按资源大类聚合展示 · 先查看详情，再进入 Resource Management 管理资源变更</p>
    </div>
    <div style="display:flex;gap:10px;align-items:center">
      <select id="tcpEnvFilter" style="background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:12px">
        <option value="">All Envs</option>
        <option value="dev">dev</option>
        <option value="sit">sit</option>
        <option value="uat">uat</option>
        <option value="stg">stg</option>
        <option value="prf">prf</option>
        <option value="prod">prod</option>
      </select>
      <button class="btn" onclick="tcpLoadAll()" style="font-size:12px;padding:8px 16px">Refresh</button>
    </div>
  </div>
</div>

<div class="grid4" style="margin-bottom:18px">
  <div class="kpi"><span>Environments</span><strong id="tcpKpiEnvs">-</strong><small>detected layouts</small></div>
  <div class="kpi"><span>AWS Resources</span><strong id="tcpKpiAws">-</strong><small>aws_* scanned</small></div>
  <div class="kpi"><span>K8S Services</span><strong id="tcpKpiK8s">-</strong><small>k8s_* scanned</small></div>
  <div class="kpi"><span>Total Objects</span><strong id="tcpKpiResources">-</strong><small>all scanned types</small></div>
</div>

<div style="display:grid;grid-template-columns:280px 1fr;gap:18px;align-items:start">
  <!-- Left: Environments -->
  <div>
    <div class="card" style="padding:20px">
      <div class="eyebrow">Environments</div>
      <div id="tcpProjectTree" style="margin-top:10px;font-size:13px">
        <div class="empty">Loading environments...</div>
      </div>
    </div>
  </div>

  <!-- Right: Resource Topology + Inventory -->
  <div>
    <div class="card" style="padding:20px;margin-bottom:14px">
      <div class="eyebrow" style="margin-bottom:10px">Resource Families <span style="color:var(--muted2);font-size:10px;margin-left:6px">先按大类聚合，点击大类后查看具体 resource_type</span></div>
      <div id="tcpTopologyView" style="min-height:160px">
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px" id="tcpTopologyGrid">
          <div class="empty" style="grid-column:1/-1">Loading topology...</div>
        </div>
      </div>
      <div id="tcpFamilyDetail" style="display:none;margin-top:12px;padding:12px;border:1px solid rgba(255,255,255,.08);border-radius:10px;background:rgba(255,255,255,.02)">
        <div style="display:flex;justify-content:space-between;gap:10px;align-items:center;margin-bottom:8px">
          <div><div id="tcpFamilyTitle" style="font-size:13px;color:#f7f8f8;font-weight:600">-</div><div id="tcpFamilyDesc" style="font-size:10px;color:var(--muted2);margin-top:2px"></div></div>
          <button class="btn" onclick="tcpClearFamily()" style="font-size:10px;padding:4px 10px">Show All Families</button>
        </div>
        <div id="tcpFamilyTypes" style="display:flex;gap:6px;flex-wrap:wrap"></div>
      </div>
    </div>

    <div class="card" style="padding:20px">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
        <div class="eyebrow">Resource Inventory</div>
        <span style="font-size:10px;color:var(--muted2)">按 family / type / env 过滤 · 点击 View Detail 查看只读详情</span>
      </div>
      <div style="display:flex;gap:8px;margin-bottom:10px;flex-wrap:wrap">
        <select id="tcpTypeFilter" style="background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:6px;padding:5px 8px;font-size:11px;flex:1;min-width:120px">
          <option value="">All discovery types</option>
        </select>
        <input id="tcpSearchFilter" placeholder="Search id / name" style="background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:6px;padding:5px 8px;font-size:11px;flex:2;min-width:120px">
      </div>
      <div class="tableWrap" style="margin-top:6px">
        <table class="table">
          <thead><tr><th>Resource</th><th>Type</th><th>Env</th><th>Source</th><th>Action</th></tr></thead>
          <tbody id="tcpResourceRows"><tr><td colspan="5" class="empty">Loading resources...</td></tr></tbody>
        </table>
      </div>
      <div style="margin-top:6px;font-size:10px;color:var(--muted2)"><span id="tcpResourceCount">-</span></div>
    </div>

    <div id="tcpDetailPanel" class="card" style="display:none;margin-top:14px;padding:20px;border-color:rgba(194,239,78,.22)">
      <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start;margin-bottom:10px">
        <div>
          <div class="eyebrow">Resource Detail</div>
          <h3 id="tcpDetailTitle" style="font-size:16px;margin:4px 0 0">-</h3>
        </div>
        <button class="btn" onclick="document.getElementById('tcpDetailPanel').style.display='none'" style="font-size:10px;padding:4px 10px">Close</button>
      </div>
      <div id="tcpDetailMeta" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:10px"></div>
      <pre id="tcpDetailSpec" style="margin:0;background:#050607;border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:12px;font-family:monospace;font-size:10px;line-height:1.45;color:#d0d6e0;max-height:240px;overflow:auto;white-space:pre-wrap"></pre>
      <div style="display:flex;align-items:center;gap:10px;margin-top:12px">
        <button class="btn" onclick="tcpManageSelectedChange()" style="background:#5e6ad2;border-color:#6f76e6;font-size:12px;padding:8px 16px">Manage Change</button>
        <span style="font-size:10px;color:var(--muted2)">打开 Resource Management，并带入当前 object / type / env 上下文</span>
      </div>
    </div>

    <div class="card" style="margin-top:14px;padding:20px">
      <div class="eyebrow" style="margin-bottom:8px">Current Supported Change Coverage</div>
      <div style="font-size:11px;color:var(--muted2);margin-bottom:10px">Import/scan 可以发现更多类型；当前支持创建变更的范围按阶段逐步开放。</div>
      <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px">
        <div style="padding:10px;border:1px solid rgba(255,255,255,.08);border-radius:10px;background:rgba(255,255,255,.02)"><b style="font-size:12px;color:#f7f8f8">AWS Terraform Resources</b><div style="font-size:10px;color:var(--muted2);margin-top:4px">aws_* HCL block assignment updates</div></div>
        <div style="padding:10px;border:1px solid rgba(255,255,255,.08);border-radius:10px;background:rgba(255,255,255,.02)"><b style="font-size:12px;color:#f7f8f8">K8S / ODP Services</b><div style="font-size:10px;color:var(--muted2);margin-top:4px">ODP/resources service YAML updates</div></div>
        <div style="padding:10px;border:1px solid rgba(255,255,255,.08);border-radius:10px;background:rgba(255,255,255,.02)"><b style="font-size:12px;color:#f7f8f8">Modules & Variables</b><div style="font-size:10px;color:var(--muted2);margin-top:4px">Use dedicated Module / Variable pages</div></div>
        <div style="padding:10px;border:1px solid rgba(255,255,255,.08);border-radius:10px;background:rgba(255,255,255,.02)"><b style="font-size:12px;color:#f7f8f8">Read-only for now</b><div style="font-size:10px;color:var(--muted2);margin-top:4px">terraform_output and unsupported provider-specific types</div></div>
      </div>
    </div>
  </div>
</div>
</section>"""

_TERRAFORM_CONTROL_PLANE_SCRIPT = """
var TCP_RESOURCE_ICONS = {
  aws_vpc: '&#127760;', aws_subnet: '&#127966;', aws_instance: '&#128187;',
  aws_db_instance: '&#128451;', aws_s3_bucket: '&#128193;', aws_security_group: '&#128274;',
  aws_iam_role: '&#128100;', aws_eks_cluster: '&#9881;', aws_elasticache_cluster: '&#9889;',
  aws_sm: '&#128272;', k8s_service: '&#9096;', cloudwatch_metric_alarm: '&#128276;',
  default: '&#9632;'
};

// Resource Topology groups detailed resource_type values into high-level families.
var TCP_RESOURCE_FAMILIES = [
  {id:'aws', label:'AWS Resources', prefixes:['aws_'], desc:'VPC, subnet, security, secrets, storage and service-level AWS resources'},
  {id:'k8s', label:'K8S / ODP Services', prefixes:['k8s_'], desc:'Kubernetes service objects discovered from ODP resource YAML'},
  {id:'cloudwatch', label:'CloudWatch', prefixes:['cloudwatch_'], desc:'Metric alarms and expressions used for observability'}
];
var _tcpFamilyFilter = '';
var _tcpTypeStats = [];

function tcpFamilyForType(rt) {
  for (var i = 0; i < TCP_RESOURCE_FAMILIES.length; i++) {
    var f = TCP_RESOURCE_FAMILIES[i];
    for (var j = 0; j < f.prefixes.length; j++) {
      if (rt.startsWith(f.prefixes[j])) return f;
    }
  }
  return null;
}

function tcpIsInfraType(rt) {
  return !!tcpFamilyForType(rt);
}

function tcpResourceIcon(type) {
  return TCP_RESOURCE_ICONS[type] || TCP_RESOURCE_ICONS.default;
}

async function tcpLoadSummary() {
  try {
    var s = await api('/inventory/summary');
    var k = s.kpis;
    document.getElementById('tcpKpiResources').textContent = k.total_objects || 0;
    document.getElementById('tcpKpiEnvs').textContent = k.environments || 0;
    var byType = k.by_resource_type || s.by_resource_type || {};
    var awsCount = 0;
    var k8sCount = 0;
    Object.keys(byType).forEach(function(rt) {
      if (rt.startsWith('aws_') || rt.startsWith('cloudwatch_')) awsCount += byType[rt];
      if (rt.startsWith('k8s_')) k8sCount += byType[rt];
    });
    var awsEl = document.getElementById('tcpKpiAws');
    var k8sEl = document.getElementById('tcpKpiK8s');
    if (awsEl) awsEl.textContent = awsCount;
    if (k8sEl) k8sEl.textContent = k8sCount;
  } catch(e) { console.error(e); }
}


async function tcpLoadTopology() {
  try {
    var summary = await api('/inventory/summary');
    var byType = (summary.kpis && summary.kpis.by_resource_type) || summary.by_resource_type || {};
    var types = Object.keys(byType).map(function(rt) {
      return {resource_type: rt, count: byType[rt]};
    }).filter(function(t) { return tcpIsInfraType(t.resource_type); }).sort(function(a, b) { return b.count - a.count; });
    _tcpTypeStats = types;
    var grid = document.getElementById('tcpTopologyGrid');
    if (!types.length) { grid.innerHTML = '<div class="empty" style="grid-column:1/-1">No supported topology resources scanned yet.</div>'; return; }
    grid.innerHTML = TCP_RESOURCE_FAMILIES.map(function(f) {
      var familyTypes = types.filter(function(t) { return tcpFamilyForType(t.resource_type).id === f.id; });
      var total = familyTypes.reduce(function(sum, t) { return sum + t.count; }, 0);
      var active = _tcpFamilyFilter === f.id;
      return '<div style="border:1px solid '+(active?'rgba(194,239,78,.75)':'rgba(255,255,255,.1)')+';border-radius:12px;padding:14px 12px;background:'+(active?'rgba(194,239,78,.10)':'rgba(255,255,255,.025)')+';cursor:pointer" onclick="tcpSelectFamily(\\''+esc(f.id)+'\\')"><div style="display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:8px"><div style="font-size:13px;font-weight:700;color:#f7f8f8">'+esc(f.label)+'</div><span class="chip">'+total+'</span></div><div style="font-size:10px;color:var(--muted2);min-height:28px">'+esc(f.desc)+'</div><div style="font-size:10px;color:var(--muted2);margin-top:8px">'+familyTypes.length+' resource types · click for details</div></div>';
    }).join('');
    if (!_tcpFamilyFilter && types.length) tcpRenderFamilyDetail('');
    else tcpRenderFamilyDetail(_tcpFamilyFilter);
    // Populate type filter with infra types only.
    var typeFilter = document.getElementById('tcpTypeFilter');
    if (typeFilter) {
      typeFilter.innerHTML = '<option value="">All discovery types</option>' + types.map(function(t) {
        return '<option value="'+esc(t.resource_type)+'">'+esc(t.resource_type)+' ('+t.count+')</option>';
      }).join('');
    }
  } catch(e) { console.error(e); }
}

function tcpRenderFamilyDetail(familyId) {
  var panel = document.getElementById('tcpFamilyDetail');
  var title = document.getElementById('tcpFamilyTitle');
  var desc = document.getElementById('tcpFamilyDesc');
  var typesEl = document.getElementById('tcpFamilyTypes');
  if (!panel || !title || !desc || !typesEl) return;
  if (!familyId) {
    panel.style.display = 'none';
    return;
  }
  var family = TCP_RESOURCE_FAMILIES.find(function(f) { return f.id === familyId; });
  if (!family) return;
  var familyTypes = _tcpTypeStats.filter(function(t) { return tcpFamilyForType(t.resource_type).id === family.id; });
  panel.style.display = 'block';
  title.textContent = family.label + ' · ' + familyTypes.length + ' resource types';
  desc.textContent = family.desc;
  typesEl.innerHTML = familyTypes.length ? familyTypes.map(function(t) {
    return '<button class="btn" onclick="tcpSelectType(\\''+esc(t.resource_type)+'\\')" style="font-size:10px;padding:4px 9px;background:rgba(255,255,255,.04)">'+esc(t.resource_type)+' <b>'+t.count+'</b></button>';
  }).join('') : '<span class="empty">No resource types in this family.</span>';
}

async function tcpLoadResources() {
  try {
    var env = document.getElementById('tcpEnvFilter') ? document.getElementById('tcpEnvFilter').value : '';
    var type = document.getElementById('tcpTypeFilter') ? document.getElementById('tcpTypeFilter').value : '';
    var q = document.getElementById('tcpSearchFilter') ? document.getElementById('tcpSearchFilter').value : '';
    var qs = new URLSearchParams();
    if (env) qs.set('env', env);
    if (type) qs.set('resource_type', type);
    if (q) qs.set('q', q);
    qs.set('limit', '300');
    var payload = await api('/inventory/objects?' + qs.toString());
    // Filter to supported topology families if no specific type selected.
    var allItems = payload.items || [];
    var items = type ? allItems : allItems.filter(function(x) { return tcpIsInfraType(x.resource_type); });
    if (!type && _tcpFamilyFilter) {
      items = items.filter(function(x) {
        var family = tcpFamilyForType(x.resource_type);
        return family && family.id === _tcpFamilyFilter;
      });
    }
    items = items.slice(0, 150);
    var count = document.getElementById('tcpResourceCount');
    if (count) count.textContent = items.length + ' resources' + (_tcpFamilyFilter ? ' in ' + _tcpFamilyFilter : '') + (env ? ' / ' + env : '');
    var rows = document.getElementById('tcpResourceRows');
    rows.innerHTML = items.length ? items.map(function(x) {
      var src = x.source || {};
      return '<tr onclick="tcpOpenResourceDetail(\\'' + esc(x.id) + '\\')" style="cursor:pointer"><td><div class="cellMain"><b>' + esc(x.display_name) + '</b><div class="muted mono" style="font-size:10px">' + esc(x.id) + '</div></div></td><td><span class="pill">' + esc(x.resource_type) + '</span></td><td>' + esc(x.scope ? x.scope.env : '-') + '</td><td><div class="mono cellPath" style="font-size:10px;max-width:160px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="' + esc(src.path||'') + '">' + esc(src.path || '-') + '</div></td><td><button class="btn" onclick="event.stopPropagation();tcpOpenResourceDetail(\\'' + esc(x.id) + '\\')" style="font-size:9px;padding:3px 8px">View Detail</button></td></tr>';
    }).join('') : '<tr><td colspan="5" class="empty">No supported topology resources found. Register a project and run a scan first.</td></tr>';
  } catch(e) { console.error(e); }
}

async function tcpOpenResourceDetail(objectId) {
  try {
    var detail = await api('/inventory/objects/' + encodeURIComponent(objectId));
    window._tcpSelectedObject = detail;
    var panel = document.getElementById('tcpDetailPanel');
    var title = document.getElementById('tcpDetailTitle');
    var meta = document.getElementById('tcpDetailMeta');
    var spec = document.getElementById('tcpDetailSpec');
    if (title) title.textContent = detail.display_name || detail.id;
    var scope = detail.scope || {};
    var source = detail.source || {};
    if (meta) {
      meta.innerHTML = [
        '<span class="chip">' + esc(detail.resource_type || '-') + '</span>',
        '<span class="chip">env: ' + esc(scope.env || '-') + '</span>',
        '<span class="chip">source: ' + esc(source.path || '-') + '</span>',
      ].join('');
    }
    if (spec) spec.textContent = JSON.stringify(detail.spec || {}, null, 2);
    if (panel) {
      panel.style.display = 'block';
      panel.scrollIntoView({behavior:'smooth', block:'nearest'});
    }
  } catch(e) { console.error(e); }
}

function tcpManageSelectedChange() {
  var detail = window._tcpSelectedObject;
  if (!detail) return;
  var ctx = {
    source: 'Resource Topology',
    target: 'terraform_infra',
    object_id: detail.id,
    display_name: detail.display_name || detail.id,
    resource_type: detail.resource_type || '',
    env: (detail.scope || {}).env || ''
  };
  window._capTransferContext = ctx;
  Promise.resolve(navigateTo('capability-terraform_infra')).then(function() {
    setTimeout(function() {
      if (typeof capApplyTransfer_terraform_infra === 'function') {
        capApplyTransfer_terraform_infra(ctx);
      }
    }, 80);
  });
}

function tcpBuildProjectTree(envs) {
  var tree = document.getElementById('tcpProjectTree');
  if (!envs || !envs.length) { tree.innerHTML = '<div class="empty">No environments detected. Import a project first.</div>'; return; }
  tree.innerHTML = '<div style="display:flex;flex-direction:column;gap:4px">' + envs.map(function(e) {
    return '<div style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:6px;background:rgba(255,255,255,.03);cursor:pointer" onclick="tcpSelectEnv(\\''+esc(e.env)+'\\')"><span style="color:#c2ef4e;font-size:11px">&#9654;</span><span style="font-size:12px;color:#f7f8f8">'+esc(e.env)+'</span><span style="margin-left:auto;font-size:10px;color:var(--muted2)">'+e.count+' resources</span></div>';
  }).join('') + '</div>';
}

function tcpRenderVarSources(env) {
  var panel = document.getElementById('tcpVarSources');
  var sources = [
    { label: 'terraform.tfvars', hint: env + '/ tfvars file', type: 'tfvars' },
    { label: 'Workspace Variables', hint: 'TF Cloud / Atlantis workspace', type: 'workspace' },
    { label: 'CI Variables', hint: 'Pipeline environment variables', type: 'ci' },
    { label: 'Secrets', hint: 'Vault / AWS SSM / GitHub Secrets', type: 'secret' },
  ];
  panel.innerHTML = sources.map(function(s) {
    return '<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid rgba(255,255,255,.06);border-radius:8px"><span class="chip" style="font-size:10px">'+esc(s.type)+'</span><div><div style="font-size:12px;color:#f7f8f8">'+esc(s.label)+'</div><div style="font-size:10px;color:var(--muted2)">'+esc(s.hint)+'</div></div></div>';
  }).join('');
}

function tcpSelectEnv(env) {
  var f = document.getElementById('tcpEnvFilter');
  if (f) f.value = env;
  tcpLoadResources();
}

function tcpSelectFamily(familyId) {
  _tcpFamilyFilter = familyId;
  var typeF = document.getElementById('tcpTypeFilter');
  if (typeF) typeF.value = '';
  tcpRenderFamilyDetail(familyId);
  tcpLoadTopology();
  tcpLoadResources();
}

function tcpClearFamily() {
  _tcpFamilyFilter = '';
  var typeF = document.getElementById('tcpTypeFilter');
  if (typeF) typeF.value = '';
  tcpRenderFamilyDetail('');
  tcpLoadTopology();
  tcpLoadResources();
}

function tcpSelectType(type) {
  var family = tcpFamilyForType(type);
  _tcpFamilyFilter = family ? family.id : '';
  var typeF = document.getElementById('tcpTypeFilter');
  if (typeF) typeF.value = type;
  tcpRenderFamilyDetail(_tcpFamilyFilter);
  tcpLoadTopology();
  tcpLoadResources();
}

function tcpFilterByType(type) {
  tcpSelectType(type);
}

async function tcpLoadAll() {
  await tcpLoadSummary();
  await tcpLoadTopology();
  try {
    var o = await api('/inventory/overview');
    tcpBuildProjectTree(o.env_distribution || []);
  } catch(e) {}
  await tcpLoadResources();
}

function bindTerraformControlPlaneEvents() {
  var envF = document.getElementById('tcpEnvFilter');
  if (envF) envF.addEventListener('change', tcpLoadResources);
  var typeF = document.getElementById('tcpTypeFilter');
  if (typeF) typeF.addEventListener('change', tcpLoadResources);
  var searchF = document.getElementById('tcpSearchFilter');
  if (searchF) searchF.addEventListener('input', function() { clearTimeout(window.__tcpQ); window.__tcpQ = setTimeout(tcpLoadResources, 200); });
}
"""


def render_terraform_control_plane_html():
    return _TERRAFORM_CONTROL_PLANE_HTML


def terraform_control_plane_script():
    return _TERRAFORM_CONTROL_PLANE_SCRIPT
