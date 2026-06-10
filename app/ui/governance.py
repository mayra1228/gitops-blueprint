_GOVERNANCE_HTML = """<section data-component="governance">
<div class="card" style="margin-bottom:18px;background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.035));border-color:rgba(194,239,78,.22)">
  <div class="toolbar">
    <div>
      <div class="eyebrow">Governance &amp; SRE Evidence</div>
      <h2 style="font-size:28px">Audit Trail &amp; Compliance</h2>
      <p>变更审计时间线 · 合规证据 · SRE 操作记录 · 变更统计</p>
    </div>
    <div style="display:flex;gap:10px">
      <button class="btn" onclick="govLoadAll()" style="font-size:12px;padding:8px 16px">Refresh</button>
      <button class="btn" onclick="govExportEvidence()" style="font-size:12px;padding:8px 16px;background:rgba(255,255,255,.06)">Export Evidence</button>
    </div>
  </div>
</div>

<div class="grid4" style="margin-bottom:18px">
  <div class="kpi"><span>Total Changes</span><strong id="govKpiTotal">-</strong><small>all time</small></div>
  <div class="kpi"><span>Approved</span><strong id="govKpiApproved" style="color:#4ec94e">-</strong><small>passed approval</small></div>
  <div class="kpi"><span>Rejected</span><strong id="govKpiRejected" style="color:#f87171">-</strong><small>denied</small></div>
  <div class="kpi"><span>Pending</span><strong id="govKpiPending" style="color:#f59e0b">-</strong><small>awaiting review</small></div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px;margin-bottom:18px">
  <div class="card" style="padding:20px">
    <div class="eyebrow">Change Status Distribution</div>
    <div class="bars" id="govStatusBars" style="min-height:80px;margin-top:10px"><div class="empty">Loading...</div></div>
  </div>
  <div class="card" style="padding:20px">
    <div class="eyebrow">Approval Policy</div>
    <div style="margin-top:10px;display:flex;flex-direction:column;gap:8px">
      <div style="display:flex;justify-content:space-between;padding:8px 10px;border:1px solid rgba(255,255,255,.06);border-radius:8px">
        <span style="font-size:12px">Production Changes</span>
        <span class="chip" style="border-color:rgba(250,127,170,.35);background:rgba(250,127,170,.12);color:#ffc0d3">Requires 2 Approvers</span>
      </div>
      <div style="display:flex;justify-content:space-between;padding:8px 10px;border:1px solid rgba(255,255,255,.06);border-radius:8px">
        <span style="font-size:12px">Staging Changes</span>
        <span class="chip" style="border-color:rgba(86,156,214,.35);background:rgba(86,156,214,.12);color:#9cdcfe">Requires 1 Approver</span>
      </div>
      <div style="display:flex;justify-content:space-between;padding:8px 10px;border:1px solid rgba(255,255,255,.06);border-radius:8px">
        <span style="font-size:12px">Dev / SIT Changes</span>
        <span class="chip primary">Self-Approve Allowed</span>
      </div>
    </div>
  </div>
</div>

<div class="card" style="padding:20px">
  <div class="toolbar" style="margin-bottom:14px">
    <div><div class="eyebrow">Audit Event Log</div></div>
    <div style="display:flex;gap:8px;align-items:center">
      <select id="govChangeFilter" style="background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:6px;padding:4px 8px;font-size:12px">
        <option value="">All statuses</option>
        <option value="Approved">Approved</option>
        <option value="PendingApproval">Pending Approval</option>
        <option value="ExecutionReady">Execution Ready</option>
        <option value="InventoryRefreshed">Completed</option>
      </select>
    </div>
  </div>
  <div class="tableWrap">
    <table class="table">
      <thead><tr><th>Change ID</th><th>Type</th><th>Object</th><th>Status</th><th>Env</th><th>Actor</th><th>Time</th></tr></thead>
      <tbody id="govAuditRows"><tr><td colspan="7" class="empty">Loading audit events...</td></tr></tbody>
    </table>
  </div>
</div>
</section>"""

