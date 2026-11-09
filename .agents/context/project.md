# Project context

## Goal

A support ticket platform. Users create tickets, technicians handle them. Prometheus/Alertmanager create incidents automatically (idempotent, deduplicated by fingerprint). Delivered end to end: local Compose, Terraform + K3s, Helm, Argo CD (GitOps), Argo Rollouts (canary with automatic rollback on 5xx > 2 %), SOPS + Age secrets, backup/restore, k6 load tests.

## Team and poles

| Member | Pole | Substitute |
|---|---|---|
| Aya | Cloud, data, resilience | Aya substitutes Doha |
| Doha | Kubernetes, GitOps, progressive delivery | Doha substitutes Maryam |
| Maryam | CI/CD, observability, performance | Maryam substitutes Aya |

Each member must be able to explain their pole, their substitute's pole and an end-to-end incident diagnosis at the defense.

## Aya's deliverables (spec §5)

- `infrastructure/terraform/`, cloud-init, K3s, kubeconfig
- `deploy/secrets/*.enc.yaml` (SOPS + Age, documented key rotation)
- StorageClass + PVC for PostgreSQL/Redis, Traefik + TLS
- `scripts/backup-db.sh`, `scripts/restore-db.sh`, restore test on an empty database
- Cost report, `terraform destroy` procedure
- Demo: Act 1 (pilot: Terraform plan, K3s up, SOPS secrets decrypted in cluster) and Act 5 (pilot: pod self-healing, deliberate data deletion, restore proof)
- Cross-contributions: Terraform fmt/validate job in `ci.yml` (with Maryam); PVC disk-space Prometheus alert (with Maryam); `values-prod.yaml` (with Doha)

## Plan by week (Aya)

| Week | Work |
|---|---|
| 2 | Terraform (network, VM), cloud-init + K3s, kubeconfig export. Milestone: interface contract frozen, K3s and GHCR images available |
| 3 | SOPS + Age, PVC for PostgreSQL/Redis, Traefik + TLS |
| 4 | `backup-db.sh`, `restore-db.sh`, restore test, `terraform destroy`, cost report |
| 5 | Rehearse acts 1 and 5, final cost report |

If a deliverable is late at the mid-week milestone, the fallback in spec §5.2 applies without negotiation (local Kind/k3d cluster, local non-versioned dev secrets, `emptyDir` via `persistence.enabled=false`).

## Status (as of 2026-11-09)

Done: application (auth, tickets, assignment, dashboard, Celery notifications + SLA beat, Alertmanager webhook with deduplicated incidents), Compose stack, CI (tests, build, Gitleaks, Trivy), Helm chart for redis/worker/scheduler (never deployed), 48 passing tests.

In progress / written but unverified:
- `docs/interfaces.md` contract (PR `docs/interfaces-contract`, awaiting review)
- Terraform for Hetzner single node (`feat/terraform-k3s`): `fmt` and `validate` pass; `plan`/`apply` never run (no cloud account, student has no card)

Not started: SOPS + Age, Postgres/API/frontend in the chart, PVC, Traefik TLS, backup/restore scripts, Argo CD/Rollouts, monitoring, k6, frontend incidents UI.

## Decisions

- Free path first: local **k3d** cluster (K3s in Docker) until a cloud account exists. Possible free cloud later: Azure for Students (school email, no card). Only the Terraform provider file would change.
- Redis Service is named `redis` (contract), so one release per namespace.
- Image tags are the full commit SHA, no `latest`.
