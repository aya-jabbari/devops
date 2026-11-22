# Rapport de performance k6 — SupportOps

Date : 22 novembre 2026 (Semaine 4).  
Auteur : Maryam (pôle CI/CD, observabilité et performance).  
Environnement testé : Docker Compose local (`supportops-backend-1`, 1 worker Uvicorn, PostgreSQL 17, Redis 8), via `grafana/k6:latest`.

---

## 1. Scénarios exécutés

| Scénario | Fichier | Profil de charge | Seuils (`thresholds`) |
|---|---|---|---|
| **Nominal (`baseline`)** | `load-tests/baseline.js` | 0 → 5 VUs (15 s) → 10 VUs (30 s) → 0 (15 s) ; `GET /healthz`, `GET /api/tickets`, `POST /api/tickets` | `http_req_failed < 1 %`, `p(95) < 500 ms` |
| **Stress canary (`canary-stress`)** | `load-tests/canary-stress.js` | 20 VUs constants (90 s) ; `GET /readyz`, `GET /api/tickets` | `http_req_failed < 2 %` (seuil d'abandon canary), `p(95) < 500 ms` |

---

## 2. Résultats mesurés

### A. Scénario nominal (`baseline.js`)

- **Durée d'exécution** : `55.5 s` — `281` itérations complètes (`0` interrompue), `5.06 itér/s`
- **Requêtes HTTP** : `844` requêtes (`15.21 req/s`)
- **Checks fonctionnels** : `100.00 %` (`845 / 845` réussis)
- **Taux d'erreurs (`http_req_failed`)** : **`0.00 %`** (`0 / 844`) — ✅ seuil `< 1 %` respecté
- **Latence (`http_req_duration`)** :
  - Moyenne : `60.6 ms`
  - Médiane : `34.24 ms`
  - P90 : `156.67 ms`
  - **P95** : **`208.05 ms`** — ✅ seuil `< 500 ms` respecté
  - Max : `758.91 ms`
- **Réseau** : `49 MB` reçus (`880 kB/s`), `221 kB` envoyés (`4.0 kB/s`)

### B. Scénario de stress canary (`canary-stress.js`)

- **Durée d'exécution** : `1m23.4s` — `1553` itérations complètes (`0` interrompue), `18.62 itér/s`
- **Requêtes HTTP** : `3107` requêtes (`37.25 req/s`)
- **Checks fonctionnels** : `100.00 %` (`3108 / 3108` réussis)
- **Taux d'erreurs (`http_req_failed`)** : **`0.00 %`** (`0 / 3107`) — ✅ seuil canary `< 2 %` respecté
- **Latence (`http_req_duration`)** :
  - Moyenne : `425 ms`
  - Médiane : `408.79 ms`
  - P90 : `658.59 ms`
  - **P95** : **`719.27 ms`** — ⚠️ dépasse le seuil cible de `500 ms`
  - Max : `1.15 s`
- **Réseau** : `183 MB` reçus (`2.2 MB/s`), `500 kB` envoyés (`6.0 kB/s`)

---

## 3. Analyse et recommandations

1. **Fiabilité sous charge** : même à `37.25 req/s` (`20 VUs`), l'API n'a renvoyé aucune erreur HTTP (`0.00 %`), ce qui valide la marge de sécurité par rapport au seuil d'abandon canary (`2 %` de 5xx).
2. **Saturation de latence à 20 VUs** : le passage de `p(95) = 208.05 ms` (10 VUs) à `p(95) = 719.27 ms` (20 VUs) s'explique par deux facteurs identifiés :
   - Le conteneur Compose exécute un **unique processus Uvicorn** (1 réplica).
   - `GET /api/tickets` retourne l'ensemble des tickets accumulés en base (`183 MB` reçus sur `3107` requêtes), augmentant le temps de sérialisation JSON.
3. **Actions recommandées** :
   - En Kubernetes / K3s, conserver plusieurs réplicas pour `api` (ex. `api.replicas: 5` en démo canary dans `deploy/environments/dev.yaml`).
   - Appliquer une pagination par défaut (`limit` / `offset`) sur `GET /api/tickets` pour borner la taille des réponses.

---

## 4. Prochaine étape (intégration cluster & incident provoqué)

- Rejouer `load-tests/canary-stress.js` contre le cluster Kubernetes cible lors de l'intégration avec Doha (`AnalysisTemplate` Argo Rollouts) afin de documenter les mesures **sous incident provoqué (erreurs 5xx > 2 %)** et le rollback automatique (Acte 4).
