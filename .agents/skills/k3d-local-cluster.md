# Skill: local k3d cluster

Use while there is no cloud account, or to test the chart before touching the cloud. Matches spec §5.2 (local cluster with the same interface contract).

## Create

```bash
k3d cluster create supportops -p "8081:80@loadbalancer"
kubectl get nodes                  # expect Ready
kubectl create namespace supportops
```

Traefik is included in K3s, reachable at `http://localhost:8081`.

## Load a local image (no GHCR yet)

```bash
docker compose build backend
docker tag supportops-backend:dev ghcr.io/aya-jabbari/supportops-backend:dev
k3d image import ghcr.io/aya-jabbari/supportops-backend:dev -c supportops
```

Install with `backendImage.pullPolicy=Never` so the cluster uses the imported image.

## Throwaway dev secret

```bash
kubectl -n supportops create secret generic supportops-secrets \
  --from-literal=DATABASE_URL='postgresql+psycopg://supportops:devpass@postgres:5432/supportops' \
  --from-literal=SECRET_KEY="$(openssl rand -hex 32)" \
  --from-literal=ALERTMANAGER_WEBHOOK_SECRET="$(openssl rand -hex 16)"
```

Lives only in the cluster. Never put these values in a file in Git.

## Reset / delete

```bash
k3d cluster delete supportops
```
