#!/usr/bin/env bash
set -euo pipefail

echo "=== GitOps Platform — K8S Sandbox Setup ==="

CLUSTER_NAME="${1:-gitops-sandbox}"
KUBECONFIG_OUT="${2:-$HOME/.kube/gitops-sandbox.yaml}"

echo ""
echo "Cluster:  ${CLUSTER_NAME}"
echo "Kubeconfig: ${KUBECONFIG_OUT}"
echo ""

# 1. Create kind cluster if not exists
if ! kind get clusters 2>/dev/null | grep -q "^${CLUSTER_NAME}$"; then
    echo "[1/4] Creating kind cluster '${CLUSTER_NAME}'..."
    cat <<YAML | kind create cluster --name "${CLUSTER_NAME}" --config=-
kind: Cluster
apiVersion: kind.x-k8s.io/v1alpha4
nodes:
  - role: control-plane
  - role: worker
YAML
else
    echo "[1/4] kind cluster '${CLUSTER_NAME}' already exists"
fi

# 2. Export kubeconfig
echo "[2/4] Exporting kubeconfig to ${KUBECONFIG_OUT}..."
kind export kubeconfig --name "${CLUSTER_NAME}" --kubeconfig "${KUBECONFIG_OUT}" 2>/dev/null || \
    kind get kubeconfig --name "${CLUSTER_NAME}" > "${KUBECONFIG_OUT}"

# 3. Create test namespace
echo "[3/4] Creating sandbox namespace..."
KUBECTL="kubectl --kubeconfig=${KUBECONFIG_OUT}"
${KUBECTL} create namespace sandbox --dry-run=client -o yaml | ${KUBECTL} apply -f -
${KUBECTL} label namespace sandbox app=gitops-platform --overwrite

# 4. Apply test resources
echo "[4/4] Deploying test HPA and Deployment..."
cat <<'YAML' | ${KUBECTL} apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: demo-app
  namespace: sandbox
  labels:
    app: demo-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: demo-app
  template:
    metadata:
      labels:
        app: demo-app
    spec:
      containers:
        - name: nginx
          image: nginx:alpine
          ports:
            - containerPort: 80
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 200m
              memory: 256Mi
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: demo-app-hpa
  namespace: sandbox
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: demo-app
  minReplicas: 2
  maxReplicas: 8
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
YAML

echo ""
echo "=== Sandbox Ready ==="
echo "Export path: export KUBECONFIG=${KUBECONFIG_OUT}"
echo "Test command: kubectl --kubeconfig=${KUBECONFIG_OUT} -n sandbox get all"
echo ""
echo "Update .env for GitOps Platform:"
echo "  KUBECONFIG_PATH=${KUBECONFIG_OUT}"
echo "  K8S_NAMESPACE_ALLOWLIST=sandbox,default"
