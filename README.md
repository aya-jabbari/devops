# SupportOps

Système de gestion des tickets de support, avec une chaîne DevSecOps complète :
Docker, Terraform, k3s, GitOps (Argo CD), déploiement progressif (Argo Rollouts) et observabilité.

## Équipe
- Doha : tickets
- Aya : affectation
- Maryam : incidents

## Stack
React · FastAPI · PostgreSQL · Celery/Redis · Docker Compose · Terraform · k3s · Helm · GitHub Actions · Argo CD · Prometheus/Grafana

## Organisation du dépôt
| Dossier | Rôle |
|---|---|
| `frontend/` | Interface React |
| `backend/` | API FastAPI et tâches Celery |
| `tests/` | Validations |
| `deploy/helm/` | Chart Helm |
| `deploy/environments/` | Valeurs par environnement |
| `infrastructure/terraform/` | Infrastructure cloud |
| `monitoring/` | Alertes et dashboards |
| `load-tests/` | Scénarios k6 |
| `scripts/` | Scripts d'exploitation |
| `docs/` | Documentation |
| `.github/workflows/` | CI |

## Conventions
- Aucun push direct sur `main` : tout passe par une Pull Request relue par une autre membre.
- Branches : `feat/...`, `fix/...`, `chore/...`, `docs/...`, `infra/...`
- Commits : [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `chore:`, `docs:`, `ci:`...)

## Démarrage local
_À venir (compose.yaml)._