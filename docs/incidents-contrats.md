# Contrat de gestion des incidents

## Objectif

Un incident représente une anomalie technique détectée par la supervision.
Il est créé à partir d'une alerte Prometheus transmise par Alertmanager.

Le système doit créer un incident, éviter les doublons lors des répétitions,
marquer l'incident comme rétabli lorsque l'alerte disparaît et permettre à un
technicien de confirmer sa clôture.

## Champs d'un incident

| Champ | Type | Obligatoire | Description |
|---|---|---:|---|
| id | UUID ou entier | Oui | Identifiant interne de l'incident |
| fingerprint | chaîne | Oui | Identifiant stable de l'alerte |
| service | chaîne | Oui | Service concerné |
| severity | chaîne | Oui | Niveau de gravité |
| alert_name | chaîne | Oui | Nom de l'alerte Prometheus |
| status | chaîne | Oui | État de l'incident |
| summary | chaîne | Oui | Résumé de l'anomalie |
| grafana_url | chaîne ou null | Non | Lien vers le dashboard Grafana |
| detected_at | date/heure UTC | Oui | Date de détection |
| recovered_at | date/heure UTC ou null | Non | Date de récupération |
| closed_at | date/heure UTC ou null | Non | Date de clôture confirmée |
| created_at | date/heure UTC | Oui | Date de création |
| updated_at | date/heure UTC | Oui | Date de dernière modification |

Toutes les dates sont stockées et échangées en UTC au format ISO 8601.

## Statuts

| Statut | Signification |
|---|---|
| active | L'alerte est toujours déclenchée |
| recovered | Alertmanager indique que l'alerte est résolue |
| closed | Un technicien a confirmé la clôture |

## Transitions autorisées

- active → recovered
- recovered → closed
- active → closed uniquement si l'équipe le valide
- closed ne revient jamais à active
- une nouvelle alerte après closed crée un nouvel incident

## Déduplication

La fingerprint identifie une occurrence logique d'alerte.

Pour une alerte `firing` :

1. rechercher un incident avec la même fingerprint ;
2. limiter la recherche aux incidents `active` ;
3. si aucun incident n'existe, créer un incident ;
4. si un incident existe, le mettre à jour ;
5. ne jamais créer un doublon actif pour la même fingerprint.

| Situation | Résultat |
|---|---|
| Première alerte firing | Création d'un incident active |
| Même alerte firing répétée | Mise à jour du même incident |
| Alerte resolved | Passage à recovered |
| Technicien confirme la clôture | Passage à closed |
| Nouvelle alerte après closed | Création d'un nouvel incident |

Même fingerprint + statut active = un seul incident.

## Règles de mise à jour

Lorsqu'une alerte `firing` répétée correspond à un incident `active` :

- conserver `id`, `fingerprint`, `detected_at` et `created_at` ;
- actualiser `updated_at` ;
- actualiser `summary`, `severity` et `grafana_url` si ces valeurs ont changé ;
- ne pas créer de nouvel incident.

Lorsqu'une alerte `resolved` correspond à un incident `active` :

- passer `status` à `recovered` ;
- renseigner `recovered_at` ;
- actualiser `updated_at` ;
- ne pas créer de nouvel incident.

Une alerte `resolved` sans incident `active` correspondant ne crée aucune
donnée métier. Le backend doit retourner une réponse explicite et journaliser
le cas sans exposer de données sensibles.

## Nouvelle occurrence après clôture

La recherche de déduplication porte toujours sur la combinaison suivante :

```text
fingerprint identique ET status = active
```

Un incident `recovered` ou `closed` n'est donc pas réutilisé. Une nouvelle
alerte `firing` avec la même fingerprint après clôture crée un nouvel incident
avec un nouvel identifiant et une nouvelle date de détection.

## Concurrence

La déduplication doit être garantie par PostgreSQL et pas uniquement par le
code applicatif. La migration devra ajouter une contrainte ou un index unique
conditionnel sur `fingerprint` pour les incidents `active`.

Cette protection empêche deux requêtes `firing` concurrentes avec la même
fingerprint de créer deux incidents actifs.

## Scénarios de test

| Scénario | Précondition | Événement | Résultat attendu |
|---|---|---|---|
| Première alerte | Aucun incident actif | `firing`, fingerprint `abc123` | Un incident `active` est créé |
| Alerte répétée | Incident `active` `abc123` | `firing`, fingerprint `abc123` | Le même incident est mis à jour |
| Récupération | Incident `active` `abc123` | `resolved`, fingerprint `abc123` | L'incident passe à `recovered` |
| Clôture | Incident `recovered` | Confirmation d'un technicien | L'incident passe à `closed` |
| Nouvelle occurrence | Incident `closed` `abc123` | `firing`, fingerprint `abc123` | Un nouvel incident `active` est créé |
| Résolution inconnue | Aucun incident `active` `abc123` | `resolved`, fingerprint `abc123` | Aucun incident n'est créé |
| Requêtes concurrentes | Aucun incident actif | Deux `firing` identiques simultanés | Un seul incident `active` existe |

