_ADMIN_SETTINGS_HTML = """<section data-component="admin-settings">
<div class="card" style="margin-bottom:18px;background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.035));border-color:rgba(194,239,78,.22)">
  <div class="toolbar">
    <div>
      <div class="eyebrow">Admin &amp; Settings</div>
      <h2 style="font-size:28px">Platform Configuration</h2>
      <p>平台设置 · 环境配置 · 默认适配器 · 审批策略</p>
    </div>
  </div>
</div>

<div style="display:grid;grid-template-columns:1fr 1fr;gap:18px">

  <div>
    <div class="card" style="padding:20px;margin-bottom:14px">
      <div class="eyebrow">Platform Info</div>
      <div style="margin-top:12px;display:flex;flex-direction:column;gap:8px">
        <div class="kvRow"><b>Platform</b><span>GitOps Terraform Control Plane</span></div>
        <div class="kvRow"><b>Version</b><span class="chip">0.1.0</span></div>
        <div class="kvRow"><b>Backend</b><span>FastAPI + PostgreSQL 14</span></div>
        <div class="kvRow"><b>Mode</b><span class="chip primary">GitOps Platform</span></div>
      </div>
    </div>

    <div class="card" style="padding:20px;margin-bottom:14px">
      <div class="eyebrow">Default Environments</div>
      <div style="margin-top:12px;display:flex;flex-direction:column;gap:6px" id="adminEnvList">
        <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;border:1px solid rgba(255,255,255,.06);border-radius:6px">
          <span class="chip" style="background:rgba(78,201,78,.15);border-color:rgba(78,201,78,.3);color:#4ec94e">dev</span>
          <span style="font-size:12px;color:var(--muted)">Development environment</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;border:1px solid rgba(255,255,255,.06);border-radius:6px">
          <span class="chip" style="background:rgba(86,156,214,.15);border-color:rgba(86,156,214,.3);color:#9cdcfe">sit</span>
          <span style="font-size:12px;color:var(--muted)">System Integration Testing</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;border:1px solid rgba(255,255,255,.06);border-radius:6px">
          <span class="chip" style="background:rgba(220,220,170,.15);border-color:rgba(220,220,170,.3);color:#dcdcaa">uat</span>
          <span style="font-size:12px;color:var(--muted)">User Acceptance Testing</span>
        </div>
        <div style="display:flex;align-items:center;gap:8px;padding:6px 10px;border:1px solid rgba(255,255,255,.06);border-radius:6px">
          <span class="chip" style="background:rgba(250,127,170,.15);border-color:rgba(250,127,170,.3);color:#ffc0d3">prod</span>
          <span style="font-size:12px;color:var(--muted)">Production (requires dual approval)</span>
        </div>
      </div>
    </div>

    <div class="card" style="padding:20px">
      <div class="eyebrow">Approval Policy</div>
      <div style="margin-top:12px;display:flex;flex-direction:column;gap:8px">
        <label style="display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--muted)">
          Default Approver Adapter
          <select style="background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:12px">
            <option>GitHub PR Review</option>
            <option>ServiceNow</option>
            <option>Jira Approval</option>
            <option>Internal Platform</option>
          </select>
        </label>
        <label style="display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--muted)">
          Prod Approval Count
          <select style="background:var(--bg);color:var(--fg);border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:12px">
            <option>2 approvers</option>
            <option>1 approver</option>
            <option>3 approvers</option>
          </select>
        </label>
        <button class="btn" style="font-size:12px;padding:8px 16px;margin-top:4px" onclick="alert('Settings saved (stub)')">Save Policy</button>
      </div>
    </div>
  </div>

  <div>
    <div class="card" style="padding:20px;margin-bottom:14px">
      <div class="eyebrow">Adapter Health</div>
      <div style="margin-top:12px;display:flex;flex-direction:column;gap:6px" id="adminAdapterHealth">
        <div class="empty">Loading adapter status...</div>
      </div>
    </div>

    <div class="card" style="padding:20px;margin-bottom:14px">
      <div class="eyebrow">API Health Check</div>
      <div style="margin-top:12px;display:flex;flex-direction:column;gap:8px">
        <div class="kvRow"><b>API Status</b><span class="chip primary" id="adminApiStatus">Checking...</span></div>
        <div class="kvRow"><b>Database</b><span class="chip primary" id="adminDbStatus">-</span></div>
        <div class="kvRow"><b>GitHub Token</b><span class="chip" id="adminGithubStatus">-</span></div>
      </div>
    </div>

    <div class="card" style="padding:20px">
      <div class="eyebrow">Danger Zone</div>
      <div style="margin-top:12px;display:flex;flex-direction:column;gap:10px">
        <div style="padding:14px;border:1px solid rgba(250,127,170,.25);border-radius:8px;background:rgba(250,127,170,.04)">
          <div style="font-size:13px;font-weight:600;color:#ffc0d3;margin-bottom:4px">Reset Inventory</div>
          <div style="font-size:12px;color:var(--muted);margin-bottom:10px">Clear all scanned inventory objects. Does not affect Git repos or changes.</div>
          <button class="btn" style="font-size:12px;padding:6px 14px;border-color:rgba(250,127,170,.4);color:#ffc0d3;background:rgba(250,127,170,.08)" onclick="alert('Inventory reset (stub)')">Reset</button>
        </div>
      </div>
    </div>
  </div>
</div>
</section>"""

_ADMIN_SETTINGS_SCRIPT = """
async function adminLoadHealth() {
  try {
    var h = await api('/api/health');
    document.getElementById('adminApiStatus').textContent = h.status || 'ok';
    document.getElementById('adminDbStatus').textContent = 'connected';
    document.getElementById('adminGithubStatus').textContent = 'configured';
  } catch(e) {
    document.getElementById('adminApiStatus').textContent = 'error';
  }
}

async function adminLoadAdapterHealth() {
  try {
    var infra = await api('/api/infrastructure-adapters');
    var allAdapters = (infra.git||[]).concat(infra.webhook||[]).concat(infra.execution||[]);
    var panel = document.getElementById('adminAdapterHealth');
    panel.innerHTML = allAdapters.length ? allAdapters.map(function(a) {
      return '<div style="display:flex;align-items:center;gap:10px;padding:7px 10px;border:1px solid rgba(255,255,255,.06);border-radius:6px"><span style="width:7px;height:7px;border-radius:99px;background:#4ec94e;flex-shrink:0"></span><span style="font-size:12px;color:#f7f8f8">'+esc(a.name)+'</span><span style="margin-left:auto;font-size:10px;color:var(--muted2)">registered</span></div>';
    }).join('') : '<div class="empty">No adapters registered. Go to Delivery &rarr; Adapters.</div>';
  } catch(e) {
    document.getElementById('adminAdapterHealth').innerHTML = '<div class="empty">Failed to load adapters.</div>';
  }
}

async function adminLoadAll() {
  await adminLoadHealth();
  await adminLoadAdapterHealth();
}
"""


def render_admin_settings_html():
    return _ADMIN_SETTINGS_HTML


def admin_settings_script():
    return _ADMIN_SETTINGS_SCRIPT
