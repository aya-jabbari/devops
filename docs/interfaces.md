# Contrat d'interface SupportOps

Ce contrat est la référence commune pour le développement local et le déploiement
Kubernetes. Toute modification doit être discutée par l'équipe avant d'être
appliquée dans un composant.

## Kubernetes

- Namespace : `supportops`
- Services : `api`, `frontend`, `worker`, `scheduler`, `postgres`, `redis`, `mailpit`
- API : port `8000`
- Frontend : port `80`
- Redis : port `6379`
- PostgreSQL : port `5432`
- Mailpit SMTP : port `1025`
- Mailpit UI : port `8025`
- Secret applicatif : `supportops-secrets`

Les variables sensibles (`DATABASE_URL`, `SECRET_KEY` et
`ALERTMANAGER_WEBHOOK_SECRET`) sont fournies par `supportops-secrets`. Elles ne
doivent jamais être ajoutées aux valeurs Helm ou au dépôt en clair.

## Images

Les images publiées utilisent le format suivant :

```text
ghcr.io/<organisation>/supportops-<composant>:<sha>
```

Les composants publiés sont `backend` et `frontend`. Le SHA est le SHA complet
du commit construit par la CI.

## Métriques API

L'API expose Prometheus sur `GET /metrics`.

| Métrique | Labels | Description |
|---|---|---|
| `http_requests_total` | `service`, `status` | Nombre de réponses HTTP par service et code |
| `http_request_duration_seconds` | `service` | Durée des requêtes HTTP en secondes |

Le service API utilise toujours le label `service="api"`.

Requête PromQL de référence du taux d'erreurs 5xx :

```promql
sum(rate(http_requests_total{service="api",status=~"5.."}[2m]))
/
sum(rate(http_requests_total{service="api"}[2m]))
```

## Vérification locale

```bash
curl http://localhost:8000/metrics
```

Le template Helm `ServiceMonitor` utilise le port `http` et le chemin
`/metrics`. Il est activé uniquement lorsque Prometheus Operator est disponible.
