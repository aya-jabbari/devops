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

## Limites connues

- Jeu de données de démonstration (quelques lignes) : la durée de 4 s ne se généralise pas à une grosse base.
- Test sur k3d, pas sur la VM cloud (aucun compte cloud à ce jour). À rejouer sur la VM pour l'acte 5 de la soutenance.
- Les tables `comments` et `incidents` étaient vides au moment du test : leur restauration n'est donc pas prouvée par les comptes.
- Les sauvegardes restent sur le poste (`backups/`, ignoré par Git). Une copie hors machine reste à prévoir.

## Rejouer

```bash
scripts/demo-acte5.sh          # sauvegarde d'abord, puis détruit et restaure
```
