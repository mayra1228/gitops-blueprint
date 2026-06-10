def render_capability_page_html(capability: dict) -> str:
    cap_id = capability["id"]
    cap_name = capability["name"]
    cap_desc = capability.get("description", "")
    resource_types = capability.get("resource_types", [])
    change_types = capability.get("change_types", [])
    default_change_type = change_types[0] if change_types else ""
    rtype_list = ",".join(resource_types)
    inventory_title = "AWS / K8S Inventory" if cap_id == "terraform_infra" else "Inventory"
    all_types_label = "All AWS/K8S types" if cap_id == "terraform_infra" else "All types"

    return f"""<section data-component="capability-page" data-capability="{cap_id}">
<div style="display:flex;gap:14px;margin-bottom:16px;align-items:stretch;flex-wrap:wrap">
<div class="card" style="flex:1;min-width:260px;background:linear-gradient(180deg,rgba(255,255,255,.065),rgba(255,255,255,.025));border-color:rgba(194,239,78,.18);padding:18px 24px">
<div style="display:flex;align-items:center;gap:12px"><div style="width:36px;height:36px;border-radius:10px;background:linear-gradient(135deg,rgba(194,239,78,.35),rgba(113,112,255,.35));flex-shrink:0"></div><div><h2 style="font-size:20px;margin:0;font-weight:600">{cap_name}</h2><p style="color:var(--muted);font-size:12px;margin:3px 0 0">{cap_desc}</p></div></div>
</div>
<div class="card kpi" style="min-width:110px;text-align:center;padding:14px 18px"><div style="color:var(--muted2);font-size:10px;text-transform:uppercase;letter-spacing:.08em">Objects</div><div style="font-size:28px;font-weight:600;margin:6px 0" id="capKpiObjects_{cap_id}">-</div><div style="font-size:10px;color:var(--muted2)">{rtype_list}</div></div>
<div class="card kpi" style="min-width:110px;text-align:center;padding:14px 18px"><div style="color:var(--muted2);font-size:10px;text-transform:uppercase;letter-spacing:.08em">Changes</div><div style="font-size:28px;font-weight:600;margin:6px 0" id="capKpiChanges_{cap_id}">-</div><div style="font-size:10px;color:var(--muted2)">total tracked</div></div>
<div class="card kpi" style="min-width:110px;text-align:center;padding:14px 18px"><div style="color:var(--muted2);font-size:10px;text-transform:uppercase;letter-spacing:.08em">Pending</div><div style="font-size:28px;font-weight:600;margin:6px 0;color:#f59e0b" id="capKpiPending_{cap_id}">-</div><div style="font-size:10px;color:var(--muted2)">awaiting action</div></div>
<div class="card kpi" style="min-width:110px;text-align:center;padding:14px 18px"><div style="color:var(--muted2);font-size:10px;text-transform:uppercase;letter-spacing:.08em">Done</div><div style="font-size:28px;font-weight:600;margin:6px 0;color:#10b981" id="capKpiDone_{cap_id}">-</div><div style="font-size:10px;color:var(--muted2)">completed</div></div>
</div>

<div id="capTransferBanner_{cap_id}" style="display:none;align-items:center;justify-content:space-between;gap:12px;margin-bottom:14px;padding:12px 14px;border:1px solid rgba(194,239,78,.25);background:rgba(194,239,78,.08);border-radius:12px">
<div><div style="color:var(--lime);font-size:11px;font-weight:600;margin-bottom:2px">Loaded from Resource Topology</div><div id="capTransferText_{cap_id}" style="color:#d0d6e0;font-size:12px"></div></div>
<button class="btn" onclick="navigateTo('tf-control-plane')" style="font-size:11px;padding:6px 12px">Back to Topology</button>
</div>

<div style="display:grid;grid-template-columns:1.15fr .85fr;gap:16px;align-items:start" class="capLayout__CAP_ID__">
<div>
<div class="card" style="margin-bottom:14px;padding:16px">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><h3 style="font-size:14px;margin:0;font-weight:600">{inventory_title}</h3><div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap"><select id="capEnvFilter_{cap_id}" style="background:#140f22;border:1px solid #4a3b70;color:#fff;border-radius:8px;padding:5px 8px;font-size:11px;min-width:auto"><option value="">All envs</option><option value="dev">dev</option><option value="sit">sit</option><option value="stg">stg</option><option value="uat">uat</option><option value="prf">prf</option><option value="prod">prod</option></select><select id="capTypeFilter_{cap_id}" style="background:#140f22;border:1px solid #4a3b70;color:#fff;border-radius:8px;padding:5px 8px;font-size:11px;min-width:auto"><option value="">{all_types_label}</option>{"".join(f'<option value="{rt}">{rt}</option>' for rt in resource_types)}</select><input id="capQFilter_{cap_id}" placeholder="Search" style="background:#140f22;border:1px solid #4a3b70;color:#fff;border-radius:8px;padding:5px 8px;font-size:11px;width:120px"><button class="btn" onclick="capRefreshInventory_{cap_id}()" style="padding:5px 10px;font-size:10px">Scan</button></div></div>
<div id="capCategoryBar_{cap_id}" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px"></div>
<div class="tableWrap" style="max-height:320px"><table class="table" style="min-width:700px"><thead><tr><th>Resource</th><th>Type</th><th>Env</th><th>Source</th></tr></thead><tbody id="capRows_{cap_id}"><tr><td colspan="4" class="empty">Loading...</td></tr></tbody></table></div>
<div style="margin-top:6px;color:var(--muted2);font-size:10px"><span id="capObjectCount_{cap_id}">-</span></div>
</div>

<div style="display:none">
<select id="changeStatusFilter_{cap_id}"><option value="">All statuses</option></select>
<div id="changeRows_{cap_id}"></div>
<span id="changeCount_{cap_id}">-</span>
</div>

<div class="card" style="padding:16px">
<div style="margin-bottom:10px"><h3 style="font-size:14px;margin:0;font-weight:600">Create Change</h3></div>
<form id="draftForm_{cap_id}" style="display:grid;gap:8px">
<input type="hidden" id="draftChangeType_{cap_id}" value="{default_change_type}">
<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
<div><label style="display:block;color:var(--muted2);font-size:10px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Object ID</label><input id="draftObjectId_{cap_id}" placeholder="Click inventory row" style="width:100%;background:#140f22;border:1px solid #4a3b70;color:#fff;border-radius:8px;padding:7px 10px;font-size:12px"></div>
<div><label style="display:block;color:var(--muted2);font-size:10px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Reason</label><input id="draftReason_{cap_id}" placeholder="e.g. scale up" style="width:100%;background:#140f22;border:1px solid #4a3b70;color:#fff;border-radius:8px;padding:7px 10px;font-size:12px"></div>
</div>
<div id="capCurrentSpecPanel_{cap_id}" style="display:none;padding:8px 10px;border:1px solid var(--line);background:rgba(16,11,28,.46);border-radius:8px">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px"><span style="color:var(--muted2);font-size:9px;text-transform:uppercase;letter-spacing:.08em">Current Spec</span><button type="button" class="btn" style="padding:2px 8px;font-size:9px" onclick="var t=document.getElementById('draftProposedJson_{cap_id}');var c=document.getElementById('capCurrentSpecRaw_{cap_id}');if(c&&c.textContent!=='Click an inventory row to load'){{t.value=c.textContent;t.style.borderColor='var(--lime)';setTimeout(function(){{t.style.borderColor='';}},800);}}">Use as Base</button></div>
<pre id="capCurrentSpecRaw_{cap_id}" style="margin:0;color:#dcdcaa;font-family:monospace;font-size:10px;max-height:100px;overflow:auto;white-space:pre-wrap">Click an inventory row to load</pre>
</div>
<div><label style="display:block;color:var(--muted2);font-size:10px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:4px">Proposed Changes (JSON)</label><textarea id="draftProposedJson_{cap_id}" rows="3" style="font-family:monospace;font-size:12px;width:100%;background:#140f22;border:1px solid #4a3b70;color:#fff;border-radius:8px;padding:7px 10px" placeholder='{{"maxReplicas": 20}}'></textarea></div>
<div style="display:flex;align-items:center;gap:10px"><button class="btn" type="submit" style="padding:8px 18px;font-size:12px;background:#5e6ad2;border-color:#6f76e6">Create Draft</button><span style="color:var(--muted2);font-size:10px">Generates patch preview; no source mutation</span></div>
</form>
</div>
</div>

<div>
<div class="card" style="margin-bottom:14px;padding:14px">
<div style="font-size:10px;color:var(--muted2);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Actions</div>
<div id="actionButtons_{cap_id}" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:6px"></div>
<div id="actionHint_{cap_id}" style="color:var(--muted2);font-size:11px">Select a change or create a draft to begin.</div>
</div>

<div class="card" style="margin-bottom:14px;padding:14px">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px"><div style="font-size:10px;color:var(--muted2);text-transform:uppercase;letter-spacing:.08em">Diff / Result</div><span style="font-size:10px;color:var(--muted2)" id="changeDetailStatus_{cap_id}"></span></div>
<pre id="actionResult_{cap_id}" style="margin:0;background:#050607;border:1px solid rgba(255,255,255,.08);border-radius:10px;padding:12px;font-family:monospace;font-size:11px;line-height:1.55;color:#d0d6e0;min-height:120px;max-height:380px;overflow:auto;white-space:pre-wrap">Run an action to see results here.</pre>
</div>

<div class="card" style="margin-bottom:14px;padding:14px">
<div style="font-size:10px;color:var(--muted2);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Object Detail</div>
<div id="changeObjectCard_{cap_id}"><div class="empty" style="padding:12px">Select a change to view object context.</div></div>
</div>

<div class="card" style="padding:14px">
<div style="font-size:10px;color:var(--muted2);text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px">Audit Trail</div>
<div id="auditTrail_{cap_id}" style="display:flex;flex-direction:column;gap:5px;max-height:180px;overflow-y:auto"><div class="empty" style="padding:12px">No audit trail selected</div></div>
</div>
</div>
</div>

<div id="capDetailPanel_{cap_id}" style="display:none;position:fixed;right:20px;bottom:20px;z-index:100;background:#191a1b;border:1px solid rgba(255,255,255,.1);border-radius:12px;padding:14px 16px;box-shadow:0 16px 40px rgba(0,0,0,.45);max-width:420px">
<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px"><span style="font-weight:600;font-size:13px" id="capDetailTitle_{cap_id}">Object</span><button onclick="document.getElementById('capDetailPanel_{cap_id}').style.display='none'" style="background:none;border:none;color:var(--muted2);cursor:pointer;font-size:16px">&times;</button></div>
<pre id="capDetail_{cap_id}" style="margin:0;font-family:monospace;font-size:10px;line-height:1.4;color:#d0d6e0;max-height:280px;overflow:auto;white-space:pre-wrap"></pre>
</div>
</section>"""


