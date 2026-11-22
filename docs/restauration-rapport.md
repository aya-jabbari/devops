# Rapport de test : persistance et restauration PostgreSQL

Test réalisé le 9 novembre 2026 sur le cluster local **k3d** (K3s v1, StorageClass `local-path`), avec
`scripts/demo-acte5.sh`. Critères du cahier des charges (§7) : « Persistance PVC » et « Restauration de données ».

## Persistance (PVC)

| Volume | Taille | Résultat |
|---|---|---|
| `postgres-data` | 5 Gi | Les données survivent à la suppression du pod (testé lors du chantier PVC) |
| `redis-data` | 1 Gi, AOF activé | Clé écrite, pod supprimé, clé relue à l'identique après recréation |

## Restauration sur base vierge (acte 5)

Scénario exécuté par `scripts/demo-acte5.sh` : état initial, sauvegarde, suppression d'un pod, destruction volontaire
des données, restauration, comparaison.

| Étape | Résultat |
|---|---|
| État initial | 5 utilisateurs, 4 tickets |
| Sauvegarde (`backup-db.sh`) | `backups/supportops-20261109T172708Z.dump`, 18 789 octets |
| Suppression du pod Redis | Recréé par Kubernetes en 7 s, données conservées (PVC) |
| Destruction volontaire | `TRUNCATE tickets CASCADE` : 0 ticket |
| Restauration (`restore-db.sh`) | Base supprimée, recréée, restaurée en **4 s** |
| État final | 5 utilisateurs, 4 tickets, 4 événements : **aucune perte** |

Le script sort en erreur si les comptes diffèrent avant et après.

## Rejeu sur AWS (22 novembre 2026)

Cluster réel : une instance EC2 `m7i-flex.large` en `eu-north-1`, K3s v1.30.5, StorageClass `local-path`, application
déployée par le chart avec `deploy/environments/prod.yaml` (images GHCR `9611e35`), Secret appliqué depuis SOPS.

### Persistance PostgreSQL (critère « Persistance PVC »)

| Étape | Résultat |
|---|---|
| Avant | 5 utilisateurs, 4 tickets, empreinte MD5 des titres `0d0daae3…` |
| Suppression du pod PostgreSQL | Nouveau pod prêt en **8 s**, même PVC `postgres-data` (10 Gi, `Bound`) |
| Après | 5 utilisateurs, 4 tickets, même empreinte : **données intactes** |

### Acte 5 (`scripts/demo-acte5.sh`)

| Étape | Résultat |
|---|---|
| Sauvegarde | `backups/supportops-20261122T125744Z.dump`, 23 076 octets |
| Suppression du pod Redis | Recréé par Kubernetes en **5 s** |
| Destruction volontaire | `TRUNCATE tickets CASCADE` (cascade sur incidents, comments, ticket_events, notifications) : 0 ticket |
| Restauration sur base vierge | Base supprimée, recréée et restaurée en **6 s** |
| État final | 5 utilisateurs, 4 tickets, 4 événements, 1 notification : **aucune perte** |
| Application après restauration | Connexion `user1` via Traefik OK, aucun pod redémarré |

## Limites connues

- Jeu de données de démonstration (quelques lignes) : la durée de 4 s ne se généralise pas à une grosse base.
- ~~Test sur k3d uniquement~~ : rejoué sur AWS le 22 novembre 2026 (voir plus haut).
- Les tables `comments` et `incidents` étaient vides lors des tests du 9 et du 22 novembre. Depuis, `demo-acte5.sh` crée d'abord
  des commentaires et un incident via la vraie API (`scripts/demo-data.py`), refuse de continuer si l'une de ces tables est vide,
  et compare les six tables (users, tickets, comments, incidents, ticket_events, notifications). **À rejouer** à la prochaine
  session sur AWS : seul `demo-data.py` a été vérifié, contre l'API lancée en local (commentaires et incidents bien créés).
- Les sauvegardes restent sur le poste (`backups/`, ignoré par Git). Une copie hors machine reste à prévoir.

## Rejouer

```bash
scripts/demo-acte5.sh          # sauvegarde d'abord, puis détruit et restaure
```
