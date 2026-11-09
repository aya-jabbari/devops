# Avancement : pôle Aya (Cloud, données et résilience)

Mis à jour le 9 novembre 2026. Référence : cahier des charges v2.1 (§5, §6, §7).

Légende : ✅ fait et vérifié · 🟡 écrit mais pas complètement vérifié ou pas encore fusionné · ⬜ pas commencé

## Principe de travail

Rien ne dépend d'une autre personne. Tant qu'il n'y a pas de compte cloud, tout avance sur un cluster local
**k3d** (K3s dans Docker), conformément à l'alternative du §5.2. Les secrets sont appliqués avec
`scripts/secrets-apply.sh` (plan B du §5.2) tant que Doha n'a pas branché le déchiffrement dans Argo CD.

## Ce qui est fait

| Livrable (§5) | État | Où | Vérification |
|---|---|---|---|
| Contrat d'interface commun (§5.1) | 🟡 | `docs/interfaces.md`, branche `docs/interfaces-contract` | Poussé. Relecture de Doha et Maryam en attente. |
| Terraform : réseau, pare-feu minimal, IP fixe, VM Ubuntu, clé SSH | 🟡 | `infrastructure/terraform/`, branche `feat/terraform-k3s` | `terraform fmt` et `validate` OK. `plan` et `apply` jamais exécutés (pas de compte cloud). |
| cloud-init : installation de K3s sans intervention | 🟡 | `infrastructure/terraform/cloud-init.yaml` | Jamais exécuté sur une vraie VM |
| Export du kubeconfig | 🟡 | `scripts/get-kubeconfig.sh` | Jamais exécuté sur une vraie VM |
| Règle de pare-feu et sortie Terraform pour l'interface Argo CD | ✅ | `network.tf`, `outputs.tf` | Relu, validé |
| PVC PostgreSQL et paramètre `persistence.enabled` | ✅ | `deploy/helm/supportops/templates/postgres.yaml`, branche `feat/postgres-pvc` | Sur k3d : les données survivent à la suppression du pod |
| Mailpit dans le chart (nécessaire au worker) | ✅ | `templates/mailpit.yaml` | `helm lint` OK, déployé sur k3d |
| Sauvegarde PostgreSQL | ✅ | `scripts/backup-db.sh`, branche `feat/backup-restore` | Sur k3d : dump créé, dump vide refusé, pas de fichier partiel |
| Restauration sur base vierge | ✅ | `scripts/restore-db.sh` | Sur k3d : base supprimée puis restaurée, données retrouvées |
| SOPS + Age : règles, Secret chiffré, scripts, contrôle anti-clair | ✅ | `.sops.yaml`, `deploy/secrets/`, `scripts/secrets-*.sh`, branche `feat/sops-age` | Déchiffrement OK avec la bonne clé, refus avec une mauvaise, aucun secret en clair |
| Rotation de clé documentée | ✅ | `docs/secrets-sops-age.md` | Procédure écrite (pas encore rejouée) |
| Contexte pour les agents IA | ✅ | `CLAUDE.md`, `.agents/`, branche `docs/agents-context` | Poussé |
| Cluster local k3d + chart installé | ✅ | n/a | Redis, scheduler, worker, PostgreSQL, Mailpit en marche |

Branches **pas encore poussées** : `feat/backup-restore`, `feat/sops-age` (vérifier aussi `feat/terraform-k3s`).

## Ce qui reste à faire

### À faire maintenant (sur k3d, sans dépendance)

| # | Tâche | Critère de réussite (§7) |
|---|---|---|
| 1 | Pousser les branches et ouvrir les PR, relecture par une autre personne sous 24 h | Historique propre de PR relues |
| 2 | Appliquer le Secret chiffré sur k3d (`scripts/secrets-apply.sh`), recréer le volume PostgreSQL, vérifier que les pods le lisent | « Secrets SOPS déchiffrés dans le cluster » |
| 3 | Traefik et TLS : certificat auto-signé, test avec un Ingress de démonstration | Accès HTTPS fonctionnel |
| 4 | PVC pour Redis et StorageClass explicite | PVC pour PostgreSQL **et** Redis (§3.2) |
| 5 | Rapport du test de restauration dans `docs/` (date, comptes de lignes, durée) | « Restauration de données » |
| 6 | README Terraform (usage, `destroy`), en remplacement de `docs/passation-terraform-cloud.md` qui est obsolète | Procédure `terraform destroy` consignée |
| 7 | Scénario d'acte 5 scripté : suppression de pod, suppression de données, restauration | Acte 5 répétable |

### Contributions croisées (§5.3), avec le binôme

| # | Tâche | Avec |
|---|---|---|
| 8 | Job CI Terraform (`fmt`, `validate`) dans `ci.yml` | Maryam |
| 9 | Alerte Prometheus sur l'espace disque des PVC (`monitoring/`) | Maryam |
| 10 | `values-prod.yaml` pour l'infrastructure réelle | Doha |

### Dépend d'un compte cloud (décision à prendre avant la semaine 4)

| # | Tâche | Critère de réussite |
|---|---|---|
| 11 | `terraform plan`, `apply`, `kubectl get nodes` prêt, puis `destroy` | « Provisioning reproductible » |
| 12 | Rapport de coûts réels | « Maîtrise des coûts » |
| 13 | Acte 1 de la démonstration (plan Terraform, K3s, secrets déchiffrés) | Acte 1 |

Pistes gratuites : Azure for Students (e-mail de l'école, sans carte), un compte partagé avec l'équipe, ou les
crédits étudiants GitHub. Seul le fichier fournisseur Terraform changerait.

### Semaine 5

- Répétition des actes 1 et 5, rapport de coûts final.
- Être capable de reproduire et présenter le pôle de Doha (suppléante) et d'expliquer un incident de bout en bout.

## Écarts assumés par rapport au cahier des charges

- PostgreSQL 17 et Redis 8 au lieu de 16 et 7 : déjà utilisés dans Compose et le chart (voir `docs/interfaces.md` §7).
- Fournisseur cloud : Hetzner dans le code Terraform, faute d'indication du cahier des charges. À remplacer si un autre compte est obtenu.

## Risques connus

- Aucun code Terraform n'a été exécuté contre un vrai fournisseur : `server_type` et `k3s_version` sont à vérifier au premier `apply`.
- Premier démarrage de PostgreSQL : un pod supprimé pendant l'initialisation laisse un volume à moitié initialisé (rencontré en test). À ne pas faire pendant la démonstration.
- La clé privée Age n'existe que sur le poste d'Aya : en faire une sauvegarde hors du dépôt, et ajouter les clés publiques de Doha et Maryam dans `.sops.yaml`.
