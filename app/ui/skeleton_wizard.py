_SKELETON_PAGE_HTML = """<section data-component="skeleton-page">
<div class="card" style="margin-bottom:18px;background:linear-gradient(180deg,rgba(255,255,255,.075),rgba(255,255,255,.035));border-color:rgba(194,239,78,.22)">
<div class="toolbar"><div><div class="eyebrow">Skeleton — Scaffolding</div><h2 style="font-size:28px">Template Scaffold</h2><p>Standardized Terraform directory structure for onboarding new resources. Select a template, fill parameters, preview, and apply.</p></div><div class="filters"><select id="skelProviderFilter"><option value="">All providers</option></select><select id="skelModeFilter"><option value="">All modes</option><option value="yaml">YAML</option><option value="hcl">HCL / Terraform</option></select><button class="btn" id="skelLoadBtn" type="button">Load</button></div></div>
</div>

<div class="grid4" style="margin-bottom:18px">
<div class="kpi"><span>Templates</span><strong id="kpiSkelCount">-</strong><small>available</small></div>
<div class="kpi"><span>YAML Mode</span><strong id="kpiYamlCount">-</strong><small>ODP-style</small></div>
<div class="kpi"><span>HCL Mode</span><strong id="kpiHclCount">-</strong><small>Terraform .tf</small></div>
<div class="kpi"><span>Providers</span><strong id="kpiProviderCount">-</strong><small>registered</small></div>
</div>

<div class="skeletonTemplateGrid" id="skelTemplateGrid"><div class="empty">Loading skeleton templates...</div></div>
</section>"""

_SKELETON_WIZARD_MODAL = """<div id="skeletonWizard" class="modal" style="display:none"><div class="skeletonWizardOverlay" onclick="closeSkeletonWizard()"></div><div class="skeletonWizardCard"><div class="toolbar"><div><div class="eyebrow" id="swTemplateName">Skeleton Wizard</div><h2 id="swTemplateTitle">Generate Scaffold</h2><p id="swTemplateDesc">Fill parameters to generate files</p></div><div class="swModeBadge" id="swModeBadge">YAML</div><button class="btn" onclick="closeSkeletonWizard()" style="background:var(--muted)">X</button></div><div class="skeletonWizardBody"><div class="skeletonFormPanel"><div class="swStepIndicator"><div class="swStep active">1. Configure</div><div class="swStepArrow">→</div><div class="swStep" id="swStepPreview">2. Preview</div><div class="swStepArrow">→</div><div class="swStep" id="swStepApply">3. Apply</div></div><form id="skeletonForm" style="margin-top:14px"><div id="skeletonFormFields"></div><div class="draftActions" style="margin-top:16px;gap:10px"><button class="btn" type="button" id="skeletonPreviewBtn">Preview Files</button><button class="btn" type="button" id="skeletonApplyBtn" disabled>Apply & Create PR</button></div></form></div><div class="skeletonPreviewPanel"><div class="eyebrow">Generated Files</div><div id="skeletonPreviewArea"><pre class="detail mono muted">Click Preview to see the generated directory tree.</pre></div></div></div><div id="skeletonResultArea" class="skeletonResultBar" style="display:none"></div></div></div>"""

