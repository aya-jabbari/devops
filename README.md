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

- Si le backend est recréé, redémarrer aussi le frontend : `docker compose restart frontend`
  (sinon la connexion échoue avec « Request failed »).

## Périmètre de Doha

Doha pilote Kubernetes, le GitOps et le déploiement progressif : chart Helm,
Argo CD, Argo Rollouts, probes et ressources, ainsi que le lien Grafana du
tableau de bord. Le chart respecte le contrat de [`docs/interfaces.md`](docs/interfaces.md)
(namespace `supportops`, Services `api`, `frontend`, `worker`, `scheduler`,
`postgres`, `redis`, `mailpit`, Secret `supportops-secrets`).

### Chart Helm

`deploy/helm/supportops/` déploie l'API, le frontend, le worker, le scheduler
(Celery Beat, exactement 1 réplique), PostgreSQL, Redis, Mailpit, l'Ingress et,
en option, un `ServiceMonitor` et un `AnalysisTemplate`. Les valeurs propres à
chaque environnement sont dans `deploy/environments/` (`dev.yaml`, `prod.yaml`).

```bash
helm lint deploy/helm/supportops
helm template supportops deploy/helm/supportops -f deploy/environments/dev.yaml
```

### Laboratoire local (Kind)

Une seule commande crée le cluster, installe ingress-nginx, Argo CD,
Argo Rollouts, kube-prometheus-stack puis l'Application `supportops` :

```bash
APP_REVISION=<branche> scripts/dev-bootstrap-kind.sh
```

Après un redémarrage du PC : `docker start supportops-control-plane`, puis
`kind export kubeconfig --name supportops`, et relancer les `port-forward`.

### GitOps avec Argo CD

L'Application `supportops` (`deploy/argocd/application.yaml`) suit `main`, avec
synchronisation automatique, `prune`, `selfHeal` et 5 tentatives espacées.
Git est la source de vérité : un abandon de canary ne change que le cluster,
donc **le retour arrière se fait par un `git revert`**, pas par `kubectl`.

### Déploiement progressif (Argo Rollouts)

L'API est un `Rollout` en canary (20 % → pause 2 min → 50 % → pause 2 min). Une
analyse Prometheus tourne en tâche de fond dès la première étape : requête de
référence de `docs/interfaces.md` (fenêtre de 2 min), mesure toutes les 30 s,
abandon automatique si le taux de 5xx dépasse **2 %** (`failureLimit: 1`).

Pour la démonstration, la variable `FAULT_RATE` de l'API (nulle par défaut)
fait échouer une fraction des requêtes `/api/` : une « mauvaise version » est
donc un simple changement de valeurs dans Git. Jamais appliquée à `/healthz`,
`/readyz` ni `/metrics` (3 tests dédiés).

| Version | AnalysisRun | Mesures du taux de 5xx | Résultat |
|---|---|---|---|
| v6, sans panne | `api-5d7d64b7b6-5` | 8 × `0` | ✅ promue automatiquement |
| v6 + `FAULT_RATE=0.5` | `api-74bc97445d-6` | `0` → `0,0355` → `0,0575` | ✖ abandon automatique, version stable intacte |

Message du Rollout : `Metric "error-rate-5xx" assessed Failed due to failed (2) > failureLimit (1)`.

### Auto-guérison (testée sur Kind)

| Test | Action | Qui répare | Résultat |
|---|---|---|---|
| 1 | Suppression d'un pod de l'API | Kubernetes (ReplicaSet) | nouveau pod immédiat, prêt en ~20 s ; **40 requêtes sur 40 répondues** pendant l'incident |
| 2 | Worker mis à 0 réplique | Argo CD (`selfHeal`) | retour à `1/1` en quelques secondes, `Synced/Healthy` |
| 3 | Suppression du Deployment Mailpit | Argo CD (`selfHeal`) | recréé en ~1 s, pod prêt, `Synced/Healthy` |

### Probes et ressources

Tous les conteneurs ont `livenessProbe`, `readinessProbe` et `resources`.

| Charge | Liveness (délai / timeout) | Readiness (délai / timeout) | CPU demandé | Mémoire demandée / limite |
|---|---|---|---|---|
| api | 20 s / 1 s | 10 s / 1 s | 100m | 192Mi / 384Mi |
| frontend | 10 s / 1 s | 3 s / 1 s | 20m | 32Mi / 128Mi |
| worker | 30 s / 10 s | 15 s / 10 s | 100m | 192Mi / 384Mi |
| scheduler | 20 s / 1 s | 10 s / 1 s | 50m | 128Mi / 256Mi |
| postgres | 30 s / 1 s | 5 s / 1 s | 100m | 256Mi / 512Mi |
| redis | 10 s / 1 s | 3 s / 1 s | 50m | 64Mi / 192Mi |
| mailpit | 10 s / 1 s | 3 s / 1 s | 25m | 32Mi / 128Mi |

Les probes du worker passent par `sh -c`, car Kubernetes n'interprète pas
`$(POD_NAME)` dans une commande de probe. Le timeout de 10 s tient compte de la
lenteur de `celery inspect ping`.

Le frontend résout l'API au moment de la requête (et non au démarrage) : après un
redémarrage du nœud, nginx ne plante plus avec `host not found in upstream`
(18 redémarrages observés avant correction, 1 seul après : le redémarrage normal du nœud).

### Production (AWS, nœud K3s)