def capability_page_script(capability: dict) -> str:
    cap_id = capability["id"]
    resource_types = capability.get("resource_types", [])
    change_types = capability.get("change_types", [])
    default_change_type = change_types[0] if change_types else ""
    rtype_list = str(resource_types)
    ctype_list = str(change_types)

    tpl = """// --- Capability: __CAP_ID__ ---
const STS___CAP_ID__={Draft:1,PatchGenerated:2,ValidationPassed:3,PlanReady:4,PendingApproval:5,Approved:6,ExecutionReady:7,InventoryRefreshed:7};
const CLR___CAP_ID__={Draft:'#888',PatchGenerated:'#c2ef4e',ValidationPassed:'#4ec9b0',PlanReady:'#569cd6',PendingApproval:'#dcdcaa',Approved:'#4ec94e',ExecutionReady:'#c586c0',InventoryRefreshed:'#569cd6'};
const FLOW___CAP_ID__=['PatchGenerated','ValidationPassed','PlanReady','PendingApproval','Approved','ExecutionReady','InventoryRefreshed'];
const FLOW_LABEL___CAP_ID__={PatchGenerated:'Patch',ValidationPassed:'Validate',PlanReady:'Plan',PendingApproval:'Submit',Approved:'Decision',ExecutionReady:'Execute',InventoryRefreshed:'Refresh'};
const ACT___CAP_ID__={PatchGenerated:[{a:'validate',l:'Validate Changes',h:'Run policy checks',s:'background:var(--purple);border-color:var(--lime);font-size:12px;padding:10px 20px'}],ValidationPassed:[{a:'plan',l:'Run Plan (Dry Run)',h:'Preview without applying',s:'background:var(--purple);border-color:var(--lime);font-size:12px;padding:10px 20px'},{a:'validate',l:'Re-Validate',h:'Re-run checks',s:'font-size:11px'}],PlanReady:[{a:'submit-approval',l:'Submit for Approval',h:'Request review',s:'background:var(--purple);border-color:var(--lime);font-size:12px;padding:10px 20px'}],PendingApproval:[{a:'approve',l:'Approve',h:'Approve change',s:'background:#1a5c1a;border-color:var(--lime);font-size:12px;padding:10px 20px'},{a:'reject',l:'Reject',h:'Reject change',s:'background:#5c1a1a;border-color:var(--pink);font-size:12px;padding:10px 20px'}],Approved:[{a:'execute',l:'Execute Changes',h:'Apply to cluster',s:'background:var(--purple);border-color:var(--lime);font-size:12px;padding:10px 20px'}],ExecutionReady:[{a:'refresh-inventory',l:'Refresh Inventory',h:'Snapshot state',s:'background:var(--purple);border-color:var(--lime);font-size:12px;padding:10px 20px'}],InventoryRefreshed:[]};
const ALLOW___CAP_ID__={Draft:[],PatchGenerated:['validate'],ValidationPassed:['validate','plan'],PlanReady:['submit-approval'],PendingApproval:['approve','reject'],Approved:['execute'],ExecutionReady:['refresh-inventory'],InventoryRefreshed:[]};

var _capCategoryFilter___CAP_ID__ = '';
var _capAllItems___CAP_ID__ = [];

var CAP_CATEGORIES___CAP_ID__ = [
  {id:'', label:'All'},
  {id:'aws_', label:'AWS'},
  {id:'k8s_', label:'K8S'},
  {id:'ODP_', label:'ODP'},
  {id:'terraform_', label:'TF'},
  {id:'mysql_', label:'MySQL'},{id:'postgresql_', label:'PgSQL'},{id:'random_', label:'Other'},
];
if('__CAP_ID__'==='terraform_infra'){
  CAP_CATEGORIES___CAP_ID__ = [
    {id:'', label:'All'},
    {id:'aws_', label:'AWS'},
    {id:'k8s_', label:'K8S'},
  ];
}

function capIsManagedResource___CAP_ID__(item){
  if('__CAP_ID__'!=='terraform_infra')return true;
  var rt=String((item&&item.resource_type)||'');
  return rt.startsWith('aws_')||rt.startsWith('cloudwatch_')||rt.startsWith('k8s_');
}

function capCategoryMatches___CAP_ID__(item, categoryId){
  var rt=String((item&&item.resource_type)||'');
  if('__CAP_ID__'==='terraform_infra'&&categoryId==='aws_'){
    return rt.startsWith('aws_')||rt.startsWith('cloudwatch_');
  }
  return rt.startsWith(categoryId);
}

function capBuildCategoryBar___CAP_ID__(items){
  var bar=document.getElementById('capCategoryBar___CAP_ID__');if(!bar)return;
  var counts={};counts['']= items.length;
  CAP_CATEGORIES___CAP_ID__.forEach(function(c){if(c.id){counts[c.id]=items.filter(function(x){return capCategoryMatches___CAP_ID__(x,c.id);}).length;}});
  var cats=CAP_CATEGORIES___CAP_ID__.filter(function(c){return !c.id||counts[c.id]>0;});
  bar.innerHTML=cats.map(function(c){var active=_capCategoryFilter___CAP_ID__===c.id;return '<span onclick="capSetCategory___CAP_ID__(\\''+c.id+'\\')" style="cursor:pointer;padding:3px 10px;border-radius:99px;font-size:10px;border:1px solid '+(active?'rgba(194,239,78,.8)':'rgba(255,255,255,.15)')+';background:'+(active?'rgba(194,239,78,.15)':'rgba(255,255,255,.05)')+';color:'+(active?'#c2ef4e':'#ccc')+'">'+esc(c.label)+(c.id&&counts[c.id]?' <b>'+counts[c.id]+'</b>':'')+'</span>';}).join('');
}

function capSetCategory___CAP_ID__(cat){_capCategoryFilter___CAP_ID__=cat;capRenderRows___CAP_ID__();}

function capRenderRows___CAP_ID__(){
  var items=_capAllItems___CAP_ID__;
  if(_capCategoryFilter___CAP_ID__){items=items.filter(function(x){return capCategoryMatches___CAP_ID__(x,_capCategoryFilter___CAP_ID__);});}
  capBuildCategoryBar___CAP_ID__(_capAllItems___CAP_ID__);
  var isModule='__CAP_ID__'==='terraform_module';
  if(isModule){
    // Group by module name (display_name), show envs as pills
    var grouped={};
    items.forEach(function(x){var name=x.display_name||x.id;if(!grouped[name])grouped[name]={item:x,envs:[]};grouped[name].envs.push(x.scope&&x.scope.env||'-');});
    var uniq=Object.values(grouped);
    document.getElementById('capObjectCount___CAP_ID__').textContent=uniq.length+' unique modules ('+items.length+' deployments)';
    var kpi=document.getElementById('capKpiObjects___CAP_ID__');if(kpi)kpi.textContent=uniq.length;
    var rows=document.getElementById('capRows___CAP_ID__');
    rows.innerHTML=uniq.length?uniq.map(function(g){var x=g.item;var envPills=g.envs.map(function(e){return '<span class="chip" style="font-size:9px;padding:1px 6px">'+esc(e)+'</span>';}).join('');try{return '<tr onclick="capLoadObjectDetail___CAP_ID__(\\''+esc(x.id)+'\\')" style="cursor:pointer"><td><div><b style="font-size:13px">'+esc(x.display_name||x.id)+'</b><div class="muted mono" style="font-size:10px">'+esc(x.id)+'</div></div></td><td><span class="pill" style="font-size:10px">'+esc(x.resource_type)+'</span></td><td>'+envPills+'</td><td><div class="mono" style="font-size:10px;max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+esc((x.source||{}).path||'')+'</div></td></tr>';}catch(e2){return '';}}).join(''):'<tr><td colspan="4" class="empty">No modules found.</td></tr>';
    return;
  }
  document.getElementById('capObjectCount___CAP_ID__').textContent=items.length+' objects';
  var kpi=document.getElementById('capKpiObjects___CAP_ID__');if(kpi)kpi.textContent=items.length;
  var rows=document.getElementById('capRows___CAP_ID__');
  rows.innerHTML=items.length?items.slice(0,150).map(function(x){try{return '<tr onclick="capLoadObjectDetail___CAP_ID__(\\''+esc(x.id)+'\\')" style="cursor:pointer"><td><div><b style="font-size:13px">'+esc(x.display_name||x.id)+'</b><div class="muted mono" style="font-size:10px">'+esc(x.id)+'</div></div></td><td><span class="pill" style="font-size:10px">'+esc(x.resource_type)+'</span></td><td style="font-size:12px">'+esc(x.scope&&x.scope.env||'-')+'</td><td><div class="mono" style="font-size:10px;max-width:200px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+esc((x.source||{}).path||'')+'</div></td></tr>';}catch(e){return '';}}).join(''):'<tr><td colspan="4" class="empty">No objects. Click Scan to discover.</td></tr>';
}

async function capLoadObjects___CAP_ID__(){try{const qs=new URLSearchParams();qs.set('limit','300');if('__CAP_ID__'==='terraform_infra')qs.set('resource_type_prefix','aws_,cloudwatch_,k8s_');const ef=document.getElementById('capEnvFilter___CAP_ID__');if(ef&&ef.value)qs.set('env',ef.value);const tf=document.getElementById('capTypeFilter___CAP_ID__');if(tf&&tf.value)qs.set('resource_type',tf.value);const qf=document.getElementById('capQFilter___CAP_ID__');if(qf&&qf.value)qs.set('q',qf.value);const payload=await api('/inventory/objects?'+qs.toString());_capAllItems___CAP_ID__=(payload.items||[]).filter(function(x){return capIsManagedResource___CAP_ID__(x)&&(!__RTYPE_LIST__.length||__RTYPE_LIST__.some(function(rt){return x.resource_type===rt||x.resource_type.startsWith(rt.replace('*',''));}));});capBuildCategoryBar___CAP_ID__(_capAllItems___CAP_ID__);capRenderRows___CAP_ID__();}catch(e){var cnt=document.getElementById('capObjectCount___CAP_ID__');if(cnt)cnt.textContent='Error: '+e.message;}}

async function capLoadObjectDetail___CAP_ID__(id){const d=await api('/inventory/objects/'+encodeURIComponent(id));var panel=document.getElementById('capDetailPanel___CAP_ID__');if(panel)panel.style.display='block';document.getElementById('capDetail___CAP_ID__').textContent=JSON.stringify(d,null,2);document.getElementById('capDetailTitle___CAP_ID__').textContent=d.display_name||d.id;document.getElementById('draftObjectId___CAP_ID__').value=id;var sp=document.getElementById('capCurrentSpecPanel___CAP_ID__');if(sp)sp.style.display='block';var fullSpec=d.spec||{};var currEl=document.getElementById('capCurrentSpecRaw___CAP_ID__');if(currEl)currEl.textContent=JSON.stringify(fullSpec,null,2);var pjEl=document.getElementById('draftProposedJson___CAP_ID__');if(pjEl&&!pjEl.value.trim()){pjEl.value=JSON.stringify(fullSpec,null,2);}}

function capEnsureTypeOption___CAP_ID__(resourceType){if(!resourceType)return;var tf=document.getElementById('capTypeFilter___CAP_ID__');if(!tf)return;for(var i=0;i<tf.options.length;i++){if(tf.options[i].value===resourceType)return;}var opt=document.createElement('option');opt.value=resourceType;opt.textContent=resourceType;tf.appendChild(opt);}

async function capApplyTransfer___CAP_ID__(ctx){if(!ctx||ctx.target&&ctx.target!=='__CAP_ID__')return;var banner=document.getElementById('capTransferBanner___CAP_ID__');var text=document.getElementById('capTransferText___CAP_ID__');var name=ctx.display_name||ctx.object_id||'';if(banner)banner.style.display='flex';if(text)text.innerHTML='<span class="mono">'+esc(name)+'</span> · '+esc(ctx.resource_type||'-')+' · env '+esc(ctx.env||'-');if(ctx.env){var ef=document.getElementById('capEnvFilter___CAP_ID__');if(ef)ef.value=ctx.env;}if(ctx.resource_type){capEnsureTypeOption___CAP_ID__(ctx.resource_type);var tf=document.getElementById('capTypeFilter___CAP_ID__');if(tf)tf.value=ctx.resource_type;}var qf=document.getElementById('capQFilter___CAP_ID__');if(qf)qf.value=(ctx.display_name||ctx.object_id||'').split('/').pop();await capLoadObjects___CAP_ID__();if(ctx.object_id)await capLoadObjectDetail___CAP_ID__(ctx.object_id);var reason=document.getElementById('draftReason___CAP_ID__');if(reason&&!reason.value)reason.value='Change requested from Resource Topology';var hint=document.getElementById('actionHint___CAP_ID__');if(hint){hint.textContent='Loaded from Resource Topology. Review current spec, edit proposed JSON, then click Create Draft.';hint.style.color='var(--lime)';}var form=document.getElementById('draftForm___CAP_ID__');if(form)form.scrollIntoView({behavior:'smooth',block:'center'});}

function capBindInventoryEvents___CAP_ID__(){const ef=document.getElementById('capEnvFilter___CAP_ID__');if(ef)ef.addEventListener('change',capLoadObjects___CAP_ID__);const tf=document.getElementById('capTypeFilter___CAP_ID__');if(tf)tf.addEventListener('change',capLoadObjects___CAP_ID__);const qf=document.getElementById('capQFilter___CAP_ID__');if(qf)qf.addEventListener('input',function(){clearTimeout(window.__q___CAP_ID__);window.__q___CAP_ID__=setTimeout(capLoadObjects___CAP_ID__,180);});}

async function capRefreshInventory___CAP_ID__(){document.getElementById('capObjectCount___CAP_ID__').textContent='Scanning...';await api('/inventory/scan',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({path:'infra'})});await capLoadObjects___CAP_ID__();}

async function capLoadChanges___CAP_ID__(){const qs=new URLSearchParams();const sf=document.getElementById('changeStatusFilter___CAP_ID__');if(sf&&sf.value)qs.set('status',sf.value);const payload=await api('/changes'+(qs.toString()?'?'+qs.toString():''));const items=(payload.items||[]).filter(function(x){return __CTYPE_LIST__.includes(x.change_type);});document.getElementById('changeCount___CAP_ID__').textContent=items.length+' tracked changes';var kpiC=document.getElementById('capKpiChanges___CAP_ID__');if(kpiC)kpiC.textContent=items.length;var kpiP=document.getElementById('capKpiPending___CAP_ID__');if(kpiP)kpiP.textContent=items.filter(function(x){return x.status==='PendingApproval'||x.status==='PlanReady';}).length;var kpiD=document.getElementById('capKpiDone___CAP_ID__');if(kpiD)kpiD.textContent=items.filter(function(x){return x.status==='InventoryRefreshed'||x.status==='ExecutionReady';}).length;function objName(oid){var p=oid.split('/');return p[p.length-1];}const rows=document.getElementById('changeRows___CAP_ID__');rows.innerHTML=items.length?items.map(function(x){var step=STS___CAP_ID__[x.status]||0;var clr=CLR___CAP_ID__[x.status]||'#888';var statusLabel=FLOW_LABEL___CAP_ID__[x.status]||x.status;return '<div class=\"row\" onclick=\"capLoadChangeDetail___CAP_ID__(\\''+x.id+'\\')\" style=\"display:grid;grid-template-columns:96px 1fr 100px 80px;gap:10px;align-items:center;padding:10px 12px;border:1px solid rgba(255,255,255,.06);background:rgba(255,255,255,.018);border-radius:8px;cursor:pointer\"><span class=\"mono\" style=\"font-size:11px\">'+esc(x.id.substring(0,14))+'</span><div><div style=\"font-size:13px;color:#f7f8f8;white-space:nowrap;overflow:hidden;text-overflow:ellipsis\">'+esc(objName(x.object_id))+'</div><div class=\"muted\" style=\"font-size:10px\">'+esc(x.env||'-')+' &middot; '+esc(x.reason||'')+'</div></div><span style=\"display:inline-flex;align-items:center;gap:5px;border:1px solid rgba(255,255,255,.08);padding:3px 7px;border-radius:999px;font-size:10px;color:#d0d6e0\"><span style=\"width:6px;height:6px;border-radius:99px;background:'+clr+';flex-shrink:0\"></span>'+esc(statusLabel)+'</span><div style=\"display:flex;align-items:center;gap:3px\"><div style=\"width:40px;height:3px;background:rgba(255,255,255,.1);border-radius:2px\"><div style=\"width:'+(step/7*100)+'%;height:100%;background:'+clr+';border-radius:2px\"></div></div><small style=\"color:var(--muted2);font-size:9px\">'+step+'/7</small></div></div>';}).join(''):'<div class=\"empty\" style=\"padding:20px\">No changes yet. Create a draft above.</div>';if(items.length&&!window._capChangeId___CAP_ID__){capLoadChangeDetail___CAP_ID__(items[0].id);}}

function capUpdateTimeline___CAP_ID__(status){var idx=FLOW___CAP_ID__.indexOf(status);var parent=document.getElementById('flowTimeline___CAP_ID__');if(!parent)return;var html='';for(var i=0;i<FLOW___CAP_ID__.length;i++){var bg='#23252a';var shadow='';if(i<idx){bg='#10b981';}else if(i===idx){bg='#7170ff';shadow='0 0 12px rgba(113,112,255,.5)';}html+='<div style=\"flex:1;height:5px;background:'+bg+';border-radius:99px;box-shadow:'+shadow+'\" title=\"'+FLOW_LABEL___CAP_ID__[FLOW___CAP_ID__[i]]+'\"></div>';}parent.innerHTML=html;document.getElementById('flowCurrentLabel___CAP_ID__').textContent=status||'-';document.getElementById('flowNextAction___CAP_ID__').textContent=idx>=0&&idx<FLOW___CAP_ID__.length-1?FLOW_LABEL___CAP_ID__[FLOW___CAP_ID__[idx+1]]:'Done';}

function capRenderActionButtons___CAP_ID__(status){var actions=ACT___CAP_ID__[status]||[];var html='';for(var j=0;j<actions.length;j++){var a=actions[j];html+='<button class=\"btn\" onclick=\"capRunAction___CAP_ID__(\\''+a.a+'\\')\" style=\"'+a.s+'\" title=\"'+esc(a.h)+'\">'+esc(a.l)+'</button>';}document.getElementById('actionButtons___CAP_ID__').innerHTML=html;var hint='';if(status==='Draft')hint='Draft created. Validate to continue.';else if(status==='PatchGenerated')hint='Patch is ready. Click Validate to check policies.';else if(status==='ValidationPassed')hint='Validation passed. Click Run Plan for dry-run preview.';else if(status==='PlanReady')hint='Plan ready. Click Submit to request approval.';else if(status==='PendingApproval')hint='Awaiting approval. Approve or Reject this change.';else if(status==='Approved')hint='Change approved. Click Execute to apply.';else if(status==='ExecutionReady')hint='Execution complete. Click Refresh to snapshot.';else if(status==='InventoryRefreshed')hint='Workflow complete.';else hint='Select a change or create a draft to begin.';document.getElementById('actionHint___CAP_ID__').textContent=hint;}

async function capLoadChangeDetail___CAP_ID__(id){window._capChangeId___CAP_ID__=id;const d=await api('/changes/'+encodeURIComponent(id));const a=await api('/changes/'+encodeURIComponent(id)+'/audit');window._capChangeStatus___CAP_ID__=d.status;window._capChangeType___CAP_ID__=d.change_type||'';document.getElementById('changeDetailStatus___CAP_ID__').textContent=d.status;document.getElementById('actionResult___CAP_ID__').textContent=JSON.stringify(d,null,2);capUpdateTimeline___CAP_ID__(d.status);capRenderActionButtons___CAP_ID__(d.status);var scope=d.scope||{};var current=d.current_spec||{};var proposed=d.proposed_spec||{};var artifacts=d.artifacts||{};var ak=Object.keys(artifacts);var fieldDiff=(artifacts.field_diff||Object.keys(proposed).map(function(f){return {field:f,from:current[f],to:proposed[f]};}));var objHtml='<div style=\"display:grid;gap:6px\"><div style=\"display:flex;gap:8px\"><span style=\"color:var(--muted2);font-size:11px;min-width:70px\">Object ID</span><span class=\"mono\" style=\"font-size:11px\">'+esc(d.object_id)+'</span></div><div style=\"display:flex;gap:8px\"><span style=\"color:var(--muted2);font-size:11px;min-width:70px\">Source</span><span class=\"mono\" style=\"font-size:11px\">'+esc(d.source_path||'-')+'</span></div><div style=\"display:flex;gap:8px\"><span style=\"color:var(--muted2);font-size:11px;min-width:70px\">Env</span><span style=\"font-size:11px\">'+esc(scope.env||d.env||'-')+'</span></div><div style=\"display:flex;gap:8px\"><span style=\"color:var(--muted2);font-size:11px;min-width:70px\">Reason</span><span style=\"font-size:11px\">'+esc(d.reason||'-')+'</span></div>';if(fieldDiff.length){objHtml+='<div style=\"margin-top:8px;padding-top:8px;border-top:1px solid rgba(255,255,255,.06)\">';for(var i=0;i<fieldDiff.length;i++){var fd=fieldDiff[i];objHtml+='<div style=\"display:flex;gap:8px;font-size:10px;margin-bottom:3px\"><span style=\"color:var(--muted2);min-width:70px\">'+esc(fd.field)+'</span><span style=\"color:#ef4444;font-family:monospace\">'+esc(JSON.stringify(fd.from))+'</span><span style=\"color:var(--muted2)\">&rarr;</span><span style=\"color:#10b981;font-family:monospace\">'+esc(JSON.stringify(fd.to))+'</span></div>';}objHtml+='</div>';}if(ak.length){objHtml+='<div style=\"margin-top:6px;display:flex;flex-wrap:wrap;gap:4px\">';for(var j=0;j<ak.length;j++){objHtml+='<span class=\"chip\" style=\"font-size:10px\">'+esc(ak[j])+'</span>';}objHtml+='</div>';}objHtml+='</div>';document.getElementById('changeObjectCard___CAP_ID__').innerHTML=objHtml;var items=(a.items||[]).sort(function(a,b){return (a.sequence||0)-(b.sequence||0);});document.getElementById('auditTrail___CAP_ID__').innerHTML=items&&items.length?items.map(function(x){return '<div style=\"display:flex;gap:8px;align-items:center;padding:5px 8px;border:1px solid rgba(255,255,255,.06);border-radius:6px;background:rgba(255,255,255,.015)\"><span style=\"width:18px;height:18px;border-radius:50%;background:rgba(194,239,78,.15);color:var(--lime);display:grid;place-items:center;font-size:9px;font-weight:700;flex-shrink:0\">'+esc(x.sequence)+'</span><div><b style=\"font-size:11px\">'+esc(x.type)+'</b><small style=\"display:block;color:var(--muted2);font-size:9px\">'+esc(x.actor||'system')+'</small></div></div>';}).join(''):'<div class=\"empty\" style=\"padding:12px\">No audit events</div>';}

async function capRunAction___CAP_ID__(action){var id=window._capChangeId___CAP_ID__;var st=window._capChangeStatus___CAP_ID__;if(!id){document.getElementById('actionResult___CAP_ID__').textContent='Select a change first.';return;}var allowed=ALLOW___CAP_ID__[st]||[];if(allowed.indexOf(action)===-1){document.getElementById('actionResult___CAP_ID__').textContent='Action \"'+action+'\" not allowed for status \"'+st+'\".';return;}var endpoint=action;var payload={};if(action==='submit-approval'){endpoint='submit';payload={requester:'sre-user',note:'ready for review'};}if(action==='approve'){endpoint='approve';payload={approver:'manager',decision:'approve',comment:'approved'};}if(action==='reject'){endpoint='approve';payload={approver:'manager',decision:'reject',comment:'needs revision'};}if(action==='execute'){payload={executor:'sre-bot'};}if(action==='refresh-inventory')payload={};var resultEl=document.getElementById('actionResult___CAP_ID__');resultEl.textContent='Running '+action+'...';try{var res=await api('/changes/'+encodeURIComponent(id)+'/'+endpoint,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});var out=JSON.stringify(res,null,2);if(res.status){resultEl.innerHTML='<div style=\"color:var(--lime);margin-bottom:6px;font-weight:600\">Status: '+esc(res.status)+'</div><pre style=\"margin:0;font-family:monospace;font-size:10px;line-height:1.4;color:#d0d6e0\">'+esc(out)+'</pre>';}else{resultEl.textContent=out;}await capLoadChanges___CAP_ID__();await capLoadChangeDetail___CAP_ID__(id);}catch(e){resultEl.textContent='Action failed: '+e.message;}}

function capBuildDraftPayload___CAP_ID__(){var oid=document.getElementById('draftObjectId___CAP_ID__').value;if(!oid){alert('Please click an inventory row or type an Object ID first');return null;}var ct='__DEFAULT_CHANGE_TYPE__';var pjEl=document.getElementById('draftProposedJson___CAP_ID__');if(!pjEl||!pjEl.value.trim()){alert('Please fill in the Proposed Changes JSON field');return null;}var pr={};try{pr=JSON.parse(pjEl.value);}catch(e){alert('Invalid JSON: '+e.message);return null;}return {object_id:oid,change_type:ct,reason:document.getElementById('draftReason___CAP_ID__').value,proposed:pr,created_by:'ui-user'};}

async function capCreateDraft___CAP_ID__(evt){evt.preventDefault();var resultEl=document.getElementById('actionResult___CAP_ID__');resultEl.textContent='Creating draft preview...';try{var payload=capBuildDraftPayload___CAP_ID__();if(!payload){resultEl.textContent='Error: check form fields and try again';return;}var res=await api('/changes/draft-preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(res.detail){resultEl.textContent=JSON.stringify(res,null,2);return;}var diff=(res.patch_preview||{}).yaml_diff||'';resultEl.innerHTML='<div style=\"color:var(--lime);margin-bottom:6px;font-weight:600;font-size:13px\">Draft: '+esc(res.change.id)+' ('+esc(res.change.status)+')</div><pre style=\"margin:0;max-height:340px;overflow:auto;font-size:10px;line-height:1.4;padding:6px 0\">'+esc(diff)+'</pre>';document.getElementById('draftReason___CAP_ID__').value='';var pj=document.getElementById('draftProposedJson___CAP_ID__');if(pj)pj.value='';await capLoadChanges___CAP_ID__();await capLoadChangeDetail___CAP_ID__(res.change.id);}catch(e){resultEl.textContent='Draft failed: '+e.message;}}

function capBindChangeEvents___CAP_ID__(){var sf=document.getElementById('changeStatusFilter___CAP_ID__');if(sf)sf.addEventListener('change',capLoadChanges___CAP_ID__);var df=document.getElementById('draftForm___CAP_ID__');if(df)df.addEventListener('submit',capCreateDraft___CAP_ID__);}

// Responsive: collapse layout on narrow screens
(function(){try{var styleEl=document.createElement('style');styleEl.textContent='@media(max-width:900px){.capLayout___CAP_ID__{grid-template-columns:1fr!important}}';document.head.appendChild(styleEl);}catch(e){}})();

capBindInventoryEvents___CAP_ID__();capBindChangeEvents___CAP_ID__();
// NOTE: capLoadObjects and capLoadChanges are triggered lazily by navigateTo() when tab is first activated.
// Do NOT call them here to avoid loading all capabilities on page startup.
"""
    return (
        tpl.replace("__CAP_ID__", cap_id)
        .replace("__RTYPE_LIST__", rtype_list)
        .replace("__CTYPE_LIST__", ctype_list)
        .replace("__DEFAULT_CHANGE_TYPE__", default_change_type)
    )
