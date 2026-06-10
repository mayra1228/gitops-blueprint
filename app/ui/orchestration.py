_PAGE_ORCHESTRATION_SCRIPT = """let _projectCache=[];async function loadProjects(){const res=await api('/api/projects');const sel=document.getElementById('projectSelector');if(res.items&&res.items.length){_projectCache=res.items;sel.innerHTML=res.items.map(p=>`<option value="${esc(p.id)}">${esc(p.name)}</option>`).join('');window.currentProject=res.items[0].id;const firstNav=document.querySelector('.sidebar-item.active');if(firstNav){navigateTo(firstNav.dataset.nav);}else{navigateTo('dashboard');}}else{sel.innerHTML='<option value="default">No projects</option>';navigateTo('dashboard');}}
let loadedTabs=new Set();

async function navigateTo(name){
  window.activeTab=name;
  document.querySelectorAll('.sidebar-item').forEach(a=>a.classList.toggle('active',a.dataset.nav===name));
  document.querySelectorAll('.tab-panel').forEach(p=>p.classList.toggle('active',p.id==='tab-'+name));
  if(!loadedTabs.has(name)){
    loadedTabs.add(name);
    if(name.startsWith('capability-')){
      const capId=name.replace('capability-','');
      const loadObjectsFn=window['capLoadObjects_'+capId];
      const loadChangesFn=window['capLoadChanges_'+capId];
      if(loadObjectsFn) await loadObjectsFn();
      if(loadChangesFn) await loadChangesFn();
    }
    if(name==='adapter'){if(typeof loadAdapterPage==='function')await loadAdapterPage();}
    if(name==='skeleton'){if(typeof loadSkelProviders==='function')await loadSkelProviders();}
    if(name==='import'){if(typeof loadImportAdapters==='function')loadImportAdapters();}
    if(name==='dashboard'){await loadRecentActivity();await loadProjectAdapterInfo();await dbLoadSummary();await dbLoadOverview();await dbLoadRecentChanges();}
    if(name==='history')await loadHistory();
    if(name==='tf-control-plane'){if(typeof tcpLoadAll==='function'){await tcpLoadAll();if(typeof bindTerraformControlPlaneEvents==='function')bindTerraformControlPlaneEvents();}}
    if(name==='governance'){if(typeof govLoadAll==='function'){await govLoadAll();if(typeof bindGovernanceEvents==='function')bindGovernanceEvents();}}
    if(name==='admin'){if(typeof adminLoadAll==='function')await adminLoadAll();}
  }
}

async function loadProjectAdapterInfo(){
  const proj=_projectCache.find(p=>p.id===window.currentProject);
  if(!proj)return;
  adapterGit.textContent=proj.git_adapter||'github';
  adapterGitDetail.textContent=proj.git_config?proj.git_config.org+'/'+proj.git_config.repo:'-';
  adapterExec.textContent=proj.execution_adapter||'jenkins';
  adapterExecDetail.textContent=proj.execution_config?proj.execution_config.job_name:'-';
  adapterWebhook.textContent=proj.git_adapter||'github';
  adapterWebhookDetail.textContent='X-Hub-Signature-256';
  try{
    const infra=await api('/api/infrastructure-adapters');
    adapterAvailableGit.textContent=(infra.git||[]).map(a=>a.name).join(', ');
  }catch(e){adapterAvailableGit.textContent='-';}
}

async function switchTab(name){navigateTo(name);}

async function loadRecentActivity(){
  const container=document.getElementById('activityFeed');
  try{
    const resp=await api('/changes?limit=5');
    const items=(resp.items||[]).slice(0,5);
    if(!items.length){container.innerHTML='<div class="empty">No activity yet</div>';return;}
    container.innerHTML=items.map(x=>`<div class="activityItem"><b>${esc(x.id)}</b><small><span class="pill changeStatusBadge">${esc(x.status)}</span> ${esc(x.change_type)} — ${esc(x.object_id||'')}</small></div>`).join('');
  }catch(e){container.innerHTML='<div class="empty">Failed to load</div>';}
}

async function loadHistory(){
  const container=document.getElementById('historyRows');
  container.innerHTML='<tr><td colspan="5" class="empty">Loading...</td></tr>';
  try{
    const filter=document.getElementById('historyTypeFilter');
    const typeFilter=filter?filter.value:'';
    let changeItems=[],scaffoldItems=[];
    if(!typeFilter||typeFilter==='change'){
      const resp=await api('/changes?limit=50');
      changeItems=(resp.items||[]).map(c=>({...c,_type:'change'}));
    }
    if(!typeFilter||typeFilter==='scaffold'){
      const scaffolds=await api('/skeletons/history?limit=50');
      scaffoldItems=(scaffolds.items||[]).map(s=>({...s,_type:'scaffold'}));
    }
    const all=[...changeItems,...scaffoldItems].sort((a,b)=>{
      const at=a.created_at||a.updated_at||'';
      const bt=b.created_at||b.updated_at||'';
      return bt.localeCompare(at);
    });
    const filtered=typeFilter?all.filter(x=>x._type===typeFilter):all;
    document.getElementById('historyCount').textContent=filtered.length?`${filtered.length} items`:'No history';
    if(!filtered.length){container.innerHTML='<tr><td colspan="5" class="empty">No history</td></tr>';return;}
    container.innerHTML=filtered.map(x=>{
      if(x._type==='scaffold'){
        const statusColor=x.status==='applied'?'#10b981':'#ef4444';
        const prLink=x.pr_url?`<a href="${esc(x.pr_url)}" target="_blank" style="color:var(--lime)">PR</a>`:esc(x.branch||'-');
        const ts=(x.created_at||'').substring(0,16);
        return `<tr><td><span class="pill" style="background:rgba(113,112,255,.14);color:#d6d7ff;border-color:rgba(113,112,255,.3)">Scaffold</span></td><td><b>${esc(x.template_name)}</b><div class="muted" style="font-size:10px">${esc(x.provider||'')} &middot; ${esc(x.author||'')}</div></td><td><span style="color:${statusColor};font-weight:600">${esc(x.status)}</span></td><td>${prLink}</td><td class="muted" style="font-size:11px">${esc(ts)}</td></tr>`;
      }else{
        const ts=(x.created_at||x.updated_at||'').substring(0,16);
        return `<tr onclick="loadChangeDetail('${encodeURIComponent(x.id)}')" style="cursor:pointer"><td><span class="pill" style="background:rgba(16,185,129,.14);color:#10b981;border-color:rgba(16,185,129,.3)">Change</span></td><td><div class="cellMain"><b>${esc(x.id)}</b><div class="mono changeCompactMeta">${esc(x.object_id)}</div></div></td><td><span class="pill changeStatusBadge">${esc(x.status)}</span></td><td style="font-size:11px">${esc(x.env||'-')} &middot; ${esc(x.change_type)} &middot; <span class="mono">${esc(x.source_path||'-')}</span></td><td class="muted" style="font-size:11px">${esc(ts)}</td></tr>`;
      }
    }).join('');
  }catch(e){container.innerHTML='<tr><td colspan="5" class="empty">Failed to load</td></tr>';}
}

bindTemplateCatalogEvents();
const histFilter=document.getElementById('historyTypeFilter');
if(histFilter)histFilter.addEventListener('change',loadHistory);
loadProjects();
"""


def page_orchestration_script():
    return _PAGE_ORCHESTRATION_SCRIPT