_GOVERNANCE_SCRIPT = """
async function govLoadKPIs() {
  try {
    var payload = await api('/changes');
    var items = payload.items || [];
    document.getElementById('govKpiTotal').textContent = items.length;
    document.getElementById('govKpiApproved').textContent = items.filter(function(x){return x.status==='Approved'||x.status==='ExecutionReady'||x.status==='InventoryRefreshed';}).length;
    document.getElementById('govKpiRejected').textContent = items.filter(function(x){return x.status==='Rejected';}).length;
    document.getElementById('govKpiPending').textContent = items.filter(function(x){return x.status==='PendingApproval';}).length;

    var statusCounts = {};
    items.forEach(function(x){ statusCounts[x.status] = (statusCounts[x.status]||0)+1; });
    var statusList = Object.keys(statusCounts).map(function(k){ return {status:k, count:statusCounts[k]}; });
    var maxCount = Math.max(1, ...statusList.map(function(x){return x.count;}));
    var STATUS_COLOR = {Draft:'#888',PatchGenerated:'#c2ef4e',ValidationPassed:'#4ec9b0',PlanReady:'#569cd6',PendingApproval:'#dcdcaa',Approved:'#4ec94e',ExecutionReady:'#c586c0',InventoryRefreshed:'#569cd6'};
    document.getElementById('govStatusBars').innerHTML = statusList.length ? statusList.map(function(x){
      var clr = STATUS_COLOR[x.status] || '#888';
      return '<div class="barRow"><div class="barLabel">'+esc(x.status)+'</div><div class="barTrack"><div class="barFill" style="width:'+Math.max(5,Math.round(x.count/maxCount*100))+'%;background:'+clr+'"></div></div><div class="barCount">'+x.count+'</div></div>';
    }).join('') : '<div class="empty">No change data</div>';
  } catch(e) { console.error(e); }
}

async function govLoadAuditRows() {
  try {
    var statusFilter = document.getElementById('govChangeFilter') ? document.getElementById('govChangeFilter').value : '';
    var qs = new URLSearchParams();
    if (statusFilter) qs.set('status', statusFilter);
    var payload = await api('/changes' + (qs.toString() ? '?' + qs.toString() : ''));
    var items = (payload.items || []).slice(0, 100);
    var STATUS_COLOR = {Draft:'#888',PatchGenerated:'#c2ef4e',ValidationPassed:'#4ec9b0',PlanReady:'#569cd6',PendingApproval:'#dcdcaa',Approved:'#4ec94e',ExecutionReady:'#c586c0',InventoryRefreshed:'#569cd6'};
    document.getElementById('govAuditRows').innerHTML = items.length ? items.map(function(x) {
      var clr = STATUS_COLOR[x.status] || '#888';
      var objParts = (x.object_id||'').split('/');
      var objShort = objParts[objParts.length-1];
      return '<tr><td><code class="mono" style="font-size:10px">'+esc(x.id.slice(0,12))+'...</code></td><td><span class="chip" style="font-size:10px">'+esc((x.change_type||'').replace('terraform_','tf_'))+'</span></td><td><div class="cellMain" style="max-width:160px"><b style="font-size:11px">'+esc(objShort)+'</b><div class="muted mono" style="font-size:9px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+esc(x.object_id)+'</div></div></td><td><span class="pill" style="border-color:'+clr+'66;background:'+clr+'18;color:'+clr+'">'+esc(x.status)+'</span></td><td>'+esc(x.env||'-')+'</td><td><code class="mono" style="font-size:10px">system</code></td><td style="font-size:10px;color:var(--muted2)">-</td></tr>';
    }).join('') : '<tr><td colspan="7" class="empty">No changes recorded yet.</td></tr>';
  } catch(e) { console.error(e); }
}

async function govLoadAll() {
  await govLoadKPIs();
  await govLoadAuditRows();
}

function govExportEvidence() {
  api('/changes').then(function(payload) {
    var data = JSON.stringify(payload.items||[], null, 2);
    var blob = new Blob([data], {type:'application/json'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href = url; a.download = 'sre-evidence-'+new Date().toISOString().slice(0,10)+'.json';
    a.click(); URL.revokeObjectURL(url);
  });
}

function bindGovernanceEvents() {
  var f = document.getElementById('govChangeFilter');
  if (f) f.addEventListener('change', govLoadAuditRows);
}
"""


def render_governance_html():
    return _GOVERNANCE_HTML


def governance_script():
    return _GOVERNANCE_SCRIPT