`deploy/environments/prod.yaml` fixe les images au SHA d'un commit de `main`
(jamais de `latest`) et `deploy/argocd/application-prod.yaml` suit `main` avec
`prune: false`, pour protéger le volume PostgreSQL. Le canary est désactivé en
production tant qu'Argo Rollouts et Prometheus ne sont pas installés sur la VM.
`application.yaml` et `application-prod.yaml` ne doivent pas être appliqués sur
le même cluster : ils ciblent le même namespace.

### Lien Grafana

Le tableau de bord de l'application affiche « Open in Grafana ↗ » vers
`http://localhost:3000/d/supportops-overview`, la même adresse que les alertes.
Elle se change au build avec `VITE_GRAFANA_URL` (chaîne vide = lien masqué).

## Tests

```bash
python -m pytest -q tests     # depuis la racine, avec backend/requirements-dev.txt installé
```

Dernière exécution complète : 48 tests réussis (tickets, affectation, notifications,
tableau de bord, incidents).

## Avancement (mis à jour le 8 novembre 2026)

Légende : ✅ fait · 🟡 partiel · ⬜ pas commencé

### Application

| Fonctionnalité | Responsable | État | Détail |
|---|---|---|---|
| Authentification et rôles (JWT, mots de passe hachés, comptes de démo) | Commun | ✅ | `/api/auth/login`, `/api/auth/me`, rôles vérifiés côté API |
| Tickets : création, liste, détail, modification, filtres, recherche | Doha | ✅ | Cycle ouvert → en cours → résolu → fermé, réouverture possible |
| Commentaires et historique des événements | Doha | ✅ | Historique des statuts et des affectations |
| Interface React : connexion, liste, détail, création | Doha | ✅ | `frontend/src/` |
| Affectation et réaffectation | Aya | ✅ | `POST /api/tickets/{id}/assign`, règles par rôle, historique, 10 tests dédiés |
| Tableau de bord (en retard, priorités, charge par technicien) | Aya | ✅ | `Dashboard.jsx` et route dashboard |
| Notifications Celery (affectation, commentaire, résolution, retard) | Aya | ✅ | Retries bornés, déduplication, mails visibles dans Mailpit |
| Contrôle périodique des échéances (Celery Beat) | Aya | ✅ | Une notification par ticket et par échéance |
| Webhook Alertmanager authentifié, incidents dédupliqués | Maryam | ✅ | Tests dédiés, voir `docs/incidents-contrats.md` |
| Liste et détail des incidents dans l'interface | Maryam | ⬜ | Aucun composant d'incidents dans `frontend/src/` à ce jour |

### Environnement local

| Élément | État | Détail |
|---|---|---|
| Docker Compose (Postgres, Redis, backend, frontend, worker, beat, Mailpit) | ✅ | Pile complète vérifiée, connexion OK sur le port 8080 |
| Image backend | ✅ | Python fixé en 3.12 (`python:3.12-slim`), lancement avec le Python du venv |
| Worker et Beat | ✅ | Démarrent et sont `healthy` dans Compose |

### Livraison, infrastructure et exploitation

| Chantier | État | Détail |
|---|---|---|
| CI GitHub Actions (tests, build image, Gitleaks, Trivy) | 🟡 | `ci.yml` présent. Pas de publication vers GHCR |
| Chart Helm : API, frontend, Redis, worker, scheduler, PostgreSQL, Mailpit, Ingress | ✅ | Déployé et vérifié sur Kind ; persistance et probes testées ; `helm template` OK avec `dev.yaml` et `prod.yaml` |
| Secrets chiffrés (SOPS + age) | ⬜ | Le chart attend un Secret `supportops-secrets` |
| Argo CD (GitOps, auto-sync, self-heal) | ✅ sur Kind · 🟡 sur AWS | Auto-guérison prouvée (tests 2 et 3) ; pas encore installé sur la VM AWS |
| Argo Rollouts (canary, abandon automatique) | ✅ sur Kind · 🟡 sur AWS | Promotion et abandon automatiques prouvés (voir section Doha) ; désactivé dans `prod.yaml` |
| Audit Trivy, doublon Gitleaks dans `ci.yml`, `.trivyignore` | 🟡 | À faire |
| Déchiffrement des secrets dans Argo CD (KSOPS) | 🟡 | Fichiers d'Aya à relire et appliquer ; clé Age de Doha à transmettre (clé publique seulement) |
| Terraform et cloud (réseau, VM, k3s) | ⬜ | Passation : `docs/passation-terraform-cloud.md` |
| Prometheus, Alertmanager, Grafana, règles d'alerte | ⬜ | `monitoring/` est vide |
| Tests de charge k6 | ⬜ | `load-tests/` est vide |
| Sauvegarde et restauration PostgreSQL | ⬜ | `scripts/` est vide |

### Points à surveiller
- Le chart Helm est vérifié uniquement par `helm lint` et `helm template`. Les probes de Celery n'ont pas été testées dans un cluster.
- L'image de base du backend est passée de Chainguard à `python:3.12-slim`. Le scan Trivy de la CI n'a pas été relancé avec cette image : à vérifier sur la PR. Le fichier `.trivyignore` mentionne encore Chainguard.
- `docs/passation-terraform-cloud.md` décrit un plan, pas un travail réalisé. Aucun fournisseur cloud n'est confirmé.

### Prochaines étapes
1. Relire et fusionner les PR en cours.
2. Secrets avec SOPS et age.
3. Manifestes Argo CD, à tester avec k3d en local.
4. Terraform : passation à Maryam.
5. Interface des incidents (Maryam).
