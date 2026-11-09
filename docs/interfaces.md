# Contrat d'interface commun

Cahier des charges v2.1, §5.1. Figé le début de la semaine 2.
Tout changement passe par une PR qui modifie ce fichier et que les trois membres approuvent.

Objectif : chacune travaille en parallèle (Kind/Minikube, Compose, image mock) sans attendre les autres.

## 1. Kubernetes

| Élément | Valeur |
|---|---|
| Namespace | `supportops` |
| Nom de release Helm | `supportops` |
| Chart | `deploy/helm/supportops` |
| Valeurs par environnement | `deploy/environments/dev.yaml`, `deploy/environments/prod.yaml` |
| Valeurs de dev locales (non versionnées) | `values-dev.yaml` |

### Services

Les Services portent exactement ces noms (sans préfixe de release) pour que les URL soient identiques
en Compose et dans le cluster.

| Service | Port | Rôle | Statut dans le chart |
|---|---|---|---|
| `api` | 8000 | FastAPI | à faire (Doha) |
| `frontend` | 80 | nginx + SPA React | à faire (Doha) |
| `worker` | aucun | Celery worker | fait (Deployment) |
| `scheduler` | aucun | Celery Beat, **1 seul réplica** | fait (Deployment) |
| `postgres` | 5432 | PostgreSQL | à faire (Aya : PVC, Doha : template) |
| `redis` | 6379 | broker Celery | fait (Service nommé `redis`) |
| `mailpit` | SMTP 1025, UI 8025 | capture des e-mails | à faire |

> Le Service Redis est nommé `redis` (sans préfixe de release), donc une seule release par namespace.
> Le frontend nginx proxifie `/api/` vers `http://backend:8000` en Compose : dans Kubernetes ce sera `http://api:8000`.

## 2. Secrets et variables d'environnement

### Secret `supportops-secrets` (jamais en clair dans Git, SOPS + Age)

| Clé | Utilisée par | Remarque |
|---|---|---|
| `DATABASE_URL` | api, worker, scheduler | `postgresql+psycopg://<user>:<pwd>@postgres:5432/<db>` |
| `SECRET_KEY` | api | signature des JWT |
| `ALERTMANAGER_WEBHOOK_SECRET` | api, Alertmanager | jeton Bearer du webhook |
| `POSTGRES_USER` | postgres | |
| `POSTGRES_PASSWORD` | postgres | |
| `POSTGRES_DB` | postgres | |

Fichier chiffré : `deploy/secrets/supportops-secrets.enc.yaml`.
Tant qu'il n'est pas disponible : un `values-dev.yaml` généré localement, **non versionné** (déjà couvert par `.gitignore` via `*.env`, à compléter pour `values-dev.yaml`).

### Variables non secrètes (ConfigMap / `config:` du chart)

| Variable | Valeur par défaut |
|---|---|
| `REDIS_URL` | `redis://redis:6379/0` |
| `SMTP_HOST` | `mailpit` |
| `SMTP_PORT` | `1025` |
| `OVERDUE_CHECK_SECONDS` | `300` |
| `NOTIFICATION_MAX_RETRIES` | `3` |

## 3. Persistance

- Le chart expose `persistence.enabled` (défaut `true`) et `persistence.size` pour `postgres` (et `redis` si besoin).
- `persistence.enabled=false` : volume `emptyDir`, pour Kind/tests sans StorageClass.
- Image PostgreSQL : `postgres:17-alpine` (décision §7, écart assumé par rapport au 16 du cahier des charges).

## 4. Points d'entrée HTTP de l'API

| Chemin | Usage |
|---|---|
| `GET /healthz` | liveness |
| `GET /readyz` | readiness (vérifie la base) |
| `POST /api/auth/login` | connexion JWT |
| `POST /api/webhooks/alertmanager` | webhook, en-tête `Authorization: Bearer <ALERTMANAGER_WEBHOOK_SECRET>` |
| `GET /api/incidents` | incidents |
| `GET /metrics` | métriques Prometheus |

## 5. Métriques exposées par l'API (Maryam)

| Métrique | Type | Étiquettes |
|---|---|---|
| `http_requests_total` | compteur | `service` (valeur `api`), `status` (code HTTP, ex. `200`, `500`) |
| `http_request_duration_seconds` | histogramme | `service` |

> Implémentées dans `backend/app/main.py`.

### Requête PromQL de référence : taux d'erreurs 5xx

Utilisée **telle quelle** par l'AnalysisTemplate (Doha) et par les alertes (Maryam).

```promql
sum(rate(http_requests_total{service="api",status=~"5.."}[2m]))
/
sum(rate(http_requests_total{service="api"}[2m]))
```

Seuil d'abandon du canary : **0,02 (2 %)**.

## 6. Images

Format : `ghcr.io/<organisation>/supportops-<composant>:<sha>`

| Composant | Image |
|---|---|
| backend (api, worker, scheduler) | `ghcr.io/<organisation>/supportops-backend:<sha>` |
| frontend | `ghcr.io/<organisation>/supportops-frontend:<sha>` |

- `<sha>` = SHA complet du commit sur `main`. Pas de tag `latest` déployé.
- `<organisation>` : `aya-jabbari` à ce jour (valeur actuelle de `values.yaml`), **à confirmer**.
- Le même SHA relie commit, image GHCR et version affichée dans Argo CD.
- En attendant le pipeline : build local puis `kind load docker-image` (ou import K3s).

## 7. Décisions prises (à contester en revue de la PR)

| Sujet | Décision | Raison |
|---|---|---|
| Versions | PostgreSQL **17** et Redis **8**, comme Compose et le chart (le cahier des charges cite 16 et 7) | Déjà testées dans toute la pile. Redescendre en 16 casserait les volumes `pgdata` existants. Écart à mentionner dans la documentation d'architecture. |
| Service Redis | Nommé `redis` (corrigé dans `redis.yaml` et `REDIS_URL`) | Conforme au contrat, même URL qu'en Compose. |
| Organisation GHCR | `aya-jabbari` | Valeur actuelle de `values.yaml`. À changer ici et dans `values.yaml` si le dépôt passe sous une organisation. |
| Clés `POSTGRES_*` | Ajoutées à `supportops-secrets` | Le pod PostgreSQL en a besoin. |
| Métriques et `/metrics` | Maryam les maintient | Instrumentation active dans `backend/app/main.py`. |
| Fournisseur cloud, région | Choix d'Aya, à renseigner ici dès qu'il est fait | Ne bloque personne : les alternatives du §8 s'appliquent. |

## 8. Responsabilités de livraison

| Fournisseur | Livre | Alternative si retard (§5.2) |
|---|---|---|
| Aya | cluster K3s + kubeconfig | Kind/Minikube avec ce contrat |
| Aya | clé Age publique + secrets chiffrés | `values-dev.yaml` local non versionné |
| Aya | StorageClass et PVC | `emptyDir` via `persistence.enabled=false` |
| Doha | chart par environnement | manifests de base ou image mock aux mêmes noms |
| Doha | Application Argo CD + Rollout | `kubectl argo rollouts` en local |
| Doha | `security.yml` | scans locaux Gitleaks/Trivy |
| Maryam | images GHCR | build local + `kind load` |
| Maryam | métriques, règles, dashboards | requête PromQL de référence ou mock |