_SKELETON_SCRIPT = """// --- Skeleton Template Browser ---
function renderSkelModeBadge(mode){const cls=mode==='hcl'?'swBadgeHcl':'swBadgeYaml';return `<span class="swBadge ${cls}">${mode.toUpperCase()}</span>`;}
function renderSkelTreePreview(dirs){return dirs.map(d=>`<div class="skelTreeDir"><div class="skelTreeDirPath mono">${esc(d.path_template)}</div>${(d.files||[]).map(f=>`<div class="skelTreeFile"><span class="skelTreeFileIcon">${f.file_type==='hcl'?'&#9881;':f.file_type==='yaml'?'&#9776;':'&#9998;'}</span><span class="skelTreeFileName">${esc(f.filename_template)}</span><span class="skelTreeFileType">${esc(f.file_type)}</span></div>`).join('')}</div>`).join('');}
function renderSkelCard(t){return `<article class="templateCard skelTemplateCard" data-template-id="${esc(t.id)}" onclick="openSkeletonWizard('${esc(t.id)}')"><div class="templateCardHead"><div><span class="templateProvider">${esc(t.provider)}</span><h3>${esc(t.name)}</h3></div>${renderSkelModeBadge(t.render_mode)}</div><div class="templateResourceType mono">${esc(t.render_mode)} mode · ${t.file_count||0} files · ${t.directory_count||0} dirs</div><p>${esc(t.description||'')}</p><div class="skelMiniTree">${renderSkelTreePreview(t.directories||[])}</div><div style="margin-top:12px;display:flex;gap:6px;flex-wrap:wrap">${(t.tags||[]).map(tag=>`<span class="chip">${esc(tag)}</span>`).join('')}</div><div class="templateActionRow"><button class="btn" type="button">Use Template</button><span class="muted">opens scaffold wizard</span></div></article>`;}
async function loadSkeletonCatalog(){const qs=new URLSearchParams();const pf=document.getElementById('skelProviderFilter');if(pf&&pf.value)qs.set('provider',pf.value);const mf=document.getElementById('skelModeFilter');if(mf&&mf.value)qs.set('render_mode',mf.value);const grid=document.getElementById('skelTemplateGrid');grid.innerHTML='<div class="empty">Loading...</div>';const res=await api('/skeletons/templates'+'?'+qs.toString());if(res.detail){grid.innerHTML=`<div class="empty">${esc(res.detail)}</div>`;return;}const items=res.items||[];kpiSkelCount.textContent=items.length;kpiYamlCount.textContent=items.filter(t=>t.render_mode==='yaml').length;kpiHclCount.textContent=items.filter(t=>t.render_mode==='hcl').length;kpiProviderCount.textContent=[...new Set(items.map(t=>t.provider))].length;grid.innerHTML=items.length?items.map(renderSkelCard).join(''):'<div class="empty">No skeleton templates found.</div>';}
async function loadSkelProviders(){const res=await api('/skeletons/templates');const items=res.items||[];const providers=[...new Set(items.map(t=>t.provider))];const sel=document.getElementById('skelProviderFilter');providers.forEach(p=>{const opt=document.createElement('option');opt.value=p;opt.textContent=p;sel.appendChild(opt);});loadSkeletonCatalog();}

// --- Skeleton Wizard ---
let _skelTemplateId='';
async function openSkeletonWizard(templateId){_skelTemplateId=templateId;const wiz=document.getElementById('skeletonWizard');wiz.style.display='block';skeletonApplyBtn.disabled=true;swStepPreview.classList.remove('active');swStepApply.classList.remove('active');skeletonPreviewArea.innerHTML='<pre class="detail mono muted">Loading schema...</pre>';skeletonResultArea.style.display='none';skeletonFormFields.innerHTML='<div class="empty">Loading...</div>';
  const res=await api('/skeletons/templates/'+encodeURIComponent(templateId)+'/schema');
  if(res.detail){skeletonFormFields.innerHTML=`<div class="empty" style="color:#f66">${esc(res.detail)}</div>`;return;}
  swTemplateName.textContent=res.provider||'';swTemplateTitle.textContent=res.template_name||templateId;swTemplateDesc.textContent='Fill parameters and preview generated files';
  const badge=document.getElementById('swModeBadge');badge.textContent=(res.render_mode||'yaml').toUpperCase();badge.className='swModeBadge '+(res.render_mode==='hcl'?'swBadgeHcl':'swBadgeYaml');
  const schema=res.parameter_schema||{};const props=schema.properties||{};const required=new Set(schema.required||[]);
  skeletonFormFields.innerHTML=Object.entries(props).map(([key,prop])=>{
    const def=prop.default!==undefined?(' value="'+esc(prop.default)+'"'):'';
    const req=required.has(key)?' (required)':'';
    const ph=prop.description?(' placeholder="'+esc(prop.description)+'"'):'';
    if(prop.type==='integer'||prop.type==='number')return `<label>${esc(prop.title||key)}${req}<input name="${esc(key)}" type="number"${def}${ph} /></label>`;
    if(prop.enum)return `<label>${esc(prop.title||key)}${req}<select name="${esc(key)}">${prop.enum.map(v=>`<option value="${esc(v)}"${prop.default===v?' selected':''}>${esc(v)}</option>`).join('')}</select></label>`;
    return `<label>${esc(prop.title||key)}${req}<input name="${esc(key)}" type="text"${def}${ph} /></label>`;
  }).join('');
}
function closeSkeletonWizard(){document.getElementById('skeletonWizard').style.display='none';_skelTemplateId='';}
function collectSkelParams(){const fd=new FormData(document.getElementById('skeletonForm'));const params={};for(const [k,v] of fd.entries())params[k]=v;return params;}

function renderTreePreview(files){
  if(!files.length)return '<pre class="detail mono muted">No files generated</pre>';
  const byDir={};
  files.forEach(f=>{const d=f.directory||'';if(!byDir[d])byDir[d]=[];byDir[d].push(f);});
  return Object.entries(byDir).map(([dir,fs])=>`<div class="skelPreviewDir"><div class="skelPreviewDirPath mono">${esc(dir)}/</div>${fs.map(f=>`<div class="skelPreviewFile"><div class="skelPreviewFileHead"><span class="skelPreviewFileName mono">${esc(f.filename)}</span><span class="chip" style="font-size:10px">${esc(f.file_type)}</span></div><pre class="detail mono" style="height:auto;max-height:300px;margin:0">${esc(f.content)}</pre></div>`).join('')}</div>`).join('');
}

skeletonPreviewBtn.addEventListener('click',async ()=>{
  if(!_skelTemplateId)return;
  swStepPreview.classList.add('active');
  skeletonPreviewArea.innerHTML='<pre class="detail mono muted">Rendering...</pre>';
  const res=await api('/skeletons/preview',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({template_id:_skelTemplateId,params:collectSkelParams()})});
  if(res.detail){skeletonPreviewArea.innerHTML='<pre class="detail mono" style="color:#f66">'+JSON.stringify(res,null,2)+'</pre>';return;}
  skeletonPreviewArea.innerHTML=renderTreePreview(res.files||[]);
  skeletonApplyBtn.disabled=(res.files||[]).length===0;
});
skeletonApplyBtn.addEventListener('click',async ()=>{
  if(!_skelTemplateId)return;
  swStepApply.classList.add('active');skeletonApplyBtn.disabled=true;skeletonApplyBtn.textContent='Applying...';
  const res=await api('/skeletons/apply',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({template_id:_skelTemplateId,params:collectSkelParams()})});
  skeletonApplyBtn.textContent='Apply & Create PR';skeletonApplyBtn.disabled=false;
  if(res.success){
    skeletonResultArea.style.display='block';
    const capLink=res.capability_id?`<button class="btn" style="margin-left:8px" onclick="navigateTo('capability-${esc(res.capability_id)}');closeSkeletonWizard()">View in Capability</button>`:'';
    skeletonResultArea.innerHTML=`<div class="skeletonSuccess"><b>&#10003; Scaffold applied!</b><a href="${esc(res.pr_url||'#')}" target="_blank" rel="noopener">View PR</a><small>Branch: ${esc(res.branch||'')}</small>${capLink}</div>`;
  }else{
    skeletonResultArea.style.display='block';
    skeletonResultArea.innerHTML=`<div class="skeletonError"><b>Apply failed:</b><span>${esc(res.error||'')}</span></div>`;
  }
});
document.getElementById('skelLoadBtn').addEventListener('click',loadSkeletonCatalog);
document.getElementById('skelProviderFilter').addEventListener('change',loadSkeletonCatalog);
document.getElementById('skelModeFilter').addEventListener('change',loadSkeletonCatalog);
"""


def render_skeleton_wizard_html():
    return _SKELETON_PAGE_HTML + _SKELETON_WIZARD_MODAL


def skeleton_wizard_script():
    return _SKELETON_SCRIPT
