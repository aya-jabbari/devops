# Skill: working on the Helm chart

Chart: `deploy/helm/supportops/` (templates: `redis.yaml`, `worker.yaml`, `scheduler.yaml`, `_helpers.tpl`). API, frontend and PostgreSQL templates belong to Doha / planned.

## Validate

```bash
helm lint deploy/helm/supportops
helm template supportops deploy/helm/supportops -f deploy/environments/dev.yaml | less
```

## Install on a cluster

```bash
helm upgrade --install supportops deploy/helm/supportops -n supportops \
  -f deploy/environments/dev.yaml \
  --set backendImage.repository=ghcr.io/aya-jabbari/supportops-backend,backendImage.pullPolicy=Never
kubectl -n supportops get pods
kubectl -n supportops logs deploy/supportops-worker
```

The Secret `supportops-secrets` must exist first (see k3d / SOPS skills). Worker and scheduler need PostgreSQL and Mailpit in the cluster to become healthy.

## Rules

- Service names follow `docs/interfaces.md` (`redis`, `postgres`, `api`, ...), without a release prefix.
- Every container: `readinessProbe`, `livenessProbe`, `resources.requests/limits`.
- Scheduler: 1 replica, `strategy: Recreate`.
- No secret values in `values*.yaml`; reference the existing Secret.
- Image: `backendImage.repository:tag`; CI sets the tag to the commit SHA.
- Persistence (planned, mine): `persistence.enabled` (default true) and `persistence.size`; `false` uses `emptyDir` for Kind/k3d tests.
- Commands run `python` directly (image has no shell); the container args must not assume `sh`.
