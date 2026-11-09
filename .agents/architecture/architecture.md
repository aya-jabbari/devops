# Architecture

## Runtime components

| Component | Tech | Notes |
|---|---|---|
| `frontend` | React (Vite), nginx | nginx serves the SPA and proxies `/api/` to the API (`backend:8000` in Compose, `api:8000` in Kubernetes) |
| `api` (`backend` in Compose) | FastAPI, SQLAlchemy | JWT auth, RBAC, tickets, assignment, dashboard, incidents. Probes: `/healthz`, `/readyz` (checks the DB) |
| `worker` | Celery 5 | Sends e-mails (assignment, comment, resolution, overdue). 3 bounded retries with backoff |
| `scheduler` | Celery Beat | **One replica only.** Runs `check_overdue` every `OVERDUE_CHECK_SECONDS` (300) |
| `postgres` | PostgreSQL 17 | Persistent volume. Backup by `pg_dump` |
| `redis` | Redis 8 | Celery broker/result backend |
| `mailpit` | Mailpit | SMTP 1025 (capture), UI 8025 |

All backend roles (api, worker, scheduler) use the same image, different command. The image entrypoint is the venv python: `/app/venv/bin/python`.

## Request and event flows

**Ticket and notification**
`frontend -> api -> postgres`; assignment/comment/resolution enqueues a Celery task in `redis`; `worker` sends the mail to `mailpit`.

**SLA escalation**
`scheduler` triggers `check_overdue` -> overdue tickets become `CRITICAL` -> escalation mail (one per ticket and due date).

**Incident from alert**
`Prometheus` evaluates `alert_rules.yml` -> `Alertmanager` -> `POST /api/webhooks/alertmanager` with `Authorization: Bearer <ALERTMANAGER_WEBHOOK_SECRET>` -> `incident_service.process_alerts`. The Alertmanager **fingerprint** is the stable key: repeats update a counter, no duplicate. States: `active -> recovered -> closed` (technician confirms closure). Contract: `docs/incidents-contrats.md`.

## Delivery chain

```
PR -> GitHub Actions (pytest, lint, build, Gitleaks, Trivy)
main -> build images -> GHCR (tag = commit SHA)
Git (deploy/helm) -> Argo CD sync -> K3s
API update -> Argo Rollouts canary 20 % -> Prometheus 5xx analysis (k6 load)
   < 2 % -> promote 100 %      >= 2 % -> abort, back to stable
```

Traceability: commit SHA = GHCR image tag = version shown in Argo CD.

## Infrastructure target

One cloud server running K3s (Traefik ingress bundled), PostgreSQL and Redis inside the cluster on PVCs. This allows pod self-healing demos but is **not** multi-master HA. A PVC is not a backup: `backup-db.sh` / `restore-db.sh` are part of the delivery.

Terraform (`infrastructure/terraform/`, Hetzner):

| Resource | Purpose |
|---|---|
| primary IPv4 | stable public IP, put in the K3s TLS SAN |
| firewall | 22, 6443, Argo CD NodePort (30443) for admin CIDRs only; 80/443 public |
| ssh key + server | Ubuntu 24.04, cloud-init installs pinned K3s on first boot |
| outputs | IP, SSH command, API URL, Argo CD URL, kubeconfig command |

`scripts/get-kubeconfig.sh <ip>` fetches the kubeconfig and rewrites `127.0.0.1` to the public IP.

Local equivalent while there is no cloud account: `k3d cluster create supportops -p "8081:80@loadbalancer"`.

## Secrets

`supportops-secrets` (namespace `supportops`) holds `DATABASE_URL`, `SECRET_KEY`, `ALERTMANAGER_WEBHOOK_SECRET`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`. Versioned only encrypted (SOPS + Age) in `deploy/secrets/`; the Age private key never enters Git. Until then: throwaway secret created with `kubectl create secret` or a non-versioned `values-dev.yaml`.

## Observability contract

API exposes `http_requests_total{service,status}` and `http_request_duration_seconds` (planned, Maryam). One reference PromQL 5xx rate query is shared by the AnalysisTemplate and the alerts; it is in `docs/interfaces.md`.
