# SupportOps

Support ticket system with automated incident handling, delivered with Docker, Kubernetes (K3s), Helm, GitOps (Argo CD) and canary releases (Argo Rollouts). Student project by a team of three: **Doha, Aya, Maryam**. Spec: `Cahier des charges v2.1` (4 to 5 weeks).

Detailed context lives in [.agents/](.agents/README.md). Read it before large tasks.

## Who owns what

| Pole | Owner | Scope |
|---|---|---|
| Cloud, data, resilience | **Aya** | `infrastructure/terraform/`, cloud-init + K3s, Traefik/TLS, StorageClass + PVC, SOPS + Age, `scripts/backup-db.sh`, `scripts/restore-db.sh`, cost report |
| Kubernetes, GitOps, progressive delivery | Doha | `deploy/helm/` (API, frontend, Ingress), Argo CD, Argo Rollouts, `security.yml`, probes/resources |
| CI/CD, observability, performance | Maryam | `.github/workflows/`, GHCR, `monitoring/`, API metrics, `load-tests/` (k6) |

Stay in your pole unless doing a listed cross-contribution (spec §5.3). The current user is **Aya** unless told otherwise.

## Repository layout

```
backend/            FastAPI API + Celery tasks (Python 3.12)
frontend/           React (Vite) SPA, served by nginx
tests/              Pytest suite (run from the repo root)
deploy/helm/        Helm chart `supportops`
deploy/environments Per-environment values (dev.yaml, later prod)
deploy/secrets/     SOPS-encrypted secrets (*.enc.yaml) - planned
infrastructure/terraform/  Cloud code (Hetzner, single K3s node)
monitoring/         Prometheus/Alertmanager/Grafana - planned (Maryam)
load-tests/         k6 scenarios - planned (Maryam)
scripts/            Operations scripts
docs/               Documentation and the interface contract
compose.yaml        Local stack
```

## Commands

```bash
# Local stack (from repo root, in WSL)
cp .env.example .env                       # never commit .env
docker compose up -d --build
docker compose exec backend python -m app.seed     # demo accounts: admin, tech1, user1
# UI http://localhost:8080 | API docs http://localhost:8000/docs | Mailpit http://localhost:8025

# Tests (needs backend/requirements-dev.txt)
python -m pytest -q tests

# Helm
helm lint deploy/helm/supportops
helm template supportops deploy/helm/supportops -f deploy/environments/dev.yaml

# Terraform (token only through the environment)
cd infrastructure/terraform
terraform fmt -check && terraform init -backend=false && terraform validate
```

## Hard rules

1. **No secret in Git.** No `.env`, tokens, `*.tfstate`, `*.tfvars` (only `*.tfvars.example`), kubeconfig, or age private keys. `.gitignore` covers them; do not weaken it. Gitleaks blocks PRs.
2. **Follow the interface contract** in `docs/interfaces.md`: namespace `supportops`, service names `api, frontend, worker, scheduler, postgres, redis, mailpit`, Secret `supportops-secrets`, image tags `ghcr.io/<org>/supportops-<component>:<sha>`. Change it only through a PR that edits that file.
3. **Never run `terraform apply`/`destroy`, `kubectl delete`, or anything that costs money or destroys data without the user asking.** Always destroy cloud resources after a demo.
4. **Exactly one Celery Beat** (`scheduler`, 1 replica, `Recreate` strategy). Two would duplicate every periodic check.
5. All containers need `readinessProbe`, `livenessProbe` and `resources.requests/limits`.
6. The backend image has no shell: probes and commands call `python` directly.

## Git workflow

- Branch off `main`, one topic per branch: `feat/...`, `fix/...`, `docs/...`, `chore/...`.
- Conventional commits (`feat(infra): ...`, `docs: ...`). Never commit directly to `main`.
- Every PR is reviewed by another member within 24 h; after that, merge is allowed if CI is green.
- CI: Pytest, syntax check, image build, Gitleaks, Trivy (HIGH/CRITICAL, `.trivyignore` documents exceptions).

## Language

Project documentation (`docs/`, README) is in **French**. Code, comments, commit messages and configuration are in English.

## Known deviations from the spec

- PostgreSQL 17 and Redis 8 (spec says 16 and 7): already used across Compose and the chart; documented in `docs/interfaces.md` section 7.
- Cloud provider: Hetzner single node (spec only says "a cloud provider"). While no cloud account exists, work runs on a local **k3d** cluster (spec §5.2 fallback).
