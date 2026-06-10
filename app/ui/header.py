_HEADER_HTML = """  <header class="top" data-component="app-header"><div class="brand"><div class="mark">G</div><div><b>GitOps Platform</b><span>Terraform Control Plane — K8S Resource Change</span></div></div><div class="topRight"><select id="projectSelector" onchange="setProject(this.value)" style="background:#140f22;border:1px solid #4a3b70;color:#fff;border-radius:12px;padding:8px 12px;font-size:13px"><option value="default">Loading projects...</option></select><div class="status"><i class="dot"></i><span id="health">checking</span></div><button class="btn" onclick="loadAll()">Refresh</button></div></header>
"""


def render_header_html():
    return _HEADER_HTML
