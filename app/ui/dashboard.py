_DASHBOARD_HTML = """<section data-component="dashboard-overview">
<div class="grid4" style="margin-bottom:18px">
<div class="kpi"><span>Terraform Resources</span><strong id="dbKpiObjects">-</strong><small>scanned inventory</small></div>
<div class="kpi"><span>Active Changes</span><strong id="dbKpiChanges">-</strong><small id="dbKpiPending" style="color:#f59e0b">pending: -</small></div>
<div class="kpi"><span>Environments</span><strong id="dbKpiEnvs">-</strong><small>detected scopes</small></div>
<div class="kpi"><span>Resource Types</span><strong id="dbKpiTypes">-</strong><small>normalized</small></div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;align-items:start">
<div>
<div class="card" style="margin-bottom:14px;padding:20px">
<div class="eyebrow">Environment Distribution</div>
<div class="bars" id="dbEnvBars" style="min-height:36px"><div class="empty">Loading...</div></div>
</div>
<div class="card" style="padding:20px">
<div class="eyebrow">Resource Type Distribution</div>
<div class="bars" id="dbTypeBars" style="min-height:36px"><div class="empty">Loading...</div></div>
<div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:12px" id="dbTypeChips"></div>
</div>
</div>

<div>
<div class="card" style="margin-bottom:14px;padding:20px">
<div class="eyebrow">Recent Changes</div>
<div id="dbRecentChanges" style="display:flex;flex-direction:column;gap:5px;max-height:360px;overflow-y:auto"><div class="empty">Loading...</div></div>
</div>
<div class="card" style="padding:20px">
<div class="eyebrow">Quick Actions</div>
<div style="display:flex;gap:10px;flex-wrap:wrap">
<button class="btn" onclick="dbScanInventory()" style="font-size:13px;padding:12px 24px;background:#5e6ad2;border-color:#6f76e6">Scan Inventory</button>
<button class="btn" onclick="navigateTo('capability-terraform_infra')" style="font-size:13px;padding:12px 24px">New TF Change</button>
<button class="btn" onclick="navigateTo('skeleton')" style="font-size:13px;padding:12px 24px">Bootstrap Project</button>
</div>
</div>
</div>
</div>
</section>"""

_DASHBOARD_SCRIPT = """function dbBarRows(items, labelKey){const max=Math.max(1,...items.map(function(x){return x.count;}));return items.map(function(x){return '<div class="barRow"><div class="barLabel" title="'+esc(x[labelKey])+'">'+esc(x[labelKey])+'</div><div class="barTrack"><div class="barFill" style="width:'+Math.max(5,Math.round(x.count/max*100))+'%"></div></div><div class="barCount">'+x.count+'</div></div>';}).join('')||'<div class="empty">No data</div>';}

var STATUS_COLOR = {Draft:'#888',PatchGenerated:'#c2ef4e',ValidationPassed:'#4ec9b0',PlanReady:'#569cd6',PendingApproval:'#dcdcaa',Approved:'#4ec94e',ExecutionReady:'#c586c0',InventoryRefreshed:'#569cd6'};

async function dbLoadSummary(){try{var s=await api('/inventory/summary');var k=s.kpis;document.getElementById('dbKpiObjects').textContent=k.total_objects;document.getElementById('dbKpiEnvs').textContent=k.environments;document.getElementById('dbKpiTypes').textContent=k.resource_types;}catch(e){console.error(e);}}

async function dbLoadOverview(){try{var o=await api('/inventory/overview');document.getElementById('dbEnvBars').innerHTML=dbBarRows(o.env_distribution||[],'env');document.getElementById('dbTypeBars').innerHTML=dbBarRows(o.top_resource_types||[],'resource_type');var chips=(o.top_resource_types||[]).map(function(x){return '<span class="chip">'+esc(x.resource_type)+' <b>'+x.count+'</b></span>';}).join('');document.getElementById('dbTypeChips').innerHTML=chips;}catch(e){console.error(e);}}

async function dbLoadRecentChanges(){try{var payload=await api('/changes?limit=10');var items=(payload.items||[]).slice(0,10);var kpiC=document.getElementById('dbKpiChanges');if(kpiC)kpiC.textContent=items.length;var kpiP=document.getElementById('dbKpiPending');if(kpiP)kpiP.textContent='pending: '+items.filter(function(x){return x.status==='PendingApproval';}).length;function objName(oid){var p=oid.split('/');return p[p.length-1];}document.getElementById('dbRecentChanges').innerHTML=items.length?items.map(function(x){var clr=STATUS_COLOR[x.status]||'#888';var cap='terraform_infra';if(x.change_type==='terraform_variable_update')cap='terraform_variables';else if(x.change_type==='terraform_module_update')cap='terraform_module';return '<div onclick=\"navigateTo(\\'capability-'+cap+'\\')\" style=\"display:flex;align-items:center;gap:10px;padding:8px 10px;border:1px solid rgba(255,255,255,.06);border-radius:8px;background:rgba(255,255,255,.018);cursor:pointer\"><span style=\"width:6px;height:6px;border-radius:99px;background:'+clr+';flex-shrink:0\" title=\"'+esc(x.status)+'\"></span><div style=\"flex:1;min-width:0\"><div style=\"font-size:12px;color:#f7f8f8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis\">'+esc(objName(x.object_id))+'</div><div style=\"font-size:10px;color:var(--muted2)\">'+esc(x.env||'-')+' &middot; '+esc(x.reason||'')+'</div></div><span style=\"font-size:10px;color:var(--muted2);flex-shrink:0\">'+esc(x.change_type.replace('terraform_','tf_'))+'</span></div>';}).join(''):'<div class="empty">No changes yet.</div>';}catch(e){console.error(e);}}

async function dbScanInventory(){document.getElementById('dbKpiObjects').textContent='...';try{await api('/inventory/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:'infra'})});await dbLoadSummary();await dbLoadOverview();}catch(e){console.error(e);}}

dbLoadSummary();dbLoadOverview();dbLoadRecentChanges();
"""


def render_dashboard_html():
    return _DASHBOARD_HTML


def dashboard_script():
    return _DASHBOARD_SCRIPT