## Exemple de séquence

| Heure | Événement | Résultat |
|---|---|---|
| 10:00 | `firing`, fingerprint `abc123` | Incident 1 créé |
| 10:05 | `firing`, fingerprint `abc123` | Incident 1 mis à jour |
| 10:10 | `resolved`, fingerprint `abc123` | Incident 1 devient `recovered` |
| 10:15 | Clôture par un technicien | Incident 1 devient `closed` |
| 11:00 | `firing`, fingerprint `abc123` | Incident 2 créé |

## Fingerprint

La fingerprint est la clé stable utilisée pour reconnaître les répétitions
d'une même alerte.

Alertmanager fournit normalement une fingerprint pour chaque alerte.
Le backend doit la conserver sans la modifier.

Une fingerprint vide ou absente doit être rejetée.

## Relation avec les tickets

Un incident technique pourra être associé à un ticket de support.

Cette relation sera finalisée lorsque le modèle Ticket et les migrations
communes seront validés par l'équipe.

La première version du contrat ne rend pas encore `ticket_id` obligatoire.


## Décisions à valider

- [ ] ORM utilisé : SQLAlchemy ou autre
- [ ] Outil de migration : Alembic ou autre
- [ ] Format de l'identifiant : UUID ou entier
- [ ] Relation exacte entre Incident et Ticket
- [ ] Valeurs autorisées pour severity
- [ ] Authentification du webhook
- [ ] Autorisation de la transition active → closed
- [ ] Format standard des erreurs API
- [ ] Pagination de la liste des incidents


## Contrat du payload Alertmanager

Alertmanager envoie une requête HTTP POST au backend SupportOps.

Endpoint prévu :

```text
POST /webhooks/alertmanager
```

## Exemple d'alerte reçue

```json
{
  "version": "4",
  "groupKey": "{}:{alertname=\"HighErrorRate\"}",
  "truncatedAlerts": 0,
  "status": "firing",
  "receiver": "supportops-webhook",
  "groupLabels": {
    "alertname": "HighErrorRate"
  },
  "commonLabels": {
    "alertname": "HighErrorRate",
    "service": "backend",
    "severity": "critical"
  },
  "commonAnnotations": {
    "summary": "Le taux d'erreur du backend est élevé"
  },
  "externalURL": "http://alertmanager:9093",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "HighErrorRate",
        "service": "backend",
        "severity": "critical"
      },
      "annotations": {
        "summary": "Le taux d'erreur du backend est élevé",
        "grafana_url": "https://grafana.example.com/d/backend"
      },
      "startsAt": "2026-10-25T17:00:00Z",
      "endsAt": "0001-01-01T00:00:00Z",
      "generatorURL": "http://prometheus:9090/graph",
      "fingerprint": "abc123"
    }
  ]
}
```
## Validation

Le backend doit refuser le payload si :

- `alerts` est absent ;
- `alerts` est vide ;
- une alerte n'a pas de `status` ;
- une alerte n'a pas de `fingerprint` ;
- `labels.alertname` est absent ;
- `labels.service` est absent ;
- `labels.severity` est absent ;
- `annotations.summary` est absent ;
- `startsAt` est invalide ;
- le statut n'est pas `firing` ou `resolved`.

Le backend doit répondre avec une erreur explicite et ne doit pas
créer d'incident à partir d'un payload invalide.

## Traitement des alertes

### Alerte `firing`

Pour chaque alerte `firing` :

1. lire la fingerprint ;
2. rechercher un incident actif avec cette fingerprint ;
3. créer un incident s'il n'existe pas ;
4. mettre à jour l'incident existant sinon ;
5. déclencher la notification après l'enregistrement.

### Alerte `resolved`

Pour chaque alerte `resolved` :

1. lire la fingerprint ;
2. rechercher l'incident actif correspondant ;
3. le passer à `recovered` ;
4. renseigner `recovered_at` ;
5. ne pas créer de nouvel incident ;
6. déclencher la notification de récupération.

## Authentification du webhook

Le webhook doit être protégé par un secret partagé.

Le secret est fourni au backend par la variable d'environnement :

```text
ALERTMANAGER_WEBHOOK_SECRET
```

## Décisions à valider par l'équipe

- [ ] Endpoint final : `/webhooks/alertmanager`
- [ ] Réponse de succès : `202` ou `200`
- [ ] Nom exact de `grafana_url`
- [ ] Valeurs autorisées pour `severity`
- [ ] Secret dans `Authorization: Bearer`
- [ ] Utilisation directe de la fingerprint Alertmanager
- [ ] Gestion de plusieurs alertes dans un même payload
- [ ] Enregistrement des alertes inconnues ou rejet en erreur