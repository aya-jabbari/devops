#!/usr/bin/env bash
# Rebuild the local Kind lab: cluster, images, ingress, dev secret, Argo CD, Argo Rollouts,
# Prometheus/Grafana, then the Argo CD Application. Safe to re-run (steps already done are skipped).
# Usage: APP_REVISION=<git branch Argo CD should follow>  scripts/dev-bootstrap-kind.sh   (default: main)
set -euo pipefail

CLUSTER=supportops
NS=supportops
APP_REVISION="${APP_REVISION:-main}"
cd "$(cd "$(dirname "$0")/.." && pwd)"

echo "==> Kind cluster"
kind get clusters | grep -qx "$CLUSTER" || kind create cluster --name "$CLUSTER" --config deploy/kind-config.yaml
kubectl config use-context "kind-$CLUSTER" >/dev/null
kubectl get ns "$NS" >/dev/null 2>&1 || kubectl create namespace "$NS"

echo "==> Images (local build, tag dev)"
docker build -q --provenance=false --sbom=false -t ghcr.io/aya-jabbari/supportops-backend:dev backend
docker build -q --provenance=false --sbom=false -t ghcr.io/aya-jabbari/supportops-frontend:dev frontend
kind load docker-image ghcr.io/aya-jabbari/supportops-backend:dev ghcr.io/aya-jabbari/supportops-frontend:dev --name "$CLUSTER"

echo "==> ingress-nginx"
kubectl apply -f https://kind.sigs.k8s.io/examples/ingress/deploy-ingress-nginx.yaml >/dev/null
sleep 15
kubectl -n ingress-nginx wait --for=condition=ready pod --selector=app.kubernetes.io/component=controller --timeout=180s

echo "==> Dev secret (cluster only, never in Git)"
if ! kubectl -n "$NS" get secret supportops-secrets >/dev/null 2>&1; then
  PGPASS=$(openssl rand -hex 12)
  kubectl -n "$NS" create secret generic supportops-secrets \
    --from-literal=POSTGRES_USER=supportops \
    --from-literal=POSTGRES_PASSWORD="$PGPASS" \
    --from-literal=POSTGRES_DB=supportops \
    --from-literal=DATABASE_URL="postgresql+psycopg://supportops:${PGPASS}@postgres:5432/supportops" \
    --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
    --from-literal=ALERTMANAGER_WEBHOOK_SECRET="$(openssl rand -hex 16)"
fi

echo "==> Argo CD"
kubectl get ns argocd >/dev/null 2>&1 || kubectl create namespace argocd
kubectl apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml >/dev/null
kubectl -n argocd rollout status deploy/argocd-server --timeout=300s

echo "==> Argo Rollouts"
kubectl get ns argo-rollouts >/dev/null 2>&1 || kubectl create namespace argo-rollouts
kubectl apply -n argo-rollouts --server-side --force-conflicts -f https://github.com/argoproj/argo-rollouts/releases/latest/download/install.yaml >/dev/null
kubectl -n argo-rollouts rollout status deploy/argo-rollouts --timeout=180s

echo "==> Prometheus + Grafana"
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts >/dev/null 2>&1 || true
helm repo update >/dev/null
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace \
  -f monitoring/kind-values.yaml --wait --timeout 10m

echo "==> Argo CD Application (following: $APP_REVISION)"
sed "s|targetRevision: main|targetRevision: ${APP_REVISION}|" deploy/argocd/application.yaml | kubectl apply -f -

echo
echo "Argo CD admin password: $(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 -d)"
echo "Next: wait for the app to be Healthy, then seed:  kubectl -n $NS exec deploy/api -- python -m app.seed"
