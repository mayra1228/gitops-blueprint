#!/usr/bin/env bash
# Demo script: full K8S HPA change workflow
# Requires: docker compose up, curl, python3
set -euo pipefail

BASE="http://localhost:9090/api"
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

step()  { echo -e "\n${CYAN}━━━ $1 ━━━${NC}"; }
ok()    { echo -e "${GREEN}  ✓ $1${NC}"; }
info()  { echo -e "${YELLOW}  → $1${NC}"; }
fail()  { echo -e "${RED}  ✗ $1${NC}"; exit 1; }

api() {
  local resp code body
  resp=$(curl -s -w "\n%{http_code}" "$@" 2>/dev/null)
  code=$(echo "$resp" | tail -1)
  body=$(echo "$resp" | sed '$d')
  if [ "${code}" -lt 200 ] || [ "${code}" -ge 300 ]; then
    fail "$1 failed (HTTP ${code}): ${body}"
  fi
  echo "${body}"
}

# ── Health check ──
step "Health check"
resp=$(curl -s "${BASE}/health")
echo "${resp}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Status: {d['status']}\")" || fail "health check failed"
ok "Platform is healthy"

# ── Create / find project ──
step "Setting up demo project"
# Try to use existing project first
existing=$(curl -s "${BASE}/projects" 2>/dev/null)
PROJECT_ID=$(echo "${existing}" | python3 -c "
import sys,json
items=json.load(sys.stdin).get('items',[])
print(items[0]['id'] if items else '')
" 2>/dev/null)

if [ -z "${PROJECT_ID}" ]; then
  project=$(api "${BASE}/projects" -X POST -H "Content-Type: application/json" \
    -d '{"name":"ECP Demo","slug":"ecp-demo","github_org":"my-org","github_repo":"ecp-infra","terraform_root":"infra"}')
  PROJECT_ID=$(echo "${project}" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
fi
info "Project ID: ${PROJECT_ID}"

# ── Inventory scan ──
step "Inventory Scan"
scan=$(api "${BASE}/${PROJECT_ID}/inventory/scan" -X POST)
echo "${scan}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Status: {d['status']}\")"

summary=$(api "${BASE}/${PROJECT_ID}/inventory/summary")
echo "${summary}" | python3 -c "
import sys,json
d=json.load(sys.stdin)['kpis']
print(f\"  Objects: {d['total_objects']} | Types: {d['resource_types']} | Envs: {d['environments']} | Errors: {d['errors']}\")
"
ok "Inventory scanned"

# ── View inventory objects ──
step "Inventory Objects (first 3)"
objects=$(api "${BASE}/${PROJECT_ID}/inventory/objects")
echo "${objects}" | python3 -c "
import sys,json
for x in json.load(sys.stdin)['items'][:3]:
    print(f\"  {x['display_name']} ({x['resource_type']}) -> {x.get('source',{}).get('path','?')}\")
"

# ── Create Change Request ──
step "Creating Change Request (scale api-gateway maxReplicas: 5 → 12)"
draft=$(api "${BASE}/${PROJECT_ID}/changes/draft-preview" -X POST \
  -H "Content-Type: application/json" \
  -d '{"change_type":"odp_resource_update","object_id":"ODP/resources/dev/ecp/api-gateway","proposed":{"maxReplicas":12},"reason":"scale up for demo","created_by":"demo-user"}')
CHANGE_ID=$(echo "${draft}" | python3 -c "import sys,json; print(json.load(sys.stdin)['change']['id'])")
info "Change ID: ${CHANGE_ID}"
echo "${draft}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
diff=d.get('patch_preview',{}).get('yaml_diff','')
print(diff[:300] if diff else 'no diff')
"
ok "Draft created + patch generated"

# ── Validate ──
step "Validation"
validate=$(api "${BASE}/${PROJECT_ID}/changes/${CHANGE_ID}/validate" -X POST)
echo "${validate}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f\"  Status: {d['status']}\")
for c in d.get('checks',[]):
    print(f\"  [{c['status']}] {c['name']}\")
"
ok "Validation complete"

# ── Plan (Dry-Run) ──
step "Plan (Dry-Run)"
plan=$(api "${BASE}/${PROJECT_ID}/changes/${CHANGE_ID}/plan" -X POST)
echo "${plan}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f\"  Status: {d['status']}\")
impact=d.get('impact',{})
print(f\"  Target:  {impact.get('target_service','?')}\")
print(f\"  Ops:     {', '.join(impact.get('operations',[]))}\")
"
ok "Plan generated"

# ── Submit for Approval ──
step "Submit for Approval"
submit=$(api "${BASE}/${PROJECT_ID}/changes/${CHANGE_ID}/submit" -X POST \
  -H "Content-Type: application/json" \
  -d '{"requester":"sre-user","note":"need scale up for demo"}')
echo "${submit}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Status: {d['status']}\")"
ok "Submitted for approval"

# ── Approve ──
step "Approval Decision"
approve=$(api "${BASE}/${PROJECT_ID}/changes/${CHANGE_ID}/approve" -X POST \
  -H "Content-Type: application/json" \
  -d '{"approver":"manager","decision":"approve","comment":"approved for demo"}')
echo "${approve}" | python3 -c "import sys,json; d=json.load(sys.stdin); print(f\"  Status: {d['status']}\")"
ok "Approved"

# ── Execute ──
step "Execution (Create PR skeleton)"
execute=$(api "${BASE}/${PROJECT_ID}/changes/${CHANGE_ID}/execute" -X POST \
  -H "Content-Type: application/json" \
  -d '{"executor":"sre-bot"}')
echo "${execute}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f\"  Status: {d['status']}\")
if d.get('external_url'): print(f\"  PR: {d['external_url']}\")
"
ok "Execution complete"

# ── Audit Trail ──
step "Audit Trail"
audit=$(api "${BASE}/${PROJECT_ID}/changes/${CHANGE_ID}/audit")
echo "${audit}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f\"  Total events: {d['total']}\")
for e in d['items']:
    print(f\"  [{e['sequence']}] {e['type']} — {e['actor']}: {e['message']}\")
"
ok "Audit trail complete"

# ── Final State ──
step "Final Change State"
final=$(api "${BASE}/${PROJECT_ID}/changes/${CHANGE_ID}")
echo "${final}" | python3 -c "
import sys,json
d=json.load(sys.stdin)
print(f\"  Status:  {d['status']}\")
arts=sorted(d.get('artifacts',{}).keys())
print(f\"  Artifacts: {', '.join(arts)}\")
"

echo -e "\n${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  Demo complete!${NC}"
echo -e "${GREEN}  Open http://localhost:9090/ to view in browser${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
