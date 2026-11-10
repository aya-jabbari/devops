# Avancement : pôle Maryam (CI/CD, observabilité et performance)

Mis à jour le 10 novembre 2026 (fin de la semaine 3). Référence : cahier des charges v2.1 (§2.4, §3.1, §4.1, §5, §6, §7).

Légende : ✅ fait et vérifié · 🟡 écrit mais en attente d'intégration finale · ⬜ prévu en semaine 4/5

---

## 1. Récapitulatif par semaine

### Semaine 1 : Gestion automatisée des incidents, Asynchrone Celery & Pytest (Validée)

| Livrable (§5 / §6) | État | Fichiers | Vérification |
|---|---|---|---|
| Webhook d'alerte Alertmanager (`POST /api/webhooks/alertmanager`) | ✅ | `backend/app/routers/incidents.py`, `backend/app/incident_service.py` | Authentification par jeton `Bearer` (`secrets.compare_digest`), code HTTP 401 si absent/invalide, HTTP 202 si traité. |
| Idempotence et déduplication stricte | ✅ | `backend/app/incident_service.py`, `backend/app/models.py` | Clé stable `fingerprint` : les répétitions d'une même alerte incrémentent `occurrences` sans créer de doublon. |
| Cycle de vie complet de l'incident (`active` → `recovered` → `closed`) | ✅ | `backend/app/incident_service.py`, `backend/app/routers/incidents.py` | Passage automatique à `recovered` sur réception de `resolved`, fermeture confirmée par un technicien/admin via `POST /api/incidents/{id}/close`. |
| Notification asynchrone Celery + Redis + Mailpit | ✅ | `backend/app/tasks.py`, `backend/app/celery_app.py` | Tâche `notify_incident` non bloquante avec retries bornés (`max_retries=3`, backoff exponentiel) et capture SMTP dans Mailpit. |
| Suite de tests unitaires et fonctionnels Pytest | ✅ | `tests/test_incident_webhook.py`, `tests/test_incidents_api.py`, `tests/test_incident_schemas.py` | Tous les scénarios nominaux, d'erreur (401/403) et d'idempotence passent au vert. |

---

### Semaine 2 : Pipeline CI/CD, GHCR, Instrumentation API & Prometheus local (Validée)

| Livrable (§5 / §6) | État | Fichiers | Vérification |
|---|---|---|---|
| Contrat d'interface commun (§5.1) | ✅ | `docs/interfaces.md` | Noms des métriques, étiquettes (`service="api"`, `status`), endpoint `/metrics` et requête PromQL 5xx figés et nettoyés. |
| Instrumentation Prometheus de l'API FastAPI | ✅ | `backend/app/main.py` | Exposition de `/metrics`, compteur `http_requests_total{service,status}` et histogramme `http_request_duration_seconds{service}` validés en conteneur (`HTTP 200`). |
| Pipeline d'intégration continue (`ci.yml`) | ✅ | `.github/workflows/ci.yml` | Exécution automatisée sur PR et push `main` : syntaxe Python, lint `ruff`, `pytest`, build frontend Node 22. |
| Construction et publication des images sur GHCR | ✅ | `.github/workflows/ci.yml` (job `images`) | Build et push de `ghcr.io/<owner>/supportops-backend:<sha>` et `supportops-frontend:<sha>` sur fusion dans `main`. |
| Stack Prometheus sur cluster local | ✅ | Cluster local Minikube (namespace `monitoring`) | Déploiement de `kube-prometheus-stack` via Helm ; pods `prometheus-operator`, `prometheus-0`, `kube-state-metrics` et `node-exporter` opérationnels. |
| Job CI de validation Terraform (§5.3, binôme avec Aya) | ✅ | `.github/workflows/ci.yml` (job `terraform`) | Exécution automatique de `terraform fmt -check`, `init -backend=false` et `validate`. |

---

### Semaine 3 : Alertmanager, Règles d'alerte, Dashboards Grafana & Contributions Helm (Validée)

