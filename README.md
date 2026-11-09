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

```bash
cp .env.example .env        # puis remplacer SECRET_KEY : openssl rand -hex 32
docker compose up -d --build
docker compose ps           # tous les services doivent être "healthy"
docker compose exec backend python -m app.seed
```

- Interface : http://localhost:8080 (comptes de démo : `admin` / `admin123`, `tech1` / `tech1123`, `user1` / `user1123`)
- API : http://localhost:8000/docs
- Mailpit (mails capturés) : http://localhost:8025
- Arrêt : `docker compose down` (garde les données) · `docker compose down -v` (supprime la base)

## Périmètre de Maryam

Maryam pilote les incidents, l'observabilité et la chaîne CI/CD. Son travail
permet de détecter les problèmes de l'API, de les transformer en incidents
SupportOps et de vérifier automatiquement la qualité des livraisons.

### Gestion automatisée des incidents

- Réception des alertes Prometheus via le webhook Alertmanager :
  `POST /api/webhooks/alertmanager`.
- Authentification du webhook par jeton configuré avec
  `ALERTMANAGER_WEBHOOK_SECRET`.
- Déduplication des alertes répétées grâce à leur `fingerprint`.
- Cycle de vie : `active` → `recovered` → `closed`.
- Notification asynchrone des nouveaux incidents avec Celery et Redis.
- Consultation et clôture des incidents dans l'API.

La documentation fonctionnelle est disponible dans
[`docs/incidents-maryam.md`](docs/incidents-maryam.md) et le contrat détaillé
dans [`docs/incidents-contrats.md`](docs/incidents-contrats.md).

### Observabilité et métriques

L'API expose les métriques Prometheus sur :

```text
GET /metrics
```

Les métriques principales sont :

- `http_requests_total{service,status}` : nombre de réponses HTTP ;
- `http_request_duration_seconds{service}` : durée des requêtes.

Les règles d'alerte sont définies dans
[`monitoring/alert_rules.yml`](monitoring/alert_rules.yml), et Alertmanager
transmet les alertes au backend dans
[`monitoring/alertmanager.yml`](monitoring/alertmanager.yml).

Le contrat partagé des ports, services, secrets, images et requêtes PromQL
est documenté dans [`docs/interfaces.md`](docs/interfaces.md).

### CI/CD et sécurité

Le workflow [`ci.yml`](.github/workflows/ci.yml) exécute automatiquement :

1. les tests Pytest et la compilation Python ;
2. le lint Ruff ;
3. le build du frontend ;
4. le build des images backend et frontend ;
5. la publication des images sur GHCR avec le SHA du commit sur `main` ;
6. les scans Gitleaks et Trivy.

Le workflow de sécurité réutilisable est disponible dans
[`security.yml`](.github/workflows/security.yml). Un échec de test ou un scan
critique bloque la validation de la Pull Request.

Les images suivent ce format :

```text
ghcr.io/<organisation>/supportops-<composant>:<sha>
```

### Helm et validation

Le chart Helm contient un template `ServiceMonitor` désactivé par défaut.
Pour l'activer avec Prometheus Operator :

```powershell
helm lint deploy\helm\supportops
helm template supportops deploy\helm\supportops `
  --set serviceMonitor.enabled=true
```

Les tests backend et le lint peuvent être lancés localement avec :

```powershell
python -m pytest -q
cd backend
python -m ruff check app tests
```