| Livrable (§5 / §6) | État | Fichiers | Vérification |
|---|---|---|---|
| Règles d'alerte Prometheus (`alert_rules.yml`) | ✅ | `monitoring/alert_rules.yml` | Règles `HighErrorRate` (> 5 % de 5xx sur 2 min), `BackendServiceDown` (`up == 0`) et `HighLatency` (P95 > 500 ms) alignées sur le contrat PromQL. |
| Alerte espace disque des PVC (§5.3, binôme avec Aya) | ✅ | `monitoring/alert_rules.yml` | Groupe `supportops-storage` : `PersistentVolumeAlmostFull` (< 15 % libre) et `PersistentVolumeFillingUp` (prédiction linéaire à 24 h). |
| Configuration du routage Alertmanager | ✅ | `monitoring/alertmanager.yml` | Récepteur `supportops-webhook` configuré avec `send_resolved: true` et jeton Bearer vers `/api/webhooks/alertmanager`. |
| Intégration des contrôles de sécurité dans la CI | ✅ | `.github/workflows/ci.yml`, `.github/workflows/security.yml` | Scan de secrets **Gitleaks** (`fetch-depth: 0`), scan d'image **Trivy** (`CRITICAL,HIGH`, `exit-code: "1"`) et appel du workflow réutilisable `security.yml`. |
| Dashboard Grafana exporté en JSON (Golden Signals) | ✅ | `monitoring/dashboards/supportops-overview.json` | 7 panneaux (`uid: supportops-overview`) : Requêtes/s, Taux d'erreurs 5xx (seuils 2 % et 5 %), Latence P95/P50, CPU par pod, Mémoire par pod, Redémarrages de pods, Activité métier des tickets. |
| Template Helm `ServiceMonitor` (§5.3, binôme avec Doha) | ✅ | `deploy/helm/supportops/templates/servicemonitor.yaml`, `values.yaml` | Cible le service `api` sur `/metrics` (port `http`) dans le namespace `supportops` ; déployé et validé sur le cluster local. |
| Template Helm `CronJob` de sauvegarde (§5.3, binôme avec Doha) | ✅ | `deploy/helm/supportops/templates/backup-cronjob.yaml`, `values.yaml` | CronJob quotidien (`0 2 * * *`) exécutant `pg_dump -Fc` sur PVC dédié (`postgres-backups`) avec rétention glissante des 7 derniers dumps (`helm lint` OK). |
| Instrumentation des endpoints Tickets (§5.3, binôme avec Doha) | ✅ | `backend/app/routers/tickets.py` | Compteur `supportops_ticket_operations_total{operation}` sur création, changement de statut, assignation et ajout de commentaire. |

---

## 2. Commandes de vérification rapide (Semaines 1 à 3)

### A. Vérifier l'exposition des métriques FastAPI
```bash
curl -s http://localhost:8000/health
curl -s http://localhost:8000/metrics | grep -E "http_requests_total|http_request_duration_seconds|supportops_ticket_operations_total"
```

### B. Valider le chart Helm (ServiceMonitor & CronJob de sauvegarde)
```bash
helm lint deploy/helm/supportops
helm template supportops deploy/helm/supportops --namespace supportops --set serviceMonitor.enabled=true --set backupCronJob.enabled=true
```

### C. Vérifier la stack Prometheus et le ServiceMonitor sur le cluster local
```bash
kubectl get pods -n monitoring
kubectl get servicemonitor -n supportops
kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090
```

---

## 3. Prochaines étapes (Semaines 4 et 5)

| Semaine | Tâche prévue | Livrable cible |
|---|---|---|
| **Semaine 4** | Scénario k6 nominal et scénario de stress canary | `load-tests/baseline.js`, `load-tests/canary-stress.js` |
| **Semaine 4** | Mesures sous charge et rédaction du rapport de performance | `docs/performance-rapport.md` |
| **Semaine 4** | Validation de la CI bloquante sur PR (test en échec / secret détecté) | Preuve de blocage PR pour l'Acte 3 |
| **Semaine 5** | Répétition de l'Acte 3 (pilote) et de l'Acte 4 (copilote avec Doha) | Démonstration finale |
